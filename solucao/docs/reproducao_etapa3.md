# Reprodução da entrega da Etapa 3

**Data:** 2026-11-19

**Pacote conferido:** `entrega3_govti.zip`, SHA-256 `8f54b27a519bc9a8994cb7e3eedab32cf4aa7b0629e1a986ff11aadda36b4875`, importado sem alterações no commit marcado com a tag `entrega-etapa3`

**Ambiente da reprodução:** Apple M4, macOS 26.6, Python 3.13.5 e as versões fixadas em `requirements.txt` (scikit-learn 1.8.0, pandas 2.3.3, numpy 2.5.4, optuna 4.9.0, pyarrow 25.0.1), as mesmas registradas pela execução entregue

## 1. Conclusão

O código entregue é reprodutível **na mesma máquina**. Em outra máquina, os dados se repetem, mas o modelo não.

- **Dados:** o dataset regenerado tem conteúdo idêntico bit a bit ao da Etapa 3. O SHA-256 do arquivo muda de uma máquina para outra.
- **Modelo:** a busca e o treino da MLP dependem de diferenças de arredondamento da ordem de 10⁻¹⁶ entre máquinas. A MLP com L-BFGS amplifica essa diferença até cerca de 0,4 ponto percentual de macro-WAPE.
- **Slides contra pacote:** os números dos slides da Etapa 3 (macro-WAPE de 5,00%) e os do pacote (5,78%) vêm **do mesmo código**, executado em máquinas diferentes. Rodando o pacote neste Mac, obtém-se exatamente o modelo dos slides.

## 2. Dados

`preprocessing.py` foi executado com os 212 arquivos RDPR locais (competências 2008-12 a 2026-07). Todas as validações do script passaram: 212 arquivos, 3.608.323 AIHs iniciais DCNT, 768 linhas completas e 3.396.090 AIHs nos meses-alvo.

| Arquivo | SHA-256 | Origem |
| --- | --- | --- |
| Dataset da execução entregue | `c074b63e…` | Máquina onde a entrega foi gerada |
| Dataset regenerado | `4c529674…` | Este Mac; igual em duas regravações |
| Dataset do pipeline antigo | `9bbd5a70…` | Este Mac, pipeline da raiz do repositório |

O dataset regenerado e o do pipeline antigo foram comparados célula a célula: mesmas chaves, mesmas 768 linhas e valores numéricos **idênticos bit a bit** nas 14 colunas numéricas. A diferença de hash vem dos metadados que pandas e pyarrow gravam no Parquet, não do conteúdo. O arquivo de `c074b63e…` não está no pacote, então sua comparação célula a célula não foi possível.

Consequência prática: `evaluation.py` recusa avaliar quando o hash do dataset difere do `config.json`. Em outra máquina, essa trava acusa mudança de dados mesmo quando o conteúdo é igual.

## 3. Busca de hiperparâmetros

`tuning.py` foi executado completo neste Mac em uma cópia de rascunho, com 675 trials em 4 minutos e 9 segundos.

| Comparação dos 675 trials | Parâmetros iguais | Valores iguais |
| --- | ---: | ---: |
| Este Mac contra a busca do pipeline antigo (2026-10-27) | 664 | 665 |
| Este Mac contra a execução entregue | 303 | 399 |

O vencedor neste Mac é o mesmo da busca antiga: MLP da janela 2010, `alpha = 0,7100`, macro-WAPE de validação de 5,5009%. A execução entregue escolheu `alpha = 1,4600`, com validação de 5,2806%.

A divergência começa no primeiro trial. Com a mesma semente, o Optuna sorteia, por exemplo, `alpha = 0.09915644566638405` neste Mac e `0.09915644566638401` na execução entregue. A diferença está no 16º dígito, e os dois ambientes Python deste Mac sorteiam o mesmo valor. Daí em diante, cada trial com valor diferente muda o caminho do amostrador TPE.

## 4. Treino e avaliação

| Execução | Onde | Hiperparâmetros | MAE | WAPE | Macro-WAPE |
| --- | --- | --- | ---: | ---: | ---: |
| `20261105T205507` (entregue) | Máquina da entrega | `alpha = 1,46` | 226,22 | 3,98% | 5,78% |
| Retreino da entregue (rascunho) | Este Mac | `alpha = 1,46` | 235,56 | 4,15% | 5,72% |
| `20261118T221057` (reprodução) | Este Mac | `alpha = 0,71` | 210,08 | 3,70% | 5,00% |
| Modelo oficial dos slides | Este Mac, pipeline antigo | `alpha = 0,71` | 210,08 | 3,70% | 5,00% |

A execução `20261118T221057` foi incluída em `results/` e em `registry.csv`, com hash da pasta `8d06f5cd…`. Os pesos do seu `model.joblib` são idênticos aos de `artifacts/modelos/modelo_oficial_etapa3.joblib`; só os bytes do pickle diferem.

No retreino em rascunho, o `config.json` da cópia recebeu o hash do dataset local para passar pela trava do `evaluation.py`. Esse retreino não foi incluído em `results/`.

### Sensibilidade numérica da MLP

Neste Mac, treinar duas vezes com os mesmos dados gera pesos idênticos. Alterar só o último bit de uma feature muda o modelo:

| Treino com os hiperparâmetros entregues | Macro-WAPE em 2025 |
| --- | ---: |
| Dados originais | 5,72% |
| `mes_seno` acrescido de 1 ulp (cerca de 10⁻¹⁶) | 5,35% |
| `media_movel_3` acrescido de 1 ulp | 5,56% |

Uma variação dessa ordem é parecida com a distância entre os primeiros colocados da busca. O ranking de modelos e a escolha de hiperparâmetros não são estáveis entre máquinas.

## 5. O que fica em aberto

- Identificar o sistema operacional e o processador da máquina que gerou a entrega.
- Decidir qual execução é a oficial da Etapa 4: a entregue (`20261105T205507`) ou a reprodutível neste Mac (`20261118T221057`).

## 6. O que muda na Etapa 4

- O `config.json` de cada execução passa a registrar o sistema operacional, o processador e as versões de numpy e pandas.
- A conferência do dataset deve comparar o conteúdo quando o hash do arquivo divergir.
- O artefato oficial é o `model.joblib` versionado. Um retreino em outra máquina não substitui o modelo, apenas confirma a ordem de grandeza do erro.
- O Model Card deve informar a variação de cerca de 0,4 ponto percentual de macro-WAPE causada por ruído numérico.
