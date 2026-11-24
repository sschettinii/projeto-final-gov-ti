"""Transforma os arquivos brutos de internações na base mensal usada pelos modelos.

Só são salvas as contagens mensais do estado. Nenhum registro individual de
internação sai deste script.
"""

from collections import Counter
from math import cos, pi, sin
from pathlib import Path
import tempfile

import datasus_dbc
from dbfread import DBF
from joblib import Parallel, delayed
import pandas as pd

RAW = Path("data/raw")
DATASET = Path("data/modelagem_dcnt_mensal_201001_202512.parquet")

CONTEXT_START = "2008-12"  # used only to compute the features of the first target
TARGET_START = "2010-01"
END = "2025-12"

# First and last ICD-10 category of each chronic disease group.
GROUPS = {
    "circulatorias": ("I00", "I99"),
    "diabetes": ("E10", "E14"),
    "neoplasias_malignas": ("C00", "C97"),
    "respiratorias_selecionadas": ("J30", "J98"),
}
EXCLUDED_CATEGORIES = {"J36"}

LAGS = [1, 2, 3, 6, 12]
MOVING_AVERAGES = [3, 6, 12]


def disease_group(icd_code):
    category = icd_code[:3]
    if category in EXCLUDED_CATEGORIES:
        return None
    for group, (first, last) in GROUPS.items():
        if first <= category <= last:
            return group
    return None


def count_admissions(path, end=END):
    """Count initial admissions per month and group in one raw file."""
    counts = Counter()
    with tempfile.TemporaryDirectory() as folder:
        dbf = Path(folder) / "file.dbf"
        datasus_dbc.decompress(str(path), str(dbf))
        for row in DBF(dbf, load=False, encoding="latin1", char_decode_errors="ignore"):
            admission = str(row["DT_INTER"]).strip()
            month = f"{admission[:4]}-{admission[4:6]}"
            group = disease_group(str(row["DIAG_PRINC"]).strip())
            is_initial = str(row["IDENT"]).strip() == "1"  # 5 means a long-stay continuation
            if is_initial and group and CONTEXT_START <= month <= end:
                counts[month, group] += 1
    return counts


def build_features(counts, end=END):
    """Create one row per month and group, using only earlier months as history."""
    months = pd.period_range(CONTEXT_START, end, freq="M").astype(str)
    month_numbers = [int(month[5:]) for month in months]
    frames = []
    for group in GROUPS:
        series = pd.Series([counts[month, group] for month in months])
        frame = pd.DataFrame({
            "mes_internacao": months,
            "grupo_dcnt": group,
            "aih_iniciais": series,
            "mes_numero": month_numbers,
            "mes_seno": [sin(2 * pi * number / 12) for number in month_numbers],
            "mes_cosseno": [cos(2 * pi * number / 12) for number in month_numbers],
            "indice_temporal": range(len(months)),
        })
        for lag in LAGS:
            frame[f"lag_{lag}"] = series.shift(lag)
        for window in MOVING_AVERAGES:
            frame[f"media_movel_{window}"] = series.shift(1).rolling(window).mean()
        frame["variacao_anual"] = (series.shift(1) - series.shift(13)) / series.shift(13)
        frames.append(frame)

    dataset = pd.concat(frames)
    dataset = dataset[dataset["mes_internacao"] >= TARGET_START]
    dataset = dataset.sort_values(["mes_internacao", "grupo_dcnt"]).reset_index(drop=True)
    lag_columns = [f"lag_{lag}" for lag in LAGS]
    dataset[lag_columns] = dataset[lag_columns].astype(int)
    return dataset


if __name__ == "__main__":
    files = sorted(RAW.glob("RDPR*.dbc"))
    assert len(files) == 212, f"expected 212 raw files, found {len(files)}; run download.py"

    file_counts = Parallel(n_jobs=-1)(delayed(count_admissions)(path) for path in files)
    counts = sum(file_counts, Counter())
    assert sum(counts.values()) == 3_608_323

    dataset = build_features(counts)
    assert len(dataset) == 768 and dataset.notna().all(axis=None)
    assert dataset["aih_iniciais"].sum() == 3_396_090

    dataset.to_parquet(DATASET, index=False, compression="zstd")
    print(f"Saved {len(dataset)} rows to {DATASET}")
