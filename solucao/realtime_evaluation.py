"""Mede o erro do modelo oficial como ele seria em uso, sem vazamento de dados futuros.

O teste de 2025 do evaluation.py usou o dataset completo: para prever dezembro, o
modelo viu novembro já com todas as AIHs, mas no começo de dezembro só metade delas
teria chegado. Aqui cada mês T é previsto só com os arquivos processados até T-1,
como aconteceria em produção, e a previsão é comparada com o valor final do mês.

Compara três formas de montar as entradas, para o MLP e para o baseline:
  - dados_completos: como no teste original (otimista, usa informação futura);
  - sem_correcao: os meses recentes como chegaram;
  - com_correcao: os meses recentes divididos pela completude esperada naquele momento.

Períodos: o teste de 2025 e os meses maduros de 2026 do ciclo de monitoramento.
Não retreina nada: carrega o modelo oficial depois de conferir o hash da pasta.

Saída: results/realtime_<última competência>/ com summary.json e tabelas CSV.
"""

from datetime import datetime, timezone
import json
import platform

import joblib
import pandas as pd

from evaluation import REGISTRY, folder_hash, metrics
from monitoring import LAST_FILE, MIN_COMPLETENESS, OFFICIAL_RUN
from preprocessing import build_features
from tuning import RESULTS, TARGET, macro_wape, predict
from vintage import completeness_curve, count_per_file, expected_completeness, issued_forecasts, series_as_of

PERIODS = {"teste_2025": ("2025-01", "2025-12"), "monitoramento_2026": ("2026-01", LAST_FILE)}


def evaluate(predictions):
    table = []
    for (period, inputs), rows in predictions.groupby(["periodo", "entradas"], sort=False):
        rows = rows.reset_index(drop=True)
        for method in ("mlp", "baseline"):
            predicted = rows[method]
            table.append({"periodo": period, "entradas": inputs, "metodo": method, "grupo": "all",
                          "macro_wape": macro_wape(rows, predicted), **metrics(rows, predicted)})
            for group, group_rows in rows.groupby("grupo_dcnt"):
                values = metrics(group_rows, predicted[group_rows.index])
                values["vies_relativo"] = 100 * values["bias"] / group_rows[TARGET].mean()
                table.append({"periodo": period, "entradas": inputs, "metodo": method, "grupo": group, **values})
    return pd.DataFrame(table)


def main():
    output = RESULTS / f"realtime_{LAST_FILE.replace('-', '')}"
    assert not output.exists(), f"{output} already exists"

    registry = pd.read_csv(REGISTRY).set_index("run")
    assert folder_hash(OFFICIAL_RUN) == registry.loc[OFFICIAL_RUN.name, "folder_sha256"], \
        "the official run folder changed; the model will not be loaded"
    model = joblib.load(OFFICIAL_RUN / "model.joblib")

    per_file = count_per_file(LAST_FILE)
    final = build_features(series_as_of(per_file, LAST_FILE), end=LAST_FILE)

    # Only months whose final value is already known can be evaluated.
    curve_now = completeness_curve(per_file, LAST_FILE)
    months = [m for start, end in PERIODS.values() for m in pd.period_range(start, end, freq="M").astype(str)]
    share_now = expected_completeness(curve_now, months, LAST_FILE)
    mature = [m for m in months if share_now[m] >= MIN_COMPLETENESS]

    curves, frames = {}, []
    for period, (start, end) in PERIODS.items():
        targets = [m for m in mature if start <= m <= end]
        truth = final[final["mes_internacao"].isin(targets)][["mes_internacao", "grupo_dcnt", TARGET]]
        complete = final[final["mes_internacao"].isin(targets)]
        frames.append(truth.assign(periodo=period, entradas="dados_completos", ultima_competencia=LAST_FILE,
                                   mlp=predict(model, complete).to_numpy(),
                                   baseline=complete["lag_12"].astype(float).to_numpy()))
        for inputs, correct in (("sem_correcao", False), ("com_correcao", True)):
            issued = issued_forecasts(per_file, targets, model, correct=correct, curves=curves)
            frames.append(issued.merge(truth, on=["mes_internacao", "grupo_dcnt"]).assign(periodo=period, entradas=inputs))
    predictions = pd.concat(frames, ignore_index=True)[
        ["periodo", "entradas", "mes_internacao", "grupo_dcnt", "ultima_competencia", TARGET, "mlp", "baseline"]]
    table = evaluate(predictions)

    output.mkdir(parents=True)
    predictions.to_csv(output / "predictions.csv", index=False)
    table.to_csv(output / "metrics.csv", index=False)
    overall = table[table["grupo"] == "all"].set_index(["periodo", "entradas", "metodo"])["macro_wape"]
    summary = {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "official_run": OFFICIAL_RUN.name,
        "official_folder_sha256": registry.loc[OFFICIAL_RUN.name, "folder_sha256"],
        "last_file": LAST_FILE,
        "evaluated_months": {period: [m for m in mature if start <= m <= end] for period, (start, end) in PERIODS.items()},
        "rule": "forecast for month T uses only files processed up to T-1; truth is the final value",
        "machine": {"system": platform.platform(), "processor": platform.machine(), "python": platform.python_version()},
        "macro_wape": {f"{p}/{i}/{m}": round(v, 4) for (p, i, m), v in overall.items()},
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    print(table[table["grupo"] == "all"].round(2).to_string(index=False))
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
