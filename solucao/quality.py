"""Mede a qualidade dos arquivos brutos usados pelo preprocessing.py.

Para cada arquivo mensal, conta quantos registros entram na base e por que os
demais ficam de fora. Só contagens são salvas; nenhum registro individual sai
deste script.

Saída: results/data_quality.csv (uma linha por arquivo).
"""

from collections import Counter
from datetime import date
from pathlib import Path
import tempfile

import datasus_dbc
from dbfread import DBF
from joblib import Parallel, delayed
import pandas as pd

from preprocessing import CONTEXT_START, END, EXCLUDED_CATEGORIES, GROUPS, RAW, disease_group

OUTPUT = Path("results/data_quality.csv")


def valid_date(text):
    if len(text) != 8 or not text.isdigit():
        return False
    try:
        date(int(text[:4]), int(text[4:6]), int(text[6:]))
        return True
    except ValueError:
        return False


def file_quality(path):
    counts = Counter()
    with tempfile.TemporaryDirectory() as folder:
        dbf = Path(folder) / "file.dbf"
        datasus_dbc.decompress(str(path), str(dbf))
        for row in DBF(dbf, load=False, encoding="latin1", char_decode_errors="ignore"):
            counts["registros"] += 1
            ident = str(row["IDENT"]).strip()
            admission = str(row["DT_INTER"]).strip()
            icd = str(row["DIAG_PRINC"]).strip()
            counts[f"ident_{ident if ident in ('1', '5') else 'outro'}"] += 1
            if not valid_date(admission):
                counts["data_internacao_invalida"] += 1
                continue
            month = f"{admission[:4]}-{admission[4:6]}"
            if not CONTEXT_START <= month <= END:
                counts["fora_do_periodo"] += 1
                continue
            if not icd:
                counts["cid_vazio"] += 1
                continue
            if icd[:3] in EXCLUDED_CATEGORIES:
                counts["cid_excluido_j36"] += 1
                continue
            group = disease_group(icd)
            if group is None:
                counts["cid_fora_dos_grupos"] += 1
                continue
            if ident != "1":
                counts["dcnt_continuidade"] += 1
                continue
            counts["selecionados"] += 1
            counts[f"grupo_{group}"] += 1
    return {"arquivo": path.name, "competencia": f"20{path.stem[4:6]}-{path.stem[6:8]}", **counts}


if __name__ == "__main__":
    files = sorted(RAW.glob("RDPR*.dbc"))
    assert len(files) == 212, f"expected 212 raw files, found {len(files)}; run download.py"

    rows = Parallel(n_jobs=-1)(delayed(file_quality)(path) for path in files)
    table = pd.DataFrame(rows).fillna(0)
    columns = ["arquivo", "competencia", "registros", "ident_1", "ident_5", "ident_outro",
               "data_internacao_invalida", "fora_do_periodo", "cid_vazio", "cid_excluido_j36",
               "cid_fora_dos_grupos", "dcnt_continuidade", "selecionados",
               *[f"grupo_{group}" for group in GROUPS]]
    table = table.reindex(columns=columns, fill_value=0)
    numeric = columns[2:]
    table[numeric] = table[numeric].astype(int)

    removed = ["data_internacao_invalida", "fora_do_periodo", "cid_vazio", "cid_excluido_j36",
               "cid_fora_dos_grupos", "dcnt_continuidade", "selecionados"]
    assert (table["registros"] == table[removed].sum(axis=1)).all(), "every record must have one outcome"
    assert table["selecionados"].sum() == 3_608_323, "must match preprocessing.py"

    table.to_csv(OUTPUT, index=False)
    totals = table[numeric].sum()
    print(totals.to_string())
    print(f"Saved {len(table)} rows to {OUTPUT}")
