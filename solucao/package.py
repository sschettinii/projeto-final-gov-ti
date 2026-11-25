"""Gera o ZIP de entrega da Etapa 4 a partir do commit atual.

O pacote contém os arquivos versionados no Git de solucao/ e entrega-etapa4/ e o
README.md da raiz, mais o dataset agregado (só contagens estaduais), para que a busca
e a avaliação rodem sem baixar os arquivos brutos. Arquivos brutos, banco do MLflow,
slides e ambientes virtuais ficam de fora.

Uso, dentro de solucao/: python package.py    (precisa de um commit sem alterações pendentes)
"""

from hashlib import sha256
from pathlib import Path
import subprocess
import zipfile

from tuning import DATASET

ROOT_FOLDER = "entrega4_govti"
CONTENT = ("solucao", "entrega-etapa4", "README.md")
OUTPUT = Path("../entrega/etapa4_gov_ti.zip")


def git(*args):
    return subprocess.run(["git", "-C", "..", *args], check=True, capture_output=True, text=True).stdout


if __name__ == "__main__":
    assert not git("status", "--porcelain", "--", *CONTENT).strip(), "commit the changes first"
    commit = git("rev-parse", "--short", "HEAD").strip()
    files = sorted(git("ls-files", "--", *CONTENT).splitlines())

    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as package:
        for name in files:
            package.write(Path("..") / name, f"{ROOT_FOLDER}/{name}")
        package.write(DATASET, f"{ROOT_FOLDER}/solucao/{DATASET}")
        package.writestr(f"{ROOT_FOLDER}/COMMIT.txt", f"Gerado a partir do commit {commit}\n")

    print(f"Saved {len(files) + 2} files from commit {commit} to {OUTPUT}")
    print(f"SHA-256: {sha256(OUTPUT.read_bytes()).hexdigest()}")
