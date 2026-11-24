# Plano de monitoramento

Depois que o modelo entra em produção, como sabemos que ele continua funcionando adequadamente? Para responder essa pergunta repetimos, a cada mês, um ciclo de verificação parecido com o que fizemos para escolher o modelo, só que agora olhando para os dados que acabaram de chegar.

## Simulação chegada de novos dados

Para testar o plano, simulamos a chegada de um conjunto de dados novo usando as internações de janeiro a julho de 2026. São dados reais que não foram usados nem na busca, nem no treino, nem no teste do modelo.

A primeira coisa que apareceu foi que os meses mais recentes chegam incompletos. Uma internação pode levar alguns meses para ser processada pelo DATASUS, e olhando para 2023 e 2024 vimos que só metade das AIHs (50,6%) aparece no próprio mês de internação. Esse número sobe para 80,4% um mês depois, 90,9% dois meses depois e 99,1% três meses depois. Por isso, maio, junho e julho de 2026 ainda estavam imaturos, e se a gente usasse esses meses do jeito que chegaram para prever agosto, a previsão sairia de 20% a 36% menor do que deveria, dependendo do grupo. Isso não aparecia no teste de 2025, porque lá as séries já estavam completas. Foi o achado mais importante da simulação.

Esse achado também mostrou um vazamento de dados no nosso próprio teste. Para prever dezembro de 2025, o modelo tinha usado novembro já completo, mas no começo de dezembro só metade das AIHs de novembro teria chegado. Ou seja, o teste usava uma informação que ainda não existiria no momento da previsão. Para corrigir, criamos o `realtime_evaluation.py`, que refaz as previsões como elas teriam sido feitas na época: cada mês é previsto só com os arquivos processados até o mês anterior, com os meses recentes corrigidos pela curva de completude daquele momento, e comparado com o valor final. Com essa regra, a macro-WAPE do teste de 2025 sobe de 5,78% para 7,18%, que continua bem melhor que os 9,60% da regra de referência. Sem a correção pela curva, o erro iria para 35,19%. O resultado está em `results/realtime_202607/`.

Fora isso, os dados chegaram íntegros. Recalculando 2010 a 2025 com os arquivos novos, as 768 combinações de mês e grupo deram exatamente o mesmo valor do dataset oficial, e não apareceu nenhum mês zerado ou feature vazia em 2026.

Nos quatro meses maduros (janeiro a abril de 2026), o início do ano cresceu menos do que nos anos anteriores, e alguns indicadores de drift entraram em alerta. A média móvel de 12 meses do grupo circulatório ficou 11,6% acima do maior valor que o modelo viu no treino, ou seja, o modelo começou a receber entradas fora da faixa que conhece. O desempenho foi medido com a mesma regra do `realtime_evaluation.py`, com as previsões como teriam sido emitidas em cada mês. A MLP ficou pior que a regra de referência (macro-WAPE de 7,99% contra 6,32%, e WAPE de 6,38% contra 6,08%), subestimou diabetes em 11,72% e superestimou respiratórias em 6,70%. Na primeira versão do ciclo, que avaliava previsões refeitas com os arquivos de julho, a macro-WAPE tinha sido 6,72%. As duas versões ficam guardadas: `results/monitoring_202607/` e `results/monitoring_202607_v2/`.

Para conferir que os indicadores realmente reagem a problemas, também rodamos dois cenários falsos. Num deles aumentamos as respiratórias em 30% a partir de março, simulando um surto, e o aumento apareceu no indicador de crescimento anual, que passou de atenção para alerta. No outro zeramos diabetes em fevereiro, simulando uma falha de carga, e o problema foi pego primeiro pelo indicador de qualidade, antes de chegar ao modelo.

A decisão desse primeiro ciclo foi não usar maio a julho sem corrigir a incompletude e não retreinar ainda. Quatro meses é pouco para concluir que o modelo piorou, e a regra do plano pede três ciclos seguidos em alerta antes de avaliar um retreino. Mas a diferença para a regra de referência (1,67 ponto percentual) já é maior que a variação que vimos entre máquinas, e o modelo está recebendo valores acima do que viu no treino. Por isso fica preparado o retreino da versão 1.1.0 com 2025 incluído, e o planejamento deve ser avisado de que o modelo subestima diabetes.

## Indicadores

Dividimos os indicadores entre os quatro grupos pedidos: dados, modelo, negócio e governança. Para cada um definimos como medir, um limite e a ação quando o limite é passado.

### Dados

Aqui a preocupação é saber se o dado que chegou é confiável e se ele ainda se parece com o que o modelo aprendeu. 

| Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- |
| Completude do mês | Fração esperada de AIHs já processadas, pela curva de 2023–2024 | Mínimo de 95% | O mês fica fora da avaliação e não é usado na previsão sem correção |
| Reconciliação do passado | Diferença entre o lote novo e o dataset oficial em 2010–2025 | Atenção a partir de 0,5%; alerta a partir de 2% | Investigar reprocessamento retroativo antes de usar o lote |
| Valores ausentes e inválidos | Meses zerados ou negativos e features vazias | Qualquer ocorrência é alerta | Conferir o download e a classificação do CID e reprocessar o mês |
| Mudança de distribuição | PSI das razões sazonais | Atenção a partir de 0,1; alerta a partir de 0,25 | Investigar a causa (epidemia, política, codificação) e reforçar a revisão humana |
| Data drift | Teste KS nas mesmas razões | p-valor: atenção até 0,05; alerta até 0,01 | Igual ao anterior; só concluir depois de três ciclos |
| Extrapolação | Entradas do lote comparadas ao maior valor visto no treino | Atenção acima do máximo; alerta 10% acima | Avaliar retreino |
| Qualidade da fonte | Proporção de registros excluídos por motivo, pelo `quality.py` | Variação de mais de 1 ponto percentual contra os 12 arquivos anteriores | Investigar com o responsável pelos dados |

### Modelo

Para o modelo, o que importa é se ele continua acertando e se continua valendo mais que a regra simples de repetir o mesmo mês do ano anterior.

| Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- |
| Desempenho | Macro-WAPE | Atenção a partir de 7,5%; alerta a partir de 10% | Atenção: acompanhar. Alerta: reconsiderar predições |
| Model drift | Macro-WAPE da MLP contra a baseline | MLP pior que a baseline é alerta | Três ciclos seguidos em alerta disparam a avaliação de retreino |
| Erros sistemáticos | Viés médio dividido pelo volume médio, por grupo | Atenção a partir de 5%; alerta a partir de 10% | Avisar o planejamento da direção do erro e considerar margem de segurança |
| Erro extremo | Maior erro percentual de um mês e grupo | Alerta acima de 20% | Revisar o mês e verificar se houve ruptura |

O limite de atenção de 7,5% fica acima da variação que vimos entre máquinas. O de alerta, 10%, é perto do erro que a mesma arquitetura teve durante a pandemia.

### Negócio

Os indicadores de negócio respondem se a solução está trazendo o benefício esperado.

| Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- |
| Benefício esperado | Erro da baseline menos erro da MLP | Benefício zero ou negativo por 3 ciclos | Avaliar retreino ou voltar para a regra de referência |
| Impacto no planejamento | Subestimação acumulada no trimestre | Mais de 5% do volume do trimestre | Revisar a margem de segurança com o planejamento |
| Utilização | Proporção de ciclos em que a previsão foi consultada | Menos de 50% num semestre | Entender por que não está sendo usada; ajustar ou encerrar |
| Revisão humana | Decisões que usaram a previsão com revisão registrada | Qualquer decisão sem registro | Tratar como incidente de governança |

### Governança

Por último, a governança acompanha o que não aparece nas métricas: incidentes, reclamações de quem usa, vieses entre os grupos de doença e os momentos em que a documentação precisa ser revista.

| Indicador | Como é medido | Limite | Ação |
| --- | --- | --- | --- |
| Incidentes | Vazamento de dados, falha da pipeline ou modelo com hash diferente | Qualquer ocorrência | Interromper o uso, guardar as evidências e registrar |
| Reclamações | Issues ou contestações sobre a previsão | Sem resposta em 30 dias | Responder e registrar a decisão |
| Necessidade de revisão | Gatilho de retreino, mudança na fonte ou novo uso da previsão | Qualquer gatilho | Revisar o Model Card e a matriz de riscos |
