# Estratégia de versionamento

**Versão:** 2.0.0

**Data:** 2026-11-19

A solução versiona quatro coisas: código, dados, modelo e configurações. Cada uma usa um mecanismo simples. Todas se ligam pela pasta de cada execução em `results/`, que guarda o hash do dataset, os parâmetros e o modelo, e pela linha dessa execução em `results/registry.csv`, que guarda o hash da pasta inteira.

## 1. Visão geral

| O quê | Mecanismo | Onde fica | Como é conferido |
| --- | --- | --- | --- |
| Código | Git, uma branch e um PR por alteração, tags nos marcos | Este repositório | Histórico do Git; tag `entrega-etapa3` para o código entregue |
| Dados brutos | Manifesto com tamanho e SHA-256 de cada arquivo DBC | `results/raw_manifest.csv` | `download.py` interrompe se um arquivo já registrado mudar |
| Dataset | SHA-256 do arquivo e SHA-256 do conteúdo | `config.json` de cada execução | `evaluation.py` recusa avaliar se o conteúdo mudou desde a busca |
| Modelo | `model.joblib` dentro da pasta da execução; SHA-256 da pasta; tag `modelo-vX.Y.Z` | `results/<execução>/`, `registry.csv` | `monitoring.py` só carrega o modelo se o hash da pasta conferir |
| Configurações | Constantes no código, versionadas pelo Git, fotografadas no `config.json` de cada execução | `tuning.py`, `evaluation.py`, `monitoring.py` | Comparação do `config.json` entre execuções |

## 2. Código

- Toda alteração entra por branch, commit em português e PR, com merge na `main`.
- A tag `entrega-etapa3` marca o pacote entregue na Etapa 3, importado sem alterações. O commit contém o SHA-256 do ZIP (`8f54b27a…`).
- As mudanças da Etapa 4 nos scripts entregues são pequenas e não alteram resultados: o parâmetro `end` do `preprocessing.py` (o dataset continua igual), o manifesto do `download.py`, o hash de conteúdo e a máquina no `config.json`, a verificação de conteúdo e a escolha da execução padrão no `evaluation.py`.

## 3. Dados

### Arquivos brutos

`download.py` grava, depois de baixar, o tamanho e o SHA-256 dos 212 arquivos em `results/raw_manifest.csv`. Se o manifesto já existir e algum arquivo tiver outro hash, o script para. Assim, uma republicação silenciosa de um arquivo pelo DATASUS é detectada.

Os 212 hashes atuais conferem com os registrados pelo extrator do pipeline antigo em 2026-10-30, ou seja, os arquivos não mudaram desde então.

### Dataset de modelagem

O dataset não vai para o Git; ele é regenerado pelo `preprocessing.py`, que confere os totais esperados. Sua versão é registrada de duas formas no `config.json`:

| Campo | O que mede | Estável entre máquinas? |
| --- | --- | --- |
| `dataset_sha256` | Bytes do arquivo Parquet | Não: inclui metadados de gravação. O mesmo conteúdo deu `c074b63e…` na máquina da entrega e `4c529674…` neste Mac |
| `dataset_content_sha256` | Valores das 768 linhas e 16 colunas | Sim: o dataset deste Mac e o do pipeline antigo, com bytes diferentes, têm o mesmo hash de conteúdo (`8e38571b…`) |

O `evaluation.py` aceita o arquivo quando o hash dos bytes confere. Se não conferir, aceita quando o hash do conteúdo confere, e avisa. Caso contrário, para. A execução oficial `20261105T205507` é anterior a essa mudança e só tem o hash dos bytes.

### Qualidade

`quality.py` grava em `results/data_quality.csv` a contagem de registros por motivo de exclusão em cada arquivo. Comparar esse arquivo entre versões mostra se uma mudança na fonte alterou a seleção.

## 4. Modelo

### Versão atual

| Item | Valor |
| --- | --- |
| Versão | 1.0.0 |
| Tag Git | `modelo-v1.0.0`, no commit `524466f` |
| Execução | `results/20261105T205507/` |
| SHA-256 do `model.joblib` | `e97c192a…` |
| SHA-256 da pasta (em `registry.csv`) | `6d7b2b5c794d9d112f44a837043e45a5b7e48687891131599d96ca92a6f96bb8` |
| Documentação | [model_card.md](model_card.md) |

### Regra de versão

| Incremento | Quando | Exemplo |
| --- | --- | --- |
| MAJOR (`2.0.0`) | Muda o alvo, a granularidade, as features, o recorte DCNT ou a família do modelo | Prever por região de saúde |
| MINOR (`1.1.0`) | Nova busca e avaliação com o mesmo código e dados estendidos | Incluir 2025 no desenvolvimento |
| PATCH (`1.0.1`) | Muda só a documentação, sem novo `model.joblib` | Corrigir o Model Card |

Toda nova versão exige:

1. nova pasta em `results/` e nova linha em `registry.csv`, sem apagar as anteriores;
2. nova tag `modelo-vX.Y.Z`;
3. comparação com o baseline e com a versão em uso nos mesmos meses, na mesma máquina;
4. Model Card e matriz de riscos atualizados.

### Execuções que não são oficiais

| Execução | Papel |
| --- | --- |
| `20261118T221057` | Reprodução da entrega em outro Mac; prova que o mesmo código gera os números dos slides da Etapa 3 ([reproducao_etapa3.md](reproducao_etapa3.md)) |
| `registro_unificado.csv` | Histórico da fase exploratória feita no pipeline antigo |

### Por que o modelo é versionado como arquivo, e não só como código

O código, os dados e a semente não bastam para recriar o mesmo modelo em outra máquina: a MLP amplifica diferenças de arredondamento (risco M6). Por isso o `model.joblib` oficial é guardado e protegido por hash, e o `config.json` passa a registrar a máquina (`machine.system` e `machine.processor`) e as versões de numpy e pandas.

## 5. Configurações

A pipeline entregue mantém os parâmetros como constantes no início de cada script, e esse estilo foi preservado:

| Script | Constantes principais |
| --- | --- |
| `download.py` | Primeira e última competência |
| `preprocessing.py` | Períodos, faixas CID dos grupos, lags, médias móveis |
| `tuning.py` | Semente, trials por modelo, janelas, anos de validação, features, modelos e espaço de busca |
| `evaluation.py` | Ano de teste |
| `monitoring.py` | Execução oficial, lote, referências e limites dos indicadores |

O Git guarda a história dessas constantes. O `config.json` de cada execução fotografa as que afetam o resultado (dataset, semente, trials, janelas, validação, features, modelos, versões e máquina). Para saber o que mudou entre duas execuções, basta comparar os dois `config.json`.

## 6. Como conferir

Dentro de `solucao/`:

```bash
.venv/bin/python download.py
.venv/bin/python -c "from evaluation import folder_hash; from pathlib import Path; print(folder_hash(Path('results/20261105T205507')))"
git show modelo-v1.0.0 --stat
```

- O primeiro comando baixa o que falta e confere os brutos contra o manifesto.
- O segundo recalcula o hash da pasta oficial; o resultado deve ser igual ao de `registry.csv`.
- O terceiro mostra o commit da versão oficial do modelo.
