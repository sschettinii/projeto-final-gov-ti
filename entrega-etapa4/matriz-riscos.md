# Matriz de riscos

Essa matriz lista o que pode dar errado com a solução, desde o download dos dados até o uso da previsão no planejamento, e o que fazemos para evitar ou perceber cada problema. Ela cobre o modelo oficial (versão 1.0.0) e a pipeline de `solucao/` que o gera, e está dividida nos cinco tipos de risco pedidos: dados, modelo, privacidade, segurança e ética.

## Como os riscos foram avaliados

Cada risco recebeu uma nota de 1 a 3 para probabilidade e outra para impacto. Na probabilidade, 1 é improvável dentro de um ano, 2 é algo que já aconteceu ou pode acontecer em algumas atualizações, e 3 é esperado na operação normal. No impacto, 1 é só retrabalho técnico, 2 é uma previsão pior ou atrasada que ainda dá para corrigir antes de usar, e 3 é uma decisão errada sobre recursos, exposição de dados pessoais ou perda de confiança na solução.

A severidade é a probabilidade vezes o impacto. Riscos de severidade 6 a 9 são altos e precisam de controle antes de qualquer uso real. De 3 a 4 são médios, com controle definido e acompanhamento. De 1 a 2 são baixos, aceitos e só registrados.

Os responsáveis são papéis, não pessoas. Na fase acadêmica, o responsável pelos dados e o responsável pelo modelo são a própria equipe. O dono do negócio proposto é a Diretoria de Contratualização e Regulação da SESA-PR.

## Dados

O maior risco do projeto está aqui. Uma internação pode levar meses para ser processada pelo DATASUS, então os meses mais recentes sempre chegam incompletos e parecem uma queda de demanda que não existe. Na simulação com 2026, usar esses meses sem correção deixaria a previsão de 20% a 36% menor.

| ID | Risco | P | I | Sev. | Controle | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- |
| D1 | Meses recentes chegam incompletos e parecem queda de demanda | 3 | 3 | 9 | O monitoramento mede a completude e tira da avaliação os meses abaixo de 95%; antes de prever, os meses recentes são corrigidos pela curva de completude (sem a correção, o erro em 2025 passaria de 35%) | Dados |
| D2 | O DATASUS muda o layout ou os códigos dos arquivos | 2 | 2 | 4 | O `preprocessing.py` para se faltar um campo ou se os totais não baterem | Dados |
| D3 | Um código CID inválido dentro de uma faixa DCNT entra na contagem | 2 | 2 | 4 | O `quality.py` mede as exclusões por motivo, e o total bate com o da Etapa 2, que validava os códigos | Dados |
| D4 | Arquivo bruto corrompido ou substituído sem ninguém perceber | 1 | 3 | 3 | Os totais conferidos pelo `preprocessing.py` acusam mudança no histórico | Dados |
| D5 | A distribuição dos dados muda (data drift) | 2 | 2 | 4 | O monitoramento mede drift e extrapolação a cada lote; só concluir depois de três ciclos | Modelo |
| D6 | O mesmo dataset tem outro hash em outra máquina e a avaliação é bloqueada sem motivo | 3 | 1 | 3 | Quando o hash for diferente, comparar o conteúdo antes de concluir que os dados mudaram | Dados |

## Modelo

No modelo, os riscos altos são três. O primeiro é o erro sistemático: com os dados consolidados de 2025 o modelo errou para baixo nos quatro grupos, e prevendo como seria em operação ele subestima diabetes em 13,43% e superestima respiratórias em 7,31%. O segundo é que a MLP muda de uma máquina para outra: o mesmo código deu macro-WAPE de 5,78% numa máquina e 5,00% em outra. O terceiro é medir o erro com informação que não existiria na hora da previsão. Foi o que aconteceu no nosso teste de 2025: ele usava os meses anteriores já completos e deu 5,78%, mas refeito como seria em operação o erro é de 7,18%.

| ID | Risco | P | I | Sev. | Controle | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- |
| M1 | Ruptura brusca da demanda (uma nova pandemia) | 1 | 3 | 3 | O efeito da pandemia foi medido (erro de 4,13% para 10,62%); alerta de erro e revisão humana durante a ruptura | Modelo |
| M2 | O modelo erra sempre para o mesmo lado em um grupo (subestima diabetes e circulatórias, superestima respiratórias) | 3 | 2 | 6 | Viés reportado por grupo e monitorado a cada ciclo; margem de segurança decidida pelo planejamento | Modelo |
| M3 | O desempenho piora aos poucos (model drift) | 2 | 2 | 4 | A baseline é computada em toda avaliação; retreinar quando o modelo perder para ela | Modelo |
| M4 | O modelo ou os parâmetros mudam sem registro | 1 | 3 | 3 | Cada execução grava sua configuração, o hash da pasta fica no `registry.csv` e o modelo em uso tem tag no Git | Modelo |
| M5 | O mesmo código gera outro modelo em outra máquina | 3 | 2 | 6 | O modelo oficial é o arquivo versionado, não um novo treino; retreinos são comparados na mesma máquina | Modelo |
| M6 | A avaliação usa dados que ainda não existiriam no momento da previsão (vazamento), e o erro medido sai menor que o real | 2 | 3 | 6 | O `realtime_evaluation.py` prevê cada mês só com os arquivos processados até o mês anterior; o monitoramento avalia só previsões feitas desse jeito | Modelo |

## Privacidade

Os arquivos do SIH/SUS são públicos, mas têm dados pessoais sensíveis de saúde. Por isso a pipeline lê só três campos de cada registro e grava só contagens do estado inteiro, e o risco de privacidade ficou baixo. Ele volta a crescer se alguém quiser previsões por município, sexo ou idade, porque contagens pequenas facilitam identificar pessoas.

| ID | Risco | P | I | Sev. | Controle | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- |
| P1 | Reidentificação a partir dos arquivos brutos guardados no computador | 1 | 3 | 3 | Só três campos são lidos, nenhum registro individual é gravado e `data/` fica fora do Git; falta definir um prazo para apagar os arquivos brutos | Dados |
| P2 | Publicar contagens pequenas em recortes novos (município, sexo, idade) | 1 | 3 | 3 | Hoje a menor contagem é de 470 internações; qualquer recorte novo precisa esconder células menores que 10, como na Etapa 2 | Dados |
| P3 | Usar os dados para uma finalidade nova sem reavaliar | 2 | 2 | 4 | Revisar esta matriz antes de integrar uma fonte ou um recorte novo | Equipe |

## Segurança

Os riscos de segurança são os mais baixos, porque os dados são públicos, não existe senha ou token na solução e as versões das bibliotecas são fixas. O ponto que merece cuidado é o arquivo do modelo: um `.joblib` adulterado pode executar código quando é carregado.

| ID | Risco | P | I | Sev. | Controle | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- |
| S1 | Vazamento dos arquivos brutos por compartilhamento indevido | 1 | 2 | 2 | `data/` fica fora do Git e do pacote de entrega | Dados |
| S2 | O arquivo do modelo é adulterado e executa código ao ser carregado | 1 | 3 | 3 | O hash da pasta da execução fica no `registry.csv`; conferir antes de carregar o modelo | Modelo |
| S3 | Uma biblioteca em outra versão muda o resultado | 1 | 2 | 2 | Versões fixas no `requirements.txt` e registradas em cada execução | Equipe |

## Ética

O principal risco ético é a previsão virar decisão automática, por exemplo cortar leitos porque o modelo previu menos internações. O modelo é só apoio ao planejamento, e toda decisão precisa de uma pessoa revisando. Também é preciso cuidado com diabetes, que tem o maior erro, para que esse grupo não acabe recebendo um planejamento pior.

| ID | Risco | P | I | Sev. | Controle | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- |
| E1 | Recursos decididos automaticamente com base na previsão | 2 | 3 | 6 | Uso proibido no Model Card; exigir registro de revisão humana em cada uso | Dono do negócio |
| E2 | Usar a previsão para ranquear ou punir hospitais e municípios | 1 | 3 | 3 | O modelo é só estadual, e esse uso é proibido no Model Card | Dono do negócio |
| E3 | O grupo com pior desempenho recebe um planejamento pior (diabetes, 13,43% de erro em tempo real) | 2 | 2 | 4 | Métricas por grupo, macro-WAPE como critério de escolha e monitoramento do erro por grupo | Modelo |
| E4 | Tratar a previsão do SUS como se valesse para toda a população | 2 | 2 | 4 | Cobertura declarada no Model Card e no dataset documentado, e avisada sempre que os resultados forem apresentados | Equipe |

## Mapa de calor

| Probabilidade \ Impacto | 1 — Baixo | 2 — Médio | 3 — Alto |
| --- | --- | --- | --- |
| **3 — Alta** | D6 | M2, M5 | D1 |
| **2 — Média** | | D2, D3, D5, M3, P3, E3, E4 | M6, E1 |
| **1 — Baixa** | | S1, S3 | D4, M1, M4, P1, P2, S2, E2 |
