# Registro dos experimentos

O registro dos experimentos é gerado automaticamente pelos scripts a cada execução, em `solucao/results/`.

Cada experimento é uma execução de `tuning.py` seguida de `evaluation.py` e o `evaluation.py`. O `tuning.py` cria uma pasta nova com a data e hora de início. Nada é sobrescrito: cada execução cria uma pasta nova, e uma pasta só pode ser avaliada uma vez.

## Parâmetros

Os parâmetros de cada tentativa da busca ficam em `trials.csv`, e o melhor de cada modelo em `best_params.json`. A configuração da busca (modelos, janelas, anos de validação, semente) fica em `config.json`.

## Versões

- Dados: o SHA-256 do dataset vai para o `config.json`, e o `evaluation.py` se recusa a avaliar se o dataset mudou depois da busca.
- Bibliotecas: as versões do Python, scikit-learn e Optuna também vão para o `config.json`; as demais estão fixadas em `solucao/requirements.txt`.
- Modelo: o modelo em uso é marcado com a tag modelo-v1.0.0.

## Resultados

As métricas de teste de cada execução ficam em `metrics.csv`, e o resumo de todas as execuções em `registry.csv`, que é o ponto de partida para comparar experimentos.
