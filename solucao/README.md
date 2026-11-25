# Previsão mensal de internações por doenças crônicas no Paraná

Pacote de governança da solução de IA — Etapa 4, Governança de TI e de Dados (UEL).

André Tomonaga Schettini e Vitor da Costa Garcia.

A solução prevê, com um mês de antecedência, quantas AIHs iniciais de quatro grupos de doenças crônicas (circulatórias, diabetes, neoplasias malignas e respiratórias selecionadas) os estabelecimentos do Paraná vão registrar no SIH/SUS. O modelo oficial é uma MLP. No teste de 2025, ela teve macro-WAPE de 5,78%, contra 9,60% da referência sazonal.

Comece pelo [relatório executivo](docs/relatorio_executivo.md).

## Produtos da entrega

| Exigência da Etapa 4 | Onde está |
| --- | --- |
| 1. Repositório da solução: código, pipeline e instruções | Este pacote; instruções abaixo |
| 2. Dataset documentado: dicionário, qualidade, origem e transformações | [docs/dados.md](docs/dados.md), `results/data_quality.csv`, `results/raw_manifest.csv` |
| 3. Registro dos experimentos: parâmetros, versões e resultados | `results/<execução>/`, `results/registry.csv`, [docs/rastreamento.md](docs/rastreamento.md) (MLflow) |
| 4. Model Card | [docs/model_card.md](docs/model_card.md) |
| 5. Plano de monitoramento: o que monitorar, indicador, limite e ação | [docs/plano_monitoramento.md](docs/plano_monitoramento.md), `results/monitoring_202607/` |
| 6. Matriz de riscos | [docs/matriz_riscos.md](docs/matriz_riscos.md) |
| 7. Relatório executivo | [docs/relatorio_executivo.md](docs/relatorio_executivo.md) |

Também fazem parte da entrega:

- [docs/versionamento.md](docs/versionamento.md): como código, dados, modelo e configurações são versionados;
- [docs/reproducao_etapa3.md](docs/reproducao_etapa3.md): reprodução da entrega da Etapa 3 e por que o modelo varia entre máquinas.

## Estrutura

```text
download.py           baixa os arquivos RDPR do DATASUS e grava results/raw_manifest.csv
quality.py            qualidade dos registros brutos → results/data_quality.csv
preprocessing.py      dataset mensal: contagens e features → data/modelagem_dcnt_mensal_201001_202512.parquet
tuning.py             busca de modelos e hiperparâmetros → results/<execução>/
evaluation.py         teste em 2025 contra o baseline → modelo, métricas, previsões, registry.csv
monitoring.py         ciclo de monitoramento com um lote novo → results/monitoring_<competência>/
tracking.py           publica execuções, modelo e monitoramento no MLflow
package.py            gera o ZIP de entrega a partir do commit atual
requirements.txt      versões exatas da pipeline
requirements-tracking.txt  versões exatas do MLflow
results/              execuções, registros, manifestos, qualidade e monitoramento
docs/                 documentação de governança
data/                 arquivos brutos e dataset (fora do Git e do pacote, exceto o dataset agregado)
```

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

Em outro computador, o modelo e o ranking da busca podem variar um pouco (de 5,00% a 5,78% de macro-WAPE em 2025). O modelo oficial é o arquivo versionado, não um retreino; veja [docs/reproducao_etapa3.md](docs/reproducao_etapa3.md).

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

## Limites de uso

A previsão é estadual e conta internações, não pessoas nem ocupação de leitos. Ela apoia o planejamento com revisão humana e não deve ser usada para decisões sobre pacientes, para cortar recursos automaticamente ou para ranquear hospitais. Os detalhes estão no [Model Card](docs/model_card.md).
