# Matriz de riscos — previsão mensal de AIHs DCNT

**Versão:** 2.0.0

**Data:** 2026-11-19

**Escopo:** modelo oficial `modelo-v1.0.0` (execução `20261105T205507`) e a pipeline de `solucao/` que o produz ([model_card.md](model_card.md))

## 1. Escala

| Nível | Probabilidade | Impacto |
| ---: | --- | --- |
| 1 | Baixa: improvável no horizonte de um ano | Baixo: retrabalho técnico, sem efeito sobre decisões |
| 2 | Média: já ocorreu ou pode ocorrer em algumas atualizações | Médio: previsão degradada ou atrasada, corrigível antes do uso |
| 3 | Alta: esperada em operação normal | Alto: decisão de recursos errada, exposição de dados pessoais ou perda de confiança |

**Severidade** = probabilidade × impacto.

| Severidade | Classificação | Tratamento |
| --- | --- | --- |
| 6 a 9 | Alta | Controle obrigatório antes de qualquer uso operacional |
| 3 a 4 | Média | Controle definido e acompanhamento periódico |
| 1 a 2 | Baixa | Aceito e registrado |

Os responsáveis são papéis. Na fase acadêmica, todos são exercidos pela equipe de desenvolvimento.

## 2. Matriz

### Dados

| ID | Risco | P | I | Sev. | Controle existente | Ação adicional | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- | --- |
| D1 | Atraso de processamento: meses recentes chegam incompletos e parecem queda de demanda | 3 | 3 | 9 | O dataset usa competências até 2026-07 para internações até 2025-12, com 7 meses de folga | Medir a completude de cada mês antes de usá-lo como entrada (monitoramento) | Responsável pelos dados |
| D2 | Mudança no layout ou nos códigos do DBC do DATASUS | 2 | 2 | 4 | `preprocessing.py` falha se faltar um campo e confere os totais esperados | Registrar o layout de cada download | Responsável pelos dados |
| D3 | Código CID inválido dentro de uma faixa DCNT entra na contagem | 2 | 2 | 4 | `quality.py` mede exclusões por motivo; os totais coincidem com a Etapa 2, que validava os códigos | Acompanhar por arquivo a proporção de CIDs fora dos grupos | Responsável pelos dados |
| D4 | Arquivo bruto corrompido ou substituído sem registro | 1 | 3 | 3 | Os totais conferidos pelo `preprocessing.py` acusam mudança no histórico | Gravar o SHA-256 de cada DBC no download | Responsável pelos dados |
| D5 | Mudança de distribuição (data drift) nas séries de entrada | 2 | 2 | 4 | Nenhum em operação | Monitorar drift e extrapolação a cada lote | Responsável pelo modelo |
| D6 | Trava de hash acusa mudança falsa: o mesmo conteúdo tem outro SHA-256 em outra máquina, e a execução é bloqueada ou a trava é desligada | 3 | 1 | 3 | `evaluation.py` compara o SHA-256 do arquivo | Comparar o conteúdo quando o hash divergir; registrar a máquina em cada execução | Responsável pelos dados |

### Modelo

| ID | Risco | P | I | Sev. | Controle existente | Ação adicional | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- | --- |
| M1 | Ruptura abrupta da demanda (nova pandemia, mudança de política) | 1 | 3 | 3 | Efeito da pandemia medido na mesma arquitetura (erro de 4,13% para 10,62%) | Alerta de erro acima do limite; revisão humana durante a ruptura | Responsável pelo modelo |
| M2 | Subestimação sistemática, principalmente no grupo circulatório (viés de -425,82 AIHs por mês em 2025) | 3 | 2 | 6 | Viés reportado por grupo em `metrics.csv` | Monitorar o viés por grupo; margem de segurança decidida pelo planejamento | Responsável pelo modelo |
| M3 | Degradação gradual do desempenho (model drift) | 2 | 2 | 4 | Baseline sazonal calculado em toda avaliação | Retreinar quando a MLP perder para o baseline ou o erro passar do limite | Responsável pelo modelo |
| M4 | Avaliação otimista: 2025 foi consultado na Etapa 3 e as séries são correlacionadas | 2 | 2 | 4 | Limitação declarada no Model Card | Confirmar com meses de 2026 | Responsável pelo modelo |
| M5 | Alteração silenciosa do modelo ou dos parâmetros | 1 | 3 | 3 | `config.json` e `best_params.json` por execução; SHA-256 da pasta em `registry.csv`; tag `modelo-v1.0.0` | Registro de versões no MLflow | Responsável pelo modelo |
| M6 | Instabilidade numérica: o mesmo código gera outro modelo e outro ranking em outra máquina | 3 | 2 | 6 | Artefato oficial versionado; variação medida (macro-WAPE de 5,00% a 5,78%) e declarada no Model Card | Registrar a máquina em `config.json`; não substituir o modelo oficial por retreino sem promoção formal | Responsável pelo modelo |

### Privacidade

| ID | Risco | P | I | Sev. | Controle existente | Ação adicional | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- | --- |
| P1 | Reidentificação a partir dos arquivos brutos guardados localmente | 1 | 3 | 3 | Só três campos são lidos; nenhum registro individual é gravado; `data/` fora do Git | Definir prazo de retenção dos DBC locais | Responsável pelos dados |
| P2 | Publicação de contagens pequenas em novos recortes (município, sexo, idade) | 1 | 3 | 3 | O dataset só tem totais estaduais, com mínimo de 470 AIHs por célula | Aplicar a regra de células menores que 10 da Etapa 2 a qualquer novo recorte | Responsável pelos dados |
| P3 | Nova finalidade para os dados sem nova avaliação | 2 | 2 | 4 | Regra de reavaliação em `docs/privacidade_etica.md` | Revisar esta matriz antes de integrar nova fonte ou recorte | Equipe |

### Segurança

| ID | Risco | P | I | Sev. | Controle existente | Ação adicional | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- | --- |
| S1 | Vazamento dos arquivos brutos por compartilhamento indevido | 1 | 2 | 2 | `.gitignore` de `data/`; o pacote de entrega não inclui dados | Nenhuma | Responsável pelos dados |
| S2 | Credencial ou token gravado no repositório | 1 | 2 | 2 | Nenhum segredo é necessário (FTP público) | Nenhuma | Equipe |
| S3 | Artefato `.joblib` adulterado executa código ao ser carregado | 1 | 3 | 3 | SHA-256 da pasta da execução em `registry.csv` | Conferir o hash antes de carregar o modelo | Responsável pelo modelo |
| S4 | Dependência com outra versão muda o resultado | 1 | 2 | 2 | `requirements.txt` com versões exatas; versões registradas em `config.json` | Nenhuma | Equipe |

### Ética

| ID | Risco | P | I | Sev. | Controle existente | Ação adicional | Responsável |
| --- | --- | :-: | :-: | :-: | --- | --- | --- |
| E1 | Decisão automática de recursos com base na previsão | 2 | 3 | 6 | Usos não recomendados no Model Card | Exigir registro de revisão humana em cada uso operacional | Dono do negócio |
| E2 | Uso para ranquear ou punir hospitais e municípios | 1 | 3 | 3 | Modelo apenas estadual; uso vedado no Model Card | Nenhuma | Dono do negócio |
| E3 | Grupo com pior desempenho recebe planejamento pior (diabetes: 11,62% de erro) | 2 | 2 | 4 | Métricas por grupo e macro-WAPE como critério de seleção | Monitorar o erro por grupo, com limite próprio | Responsável pelo modelo |
| E4 | Generalizar a previsão do SUS para toda a população | 2 | 2 | 4 | Cobertura declarada no Model Card e em [dados.md](dados.md) | Manter o aviso de cobertura em toda apresentação dos resultados | Equipe |

## 3. Mapa de calor

| Probabilidade \ Impacto | 1 — Baixo | 2 — Médio | 3 — Alto |
| --- | --- | --- | --- |
| **3 — Alta** | D6 | M2, M6 | D1 |
| **2 — Média** | | D2, D3, D5, M3, M4, P3, E3, E4 | E1 |
| **1 — Baixa** | | S1, S2, S4 | D4, M1, M5, P1, P2, S3, E2 |

## 4. Prioridades

Os quatro riscos de severidade alta orientam o versionamento e o monitoramento:

1. **D1 — atraso de processamento:** o risco mais provável em operação, que pode ser confundido com queda real de demanda.
2. **M2 — subestimação:** o viés negativo aparece nos quatro grupos em 2025.
3. **M6 — instabilidade numérica:** já ocorreu entre a apresentação e o pacote da Etapa 3.
4. **E1 — decisão automática:** o principal risco de uso indevido.

## 5. Mudanças em relação à versão 1

A versão 1 (`docs/matriz_riscos.md` na raiz) avaliava o pipeline antigo. Na pipeline simplificada:

- P2 caiu de severidade 6 para 3, porque nenhuma base por AIH é produzida e todas as células têm pelo menos 470 AIHs;
- S1 caiu de 3 para 2, porque só os arquivos públicos do DATASUS ficam guardados localmente;
- D6 e M6 são novos, identificados na reprodução da entrega;
- D2, D3 e D4 passaram a ter como controles os totais conferidos pelo `preprocessing.py` e o `quality.py`, no lugar dos manifestos e da validação CID.

## 6. Revisão

A matriz deve ser revisada:

- a cada nova versão do modelo;
- quando um indicador do monitoramento ultrapassar o limite;
- antes de integrar nova fonte de dados ou mudar a finalidade;
- após qualquer incidente ou reclamação.

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0.0 | 2026-11-18 | Primeira versão, sobre o pipeline antigo |
| 2.0.0 | 2026-11-19 | Refeita sobre a pipeline simplificada entregue na Etapa 3 |
