# Dataset documentado — AIHs iniciais DCNT por mês e grupo

**Data:** 2026-11-19

**Dataset:** `data/modelagem_dcnt_mensal_201001_202512.parquet`, gerado por `preprocessing.py`

## 1. Origem

| Item | Descrição |
| --- | --- |
| Sistema | SIH/SUS — Sistema de Informações Hospitalares do SUS, mantido pelo DATASUS |
| Arquivo | AIH reduzida (`RD`) de estabelecimentos do Paraná (`PR`): `RDPRaamm.dbc`, onde `aamm` é a competência de processamento |
| Endereço | `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/` |
| Acesso | Público, sem credencial |
| Arquivos usados | 212, de `RDPR0812.dbc` (2008-12) a `RDPR2607.dbc` (2026-07) |
| Registros lidos | 15.131.255 |
| Coleta | `download.py`; arquivos já baixados não são baixados de novo |

A competência indica o mês em que a AIH foi **processada**, não o mês da internação. Uma internação pode aparecer em arquivos de meses seguintes. Por isso, o dataset usa as competências até 2026-07 para contar internações até 2025-12.

### Campos usados do arquivo bruto

| Campo | Conteúdo | Uso |
| --- | --- | --- |
| `DT_INTER` | Data de internação, `AAAAMMDD` | Mês de internação (`AAAA-MM`) |
| `DIAG_PRINC` | CID-10 do diagnóstico principal | Grupo DCNT pela categoria (3 primeiros caracteres) |
| `IDENT` | Tipo de AIH: `1` inicial, `5` continuidade de longa permanência | Só `1` é contada |

Nenhum outro campo é lido. Identificadores, datas exatas, município, sexo, idade, procedimento, valor e desfecho não entram na pipeline.

## 2. Transformações

| Ordem | Regra | Onde |
| --- | --- | --- |
| 1 | Descompactar cada DBC num arquivo temporário e ler o DBF registro a registro | `count_admissions` |
| 2 | Mês de internação = 6 primeiros dígitos de `DT_INTER` | `count_admissions` |
| 3 | Manter internações de 2008-12 a 2025-12 | `count_admissions` |
| 4 | Classificar o CID principal pela categoria: circulatórias `I00–I99`, diabetes `E10–E14`, neoplasias malignas `C00–C97`, respiratórias selecionadas `J30–J98` sem `J36` | `disease_group` |
| 5 | Contar só AIHs iniciais (`IDENT = 1`) com grupo DCNT | `count_admissions` |
| 6 | Somar as contagens dos 212 arquivos por mês e grupo | `__main__` |
| 7 | Montar a grade completa de 205 meses × 4 grupos, com zero onde não houver registro | `build_features` |
| 8 | Calcular features só com meses anteriores: lags, médias móveis deslocadas um mês, variação anual e calendário | `build_features` |
| 9 | Descartar os 13 meses de contexto (2008-12 a 2009-12) e gravar 2010-01 a 2025-12 | `build_features` |

## 3. Validação

O `preprocessing.py` interrompe a execução se qualquer uma destas condições falhar:

| Verificação | Valor esperado |
| --- | --- |
| Arquivos brutos | 212 |
| AIHs iniciais DCNT de 2008-12 a 2025-12 | 3.608.323 |
| Linhas do dataset | 768 |
| Valores ausentes | Nenhum |
| AIHs nos meses-alvo | 3.396.090 |

Os totais esperados são os mesmos do tratamento completo da Etapa 2, que validava cada código CID contra a lista oficial. A coincidência mostra que a regra simplificada por categoria seleciona o mesmo conjunto de AIHs.

## 4. Qualidade

`quality.py` classifica cada registro bruto pelo primeiro motivo que o exclui e grava uma linha por arquivo em `results/data_quality.csv`. A soma de cada linha fecha com o total de registros do arquivo.

| Situação | Registros | % do total |
| --- | ---: | ---: |
| Total lido | 15.131.255 | 100,00% |
| Data de internação inválida ou vazia | 0 | 0,00% |
| Internação fora de 2008-12 a 2025-12 | 637.756 | 4,21% |
| CID principal vazio | 0 | 0,00% |
| CID na categoria excluída `J36` | 7.832 | 0,05% |
| CID fora dos grupos DCNT | 10.876.693 | 71,88% |
| CID DCNT em AIH de continuidade (`IDENT = 5`) | 651 | 0,00% |
| **Selecionados** | **3.608.323** | **23,85%** |

Outras medidas:

- `IDENT`: 14.808.763 registros `1`, 322.492 registros `5` e nenhum outro valor;
- por arquivo, de 53.099 a 99.618 registros;
- por grupo, entre os selecionados: 1.744.212 circulatórias, 969.147 neoplasias malignas, 755.485 respiratórias selecionadas e 139.479 diabetes.

A regra por categoria não verifica se o código completo existe na CID-10. Um código inválido dentro de uma faixa DCNT seria contado. Como o total coincide com o da Etapa 2, que fazia essa verificação, isso não afetou os dados atuais. O plano de monitoramento acompanha essa medida.

## 5. Dicionário do dataset

Uma linha por mês de internação e grupo. 768 linhas, sem valores ausentes.

| Coluna | Tipo | Descrição | Faixa observada |
| --- | --- | --- | --- |
| `mes_internacao` | texto `AAAA-MM` | Mês de internação previsto | 2010-01 a 2025-12 |
| `grupo_dcnt` | texto | `circulatorias`, `diabetes`, `neoplasias_malignas` ou `respiratorias_selecionadas` | 4 valores |
| `aih_iniciais` | inteiro | **Alvo.** AIHs iniciais do grupo no mês | 470 a 11.671 |
| `mes_numero` | inteiro | Mês do ano | 1 a 12 |
| `mes_seno` | real | Seno de 2π·mês/12, para representar o ciclo anual | -1 a 1 |
| `mes_cosseno` | real | Cosseno de 2π·mês/12 | -1 a 1 |
| `indice_temporal` | inteiro | Posição do mês na série, contando a partir de 2008-12 = 0 | 13 a 204 |
| `lag_1`, `lag_2`, `lag_3`, `lag_6`, `lag_12` | inteiro | AIHs do mesmo grupo 1, 2, 3, 6 e 12 meses antes | 470 a 11.671 |
| `media_movel_3`, `media_movel_6`, `media_movel_12` | real | Média das AIHs dos 3, 6 e 12 meses anteriores, sem incluir o mês previsto | 493,33 a 11.618,33 |
| `variacao_anual` | real | (`lag_1` − AIHs de 13 meses antes) ÷ AIHs de 13 meses antes | -0,496 a 0,990 |

Totais por grupo nos meses-alvo:

| Grupo | AIHs | Média mensal | Mínimo | Máximo |
| --- | ---: | ---: | ---: | ---: |
| Circulatórias | 1.639.778 | 8.540,5 | 5.204 | 11.671 |
| Neoplasias malignas | 933.169 | 4.860,3 | 2.683 | 7.565 |
| Respiratórias selecionadas | 694.502 | 3.617,2 | 1.767 | 5.467 |
| Diabetes | 128.641 | 670,0 | 470 | 951 |

## 6. Versão e integridade

- O SHA-256 do dataset vai para o `config.json` de cada execução de `tuning.py`, e o `evaluation.py` recusa avaliar se o arquivo mudou.
- O SHA-256 é calculado sobre os bytes do Parquet, que incluem metadados de gravação. Na reprodução da Etapa 3, o mesmo conteúdo gerou `c074b63e…` na máquina da entrega e `4c529674…` em outro Mac ([reproducao_etapa3.md](reproducao_etapa3.md)). Quando o hash diverge, deve-se comparar o conteúdo antes de concluir que os dados mudaram.

## 7. Privacidade

Os arquivos brutos contêm dados pessoais sensíveis de saúde, ainda que publicados pelo DATASUS. A pipeline reduz a exposição desde a leitura:

- só três campos de cada registro são lidos;
- só contagens mensais estaduais são gravadas;
- a menor célula do dataset tem 470 AIHs, longe de qualquer limite de proteção para contagens pequenas;
- os arquivos brutos e o dataset ficam em `data/`, fora do Git.

## 8. Diferenças em relação ao tratamento da Etapa 2

A Etapa 2 produziu uma base tratada por AIH, com 29 campos, relatório de qualidade e base reduzida para publicação (documentação na pasta `docs/` da raiz do repositório). A pipeline simplificada:

- conta direto dos arquivos brutos, sem gravar a base por AIH;
- classifica o CID por faixas de categoria, sem a lista oficial de códigos;
- não registra o mês de processamento de cada AIH no dataset.

O resultado é o mesmo número de AIHs selecionadas. A documentação da Etapa 2 continua válida como descrição detalhada da fonte.
