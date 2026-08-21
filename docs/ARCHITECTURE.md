# Arquitetura

## Princípio

O projeto separa corpus, retrieval, geração e avaliação. Uma camada pode ser substituída sem alterar o golden set, permitindo atribuir ganho ou regressão ao componente correto.

```text
fontes fixadas
  -> coletor + proveniência + hashes
  -> parser e chunking versionados
  -> BM25 local / PostgreSQL + pgvector
  -> retrievers independentes
  -> rank fusion e reranker
  -> geração com citações
  -> métricas de retrieval, resposta, custo e latência
```

## Fronteiras

### Corpus

Responsável apenas por adquirir documentos permitidos, preservar proveniência e fornecer conteúdo imutável para uma execução.

### Retrieval

Recebe uma pergunta e retorna documentos ou chunks com score. A implementação inicial usa BM25 próprio sobre chunks e agrega cada documento pelo maior score de seus chunks. Vetores, busca híbrida e reranker entram como estratégias comparáveis, não como substituições silenciosas.

### Geração

Recebe pergunta e contexto recuperado. Deve retornar resposta estruturada, citações e recusa quando o corpus não sustenta a afirmação.

### Avaliação

Compara resultados contra o golden set. Métricas determinísticas de retrieval não dependem de LLM. Métricas julgadas por modelo devem registrar modelo, prompt, temperatura, repetição e calibração humana.

## Decisões iniciais

- Python 3.11 ou superior.
- Pydantic para contratos externos.
- JSONL para datasets versionáveis e revisáveis em diff.
- YAML para manifesto humano de fontes.
- Conteúdo bruto e índices reconstruíveis fora do Git; métricas agregadas e rankings publicados em `evals/results/`.
- Revisões de corpus sempre fixadas por SHA completo.
- Nenhuma chave de API é necessária nas Fases 0, 1 e 2.

## Decisões da Fase 1

- BM25 implementado no projeto, sem serviço ou índice externo.
- Tokenização Unicode, case-insensitive, sem stemming ou tradução.
- Markdown separado por headings e janelas de até 220 palavras com overlap de 40.
- OpenAPI separado por operação HTTP e componente, preservando contratos, schemas e metadados relevantes.
- Ranking avaliado em nível de documento, compatível com os rótulos do golden set.
- Score do documento definido pelo melhor chunk, evitando somar vantagem por tamanho do arquivo.
- Empates resolvidos por identificador estável para garantir reprodução.

## Decisões da Fase 2

- `multilingual-e5-small` fixado por SHA, com 384 dimensões e execução local em CPU.
- Prefixos `query:` e `passage:` aplicados explicitamente conforme o treinamento do modelo.
- Embeddings normalizados antes da persistência.
- PostgreSQL 17 com pgvector 0.8.6 em imagem Docker fixada.
- Porta do banco exposta apenas em `127.0.0.1`.
- Busca exata por cosine distance na medição atual, evitando introduzir erro aproximado em apenas 1.458 vetores.
- Índice HNSW criado para demonstrar o caminho de escala, mas não atribuído falsamente aos resultados atuais.
- Cache local retomável por lote, evitando recalcular embeddings depois de interrupções.
- Mesmo chunking, golden set, top-k e agregação do BM25 para manter a comparação controlada.

## Próximas decisões

- método de rank fusion;
- reranker;
- provedor e protocolo de geração.

Cada decisão será tomada depois da métrica anterior existir.
