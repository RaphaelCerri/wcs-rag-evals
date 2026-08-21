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

## Métricas planejadas

### Retrieval

- Recall@k
- Precision@k
- Mean Reciprocal Rank
- nDCG@k

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

