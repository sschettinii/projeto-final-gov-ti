# Model Card — Previsão mensal de AIHs iniciais por DCNT no Paraná

**Versão do modelo:** 1.0.0 (tag Git `modelo-v1.0.0`)

**Execução oficial:** `20261105T205507`, avaliada em 2026-11-06 e entregue na Etapa 3

**Status:** modelo oficial; uso acadêmico e de apoio ao planejamento, sem operação em produção

**Data deste documento:** 2026-11-24

## 1. Resumo

| Item | Valor |
| --- | --- |
| Tarefa | Regressão de contagem mensal, um mês à frente |
| Saída | Quantidade estimada de AIHs iniciais no mês seguinte, por grupo DCNT |
| Algoritmo | `MLPRegressor` (scikit-learn 1.8.0) com padronização das entradas e do alvo |
| Arquitetura | Camadas ocultas de 32 e 16 neurônios, ReLU, solver L-BFGS |
| Hiperparâmetros | `alpha = 1,4600`, `learning_rate_init = 0,00078`, `max_iter = 3000`, semente 42 |
| Referência obrigatória | Baseline sazonal: mesmo grupo, mesmo mês do ano anterior |
| Artefato | `results/20261105T205507/model.joblib` (SHA-256 `e97c192a…`) |
| Rastreabilidade | `config.json` e `best_params.json` da execução; linha em `results/registry.csv` com o SHA-256 da pasta (`6d7b2b5c…`) |
| Código | `tuning.py` e `evaluation.py`, na versão marcada pela tag `entrega-etapa3` |

## 2. Objetivo

Estimar, com um mês de antecedência, quantas AIHs iniciais de quatro grupos de doenças crônicas não transmissíveis serão registradas no SIH/SUS pelos estabelecimentos do Paraná. Os grupos são circulatórias, diabetes, neoplasias malignas e respiratórias selecionadas.

A previsão é um insumo para o planejamento de leitos, equipes e insumos. Ela antecipa meses de maior volume, mas a decisão continua com as pessoas responsáveis pelo planejamento.

## 3. Dados utilizados

| Item | Descrição |
| --- | --- |
| Fonte | AIH reduzida (`RDPR`) do SIH/SUS, DATASUS, de acesso público |
| Arquivos | 212 competências de processamento, de 2008-12 a 2026-07, com 15.131.255 registros |
| Seleção | AIH inicial (`IDENT = 1`), internação de 2008-12 a 2025-12, CID principal nos grupos DCNT: 3.608.323 AIHs |
| Dataset do modelo | `data/modelagem_dcnt_mensal_201001_202512.parquet`: 768 linhas (192 meses × 4 grupos), só contagens estaduais |
| Alvos | Janeiro de 2010 a dezembro de 2025, com 3.396.090 AIHs |
| Contexto histórico | 2008-12 a 2009-12, usado só para calcular as features dos primeiros alvos |

### Features

Todas usam apenas meses anteriores ao mês previsto:

- grupo DCNT;
- calendário: mês do ano, seno e cosseno do mês, índice temporal;
- lags de 1, 2, 3, 6 e 12 meses;
- médias móveis de 3, 6 e 12 meses;
- variação anual: último mês conhecido contra o mesmo mês do ano anterior.

Óbito, desfecho, permanência, valor, procedimento e qualquer dado do próprio mês previsto não entram no modelo. Dicionário, origem, transformações e qualidade estão em [dados.md](dados.md).

### Divisão temporal

| Parte | Período | Linhas | Uso |
| --- | --- | ---: | --- |
| Desenvolvimento | 2010-01 a 2024-12 | 720 | Busca e treinamento final |
| Validação temporal | Anos 2022, 2023 e 2024 | 144 | Escolha de modelo, janela e hiperparâmetros |
| Teste retrospectivo | 2025-01 a 2025-12 | 48 | Comparação final com o baseline |

Não há embaralhamento aleatório. Em cada fold de validação, o treino usa apenas meses anteriores ao ano avaliado. A busca comparou 9 famílias de modelos em 3 janelas de histórico (início em 2020, 2015 e 2010), com 25 trials Optuna cada, num total de 675 trials. Venceu a MLP com histórico desde 2010, com macro-WAPE de validação de 5,28%.

## 4. População e contexto

- **Unidade:** AIH inicial com diagnóstico principal no recorte DCNT. Uma AIH não equivale a uma pessoa: a mesma pessoa pode gerar várias AIHs, e AIHs de continuidade não são contadas.
- **Cobertura:** internações financiadas e registradas no SIH/SUS por estabelecimentos localizados no Paraná, incluindo pacientes residentes em outras UFs. Atendimentos exclusivamente privados e internações de residentes do Paraná em outras UFs ficam de fora.
- **Agregação:** estado inteiro, por mês de internação e grupo. O modelo não produz previsões por município, hospital, região de saúde, sexo ou faixa etária.
- **Período:** 2010 a 2025, incluindo a ruptura da pandemia de covid-19 (2020-03 a 2022-04).

## 5. Métricas

| Métrica | Por que foi escolhida |
| --- | --- |
| MAE | Erro médio em AIHs, na unidade usada pelo planejamento |
| RMSE | Penaliza mais os erros grandes, que são os mais custosos nos meses de pico |
| WAPE | Erro proporcional ao volume total |
| Macro-WAPE | Média simples do WAPE por grupo, para que o grupo circulatório, o maior, não esconda o desempenho de diabetes. É o critério de seleção |
| Viés médio | Direção do erro; negativo indica subestimação |

Métricas de classificação (accuracy, precision, recall, F1, AUC) não se aplicam, porque o alvo é uma quantidade.

### Teste retrospectivo de 2025

Fonte: `results/20261105T205507/metrics.csv`.

| Método | MAE | RMSE | WAPE | Macro-WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline sazonal | 469,81 | 626,15 | 8,27% | 9,60% | -460,27 |
| MLP oficial | 226,22 | 332,61 | 3,98% | 5,78% | -146,89 |

A MLP reduz o MAE em 52% e a macro-WAPE em 40% em relação ao baseline.

| Grupo | MAE | RMSE | WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: |
| Circulatórias | 439,17 | 548,64 | 4,13% | -425,82 |
| Diabetes | 80,61 | 92,64 | 11,62% | -30,13 |
| Neoplasias malignas | 163,96 | 201,62 | 2,34% | -40,25 |
| Respiratórias selecionadas | 221,15 | 303,76 | 5,03% | -91,35 |

A MLP supera o baseline nos quatro grupos. O viés é negativo em todos eles: o modelo subestima, principalmente no grupo circulatório.

### Teste de 2025 em tempo real, sem vazamento

O teste acima usa as séries consolidadas: para prever um mês, o modelo viu o mês anterior completo, mas no momento da previsão só cerca de metade das AIHs dele teria sido processada. Isso é vazamento de dados futuros e deixa o resultado otimista (risco M7). O `realtime_evaluation.py` refaz o teste prevendo cada mês só com os arquivos processados até o mês anterior, com os meses recentes corrigidos pela curva de completude daquele momento (`vintage.py`), e compara com o valor final.

Fonte: `results/realtime_202607/metrics.csv`.

| Método e entradas | MAE | RMSE | WAPE | Macro-WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline sazonal | 469,85 | 626,16 | 8,27% | 9,60% | -460,31 |
| MLP oficial, meses recentes corrigidos pela curva | 268,96 | 332,39 | 4,73% | 7,18% | 59,72 |
| MLP oficial, meses recentes como chegaram | 1.983,82 | 2.349,05 | 34,91% | 35,19% | -1.983,82 |

| Grupo | MAE | WAPE | WAPE do baseline | Viés relativo |
| --- | ---: | ---: | ---: | ---: |
| Circulatórias | 376,63 | 3,55% | 9,49% | -1,37% |
| Diabetes | 93,11 | 13,43% | 13,05% | -13,43% |
| Neoplasias malignas | 240,91 | 3,43% | 3,20% | +2,23% |
| Respiratórias selecionadas | 365,19 | 8,30% | 12,64% | +7,31% |

Este é o erro esperado em operação. A MLP continua melhor que o baseline no total e em circulatórias e respiratórias, mas fica um pouco pior em diabetes e neoplasias. O viés deixa de ser negativo em todos os grupos: subestima diabetes e circulatórias e superestima respiratórias e neoplasias. Sem corrigir os meses recentes, o erro passa de 35%.

### Variação numérica entre máquinas

O mesmo código, com os mesmos dados e as mesmas versões de bibliotecas, produz modelos diferentes em máquinas diferentes. A MLP com L-BFGS amplifica diferenças de arredondamento da ordem de 10⁻¹⁶ ([reproducao_etapa3.md](reproducao_etapa3.md)).

| Treino com a mesma configuração | Macro-WAPE em 2025 |
| --- | ---: |
| Execução oficial (máquina da entrega) | 5,78% |
| Mesmos hiperparâmetros, retreinados em outro Mac | 5,72% |
| Último bit de uma feature alterado | 5,35% a 5,56% |
| Busca completa refeita em outro Mac (vencedor com `alpha = 0,71`) | 5,00% |

O desempenho deve ser lido como uma faixa de cerca de 5% a 6% de macro-WAPE, não como um valor exato. O artefato oficial é o `model.joblib` versionado; retreinos servem para confirmar a ordem de grandeza.

### Desempenho em períodos de ruptura

Uma análise de backtest de 2018 a 2025 feita com a mesma arquitetura (`docs/analise_erro_pandemia.md`, versão com `alpha = 0,71`) mostrou o erro médio mensal da MLP subindo de 4,13% antes da pandemia para 10,62% durante ela, com pico de 41,20% em 2020-04. O baseline subiu de 5,44% para 20,70%. A análise não foi repetida com o `alpha` oficial.

## 6. Limitações

- O teste de 2025 do `evaluation.py` usa contagens consolidadas e tem vazamento de dados futuros. O erro esperado em operação é o do teste em tempo real (macro-WAPE de 7,18%), não o de 5,78% (seção 5).
- O modelo foi escolhido e treinado com entradas completas e é usado com entradas corrigidas pela curva de completude. A correção é uma aproximação, mais ruidosa no mês mais recente.
- O resultado varia entre máquinas (seção 5). Diferenças de até cerca de 0,8 ponto percentual de macro-WAPE não indicam, sozinhas, mudança nos dados ou no código.
- São quatro séries mensais correlacionadas, não 768 observações independentes. A incerteza da avaliação é maior do que o número de linhas sugere.
- O modelo não usa capacidade instalada, ocupação diária, equipes, estoques, população ou políticas locais.
- O recorte por CID principal não captura todas as internações de pessoas com doença crônica.
- Diabetes tem o maior erro: 11,62% com dados consolidados e 13,43% em tempo real, um pouco pior que o baseline (13,05%).
- Rupturas abruptas, como a pandemia, aumentam o erro e não são antecipadas pelo modelo.
- O modelo é estadual. Aplicar a previsão a municípios ou hospitais exige outro modelo e nova avaliação.

## 7. Usos recomendados

- Antecipar meses de maior volume de internações DCNT no Paraná para apoiar o planejamento estadual de leitos, equipes e insumos.
- Sinalizar meses que merecem análise detalhada pelas equipes de planejamento.
- Servir como referência acadêmica de pipeline reprodutível e governado.

Todo uso deve ter revisão humana e considerar fontes que o modelo não conhece.

## 8. Usos não recomendados

- Decisões clínicas ou sobre atendimento, prioridade ou cobertura de uma pessoa.
- Reduzir ou realocar recursos automaticamente, sem revisão humana.
- Avaliar, ranquear ou punir hospitais ou municípios.
- Estimar prevalência de doença ou número de pessoas doentes.
- Estimar ocupação diária de leitos apenas pela contagem de AIHs.
- Prever outros grupos de doença, outras UFs ou outras granularidades sem retreinar e reavaliar.
- Usar meses recentes ainda incompletos como entrada sem correção.
- Usar em períodos de ruptura sem acompanhamento reforçado do erro.

## 9. Riscos

| Risco | Efeito | Controle |
| --- | --- | --- |
| Subestimação sistemática | Faltam leitos ou insumos planejados | Viés reportado por grupo; margem de segurança decidida por pessoas |
| Atraso de processamento | Meses recentes parecem queda de demanda | Monitoramento da completude e correção dos meses recentes pela curva antes de prever |
| Vazamento de dados futuros na avaliação | O erro medido sai menor que o erro real | Avaliar só previsões feitas com os arquivos disponíveis na época (`realtime_evaluation.py`) |
| Instabilidade numérica entre máquinas | Retreino muda o modelo e o ranking | Artefato oficial versionado; ambiente registrado em cada execução |
| Mudança de distribuição | O modelo extrapola fora do padrão aprendido | Monitoramento de drift |
| Uso fora do escopo | Decisões indevidas sobre pessoas ou hospitais | Usos não recomendados explícitos e revisão humana |

A avaliação completa está em [matriz_riscos.md](matriz_riscos.md).

## 10. Aspectos éticos

- **Privacidade:** a fonte contém dados pessoais sensíveis de saúde. O `preprocessing.py` lê os arquivos brutos e grava só contagens mensais estaduais, com no mínimo 470 AIHs por célula. Nenhum registro individual é salvo pela pipeline, e os arquivos brutos ficam fora do Git.
- **Justiça entre grupos:** o desempenho é reportado por grupo, e a macro-WAPE impede que o grupo maior esconda o pior. Diabetes, com 11,62% de erro com dados consolidados e 13,43% em tempo real, precisa de atenção específica.
- **Cobertura:** a base representa o SUS. Conclusões não se aplicam diretamente à população atendida apenas pela rede privada.
- **Autonomia humana:** a previsão é apoio à decisão. Nenhuma alocação ou retirada de recursos deve ser automática.
- **Transparência:** código, parâmetros, hashes, métricas e previsões de cada execução estão versionados em `results/`, e a variação entre máquinas está documentada.

## 11. Responsável pelo modelo

| Papel | Responsável |
| --- | --- |
| Desenvolvimento e manutenção técnica | André Tomonaga Schettini e Vitor da Costa Garcia |
| Contexto | Disciplina de Governança de TI e de Dados, Universidade Estadual de Londrina |
| Dono do negócio em operação | A definir; em uso real, a área de planejamento da gestão estadual de saúde |

Dúvidas, incidentes e pedidos de revisão devem ser registrados como issue no repositório.

## 12. Reprodução

Dentro de `solucao/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python download.py
.venv/bin/python preprocessing.py
.venv/bin/python tuning.py
.venv/bin/python evaluation.py
```

Em outra máquina, o dataset deve ter o mesmo conteúdo, mas pode ter outro SHA-256 de arquivo, e o modelo pode variar dentro da faixa da seção 5.
