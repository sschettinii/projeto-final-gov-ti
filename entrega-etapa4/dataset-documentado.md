# Dataset Documentado

O dataset usado no treino e na avaliação é `data/modelagem_dcnt_mensal_201001_202512.parquet`. Montado a partir dos arquivos brutos do DATASUS em dois passos, dentro de `solucao/`:

1. `python download.py` baixa os arquivos mensais do Paraná.
2. `python preprocessing.py` lê os arquivos brutos, conta as internações e calcula as features.

## Data Dictionary

Uma linha por mês de internação e grupo. 768 linhas (192 meses × 4 grupos), sem valores ausentes.

| Coluna | Tipo | Descrição |
| --- | --- | --- | 
| mes_internacao | texto (AAAA-MM) | Mês de internação previsto | 2010-01 a 2025-12 |
| grupo_dcnt | texto | circulatorias, diabetes, neoplasias_malignas ou respiratorias_selecionadas |
| aih_iniciais | inteiro | **Alvo.** AIHs iniciais do grupo no mês |
| mes_numero | inteiro | Mês do ano |
| mes_seno | real | Seno de 2π·mês/12, para representar o ciclo anual |
| mes_cosseno | real | Cosseno de 2π·mês/12 |
| indice_temporal | inteiro | Posição do mês na série, contando a partir de 2008-12 = 0 |
| lag_1, lag_2, lag_3, lag_6, lag_12 | inteiro | AIHs do mesmo grupo 1, 2, 3, 6 e 12 meses antes |
| media_movel_3, media_movel_6, media_movel_12 | real | Média das AIHs dos 3, 6 e 12 meses anteriores, sem incluir o mês previsto |
| variacao_anual | real | (lag_1 − AIHs de 13 meses antes) ÷ AIHs de 13 meses antes |

Todas as features usam só meses anteriores ao mês previsto. Totais por grupo nos meses-alvo:

| Grupo | AIHs | Média mensal | Mínimo | Máximo |
| --- | ---: | ---: | ---: | ---: |
| Circulatórias | 1.639.778 | 8.540,5 | 5.204 | 11.671 |
| Neoplasias malignas | 933.169 | 4.860,3 | 2.683 | 7.565 |
| Respiratórias selecionadas | 694.502 | 3.617,2 | 1.767 | 5.467 |
| Diabetes | 128.641 | 670,0 | 470 | 951 |
| Total | 3.396.090 | | | |

## Qualidade

O script `quality.py` lê todos os registros brutos e classifica cada um pelo primeiro motivo que o tira do dataset. O resultado fica em `results/data_quality.csv`, com uma linha por arquivo, e a soma de cada linha fecha com o total de registros do arquivo.

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

Não foi encontrada nenhuma data de internação inválida ou vazia, e todos os registros tinham o CID principal preenchido. Outras medidas:

## Validação

O `preprocessing.py` para a execução se alguma dessas condições falhar. Isso garante que um download incompleto ou uma mudança na regra não gere um dataset diferente sem ninguém perceber.

| Verificação | Valor esperado |
| --- | --- |
| Arquivos brutos | 212 |
| AIHs iniciais DCNT de 2008-12 a 2025-12 | 3.608.323 |
| Linhas do dataset | 768 |
| Valores ausentes | Nenhum |
| AIHs nos meses-alvo | 3.396.090 |

## Origem

- Sistema de Informações Hospitalares do SUS (SIH/SUS), mantido pelo DATASUS.
- Endereço - ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/

Dos arquivos brutos, só três campos são lidos:

- `DT_INTER`: Data de internação, `AAAAMMDD` | Mês de internação (`AAAA-MM`)
- `DIAG_PRINC`: CID-10 do diagnóstico principal | Grupo DCNT pela categoria
- `IDENT`: Tipo de AIH: `1` inicial, `5` continuidade | Só `1` é contada

## Transformações

1. Descompactar cada DBC baixado num arquivo temporário e ler o DBF registro a registro.
2. Mês de internação são os 6 primeiros dígitos de `DT_INTER`.
3. Manter só internações de 2008-12 a 2025-12.
4. Classificar o CID principal pela categoria: circulatórias `I00–I99`, diabetes `E10–E14`, neoplasias malignas `C00–C97` e respiratórias selecionadas `J30–J98` sem `J36`.
5. Contar só AIHs iniciais (`IDENT = 1`) com grupo DCNT.
6. Somar as contagens dos 212 arquivos por mês e grupo.
7. Montar a grade completa (205 meses × 4 grupos), com zero onde não houver registro.
8. Feature engineering: calcular as features só com meses anteriores (lags, médias móveis deslocadas um mês, variação anual e calendário).
9. Descartar os 13 meses de contexto (2008-12 a 2009-12) e gravar o Parquet de 2010-01 a 2025-12.
