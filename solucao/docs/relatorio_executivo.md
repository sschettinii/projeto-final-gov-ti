# Relatório executivo — previsão de internações por doenças crônicas no Paraná

**Data:** 2026-11-19

**Equipe:** André Tomonaga Schettini e Vitor da Costa Garcia — Governança de TI e de Dados, UEL

**Organização-alvo:** Secretaria de Estado da Saúde do Paraná (SESA-PR)

## 1. Em uma página

A SESA-PR tem dificuldade em prever a demanda de internações por doenças crônicas ao longo do ano, o que gera picos de superlotação e leitos subutilizados. Este projeto usa os registros públicos do SIH/SUS para prever, com um mês de antecedência, quantas internações iniciais de quatro grupos de doenças crônicas os hospitais do Paraná vão registrar.

**Resultado.** No teste retrospectivo de 2025, o modelo errou em média 226 internações por mês e grupo, contra 470 da regra usada como referência (repetir o mesmo mês do ano anterior). O erro proporcional caiu de 8,27% para 3,98% no total e de 9,60% para 5,78% na média dos grupos.

**Governança.** A solução é rastreável do arquivo bruto ao modelo em uso. Cada arquivo baixado tem hash, cada execução guarda dados, parâmetros, máquina e modelo, e a versão em uso está marcada no Git e no MLflow. O modelo tem Model Card, matriz de riscos e plano de monitoramento.

**Primeiro ciclo de monitoramento.** Com as internações de 2026 como dados novos, três achados pedem ação antes de qualquer uso operacional:

1. os três meses mais recentes chegam incompletos, e usá-los sem correção reduziria a previsão em 20% a 36%;
2. no início de 2026, o modelo empatou com a regra de referência e subestimou diabetes em todos os meses;
3. o mesmo código gera modelos ligeiramente diferentes em máquinas diferentes, o que obriga a guardar o modelo oficial como arquivo.

**Recomendação.** Usar a previsão como apoio ao planejamento, com revisão humana. Antes de operar, corrigir os meses incompletos, acompanhar mais três ciclos de monitoramento e preparar o retreino com 2025 incluído.

## 2. Objetivos estratégicos e atendimento

A Etapa 1 definiu dois objetivos estratégicos para a SESA-PR.

| Objetivo | Indicador da Etapa 1 | Contribuição prevista | O que a solução entrega | Situação |
| --- | --- | --- | --- | --- |
| Melhorar a eficiência na alocação de leitos | Taxa de ocupação de leitos | Prever a demanda com antecedência | Previsão mensal por grupo DCNT para o estado, com erro de 3,98% em 2025, metade do erro da regra de referência | **Parcial.** A previsão existe e é melhor que a referência. Ela é estadual, não regional, e prevê internações, não ocupação de leitos |
| Apoiar decisões gerenciais com base em dados | % de decisões de alocação com suporte analítico | Painel com previsões, alertas e indicadores | Previsões em CSV, alertas de monitoramento por nível (OK, atenção, alerta) e registro de decisões | **Parcial.** Os alertas e o registro de decisões existem; o painel para gestores não foi construído |

O que ficou fora, e por quê:

- **Previsão regional:** as séries por município são pequenas e instáveis. A previsão regional depende da tabela oficial de regiões de saúde e de nova avaliação de privacidade, porque contagens pequenas facilitam a reidentificação.
- **Taxa de ocupação:** o SIH/SUS não informa leitos ocupados por dia. Converter internações em ocupação exige a capacidade do CNES e o tempo de permanência, que ficaram como trabalho futuro.
- **Painel:** a prioridade desta disciplina foi tornar o modelo governável. Um painel sobre um modelo sem monitoramento ampliaria o risco de uso indevido.

## 3. A solução

```text
download.py      212 arquivos mensais do DATASUS (2008-12 a 2026-07), com manifesto de hashes
quality.py       qualidade dos 15,1 milhões de registros brutos
preprocessing.py contagem mensal de 3,6 milhões de internações DCNT; só totais estaduais são gravados
tuning.py        9 famílias de modelos × 3 janelas × 25 tentativas, validadas em 2022–2024
evaluation.py    teste em 2025 contra a regra de referência; registro da execução
monitoring.py    completude, integridade, drift e desempenho a cada lote novo
tracking.py      publicação das execuções, do modelo e do monitoramento no MLflow
```

O modelo escolhido é uma rede neural pequena (MLP), treinada com o histórico mensal desde 2010. Ela usa apenas meses anteriores ao previsto: contagens recentes, médias móveis, variação anual e calendário.

## 4. Como a solução é governada

| Prática | Como foi aplicada | Documento |
| --- | --- | --- |
| Versionamento | Git para código; hashes para arquivos brutos e dataset; pasta por execução com hash; tag `modelo-v1.0.0` | [versionamento.md](versionamento.md) |
| Rastreabilidade | Cada execução guarda dataset, parâmetros, versões, máquina, métricas, previsões e modelo; MLflow com experimento, busca, Model Registry e monitoramento | [rastreamento.md](rastreamento.md) |
| Reprodutibilidade | A entrega da Etapa 3 foi refeita do zero e as diferenças foram explicadas | [reproducao_etapa3.md](reproducao_etapa3.md) |
| Documentação | Model Card com usos permitidos e vedados; dicionário, origem, transformações e qualidade dos dados | [model_card.md](model_card.md), [dados.md](dados.md) |
| Gestão de riscos | 23 riscos de dados, modelo, privacidade, segurança e ética, com controle e responsável | [matriz_riscos.md](matriz_riscos.md) |
| Monitoramento | 19 indicadores com limite e ação; primeiro ciclo executado com dados de 2026 | [plano_monitoramento.md](plano_monitoramento.md) |
| Privacidade | Só três campos dos registros brutos são lidos; só totais estaduais, com no mínimo 470 internações por célula, são gravados | [dados.md](dados.md) |
| Supervisão humana | Nenhuma decisão automática; retreino e promoção de versão exigem aprovação registrada | [plano_monitoramento.md](plano_monitoramento.md) |

### Papéis

| Papel | Responsabilidade | Na fase acadêmica |
| --- | --- | --- |
| Responsável pelos dados | Download, qualidade, completude, integridade | Equipe |
| Responsável pelo modelo | Desempenho, viés, retreino, Model Card | Equipe |
| Dono do negócio | Uso da previsão, decisões de alocação, aprovação de novas versões | A definir: área de planejamento da SESA-PR |
| Alta gestão | Aprovar o uso da solução e seu alinhamento estratégico | Secretário de Estado da Saúde, conforme a Etapa 1 |

## 5. Riscos que exigem decisão

| Risco | Severidade | O que fazer |
| --- | --- | --- |
| Meses recentes incompletos parecem queda de demanda | Alta | Corrigir pela curva de completude ou prever um mês já maduro |
| Subestimação, principalmente em circulatórias e diabetes | Alta | Informar o viés ao planejamento e definir margem de segurança |
| Modelo muda entre máquinas | Alta | Usar o modelo versionado; retreinar e comparar sempre na mesma máquina |
| Decisão automática a partir da previsão | Alta | Exigir revisão humana registrada em cada uso |

Os riscos levantados na Etapa 1 foram tratados assim:

- **qualidade e atraso dos dados:** `quality.py` e o indicador de completude;
- **infraestrutura para atualização contínua:** pipeline de scripts simples, que roda em minutos num computador comum;
- **uso inadequado e confiança cega:** Model Card, usos vedados e revisão humana obrigatória;
- **baixa adesão dos gestores:** continua aberto, porque depende de uso real e do painel.

## 6. Próximos passos

1. Corrigir os meses incompletos antes de usar a previsão em operação.
2. Retreinar com 2025 incluído (versão 1.1.0) e promovê-la só se vencer a referência e a versão atual.
3. Acompanhar mais três ciclos de monitoramento antes de concluir sobre o desempenho em 2026.
4. Estender a previsão às regiões de saúde, com avaliação de privacidade.
5. Converter a previsão em demanda de leitos com dados do CNES e construir o painel para gestores.
