"""Reconstrói os dados como eles estavam disponíveis em cada mês.

Cada arquivo RDPR traz as AIHs processadas numa competência, e uma internação pode
ser processada meses depois de acontecer. Por isso o valor de um mês muda com o
tempo: no próprio mês chega cerca de metade das AIHs. Usar o valor final, que só
se conhece meses depois, para prever ou avaliar é vazamento de dados.

Aqui ficam as funções que respondem "o que se sabia na competência F": a série
montada só com os arquivos até F, a curva de completude calculada só com meses que
já estavam completos em F e a correção dos meses recentes por essa curva.
"""

from collections import Counter

from joblib import Parallel, delayed
import pandas as pd

from preprocessing import RAW, count_admissions

PER_FILE = RAW.parent / "contagens_por_competencia.parquet"
EXPECTED_FILES = 212

# Cohorts used by the completeness curve, in months before the last available file:
# two years of admissions, each with at least twelve months of follow-up.
CURVE_COHORT_AGES = (35, 12)


def month_index(month):
    return int(month[:4]) * 12 + int(month[5:]) - 1


def shift(month, months):
    return str(pd.Period(month, freq="M") + months)


def file_month(path):
    return f"20{path.stem[4:6]}-{path.stem[6:8]}"


def count_per_file(end):
    """Monthly counts per processing month (file). Only aggregated counts are cached."""
    files = sorted(RAW.glob("RDPR*.dbc"))
    assert len(files) == EXPECTED_FILES, f"expected {EXPECTED_FILES} raw files, found {len(files)}; run download.py"
    if PER_FILE.exists():
        cached = pd.read_parquet(PER_FILE)
        if sorted(cached["competencia"].unique()) == [file_month(path) for path in files] \
                and cached["mes_internacao"].max() >= end:
            cached = cached[cached["mes_internacao"] <= end]
            return [(month, Counter({(row.mes_internacao, row.grupo_dcnt): row.aih_iniciais
                                     for row in rows.itertuples()}))
                    for month, rows in cached.groupby("competencia")]
    counts = Parallel(n_jobs=-1)(delayed(count_admissions)(path, end) for path in files)
    pd.DataFrame([{"competencia": file_month(path), "mes_internacao": month, "grupo_dcnt": group, "aih_iniciais": value}
                  for path, file_counts in zip(files, counts) for (month, group), value in file_counts.items()]
                 ).to_parquet(PER_FILE, index=False)
    return [(file_month(path), file_counts) for path, file_counts in zip(files, counts)]


def series_as_of(per_file, last_file):
    """Counts per admission month and group using only the files processed up to last_file."""
    return sum((counts for month, counts in per_file if month <= last_file), Counter())


def completeness_curve(per_file, last_file):
    """Average share of a month's admissions already processed k months after admission.

    Uses only files up to last_file and only cohorts that were already complete then.
    """
    oldest, newest = (shift(last_file, -age) for age in CURVE_COHORT_AGES)
    available = [(month, counts) for month, counts in per_file if month <= last_file]
    shares = []
    for cohort in pd.period_range(oldest, newest, freq="M").astype(str):
        processed = Counter()
        for month, counts in available:
            processed[month_index(month) - month_index(cohort)] += sum(
                value for (admission, _), value in counts.items() if admission == cohort)
        cumulative = pd.Series(processed).sort_index().cumsum() / sum(processed.values())
        shares.append(cumulative.reindex(range(cumulative.index.max() + 1)).ffill())
    return pd.concat(shares, axis=1).fillna(1.0).mean(axis=1)


def expected_completeness(curve, months, last_file):
    """Expected share already processed for each admission month, read from the curve."""
    return {month: float(curve.get(month_index(last_file) - month_index(month), 1.0)) for month in months}


def corrected(series, curve, last_file):
    """Divide each recent month by its expected completeness, estimating its final value."""
    months = {month for month, _ in series}
    share = expected_completeness(curve, months, last_file)
    return Counter({key: round(value / share[key[0]]) for key, value in series.items()})


def issued_forecasts(per_file, targets, model, correct=True, transform=None, curves=None):
    """Forecast each target month with only what was known one month before it.

    The forecast for month T uses the files processed up to T-1, with the recent months
    corrected by the completeness curve of that moment (or as they arrived, if correct is
    False). The baseline, the same month of the previous year, uses the same information.
    """
    from preprocessing import build_features
    from tuning import predict

    curves = {} if curves is None else curves
    frames = []
    for target in targets:
        last_file = shift(target, -1)
        series = series_as_of(per_file, last_file)
        if transform is not None:
            series = transform(series)
        if correct:
            if last_file not in curves:
                curves[last_file] = completeness_curve(per_file, last_file)
            series = corrected(series, curves[last_file], last_file)
        rows = build_features(series, end=target)
        rows = rows[rows["mes_internacao"] == target]
        frames.append(pd.DataFrame({"mes_internacao": target, "grupo_dcnt": rows["grupo_dcnt"].to_numpy(),
                                    "ultima_competencia": last_file,
                                    "mlp": predict(model, rows).to_numpy(),
                                    "baseline": rows["lag_12"].astype(float).to_numpy()}))
    return pd.concat(frames, ignore_index=True)
