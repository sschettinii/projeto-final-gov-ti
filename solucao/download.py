"""Baixa do DATASUS os arquivos mensais de internações (SIH/SUS) do Paraná.

Arquivos já baixados são ignorados, então basta rodar o script de novo se um
download falhar.
"""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

FTP = "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/"
RAW = Path("data/raw")
MANIFEST = Path("results/raw_manifest.csv")

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

    # Data version: size and SHA-256 of every raw file, so that a changed file is noticed.
    files = [RAW / f"RDPR{month.strftime('%y%m')}.dbc" for month in pd.period_range(FIRST_FILE, LAST_FILE, freq="M")]
    manifest = pd.DataFrame([
        {"arquivo": path.name, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()}
        for path in files
    ])
    if MANIFEST.exists():
        previous = pd.read_csv(MANIFEST)
        changed = previous.merge(manifest, on="arquivo", suffixes=("_antes", "_agora"))
        changed = changed[changed["sha256_antes"] != changed["sha256_agora"]]
        assert changed.empty, f"raw files changed since the last manifest: {changed['arquivo'].tolist()}"
    manifest.to_csv(MANIFEST, index=False)
    print(f"Saved {len(manifest)} files to {MANIFEST}")
