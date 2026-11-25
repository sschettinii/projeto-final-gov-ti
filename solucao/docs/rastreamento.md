# Rastreamento de experimentos e ciclo de vida do modelo

**Data:** 2026-11-19

**Ferramenta:** MLflow 3.17.2 (`mlflow-skinny`, banco SQLite local)

**Script:** `tracking.py`

## 1. Treinar um modelo contra gerenciar o seu ciclo de vida

Treinar é rodar `tuning.py` e `evaluation.py` e obter um `model.joblib` com métricas. Gerenciar o ciclo de vida é conseguir responder, a qualquer momento:

- de qual experimento, dados, parâmetros e máquina veio o modelo em uso;
- quais alternativas foram comparadas antes dele;
- qual versão está em uso e por quê;
- o que o monitoramento disse sobre essa versão depois que ela entrou em uso.

A pipeline já gravava essas respostas em arquivos: as pastas de `results/` e o `registry.csv`. O `tracking.py` publica esses arquivos no MLflow, organizados como experimento → parâmetros → métricas → modelo → artefatos, com o Model Registry e os ciclos de monitoramento ligados à versão do modelo.

## 2. O que fica registrado

```text
Experimento "previsao-aih-dcnt"
  ├─ run 20261105T205507   (oficial)
  │    tags        pasta, papel, data da avaliação, SHA-256 da pasta e do dataset, máquina
  │    parâmetros  modelo, janela, hiperparâmetros, semente, trials, anos de validação, versões
  │    métricas    validação; teste 2025 da MLP e do baseline (geral e por grupo)
  │    artefatos   config.json, best_params.json, trials.csv, metrics.csv, predictions.csv, model.joblib
  │    modelo      MLP em formato MLflow
  │    └─ 27 runs filhos: o melhor resultado de cada família de modelo em cada janela
  └─ run 20261118T221057   (reprodução em outro Mac, não oficial)
       └─ 27 runs filhos

Model Registry "previsao-aih-dcnt-mlp"
  └─ versão 1  ← apelido "champion"
       tags: versao_semantica 1.0.0, tag_git modelo-v1.0.0, execucao 20261105T205507,
             monitoramento_2026-07 = alerta

Experimento "monitoramento-modelo-oficial"
  └─ run monitoring_202607
       tags        nível de cada indicador, nível geral, versão do modelo monitorada
       parâmetros  lote, última competência, meses maduros
       métricas    macro-WAPE e WAPE da MLP e do baseline, viés por grupo, PSI, extrapolação,
                   diferença da previsão sem correção de completude
       artefatos   todos os arquivos de results/monitoring_202607/
```

Os runs filhos permitem comparar, na própria interface, as 9 famílias de modelos nas 3 janelas, por macro-WAPE de validação. A MLP da janela 2010 venceu com 5,28%.

O identificador de cada run no banco local fica em `results/mlflow_runs.csv`.

## 3. Garantias

- **O MLflow não é a fonte da verdade.** Os arquivos de `results/` são versionados no Git; o banco `mlflow.db` e a pasta `mlartifacts/` são locais e podem ser recriados com `tracking.py`.
- **Sem duplicação.** Cada pasta é registrada uma vez; rodar o script de novo só acrescenta o que é novo. Na conferência, a segunda execução manteve os mesmos 56 runs no experimento principal.
- **Modelo conferido antes de carregar.** O `model.joblib` só é carregado se o SHA-256 da pasta conferir com o `registry.csv` (risco S3).
- **O modelo registrado é o entregue.** Carregado do Registry pelo apelido (`models:/previsao-aih-dcnt-mlp@champion`), ele produz exatamente as previsões de 2025 gravadas em `predictions.csv`.
- **O arquivo original também é guardado.** O MLflow serializa o modelo de novo no próprio formato, com outros bytes. Por isso o `model.joblib` original também vai como artefato do run.

## 4. Como usar

Dentro de `solucao/`, o MLflow fica num arquivo de requisitos separado. O pacote completo do MLflow exige `pyarrow` abaixo de 22, o que mudaria a versão fixada na entrega (25.0.1); o `mlflow-skinny` não tem essa restrição.

```bash
.venv/bin/pip install -r requirements-tracking.txt
.venv/bin/python tracking.py
```

Para abrir a interface sem instalar o MLflow completo no ambiente da pipeline:

```bash
uvx --from mlflow==3.17.2 mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5050
```

Na interface:

- **Experiments → previsao-aih-dcnt:** compare as execuções e os runs de busca;
- **Models → previsao-aih-dcnt-mlp:** veja a versão `champion` e as tags de monitoramento;
- **Experiments → monitoramento-modelo-oficial:** veja os níveis de cada ciclo.

## 5. Como o ciclo continua

| Evento | O que acontece no MLflow |
| --- | --- |
| Novo ciclo de monitoramento | Novo run em `monitoramento-modelo-oficial` e nova tag `monitoramento_AAAA-MM` na versão em uso |
| Retreino (versão MINOR) | Novo run em `previsao-aih-dcnt`; registro como nova versão do modelo, ainda sem apelido |
| Promoção aprovada | O apelido `champion` passa para a nova versão; a anterior continua no Registry e na tag Git |

A promoção segue os critérios do [plano de monitoramento](plano_monitoramento.md): vencer o baseline e a versão em uso nos mesmos meses, na mesma máquina, com aprovação registrada. Mover o apelido é um passo manual, nunca automático.
