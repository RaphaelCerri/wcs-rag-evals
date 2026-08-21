# Estratégia de avaliação

## Unidade do golden set

Cada caso registra:

- pergunta;
- categoria e dificuldade;
- se é respondível pelo corpus;
- documentos relevantes;
- resposta de referência em paráfrase;
- fatos que precisam aparecer;
- claims que não podem aparecer;
- observação sobre ambiguidade ou maturidade.

## Partições

- `dev`: usado para desenvolver e depurar o pipeline;
- `test`: usado somente para confirmar generalização e regression gate.

O conjunto inicial é pequeno e serve para validar contratos. Antes de publicar métricas finais, deve crescer e receber revisão humana sem usar respostas do sistema como rótulo.

## Métricas

### Retrieval

- Recall@k
- Precision@k
- Mean Reciprocal Rank
- nDCG@k

O baseline BM25 calcula todas as métricas em `k = 1, 3, 5, 10`, além de MRR@10. A avaliação agrega resultados para o conjunto completo, splits `dev` e `test` e idioma. Casos não respondíveis são excluídos das métricas de retrieval porque não possuem documentos relevantes; eles serão avaliados na camada de geração e recusa.

Resultados publicados: [`evals/results/bm25-v0.1.md`](../evals/results/bm25-v0.1.md).

O baseline vetorial publica as mesmas métricas e inclui deltas agregados e por caso contra o BM25. O modelo denso não venceu todas as métricas: perdeu Recall@5 agregado, mas ganhou Recall@10, melhorou o split de teste e reduziu o gap cross-lingual. Por isso, ele não substitui o lexical e serve como evidência para testar rank fusion na Fase 3.

Comparação publicada: [`evals/results/dense-v0.1.md`](../evals/results/dense-v0.1.md).

### Geração

- cobertura de fatos obrigatórios;
- incidência de claims proibidos;
- faithfulness ao contexto;
- correção das citações;
- recusa correta em perguntas não respondíveis.

### Operação

- latência p50 e p95 por etapa;
- tokens de entrada e saída;
- custo por pergunta;
- tamanho do contexto recuperado.

## Casos difíceis intencionais

O corpus contém documentação com níveis diferentes de autoridade. Um ADR pode estar marcado como `Proposed` enquanto `AS-BUILT.md` descreve parte da capacidade como entregue. A resposta correta precisa qualificar a divergência em vez de escolher silenciosamente a narrativa mais conveniente.

## Regression gate

Os limites só serão definidos depois do primeiro baseline. O gate não será calibrado para fazer a implementação atual passar. Uma regressão deliberada deverá falhar o CI como teste do próprio gate.
