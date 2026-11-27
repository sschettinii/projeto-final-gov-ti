# Registro dos experimentos

O registro dos experimentos é gerado automaticamente pelos scripts a cada execução, em `solucao/results/`.

Cada experimento é uma execução de `tuning.py` seguida de `evaluation.py`. O `tuning.py` cria uma pasta nova com a data e hora de início. Nada é sobrescrito, e uma pasta só pode ser avaliada uma vez.

## Parâmetros

Os parâmetros de cada tentativa da busca ficam em `trials.csv`, e o melhor de cada modelo em `best_params.json`. A configuração da busca (modelos, janelas, anos de validação, semente) fica em `config.json`.

## Versões

- Dados: o SHA-256 do dataset vai para o `config.json`, e o `evaluation.py` se recusa a avaliar se o dataset mudou depois da busca.
- Bibliotecas: as versões do Python, scikit-learn e Optuna também vão para o `config.json`; as demais estão fixadas em `solucao/requirements.txt`.
- Modelo: o modelo em uso é marcado com a tag modelo-v1.0.0.

## Resultados

As métricas de teste de cada execução ficam em `metrics.csv`, e o resumo de todas as execuções em `registry.csv`, que é o ponto de partida para comparar experimentos.

## Avaliação em tempo real e monitoramento

O `metrics.csv` de cada execução mede o teste de 2025 com os meses anteriores já completos, o que usa informação que ainda não existiria no momento da previsão. Por isso o modelo oficial também é avaliado pelo `realtime_evaluation.py`, que prevê cada mês só com os arquivos processados até o mês anterior. O resultado fica em `results/realtime_202607/`, com as previsões e as métricas de cada forma de montar as entradas.

Os ciclos de monitoramento ficam em `results/monitoring_<competência>/`. O primeiro ciclo foi rodado duas vezes, e as duas pastas ficam guardadas: `monitoring_202607` avaliava previsões refeitas com os arquivos de julho, e `monitoring_202607_v2` avalia as previsões como teriam sido emitidas em cada mês.

## MLflow

O `tracking.py` registra no MLflow tudo o que está em `results/`: cada execução vira um run com parâmetros, métricas, artefatos e o modelo, e cada ciclo de monitoramento vira um run ligado ao modelo oficial. O modelo oficial fica no Model Registry como `previsao-aih-dcnt-mlp`, com o apelido `champion`. A ligação entre cada pasta e o seu run fica em `results/mlflow_runs.csv`. As dependências do MLflow ficam em `solucao/requirements-tracking.txt`, separadas das da pipeline.

Os arquivos de `results/` continuam sendo a fonte da verdade: o MLflow é só uma visão sobre eles e pode ser recriado a qualquer momento. Os experimentos das Etapas 2 e 3, anteriores a essa estrutura, estão reunidos em `results/registro_unificado.csv`.
