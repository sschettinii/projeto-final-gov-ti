"""Simula o monitoramento do modelo oficial com as internações de 2026 como lote novo.

O lote são as internações de janeiro a julho de 2026, lidas dos mesmos arquivos
RDPR usados pelo preprocessing.py. O script não retreina nada: carrega o modelo
oficial, depois de conferir o hash da pasta da execução, e mede se os dados novos
chegaram completos, íntegros e parecidos com os antigos, e se o modelo continua
melhor que o baseline sazonal.

O desempenho é medido com as previsões como teriam sido emitidas: cada mês T é
previsto só com os arquivos processados até T-1, com os meses recentes corrigidos
pela curva de completude daquele momento (vintage.py). Assim a avaliação não usa
informação que ainda não existia quando a previsão seria feita.

Saída: results/monitoring_<última competência>/ com summary.json e tabelas CSV.
"""

from collections import Counter
from datetime import datetime, timezone
import json
from math import log
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from evaluation import REGISTRY, folder_hash, metrics
from preprocessing import GROUPS, build_features
from tuning import DATASET, FEATURES, RESULTS, TARGET, between, file_hash, macro_wape, predict
from vintage import count_per_file, issued_forecasts, month_index

OFFICIAL_RUN = RESULTS / "20261105T205507"
BATCH_START, BATCH_END = "2026-01", "2026-07"
LAST_FILE = "2026-07"  # last processing month available on the DATASUS server

COMPLETENESS_COHORTS = ("2023-01", "2024-12")  # admission months old enough to be complete
DRIFT_REFERENCE = ("2023-01", "2025-12")
TRAINING = ("2010-01", "2024-12")

# Limits: (attention, alert). For the p-value, lower is worse.
MIN_COMPLETENESS = 0.95
PSI_LIMITS = (0.10, 0.25)
KS_P_LIMITS = (0.05, 0.01)
MACRO_WAPE_LIMITS = (7.5, 10.0)
RELATIVE_BIAS_LIMITS = (5.0, 10.0)
EXTRAPOLATION_LIMITS = (1.0, 1.1)
RECONCILIATION_LIMITS = (0.5, 2.0)
PSI_BINS = 4

# Ratios without scale: raw counts grow with the long-term trend and would always look like drift.
DRIFT_RATIOS = {
    "razao_sazonal": ("aih_iniciais", "media_movel_12"),
    "crescimento_anual": ("aih_iniciais", "lag_12"),
    "razao_lag_1": ("lag_1", "media_movel_12"),
    "variacao_anual": ("variacao_anual", None),
}
# Second run of the 2026-07 cycle, after the leakage fix: the first one (monitoring_202607)
# evaluated forecasts rebuilt with the July files. Both folders are kept for the audit trail.
REVISION = "v2"
REPLACES = "monitoring_202607"
SCENARIOS = {
    "choque_respiratorias": ("respiratorias_selecionadas", "2026-03", BATCH_END, 1.3),
    "falha_carga_diabetes": ("diabetes", "2026-02", "2026-02", 0.0),
}


def level(value, limits, lower_is_worse=False):
    attention, alert = limits
    if value is None or np.isnan(value):
        return "alerta"
    if lower_is_worse:
        return "alerta" if value <= alert else "atencao" if value <= attention else "ok"
    return "alerta" if value >= alert else "atencao" if value >= attention else "ok"


def worst(levels):
    order = ["ok", "atencao", "alerta"]
    return max(levels, key=order.index, default="ok")


def completeness_curve(per_file):
    """Average share of a month's admissions already processed k months after admission."""
    cohorts = pd.period_range(*COMPLETENESS_COHORTS, freq="M").astype(str)
    shares = []
    for month in cohorts:
        processed = Counter()
        for file_month, counts in per_file:
            lag = month_index(file_month) - month_index(month)
            processed[lag] += sum(counts[month, group] for group in GROUPS)
        total = sum(processed.values())
        cumulative = pd.Series(processed).sort_index().cumsum() / total
        shares.append(cumulative.reindex(range(cumulative.index.max() + 1)).ffill())
    return pd.concat(shares, axis=1).fillna(1.0).mean(axis=1)


def psi(reference, current):
    cuts = np.quantile(reference, np.linspace(0, 1, PSI_BINS + 1)[1:-1])
    def shares(values):
        counts = np.bincount(np.searchsorted(cuts, values, side="left"), minlength=PSI_BINS)
        return (counts + 0.5) / (len(values) + 0.5 * PSI_BINS)  # smoothing for small samples
    ref, cur = shares(reference), shares(current)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def ratio(rows, numerator, denominator):
    values = rows[numerator] if denominator is None else rows[numerator] / rows[denominator]
    return values.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()


def drift(reference, current, training):
    # Compare with the same months of the year, so that seasonality does not look like drift.
    reference = reference[reference["mes_numero"].isin(current["mes_numero"])]
    table = []
    for name, (numerator, denominator) in DRIFT_RATIOS.items():
        ref, cur = ratio(reference, numerator, denominator), ratio(current, numerator, denominator)
        value, p_value = psi(ref, cur), float(ks_2samp(ref, cur).pvalue)
        table.append({"indicador": name, "media_referencia": ref.mean(), "media_atual": cur.mean(),
                      "psi": value, "ks_p_valor": p_value,
                      "nivel": worst([level(value, PSI_LIMITS), level(p_value, KS_P_LIMITS, True)])})
    for feature in ("lag_1", "media_movel_12"):
        largest = training.groupby("grupo_dcnt")[feature].max()
        ratios = current.groupby("grupo_dcnt")[feature].max() / largest
        table.append({"indicador": f"extrapolacao_{feature}", "media_referencia": 1.0,
                      "media_atual": ratios.max(), "psi": None, "ks_p_valor": None,
                      "nivel": level(ratios.max(), EXTRAPOLATION_LIMITS),
                      **{f"razao_{group}": value for group, value in ratios.items()}})
    return pd.DataFrame(table)


def performance(rows, issued):
    """Compare the forecasts issued one month ahead with the final value of each month."""
    issued = rows[["mes_internacao", "grupo_dcnt"]].merge(issued, on=["mes_internacao", "grupo_dcnt"], how="left")
    assert issued[["mlp", "baseline"]].notna().all(axis=None), "missing issued forecast"
    predictions = {method: pd.Series(issued[method].to_numpy(), index=rows.index) for method in ("mlp", "baseline")}
    table = []
    for method, predicted in predictions.items():
        table.append({"metodo": method, "grupo": "all", "macro_wape": macro_wape(rows, predicted),
                      **metrics(rows, predicted)})
        for group, group_rows in rows.groupby("grupo_dcnt"):
            values = metrics(group_rows, predicted[group_rows.index])
            values["vies_relativo"] = 100 * values["bias"] / group_rows[TARGET].mean()
            table.append({"metodo": method, "grupo": group, **values})
    table = pd.DataFrame(table)
    mlp, baseline = (table[(table["metodo"] == m) & (table["grupo"] == "all")].iloc[0] for m in ("mlp", "baseline"))
    groups = table[(table["metodo"] == "mlp") & (table["grupo"] != "all")]
    levels = {
        "macro_wape": level(mlp["macro_wape"], MACRO_WAPE_LIMITS),
        "mlp_contra_baseline": "alerta" if mlp["macro_wape"] > baseline["macro_wape"] else "ok",
        **{f"vies_{row.grupo}": level(abs(row.vies_relativo), RELATIVE_BIAS_LIMITS) for row in groups.itertuples()},
    }
    output = rows[["mes_internacao", "grupo_dcnt", TARGET]].assign(**predictions)
    return table, levels, output


def monitor(series, mature, reference, training, issued):
    rows = build_features(series, end=BATCH_END)
    batch = between(rows, BATCH_START, BATCH_END)
    evaluated = batch[batch["mes_internacao"].isin(mature)]
    zeros = [f"{row.mes_internacao}/{row.grupo_dcnt}" for row in batch[batch[TARGET] <= 0].itertuples()]
    quality = {"celulas_zeradas_ou_negativas": zeros, "features_ausentes": int(batch[FEATURES].isna().sum().sum()),
               "nivel": "alerta" if zeros or batch[FEATURES].isna().any(axis=None) else "ok"}
    drift_table = drift(reference, evaluated, training)
    performance_table, performance_levels, predictions = performance(evaluated, issued)
    levels = {"qualidade": quality["nivel"],
              **{f"drift_{row.indicador}": row.nivel for row in drift_table.itertuples()},
              **performance_levels}
    return {"rows": rows, "quality": quality, "drift": drift_table, "performance": performance_table,
            "predictions": predictions, "levels": levels, "overall": worst(levels.values())}


def operational_forecast(model, series, completeness):
    """Forecast the month after the last file, with the recent months as they arrive and corrected."""
    target = str(pd.Period(BATCH_END, freq="M") + 1)
    corrected = Counter({key: value / completeness.get(key[0], 1.0) for key, value in series.items()})
    forecasts = []
    for label, counts in (("sem_correcao", series), ("com_correcao", corrected)):
        rows = build_features(counts, end=target)
        forecast = predict(model, rows[rows["mes_internacao"] == target])
        forecasts.append(pd.Series(forecast.to_numpy(), index=rows.loc[forecast.index, "grupo_dcnt"], name=label))
    table = pd.concat(forecasts, axis=1)
    table["diferenca_percentual"] = 100 * (table["sem_correcao"] / table["com_correcao"] - 1)
    return target, table.reset_index()


def main():
    output = RESULTS / f"monitoring_{LAST_FILE.replace('-', '')}_{REVISION}"
    assert not output.exists(), f"{output} already exists"

    registry = pd.read_csv(REGISTRY).set_index("run")
    assert folder_hash(OFFICIAL_RUN) == registry.loc[OFFICIAL_RUN.name, "folder_sha256"], \
        "the official run folder changed; the model will not be loaded"
    model = joblib.load(OFFICIAL_RUN / "model.joblib")

    per_file = count_per_file(BATCH_END)
    series = sum((counts for _, counts in per_file), Counter())

    curve = completeness_curve(per_file)
    completeness = pd.DataFrame({"mes_internacao": pd.period_range(BATCH_START, BATCH_END, freq="M").astype(str)})
    completeness["meses_desde_internacao"] = [month_index(LAST_FILE) - month_index(m) for m in completeness["mes_internacao"]]
    completeness["completude_esperada"] = completeness["meses_desde_internacao"].map(curve).fillna(1.0)
    completeness["maduro"] = completeness["completude_esperada"] >= MIN_COMPLETENESS
    mature = completeness.loc[completeness["maduro"], "mes_internacao"].tolist()
    expected = dict(zip(completeness["mes_internacao"], completeness["completude_esperada"]))

    official = pd.read_parquet(DATASET)
    reference, training = between(official, *DRIFT_REFERENCE), between(official, *TRAINING)
    curves = {}
    issued = issued_forecasts(per_file, mature, model, curves=curves)
    results = {"real_2026": monitor(series, mature, reference, training, issued)}

    # Reconciliation: the new batch must not change the months the model was built on.
    rebuilt = between(results["real_2026"]["rows"], "2010-01", "2025-12").reset_index(drop=True)
    difference = 100 * (rebuilt[TARGET] - official[TARGET]).abs() / official[TARGET]
    reconciliation = {"combinacoes": len(rebuilt), "divergentes": int((difference > 0).sum()),
                      "maior_diferenca_percentual": float(difference.max()),
                      "nivel": level(float(difference.max()), RECONCILIATION_LIMITS)}

    for name, (group, start, end, factor) in SCENARIOS.items():
        def change(counts, group=group, start=start, end=end, factor=factor):
            return Counter({key: round(value * factor) if key[1] == group and start <= key[0] <= end else value
                            for key, value in counts.items()})
        scenario_issued = issued_forecasts(per_file, mature, model, transform=change, curves=curves)
        results[name] = monitor(change(series), mature, reference, training, scenario_issued)
    real_levels = results["real_2026"]["levels"]
    order = ["ok", "atencao", "alerta"]

    target, forecast = operational_forecast(model, series, expected)

    output.mkdir(parents=True)
    curve.rename("fracao_processada").rename_axis("meses_desde_internacao").to_csv(output / "completeness_curve.csv")
    completeness.to_csv(output / "completeness.csv", index=False)
    results["real_2026"]["drift"].to_csv(output / "drift.csv", index=False)
    results["real_2026"]["performance"].to_csv(output / "performance.csv", index=False)
    results["real_2026"]["predictions"].to_csv(output / "predictions.csv", index=False)
    forecast.to_csv(output / "forecast.csv", index=False)
    summary = {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_run": OFFICIAL_RUN.name,
        "official_folder_sha256": registry.loc[OFFICIAL_RUN.name, "folder_sha256"],
        "revision": REVISION,
        "replaces": REPLACES,
        "evaluation": "forecasts issued with files up to T-1, recent months corrected by the completeness curve",
        "dataset_sha256": file_hash(DATASET),
        "batch": {"start": BATCH_START, "end": BATCH_END, "last_file": LAST_FILE, "mature_months": mature},
        "machine": {"system": platform.platform(), "processor": platform.machine(), "python": platform.python_version()},
        "limits": {"min_completeness": MIN_COMPLETENESS, "psi": PSI_LIMITS, "ks_p": KS_P_LIMITS,
                   "macro_wape": MACRO_WAPE_LIMITS, "relative_bias": RELATIVE_BIAS_LIMITS,
                   "extrapolation": EXTRAPOLATION_LIMITS, "reconciliation": RECONCILIATION_LIMITS},
        "reconciliation": reconciliation,
        "operational_forecast_month": target,
        "scenarios": {
            name: {"overall": result["overall"], "quality": result["quality"], "levels": result["levels"],
                   "worse_than_real": [key for key, value in result["levels"].items()
                                       if order.index(value) > order.index(real_levels[key])]}
            for name, result in results.items()
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    print(completeness.round(3).to_string(index=False))
    print(results["real_2026"]["drift"].round(3).to_string(index=False))
    print(results["real_2026"]["performance"].round(2).to_string(index=False))
    print(forecast.round(1).to_string(index=False))
    print(json.dumps({k: v for k, v in summary.items() if k in ("reconciliation", "scenarios")}, indent=1, ensure_ascii=False))
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
