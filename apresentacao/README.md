# Apresentação da Etapa 4

Projeto LaTeX/Beamer da apresentação final de Governança de TI e de Dados. Usa o mesmo tema, fontes e logotipos da apresentação da Etapa 3, copiados para que a pasta compile sozinha.

## Compilar

No TeXStudio, abra `etapa4.tex` e compile com **XeLaTeX**. Pelo terminal, dentro desta pasta:

```bash
latexmk etapa4.tex
```

O PDF fica fora do Git, como na Etapa 3.

## Roteiro

| Slides | Conteúdo |
| --- | --- |
| 1 | Problema, objetivos estratégicos e proposta |
| 2–3 | Pipeline, ferramentas, dados e modelo oficial |
| 4–8 | Versionamento, MLflow, documentação, riscos e monitoramento |
| 9–11 | Teste de 2025 e primeiro ciclo de monitoramento com 2026 |
| 12 | Desafios |
| 13–14 | Atendimento aos objetivos, limitações, aprendizados e próximos passos |
| Apoio | Variação do modelo entre máquinas; onde está cada produto da entrega |

Todos os números vêm de `solucao/results/`, de `solucao/docs/` e de `entrega-etapa4/`.

## Figura

`img/mlflow_registry.png` é uma captura da interface do MLflow (versão 1 do modelo `previsao-aih-dcnt-mlp`), aberta com:

```bash
uvx --from mlflow==3.17.2 mlflow ui --backend-store-uri sqlite:///solucao/mlflow.db --port 5050
```
