# Plano de monitoramento — modelo `modelo-v1.0.0`

**Versão:** 2.0.0

**Data:** 2026-11-19

**Script:** `monitoring.py` (limites definidos no início do arquivo)

**Primeiro ciclo:** `results/monitoring_202607/`, simulação com as internações de 2026

## 1. Pergunta

> Depois que o modelo entra em produção, como sabemos que ele continua funcionando adequadamente?

A cada nova competência publicada pelo DATASUS, a pipeline baixa o arquivo novo, roda `monitoring.py` e classifica cada indicador como **OK**, **Atenção** ou **Alerta**. Uma pessoa revisa o resultado, registra a decisão (seção 8) e libera, retém ou ressalva a previsão do mês seguinte.

```text
DATASUS publica a competência AAAA-MM
  → download.py      baixa o arquivo novo
  → quality.py       qualidade dos registros brutos, por arquivo
  → monitoring.py    confere o hash do modelo oficial antes de carregá-lo
                     completude → reconciliação → qualidade do lote → drift → desempenho
                     previsão do mês seguinte, com e sem correção de completude
                     → results/monitoring_AAAAMM/
  → revisão humana e registro de decisão
```

Cada ciclo grava uma pasta nova; nenhum resultado anterior é sobrescrito. O modelo não é retreinado no ciclo.

## 2. Primeiro ciclo: simulação com o lote de 2026

As internações de janeiro a julho de 2026, lidas dos arquivos processados até a competência 2026-07, foram tratadas como o lote novo. São dados reais, que não participaram da busca, do treino nem do teste.

### 2.1 Três dos sete meses ainda estão incompletos

Nas internações de 2023 e 2024, só 50,6% das AIHs estavam processadas no próprio mês de internação. A fração sobe para 80,4% um mês depois, 90,9% dois meses depois e 99,1% três meses depois.

| Mês | Meses desde a internação | Completude esperada | Situação |
| --- | ---: | ---: | --- |
| 2026-01 | 6 | 100,0% | Maduro |
| 2026-02 | 5 | 100,0% | Maduro |
| 2026-03 | 4 | 99,9% | Maduro |
| 2026-04 | 3 | 99,1% | Maduro |
| 2026-05 | 2 | 90,9% | Imaturo |
| 2026-06 | 1 | 80,4% | Imaturo |
| 2026-07 | 0 | 50,6% | Imaturo |

Os meses imaturos parecem uma queda de demanda, mas a queda é só atraso de processamento. Eles ficam fora do drift e do desempenho.

### 2.2 Usar os dados como chegam subestimaria a previsão de 20% a 36%

Em operação, a previsão de agosto de 2026 seria feita com os lags de maio a julho incompletos.

| Grupo | Dados como chegaram | Corrigindo a completude | Diferença |
| --- | ---: | ---: | ---: |
| Circulatórias | 8.068 | 11.069 | -27,1% |
| Diabetes | 460 | 575 | -20,0% |
| Neoplasias malignas | 4.735 | 7.363 | -35,7% |
| Respiratórias selecionadas | 3.743 | 5.708 | -34,4% |

O teste de 2025 usou séries consolidadas e não mede esse efeito. Esse é o risco D1 da [matriz de riscos](matriz_riscos.md), confirmado com dados reais. A correção pela curva média é uma primeira aproximação: com 50% de completude, ela dobra o valor observado e amplia o ruído.

### 2.3 Os dados chegaram íntegros

- **Reconciliação:** as 768 combinações de mês e grupo de 2010 a 2025, recalculadas com o lote novo, são idênticas ao dataset oficial.
- **Qualidade:** nenhuma célula zerada ou negativa e nenhuma feature ausente em 2026.

### 2.4 O início de 2026 cresceu menos que os anos anteriores

Janeiro a abril de 2026 foram comparados com janeiro a abril de 2023–2025:

| Indicador | Definição | Referência | 2026 | PSI | KS p-valor | Situação |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Razão sazonal | AIHs ÷ média dos 12 meses anteriores | 1,015 | 0,954 | 0,352 | 0,039 | Alerta |
| Crescimento anual | AIHs ÷ mesmo mês do ano anterior | 1,089 | 1,025 | 0,227 | 0,087 | Atenção |
| Razão do último mês | `lag_1` ÷ média dos 12 meses anteriores | 0,983 | 0,943 | 0,799 | 0,059 | Alerta |
| Variação anual | Feature `variacao_anual` | 0,077 | 0,059 | 0,025 | 0,949 | OK |

As contagens brutas não são comparadas: elas crescem com a tendência de longo prazo e acusariam drift em qualquer lote novo. As razões medem se a relação entre o mês e o seu passado mudou.

A média móvel de 12 meses do grupo circulatório está 11,6% acima do maior valor visto no treino (2010–2024), e a de neoplasias, 3,1% acima. O modelo recebe entradas fora da faixa que conheceu.

São 16 linhas contra 48 de referência. PSI e KS têm pouca potência com amostras desse tamanho; os alertas pedem investigação, não provam mudança estrutural.

### 2.5 O modelo perdeu a vantagem na macro-WAPE

| Janeiro a abril de 2026 | MAE | WAPE | Macro-WAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: |
| Baseline sazonal | 333,88 | 6,08% | 6,32% | -165,88 |
| MLP oficial | 308,88 | 5,62% | 6,72% | -125,11 |
| MLP oficial no teste de 2025 | 226,22 | 3,98% | 5,78% | -146,89 |

| Grupo | WAPE da MLP | WAPE do baseline | Viés relativo da MLP | Situação do viés |
| --- | ---: | ---: | ---: | --- |
| Circulatórias | 4,92% | 6,05% | -2,36% | OK |
| Diabetes | 9,86% | 6,58% | -9,86% | Atenção |
| Neoplasias malignas | 6,03% | 5,31% | -0,99% | OK |
| Respiratórias selecionadas | 6,07% | 7,35% | -3,00% | OK |

No volume total, a MLP continua melhor que o baseline (WAPE de 5,62% contra 6,08%). Na macro-WAPE, que dá o mesmo peso aos quatro grupos, ela ficou 0,40 ponto percentual pior. A perda vem de diabetes e neoplasias. Em diabetes, a MLP subestimou todos os quatro meses: o viés médio é igual ao erro médio (-64,49 e 64,49 AIHs).

Quatro meses são pouco para concluir que o modelo degradou. O quadro é coerente com a seção 2.4: o modelo aprendeu o crescimento de 2010–2024, e o início de 2026 cresceu menos. A diferença entre a MLP e o baseline também está dentro da variação numérica entre máquinas descrita no [Model Card](model_card.md).

### 2.6 Os indicadores reagem a falhas conhecidas

Dois cenários alteraram cópias do lote em memória e rodaram o mesmo monitoramento:

| Cenário | Indicadores que pioraram em relação ao lote real |
| --- | --- |
| Respiratórias +30% a partir de 2026-03 | Crescimento anual (atenção → alerta), macro-WAPE (OK → atenção), viés das respiratórias (OK → alerta) |
| Diabetes zerado em 2026-02 | Qualidade (OK → alerta, célula zerada), macro-WAPE (OK → alerta) |

O surto aparece como viés no grupo afetado; a falha de carga aparece primeiro na qualidade, antes de chegar ao modelo.

## 3. Indicadores de dados

| ID | Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- | --- |
| DA1 | Completude do mês | Fração esperada de AIHs já processadas, pela curva das internações de 2023–2024 | Completude mínima 95% | O mês fica fora da avaliação e não entra como lag sem correção |
| DA2 | Reconciliação do passado | Maior diferença percentual entre o lote e o dataset oficial em 2010–2025 | Atenção ≥ 0,5%; alerta ≥ 2% | Investigar reprocessamento retroativo; não usar o lote até explicar |
| DA3 | Valores ausentes e inválidos | Células zeradas ou negativas e features nulas no lote | Qualquer ocorrência gera alerta | Verificar o download e a classificação CID; reprocessar o mês |
| DA4 | Mudança de distribuição | PSI das razões da seção 2.4, contra os mesmos meses do ano em 2023–2025 | Atenção ≥ 0,1; alerta ≥ 0,25 | Investigar a causa (epidemia, política, codificação); reforçar a revisão humana |
| DA5 | Data drift (teste estatístico) | Teste KS nas mesmas razões | p-valor: atenção ≤ 0,05; alerta ≤ 0,01 | Igual a DA4; exige pelo menos três ciclos para concluir |
| DA6 | Extrapolação | Maior razão entre `lag_1` ou `media_movel_12` do lote e o máximo do grupo no treino | Atenção ≥ 1; alerta ≥ 1,1 | Avaliar retreino (seção 7) |
| DA7 | Qualidade da fonte | `quality.py`: proporção de registros por motivo de exclusão em cada arquivo novo | Variação maior que 1 ponto percentual em relação à média dos 12 arquivos anteriores | Abrir investigação com o responsável pelos dados |

## 4. Indicadores de modelo

| ID | Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- | --- |
| MO1 | Desempenho | Macro-WAPE da MLP nos meses maduros do lote | Atenção ≥ 7,5%; alerta ≥ 10% | Atenção: registrar e acompanhar. Alerta: previsão liberada só com ressalva |
| MO2 | Model drift contra o baseline | Macro-WAPE da MLP comparada à do baseline sazonal | MLP pior que o baseline gera alerta | Alerta em 3 ciclos seguidos dispara avaliação de retreino |
| MO3 | Erros sistemáticos | Viés médio ÷ volume médio, por grupo | Valor absoluto: atenção ≥ 5%; alerta ≥ 10% | Informar a direção do erro ao planejamento; considerar margem de segurança |
| MO4 | Erro pontual extremo | Maior erro percentual de um mês e grupo, em `predictions.csv` | Alerta acima de 20% | Revisar o mês; verificar ruptura |

O limite de atenção da macro-WAPE (7,5%) fica cerca de 30% acima do teste de 2025 (5,78%) e acima da variação numérica entre máquinas (5,00% a 5,78%). O limite de alerta (10%) corresponde ao erro médio da mesma arquitetura durante a pandemia (10,62%).

## 5. Indicadores de negócio

| ID | Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- | --- |
| NE1 | Benefício esperado | Erro evitado: MAE do baseline menos MAE da MLP, em AIHs por mês e grupo | Benefício igual ou menor que zero por 3 ciclos | O modelo deixou de agregar valor; avaliar retreino ou voltar ao baseline |
| NE2 | Impacto no planejamento | Subestimação acumulada no trimestre, em AIHs, pelo viés da MLP | Mais de 5% do volume do trimestre | Revisar a margem de segurança com o planejamento |
| NE3 | Utilização | Proporção de ciclos em que a previsão foi consultada no planejamento | Menos de 50% dos ciclos num semestre | Entender por que não é usada; ajustar formato ou encerrar |
| NE4 | Decisões com revisão humana | Proporção das decisões que usaram a previsão e têm registro de revisão | Qualquer decisão sem registro | Tratar como incidente de governança (risco E1) |

Referência do benefício: no teste de 2025, o erro evitado foi de 243,59 AIHs por mês e grupo (469,81 contra 226,22). Em janeiro a abril de 2026, caiu para 25,00 (333,88 contra 308,88).

## 6. Indicadores de governança

| ID | Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- | --- |
| GO1 | Incidentes | Vazamento, falha da pipeline, modelo carregado com hash divergente | Qualquer ocorrência | Interromper o uso, preservar evidências e registrar |
| GO2 | Reclamações | Issues ou contestações sobre a previsão | Qualquer reclamação sem resposta em 30 dias | Responder e registrar a decisão |
| GO3 | Vieses entre grupos | Diferença entre o maior e o menor WAPE por grupo | Atenção ≥ 8 pontos percentuais; alerta ≥ 10 | Investigar o grupo pior; avaliar ajuste ou aviso específico |
| GO4 | Necessidade de revisão | Gatilhos da seção 7, mudança na fonte, nova finalidade de uso | Qualquer gatilho | Revisar Model Card e matriz de riscos |

Referência de viés entre grupos: no teste de 2025 a diferença foi de 9,28 pontos percentuais (diabetes 11,62%, neoplasias 2,34%), já em atenção. Em janeiro a abril de 2026 foi de 4,94 pontos (diabetes 9,86%, circulatórias 4,92%).

## 7. Gatilhos de retreino e de promoção

Uma nova versão do modelo é avaliada quando ocorrer qualquer um destes gatilhos:

- MO1 em alerta por 2 ciclos seguidos;
- MO2 em alerta por 3 ciclos seguidos;
- DA6 em alerta;
- um ano completo novo de dados maduros (a cada abril, com o ano anterior consolidado).

A nova versão só é promovida se:

1. rodar `tuning.py` e `evaluation.py` com o período estendido, gerando nova pasta em `results/` e nova linha em `registry.csv` (versão MINOR);
2. vencer o baseline e a versão em uso nos mesmos meses maduros mais recentes;
3. tiver tag `modelo-vX.Y.Z`, Model Card e matriz de riscos atualizados;
4. receber aprovação registrada do responsável pelo modelo e do dono do negócio.

Por causa da instabilidade numérica (risco M6), o retreino e a comparação acontecem na mesma máquina, e a máquina fica registrada. O retreino nunca é automático, e a versão anterior continua disponível pela tag.

## 8. Resposta por nível, responsáveis e registro de decisões

| Nível | Prazo | O que acontece |
| --- | --- | --- |
| OK | No ciclo | Previsão liberada |
| Atenção | Até o próximo ciclo | O responsável investiga e registra a causa; previsão liberada com nota |
| Alerta | Antes de liberar a previsão | Previsão retida ou liberada só com ressalva escrita; dono do negócio informado |

| Papel | Indicadores | Responsável na fase acadêmica |
| --- | --- | --- |
| Responsável pelos dados | DA1–DA7, GO1 | Equipe (André e Vitor) |
| Responsável pelo modelo | MO1–MO4, GO3, GO4 | Equipe (André e Vitor) |
| Dono do negócio | NE1–NE4, GO2 | A definir em operação real |

| Ciclo | Níveis principais | Decisão | Responsável |
| --- | --- | --- | --- |
| 2026-07 (simulação) | DA1: 3 meses imaturos; DA2 e DA3 OK; DA4 alerta; DA6 alerta (circulatórias 1,116); MO1 OK (6,72%); MO2 alerta (MLP 6,72% contra baseline 6,32%); MO3 atenção (diabetes -9,86%); MO4 OK (maior erro: 17,73%, diabetes em 2026-01) | Não usar maio a julho sem correção. Não retreinar ainda: MO2 está no primeiro ciclo, há só 4 meses maduros e a diferença está dentro da variação numérica. Preparar o retreino `1.1.0` com 2025 incluído por causa de DA6. Avisar o planejamento sobre a subestimação em diabetes | Equipe |

## 9. Relação com a matriz de riscos

| Risco | Indicadores |
| --- | --- |
| D1 — atraso de processamento | DA1 |
| D2 — mudança de layout | DA2, DA3 |
| D3 — CID inválido nas faixas | DA7 |
| D5 — data drift | DA4, DA5, DA6 |
| M1 — ruptura abrupta | MO1, MO4 |
| M2 — subestimação | MO3, NE2 |
| M3 — degradação gradual | MO1, MO2, NE1 |
| M6 — instabilidade numérica | Seção 7 |
| S3 — artefato adulterado | GO1 |
| E1 — decisão automática | NE4 |
| E3 — desempenho desigual entre grupos | GO3 |

## 10. Reprodução e limitações

Dentro de `solucao/`, com os 212 arquivos brutos em `data/raw/`:

```bash
.venv/bin/python monitoring.py
```

O script leva cerca de 3 minutos e recusa sobrescrever uma pasta de ciclo existente.

- Com só quatro meses maduros, DA4, DA5 e MO2 oscilam. Decisões de retreino dependem de ciclos seguidos.
- A curva de completude é única para os quatro grupos; uma curva por grupo melhoraria DA1 e a correção.
- Os indicadores de negócio e de governança dependem de registro manual e não foram exercidos fora da simulação.
- Os limites são uma primeira calibração e devem ser revisados após 12 ciclos reais.
