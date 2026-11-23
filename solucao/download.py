"""Baixa do DATASUS os arquivos mensais de internações (SIH/SUS) do Paraná.

Arquivos já baixados são ignorados, então basta rodar o script de novo se um
download falhar.
"""

from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

FTP = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/"
RAW = Path("data/raw")

# Months in which the records were processed, not months of admission.
FIRST_FILE, LAST_FILE = "2008-12", "2026-07"


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for month in pd.period_range(FIRST_FILE, LAST_FILE, freq="M"):
        name = f"RDPR{month.strftime('%y%m')}.dbc"
        path = RAW / name
        if path.exists():
            continue
        print(f"Downloading {name}", flush=True)
        partial = path.with_suffix(".part")
        urlretrieve(FTP + name, partial)
        partial.rename(path)
