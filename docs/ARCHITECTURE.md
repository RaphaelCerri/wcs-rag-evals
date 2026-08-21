# Arquitetura

## Princípio

O projeto separa corpus, retrieval, geração e avaliação. Uma camada pode ser substituída sem alterar o golden set, permitindo atribuir ganho ou regressão ao componente correto.

```text
fontes fixadas
  -> coletor + proveniência + hashes
  -> parser e chunking versionados
  -> índice lexical / índice vetorial
  -> retrievers independentes
  -> rank fusion e reranker
  -> geração com citações
  -> métricas de retrieval, resposta, custo e latência
```

## Fronteiras

### Corpus

Responsável apenas por adquirir documentos permitidos, preservar proveniência e fornecer conteúdo imutável para uma execução.

### Retrieval

Recebe uma pergunta e retorna documentos ou chunks com score. A primeira implementação será lexical. Vetores, busca híbrida e reranker entram como estratégias comparáveis, não como substituições silenciosas.

### Geração

Recebe pergunta e contexto recuperado. Deve retornar resposta estruturada, citações e recusa quando o corpus não sustenta a afirmação.

### Avaliação

Compara resultados contra o golden set. Métricas determinísticas de retrieval não dependem de LLM. Métricas julgadas por modelo devem registrar modelo, prompt, temperatura, repetição e calibração humana.

## Decisões iniciais

- Python 3.11 ou superior.
- Pydantic para contratos externos.
- JSONL para datasets versionáveis e revisáveis em diff.
- YAML para manifesto humano de fontes.
- Conteúdo bruto e relatórios locais fora do Git.
- Revisões de corpus sempre fixadas por SHA completo.
- Nenhuma chave de API é necessária na Fase 0.

## Próximas decisões

- BM25 puro ou PostgreSQL full-text como baseline lexical.
- unidade de chunking e estratégia para Markdown/OpenAPI;
- modelo de embedding;
- pgvector local ou Supabase para execução pública;
- rank fusion e reranker;
- provedor e protocolo de geração.

Cada decisão será tomada depois da métrica anterior existir.

