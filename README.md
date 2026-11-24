# Previsão de internações por doenças crônicas no Paraná

Projeto final da disciplina de Governança de TI e de Dados (UEL).

André Tomonaga Schettini e Vitor da Costa Garcia.

O projeto prevê, com um mês de antecedência, as internações por doenças crônicas não transmissíveis nos estabelecimentos do Paraná, a partir dos dados públicos do SIH/SUS. A Etapa 4 transforma a solução entregue na Etapa 3 numa solução governável: versionamento, rastreamento de experimentos, Model Card, monitoramento e gestão de riscos.

## Requisitos

- Python 3.13 (a execução oficial usou o 3.13.5). Versões mais antigas podem não instalar as bibliotecas fixadas.
- Cerca de 1,5 GB livres em disco: os 212 arquivos brutos ocupam perto de 1 GB.

## Passo a passo

Executar dentro da pasta `solucao/`**:

### 1. Criar o ambiente

macOS e Linux:

```bash
cd solucao
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd solucao
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Nos passos seguintes, troque `.venv/bin/python` por `.venv\Scripts\python` no Windows.

### 2. Baixar os dados brutos

```bash
.venv/bin/python download.py
```

Baixa os arquivos `RDPR0812.dbc` a `RDPR2607.dbc` para `data/raw/`. Arquivos que já existem não são baixados de novo, então se o FTP cair no meio é só rodar o comando outra vez.

Confira se vieram os 212 arquivos:

```bash
ls data/raw/RDPR*.dbc | wc -l
```

### 3. Medir a qualidade dos dados (opcional)

```bash
.venv/bin/python quality.py
```

Gera `results/data_quality.csv`, com uma linha por arquivo e o motivo de cada registro ter ficado de fora. O script confere que o total selecionado é 3.608.323 AIHs, igual ao do `preprocessing.py`.

### 4. Montar o dataset

```bash
.venv/bin/python preprocessing.py
```

Gera `data/modelagem_dcnt_mensal_201001_202512.parquet` com 768 linhas. O script para com erro se algum destes valores não bater:

| Verificação | Valor esperado |
| --- | --- |
| Arquivos brutos | 212 |
| AIHs iniciais DCNT de 2008-12 a 2025-12 | 3.608.323 |
| Linhas do dataset | 768, sem valores ausentes |
| AIHs nos meses-alvo (2010-01 a 2025-12) | 3.396.090 |

Se passar, o conteúdo do dataset é idêntico ao usado no projeto.

### 5. Buscar o modelo

```bash
.venv/bin/python tuning.py
```

Testa 9 famílias de modelos em 3 janelas de histórico, com 25 tentativas do Optuna cada (675 no total), validando em 2022, 2023 e 2024. O ano de teste (2025) não é usado aqui.

Cria uma pasta nova `results/AAAAMMDDTHHMMSS/` com:

- `config.json`: dataset e seu SHA-256, semente, janelas, anos de validação, features e versões das bibliotecas;
- `best_params.json`: melhor resultado de cada modelo em cada janela;
- `trials.csv`: todas as 675 tentativas.

### 6. Avaliar no teste de 2025

```bash
.venv/bin/python evaluation.py
```

Por padrão avalia a execução mais recente de `results/`. Para escolher outra: `.venv/bin/python evaluation.py results/<pasta>`.

O script treina o vencedor da busca, testa em 2025 contra a regra de referência (repetir o mesmo mês do ano anterior) e grava na pasta da execução:

- `model.joblib`: o modelo treinado;
- `metrics.csv`: MAE, RMSE, WAPE, macro-WAPE e viés, no total e por grupo;
- `predictions.csv`: previsão de cada mês e grupo de 2025.

Depois acrescenta uma linha em `results/registry.csv` com a data, o SHA-256 da pasta e do dataset, o modelo vencedor e as métricas. Cada pasta só pode ser avaliada uma vez.

## Conferir o modelo oficial sem retreinar

O modelo oficial é o arquivo `results/20261105T205507/model.joblib`. Depois do passo 4, dá para recalcular as métricas de 2025 com ele, dentro de `solucao/`:

```bash
.venv/bin/python -c "
import joblib, pandas as pd
from tuning import DATASET, between, predict
from evaluation import metrics_table
model = joblib.load('results/20261105T205507/model.joblib')
test = between(pd.read_parquet(DATASET), '2025-01', '2025-12')
table = metrics_table(test, {'mlp': predict(model, test), 'baseline': test['lag_12'].astype(float)})
print(table.round(2).to_string(index=False))
"
```

O resultado esperado, no total, é:

| Método | MAE | RMSE | WAPE | Macro-WAPE |
| --- | ---: | ---: | ---: | ---: |
| MLP oficial | 226,22 | 332,61 | 3,98% | 5,78% |
| Regra de referência | 469,81 | 626,15 | 8,27% | 9,60% |

Esses números devem ser iguais em qualquer máquina, porque o modelo já está treinado.

## O que esperar ao retreinar em outra máquina

- Os dados se repetem. Se o `preprocessing.py` passar nas verificações, o conteúdo do dataset é o mesmo.
- O SHA-256 do dataset pode mudar. O hash é calculado sobre os bytes do Parquet, que incluem metadados de gravação. Por isso o `evaluation.py` só avalia execuções feitas com o dataset da própria máquina.
- O modelo pode mudar. A MLP amplifica diferenças de arredondamento entre processadores. A execução oficial (Debian Linux, AMD Ryzen 7 série 4000) teve macro-WAPE de 5,78%, e a busca refeita num Mac com Apple M4 escolheu outro `alpha` e teve 5,00%. Um resultado entre cerca de 5% e 6% é esperado.

Um retreino não substitui o modelo oficial. Ele só confirma a ordem de grandeza do erro.
