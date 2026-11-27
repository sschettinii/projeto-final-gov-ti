### Execuções em `results/`

| Pasta | Papel |
| --- | --- |
| `20261105T205507` | **Modelo oficial** (`modelo-v1.0.0`), entregue na Etapa 3 |
| `20261118T221057` | Reprodução da pipeline em outro computador; não é oficial |
| `monitoring_202607` | Primeiro ciclo de monitoramento, com as internações de 2026 |
| `registro_unificado.csv` | Histórico da fase exploratória, feita com o pipeline anterior |

## Como reproduzir

Requer Python 3.13 e cerca de 1,1 GB livre para os 212 arquivos brutos.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Pipeline completa

```bash
.venv/bin/python download.py
.venv/bin/python quality.py
.venv/bin/python preprocessing.py
.venv/bin/python tuning.py
.venv/bin/python evaluation.py
```

- `download.py` baixa só os arquivos que faltam e para se um arquivo já registrado no manifesto tiver mudado.
- `preprocessing.py` para se os totais esperados não conferirem: 212 arquivos, 3.608.323 internações e 768 linhas.
- `tuning.py` leva cerca de 4 minutos e cria uma nova pasta em `results/`.
- `evaluation.py` avalia a execução mais recente e acrescenta uma linha em `registry.csv`.

Em outro computador, o modelo e o ranking da busca podem variar um pouco (de 5,00% a 5,78% de macro-WAPE em 2025). O modelo oficial é o arquivo versionado, não um retreino; veja a seção "Variação entre máquinas" do [Model Card](../entrega-etapa4/model-card.md#variação-entre-máquinas).

### Sem baixar os arquivos brutos

O pacote inclui o dataset agregado (768 linhas, só contagens estaduais) em `data/`. Com ele, dá para rodar `tuning.py` e `evaluation.py` direto. O monitoramento e a medição de qualidade precisam dos arquivos brutos.

### Monitoramento e MLflow

```bash
.venv/bin/python monitoring.py
.venv/bin/pip install -r requirements-tracking.txt
.venv/bin/python tracking.py
uvx --from mlflow==3.17.2 mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5050
```

`monitoring.py` recusa sobrescrever um ciclo existente; para repeti-lo, mova a pasta `results/monitoring_202607`. `tracking.py` pode ser rodado quantas vezes for preciso, sem duplicar registros.

### Conferir a integridade do modelo oficial

```bash
.venv/bin/python -c "from evaluation import folder_hash; from pathlib import Path; print(folder_hash(Path('results/20261105T205507')))"
```

O resultado deve ser igual ao `folder_sha256` da linha `20261105T205507` em `results/registry.csv`.
