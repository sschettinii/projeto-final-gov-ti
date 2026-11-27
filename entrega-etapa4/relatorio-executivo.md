# Previsão de Internações por Doenças Crônicas no Paraná

Relatório executivo — Projeto Final de Governança de TI e de Dados (UEL)

## O que o projeto fez?

A equipe desenvolveu, entre as Etapas 1 e 4 da disciplina, uma solução de ciência de dados que tem como objetivo prever, com um mês de antecedência, quantas internações iniciais por doenças crônicas não transmissíveis (DCNT) os hospitais do Paraná vão registrar. A solução foi pensada para apoiar a Secretaria de Estado da Saúde do Paraná (SESA-PR), que tem dificuldade em prever essa demanda ao longo do ano e por isso alterna entre picos de superlotação e leitos subutilizados.

A previsão é feita para quatro grupos de doenças: circulatórias, diabetes, neoplasias malignas e respiratórias selecionadas. Os dados vêm do Sistema de Informações Hospitalares do SUS (SIH/SUS), público e mantido pelo DATASUS. Além de treinar o modelo, a Etapa 4 transformou a solução em algo governável, com versionamento, rastreamento de experimentos, Model Card, monitoramento e gestão de riscos.

## O que o projeto encontrou?

Foram lidos 15,1 milhões de registros de internação de 212 arquivos mensais (2008-12 a 2026-07), dos quais 3,6 milhões são internações iniciais por DCNT. Com esses dados foram testadas 9 famílias de modelos em 3 janelas de histórico, e o modelo escolhido foi uma rede neural pequena (MLP). No teste com o ano de 2025, comparado com a regra de repetir o mesmo mês do ano anterior:

- o erro médio caiu de 470 para 226 internações por mês e grupo;
- o erro proporcional total (WAPE) caiu de 8,27% para 3,98%;
- o erro proporcional médio dos grupos (macro-WAPE) caiu de 9,60% para 5,78%;
- o modelo errou menos que a referência nos quatro grupos;
- o pior grupo é diabetes, com 11,62% de erro, por ter as menores contagens;
- o modelo tende a subestimar a demanda em todos os grupos, principalmente em circulatórias.

Esse teste, porém, usou os meses anteriores já completos, e na prática eles ainda estariam chegando. Refazendo o teste como ele seria em operação, prevendo cada mês só com os dados disponíveis no mês anterior e corrigindo os meses recentes pela curva de completude, o erro proporcional médio dos grupos fica em 7,18%, ainda bem abaixo dos 9,60% da referência. Nesse cenário o modelo continua melhor em circulatórias e respiratórias, mas fica um pouco pior que a referência em diabetes e neoplasias. Sem a correção dos meses recentes, o erro passaria de 35%.

Entre os benefícios esperados estão a alocação de leitos, equipes e insumos antes dos picos, decisões de alocação apoiadas em dados e suporte à prestação de contas da alta gestão.

Com relação ao objetivo estratégico definido na Etapa 1, melhorar a eficiência na alocação de leitos, a análise mostrou que ele foi atendido em parte: a previsão existe e tem metade do erro da referência, mas é estadual, não por região, e prevê internações, não ocupação de leitos. A Etapa 1 também listava apoiar decisões gerenciais com base em dados, mas isso é o meio para chegar ao objetivo, e não um objetivo à parte: a solução já entrega previsões, alertas de monitoramento e registro de decisões, e falta o painel para gestores.

Por fim, ao simular a chegada de dados novos com as internações de 2026, o primeiro ciclo de monitoramento encontrou três pontos que precisam de atenção antes de qualquer uso real:

- os três meses mais recentes chegam incompletos, porque o DATASUS ainda está processando as AIHs, e usá-los sem correção reduziria a previsão em 20% a 36%;
- no início de 2026, avaliado como seria em operação, o modelo ficou pior que a regra de referência (7,99% contra 6,32% de erro proporcional médio) e subestimou diabetes em 11,72%;
- o teste de 2025 original usava informação que ainda não existiria no momento da previsão, e foi refeito sem esse vazamento;
- o mesmo código gera modelos um pouco diferentes em máquinas diferentes (Debian com Ryzen e macOS com M4).

## Como a solução será governada?

Para que a solução possa ser auditada e mantida, foram adotadas as seguintes práticas:

- Versionamento: Git para o código, SHA-256 para os arquivos brutos e o dataset, uma pasta com hash para cada execução e a tag `modelo-v1.0.0` para o modelo em uso;
- Rastreabilidade: cada execução guarda dataset, parâmetros, versões das bibliotecas, máquina, métricas, previsões e modelo, organizados também no MLflow;
- Documentação: Model Card com usos permitidos e proibidos, e dataset documentado com dicionário, qualidade, origem e transformações;
- Gestão de riscos: matriz com 22 riscos de dados, modelo, privacidade, segurança e ética, cada um com controle e responsável;
- Monitoramento: 19 indicadores de dados, modelo, negócio e governança, cada um com limite e ação;
- Privacidade: só três campos dos registros brutos são lidos e só contagens do estado são gravadas, com no mínimo 470 internações por célula;
- Supervisão humana: o modelo não toma nenhuma decisão sozinho, e retreino e troca de versão precisam de aprovação registrada.

Os papéis ficaram definidos assim: a equipe é responsável pelos dados e pelo modelo; a Diretoria de Contratualização e Regulação da SESA-PR, que coordena a regulação de leitos, é proposta como dona do negócio; e o Secretário de Estado da Saúde, como alta gestão, aprova o uso da solução.

## O que a equipe decidiu?

Para lidar com os riscos encontrados e com o uso da previsão pela gestão, a equipe recomenda que sejam conduzidas as seguintes ações:

- Usar a previsão apenas como apoio ao planejamento, sempre com revisão humana registrada em cada uso;
- Corrigir os meses incompletos pela curva de completude antes de prever, porque sem a correção o erro passa de 35%;
- Avaliar o modelo só com previsões feitas com os dados disponíveis na época, e esperar um erro próximo de 7%, não de 5,78%;
- Informar o planejamento sobre a direção do erro de cada grupo (subestima diabetes e circulatórias, superestima respiratórias) e definir uma margem de segurança;
- Usar sempre o modelo versionado, comparando retreinos apenas na mesma máquina;
- Retreinar com 2025 incluído (versão 1.1.0) e só trocar de versão se ela for melhor que a referência e que a versão atual;
- Acompanhar mais três ciclos de monitoramento antes de concluir algo sobre o desempenho em 2026;
- Estender a previsão para as regiões de saúde, com nova avaliação de privacidade, e converter a previsão em demanda de leitos com dados do CNES, junto com um painel para gestores.

## Decisões recentes

- 2026-11-19: a execução entregue na Etapa 3 (`20261105T205507`) foi definida como modelo oficial, mesmo com uma reprodução em outra máquina tendo resultado melhor, para não escolher modelo pelo resultado do teste;
- 2026-11-19: após o primeiro ciclo de monitoramento, decidiu-se não retreinar ainda, porque há só quatro meses maduros de 2026;
- 2026-11-23: a Diretoria de Contratualização e Regulação da SESA-PR foi proposta como dona do negócio;
- 2026-11-24: o teste de 2025 e o primeiro ciclo de monitoramento foram refeitos sem vazamento de dados futuros. O modelo oficial não mudou; mudou a forma de medir o erro, que passou a ser de 7,18% em 2025 e 7,99% no início de 2026. A decisão de não retreinar ainda foi mantida, porque a regra do plano pede três ciclos seguidos em alerta.

## Dados do projeto

| Item | Descrição |
| --- | --- |
| Equipe | André Tomonaga Schettini e Vitor da Costa Garcia |
| Disciplina | Governança de TI e de Dados, Universidade Estadual de Londrina |
| Organização-alvo | Secretaria de Estado da Saúde do Paraná (SESA-PR) |
| Fonte dos dados | SIH/SUS, DATASUS |
| Modelo em uso | MLP, versão 1.0.0 (tag `modelo-v1.0.0`) |
| Execução oficial | `20261105T205507` |
| Repositório | https://github.com/sschettinii/projeto-final-gov-ti |
