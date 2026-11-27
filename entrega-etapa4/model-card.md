---
# Formato baseado no template de Model Card do Hugging Face:
# https://github.com/huggingface/hub-docs/blob/main/modelcard.md?plain=1
library_name: scikit-learn
pipeline_tag: tabular-regression
tags:
  - previsao-de-demanda
  - series-temporais
  - saude-publica
  - sih-sus
metrics:
  - mae
  - rmse
  - wape
model-index:
  - name: previsao-aih-dcnt-mlp
    results:
      - task:
          type: tabular-regression
          name: Previsão mensal de AIHs iniciais por grupo DCNT
        dataset:
          type: sih-sus-rdpr
          name: SIH/SUS, AIHs iniciais DCNT do Paraná, 2010-01 a 2025-12
        metrics:
          - type: wape
            name: WAPE no teste de 2025
            value: 3.98
          - type: macro-wape
            name: Macro-WAPE no teste de 2025
            value: 5.78
          - type: mae
            name: MAE no teste de 2025
            value: 226.22
          - type: macro-wape
            name: Macro-WAPE no teste de 2025 em tempo real (sem dados futuros)
            value: 7.18
---

# Model Card do previsao-aih-dcnt-mlp

Rede neural pequena (MLP) que prevê, com um mês de antecedência, quantas internações iniciais (AIHs) de quatro grupos de doenças crônicas não transmissíveis (DCNT) os hospitais do Paraná vão registrar no SUS.

## Model Details

### Model Description

O objetivo do modelo é estimar a demanda do mês seguinte para quatro grupos de doenças crônicas não transmissiveis. A previsão é um indicador para o planejamento de leitos. Ela mostra quais meses devem ter mais internações, mas a decisão continua com as pessoas responsáveis pelo planejamento.

O modelo usa só meses anteriores ao mês previsto: contagens recentes, médias móveis, variação anual e calendário. Ele foi escolhido entre 9 famílias de modelos e é comparado sempre com uma regra simples de referência: repetir o mesmo mês do ano anterior.

- **Versão:** 1.0.0 (tag Git `modelo-v1.0.0`), execução oficial `20261105T205507`
- **Status:** modelo oficial do projeto; uso acadêmico e de apoio ao planejamento, sem operação em produção
- **Developed by:** André Tomonaga Schettini e Vitor da Costa Garcia
- **Funded by:** sem financiamento, projeto acadêmico
- **Shared by:** disciplina de Governança de TI e de Dados, Universidade Estadual de Londrina (UEL)
- **Model type:** regressão tabular de contagem mensal (`MLPRegressor` do scikit-learn)
- **Language(s):** não se aplica, os dados são tabulares; a documentação está em português
- **License:** não definida, uso acadêmico
- **Finetuned from model:** não, treinado do zero

### Responsável pelo modelo

| Papel | Responsável |
| --- | --- |
| Responsável pelos dados e pelo modelo | André Tomonaga Schettini e Vitor da Costa Garcia |
| Dono do negócio (proposto) | Diretoria de Contratualização e Regulação da SESA-PR, que coordena a regulação de leitos. Titular em nov/2026: Raquel Mazetti Castro |
| Alta gestão | Secretário de Estado da Saúde, que aprova o uso da solução. Em nov/2026: César Neves |

O dono do negócio é uma proposta da equipe, sem acordo formal com a SESA-PR. A responsabilidade é do cargo, e o nome da titular é só uma referência datada.

### Model Sources

- **Repository:** https://github.com/sschettinii/projeto-final-gov-ti
- **Paper:** não há; o contexto do problema está nos relatórios das Etapas 1 e 2 da disciplina
- **Demo:** não há

## Uses

### Direct Use

- Antecipar os meses de maior volume de internações por DCNT no Paraná para apoiar o planejamento estadual de leitos, equipes e insumos.
- Sinalizar meses que merecem uma análise mais detalhada pela equipe de planejamento.
- Servir de referência acadêmica de uma pipeline reprodutível e governada.

Os usuários previstos são os gestores regionais de saúde da SESA-PR e os diretores de hospitais. Quem é afetado pelas decisões são os profissionais de saúde e os pacientes com doenças crônicas.

### Downstream Use

- Base para um painel de gestores com previsões, alertas e indicadores (objetivo da Etapa 1, ainda não construído).
- Ponto de partida para converter a previsão de internações em demanda de leitos, cruzando com a capacidade do CNES e o tempo de permanência.
- Ponto de partida para previsões por região de saúde. Isso exige outro modelo, nova avaliação e nova análise de privacidade.

### Out-of-Scope Use

- Decisões clínicas ou sobre atendimento, prioridade ou cobertura de uma pessoa.
- Reduzir ou realocar recursos automaticamente, sem revisão humana.
- Avaliar, ranquear ou punir hospitais ou municípios.
- Estimar prevalência de doença ou número de pessoas doentes.
- Estimar ocupação diária de leitos só pela contagem de AIHs.
- Prever outros grupos de doença, outros estados ou outras granularidades sem retreinar e reavaliar.
- Usar meses recentes ainda incompletos como entrada sem correção.
- Usar em períodos de ruptura, como uma pandemia, sem acompanhamento reforçado do erro.

## Bias, Risks, and Limitations

### Limitações

- O teste de 2025 original usa contagens já consolidadas, o que é um vazamento de dados: para prever um mês, o modelo viu o mês anterior completo, mas na época só metade das AIHs dele teria chegado. Refeito como seria em operação, com os meses recentes corrigidos pela curva de completude, a macro-WAPE sobe de 5,78% para 7,18% (seção Results). Sem essa correção, o erro passa de 35%.
- O resultado varia entre máquinas. A mesma configuração deu macro-WAPE de 5,78% na máquina da entrega e até 5,00% em outro computador. O desempenho deve ser lido como uma faixa de cerca de 5% a 6%.
- São quatro séries mensais correlacionadas, não 768 observações independentes, então a incerteza da avaliação é maior do que o número de linhas sugere.
- O modelo não sabe nada sobre capacidade instalada, ocupação diária, equipes, estoques, população ou políticas locais.
- O recorte por CID principal não pega todas as internações de pessoas com doença crônica.
- O erro de diabetes é o maior dos quatro grupos: 11,62% com dados consolidados e 13,43% em tempo real, um pouco pior que a regra de referência (13,05%).
- Rupturas bruscas, como a pandemia, aumentam o erro e não são antecipadas pelo modelo.
- O modelo é estadual. Aplicar a previsão a municípios ou hospitais exige outro modelo.

### Riscos

| Risco | Efeito | Controle |
| --- | --- | --- |
| Subestimação sistemática | Faltam leitos ou insumos planejados | Viés reportado por grupo; margem de segurança decidida por pessoas |
| Atraso de processamento | Meses recentes parecem queda de demanda | Monitorar a completude e corrigir os meses recentes pela curva antes de prever |
| Vazamento de dados futuros na avaliação | O erro medido sai menor do que o erro real | Avaliar só previsões feitas com os arquivos disponíveis na época (`realtime_evaluation.py`) |
| Instabilidade numérica entre máquinas | Um retreino muda o modelo e o ranking | Modelo oficial guardado como arquivo versionado |
| Mudança de distribuição | O modelo extrapola fora do padrão aprendido | Monitoramento de drift |
| Uso fora do escopo | Decisões indevidas sobre pessoas ou hospitais | Usos proibidos explícitos e revisão humana |

A lista completa, com 22 riscos de dados, modelo, privacidade, segurança e ética, está na [matriz de riscos](matriz-riscos.md).

### Aspectos éticos

- **Privacidade:** a fonte tem dados pessoais sensíveis de saúde. A pipeline lê só três campos de cada registro e grava só contagens mensais do estado, com no mínimo 470 AIHs por célula. Nenhum registro individual é salvo, e os arquivos brutos ficam fora do Git.
- **Justiça entre grupos:** o desempenho é reportado por grupo, e a macro-WAPE impede que o grupo maior esconda o pior. Diabetes precisa de atenção específica.
- **Cobertura:** a base representa o SUS. As conclusões não valem direto para quem é atendido só pela rede privada.
- **Autonomia humana:** a previsão é apoio à decisão. Nenhuma alocação ou retirada de recursos deve ser automática.
- **Transparência:** código, parâmetros, hashes, métricas e previsões de cada execução estão versionados em `results/`.

### Recommendations

- Toda previsão usada no planejamento deve ter revisão humana registrada.
- Avisar o planejamento da direção do erro de cada grupo (em tempo real, subestima diabetes e circulatórias e superestima respiratórias) e definir uma margem de segurança.
- Não usar os três meses mais recentes sem corrigir a incompletude.
- Esperar um erro próximo do teste em tempo real (macro-WAPE de 7,18% em 2025), não dos 5,78% do teste com dados consolidados.
- Usar sempre o modelo versionado (`results/20261105T205507/model.joblib`) e comparar retreinos só na mesma máquina.
- Só trocar de versão se a nova for melhor que a regra de referência e que a versão atual, com aprovação do dono do negócio.

## How to Get Started with the Model

Para reproduzir tudo do zero, dentro de `solucao/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python download.py
.venv/bin/python preprocessing.py
.venv/bin/python tuning.py
.venv/bin/python evaluation.py
```

Para usar o modelo oficial já treinado:

```python
import joblib
import pandas as pd
from tuning import DATASET, predict

model = joblib.load("results/20261105T205507/model.joblib")
dataset = pd.read_parquet(DATASET)
rows = dataset[dataset["mes_internacao"] >= "2025-01"]
rows.assign(previsao=predict(model, rows))[["mes_internacao", "grupo_dcnt", "aih_iniciais", "previsao"]]
```

## Training Details

### Training Data

Os dados vêm da AIH reduzida (`RDPR`) do SIH/SUS, mantido pelo DATASUS e de acesso público. Foram lidos 15.131.255 registros de 212 arquivos mensais (2008-12 a 2026-07), dos quais 3.608.323 são AIHs iniciais por DCNT.

O dataset do modelo é `data/modelagem_dcnt_mensal_201001_202512.parquet`: 768 linhas (192 meses × 4 grupos), só com contagens do estado. Dicionário, qualidade, origem e transformações estão no [dataset documentado](dataset-documentado.md).

| Parte | Período | Linhas | Uso |
| --- | --- | ---: | --- |
| Desenvolvimento | 2010-01 a 2024-12 | 720 | Busca de modelos e treino final |
| Validação temporal | Anos 2022, 2023 e 2024 | 144 | Escolha de modelo, janela e hiperparâmetros |
| Teste | 2025-01 a 2025-12 | 48 | Comparação final com a regra de referência |

### Training Procedure

#### Preprocessing

- Contagem mensal das AIHs iniciais por grupo DCNT, pelo mês de internação.
- Features calculadas só com meses anteriores: lags de 1, 2, 3, 6 e 12 meses, médias móveis de 3, 6 e 12 meses, variação anual, mês do ano (número, seno e cosseno) e índice temporal.
- Dentro do modelo: o grupo DCNT vira variáveis indicadoras (`DictVectorizer`), as entradas são padronizadas (`StandardScaler`) e o alvo também é padronizado (`TransformedTargetRegressor`).
- Previsões negativas são cortadas em zero.

Óbito, desfecho, permanência, valor, procedimento e qualquer dado do próprio mês previsto não entram no modelo.

#### Training Hyperparameters

- **Training regime:** CPU, precisão padrão do scikit-learn (float64)
- **Arquitetura:** camadas ocultas de 32 e 16 neurônios, ativação ReLU, solver L-BFGS
- **Hiperparâmetros:** `alpha = 1,4600`, `learning_rate_init = 0,00078`, `max_iter = 3000`, semente 42
- **Busca:** 9 famílias de modelos × 3 janelas de histórico (início em 2020, 2015 e 2010) × 25 tentativas do Optuna = 675 tentativas. Venceu a MLP com histórico desde 2010, com macro-WAPE de validação de 5,28%.

Não há embaralhamento aleatório. Em cada fold de validação, o treino usa só meses anteriores ao ano avaliado.

#### Speeds, Sizes, Times

- Arquivo do modelo: `model.joblib` com 27 KB.
- Execução oficial avaliada em 2026-11-06.
- Tempo de treino não foi registrado; a pipeline roda num computador comum, sem GPU.

## Evaluation

### Testing Data, Factors & Metrics

#### Testing Data

As 48 linhas de 2025 (12 meses × 4 grupos), que não foram usadas na busca nem na escolha do modelo.

#### Factors

- **Grupo DCNT:** os resultados são reportados para cada um dos quatro grupos, porque eles têm volumes muito diferentes (diabetes tem cerca de 670 AIHs por mês, circulatórias cerca de 8.500).
- **Período de ruptura:** o comportamento durante a pandemia de covid-19 (2020-03 a 2022-04) foi analisado à parte.

#### Metrics

| Métrica | Por que foi escolhida |
| --- | --- |
| MAE | Erro médio em AIHs, na mesma unidade usada pelo planejamento |
| RMSE | Pesa mais os erros grandes, que são os mais caros nos meses de pico |
| WAPE | Erro proporcional ao volume total |
| Macro-WAPE | Média simples do WAPE de cada grupo, para o grupo circulatório, que é o maior, não esconder o desempenho de diabetes. É o critério de escolha do modelo |
| Viés médio | Direção do erro; negativo indica que o modelo subestima |

Métricas de classificação (accuracy, precision, recall, F1, AUC) não se aplicam, porque o alvo é uma quantidade.

### Results

Há dois resultados para 2025. O primeiro é o teste original, com as contagens já consolidadas. Ele mede o modelo quando as entradas estão completas e é otimista, porque usa informação que não existiria no momento da previsão. O segundo é o teste em tempo real, em que cada mês é previsto só com os arquivos processados até o mês anterior, com os meses recentes corrigidos pela curva de completude daquele momento, e comparado com o valor final. É o erro esperado em operação.

**Teste com dados consolidados.** Fonte: `results/20261105T205507/metrics.csv`.

| Método | MAE | RMSE | WAPE | Macro-WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regra de referência | 469,81 | 626,15 | 8,27% | 9,60% | -460,27 |
| MLP oficial | 226,22 | 332,61 | 3,98% | 5,78% | -146,89 |

| Grupo | MAE | RMSE | WAPE | WAPE da referência | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Circulatórias | 439,17 | 548,64 | 4,13% | 9,49% | -425,82 |
| Diabetes | 80,61 | 92,64 | 11,62% | 13,05% | -30,13 |
| Neoplasias malignas | 163,96 | 201,62 | 2,34% | 3,20% | -40,25 |
| Respiratórias selecionadas | 221,15 | 303,76 | 5,03% | 12,64% | -91,35 |

**Teste em tempo real.** Fonte: `results/realtime_202607/metrics.csv` (entradas `com_correcao`).

| Método | MAE | RMSE | WAPE | Macro-WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regra de referência | 469,85 | 626,16 | 8,27% | 9,60% | -460,31 |
| MLP oficial | 268,96 | 332,39 | 4,73% | 7,18% | 59,72 |
| MLP oficial, sem corrigir os meses recentes | 1.983,82 | 2.349,05 | 34,91% | 35,19% | -1.983,82 |

| Grupo | MAE | RMSE | WAPE | WAPE da referência | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Circulatórias | 376,63 | 431,31 | 3,55% | 9,49% | -145,95 |
| Diabetes | 93,11 | 111,83 | 13,43% | 13,05% | -93,11 |
| Neoplasias malignas | 240,91 | 283,89 | 3,43% | 3,20% | 156,49 |
| Respiratórias selecionadas | 365,19 | 403,47 | 8,30% | 12,64% | 321,47 |

A regra de referência quase não muda, porque ela usa o mesmo mês do ano anterior, que já está completo quando a previsão é feita.

#### Summary

Com dados consolidados, a MLP reduz o erro médio em 52% e a macro-WAPE em 40% em relação à regra de referência, é melhor nos quatro grupos e subestima em todos eles, principalmente em circulatórias.

Em tempo real, que é como o modelo seria usado, a vantagem diminui mas continua: macro-WAPE de 7,18% contra 9,60%, e erro médio 43% menor. A MLP continua bem melhor em circulatórias e respiratórias, mas fica um pouco pior que a referência em diabetes e neoplasias. O viés muda de direção conforme o grupo: subestima diabetes (-13,43%) e circulatórias, e superestima respiratórias (+7,31%) e neoplasias. Corrigir os meses recentes é obrigatório: sem a correção, o erro passa de 35%.

## Model Examination

### Variação entre máquinas

O mesmo código, com os mesmos dados e as mesmas versões de bibliotecas, gera modelos diferentes em máquinas diferentes. A MLP com L-BFGS amplifica diferenças de arredondamento da ordem de 10⁻¹⁶ ([reproducao_etapa3.md](../solucao/docs/reproducao_etapa3.md)).

| Treino com a mesma configuração | Macro-WAPE em 2025 |
| --- | ---: |
| Execução oficial (Debian Linux, AMD Ryzen 7 série 4000) | 5,78% |
| Mesmos hiperparâmetros, retreinados em outro Mac | 5,72% |
| Último bit de uma feature alterado | 5,35% a 5,56% |
| Busca completa refeita em outro Mac (macOS, Apple M4) | 5,00% |

Por isso o modelo oficial é o arquivo versionado, e um retreino serve só para confirmar a ordem de grandeza do erro.

### Desempenho em períodos de ruptura

Um backtest de 2018 a 2025 com a mesma arquitetura (versão com `alpha = 0,71`) mostrou o erro médio mensal da MLP subindo de 4,13% antes da pandemia para 10,62% durante ela, com pico de 41,20% em 2020-04. A regra de referência subiu de 5,44% para 20,70%. Essa análise não foi repetida com o `alpha` oficial.

## Environmental Impact

- **Hardware Type:** CPU de computador pessoal (AMD Ryzen 7 série 4000), sem GPU
- **Hours used:** não medido; o modelo é pequeno e a busca roda localmente
- **Cloud Provider:** nenhum, execução local
- **Compute Region:** não se aplica
- **Carbon Emitted:** não estimado; o impacto é baixo porque não há GPU nem nuvem

## Technical Specifications

### Model Architecture and Objective

`Pipeline` do scikit-learn com três passos: `DictVectorizer` para o grupo DCNT, `StandardScaler` nas entradas e `TransformedTargetRegressor` com `StandardScaler` no alvo em volta de um `MLPRegressor` (32 e 16 neurônios, ReLU, L-BFGS). O objetivo do treino é o erro quadrático médio do alvo padronizado; a escolha do modelo usa a macro-WAPE da validação.

### Compute Infrastructure

#### Hardware

- Execução oficial: Debian Linux, AMD Ryzen 7 série 4000.
- Reprodução: macOS, Apple M4.

#### Software

Python 3.13.5, scikit-learn 1.8.0, Optuna 4.9.0, pandas 2.3.3, numpy 2.5.4, pyarrow 25.0.1, joblib 1.6.0, datasus-dbc 0.1.3 e dbfread 2.0.7 (`solucao/requirements.txt`).

## Citation

**APA:**

Schettini, A. T., & Garcia, V. C. (2026). *Previsão de internações por doenças crônicas no Paraná* [Projeto final, Governança de TI e de Dados]. Universidade Estadual de Londrina. https://github.com/sschettinii/projeto-final-gov-ti

## Glossary

- **AIH:** Autorização de Internação Hospitalar, o registro de uma internação no SUS. Uma pessoa pode ter várias AIHs.
- **AIH inicial:** a primeira AIH de uma internação (`IDENT = 1`). AIHs de continuidade de longa permanência não são contadas.
- **DCNT:** doenças crônicas não transmissíveis.
- **Competência:** mês em que a AIH foi processada pelo DATASUS, que pode ser posterior ao mês da internação.
- **Regra de referência (baseline sazonal):** prever para cada grupo o mesmo valor do mesmo mês do ano anterior.
- **WAPE:** soma dos erros absolutos dividida pela soma dos valores reais.
- **Macro-WAPE:** média simples do WAPE de cada grupo.

## More Information

- [Dataset documentado](dataset-documentado.md)
- [Registro dos experimentos](registro-experimentos.md)
- [Plano de monitoramento](plano-monitoramento.md)
- [Matriz de riscos](matriz-riscos.md)
- [Relatório executivo](relatorio-executivo.md)

## Model Card Authors

André Tomonaga Schettini e Vitor da Costa Garcia.

## Model Card Contact

Dúvidas, incidentes e pedidos de revisão devem ser registrados como issue no repositório.
