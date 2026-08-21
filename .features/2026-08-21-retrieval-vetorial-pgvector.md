---
data: 2026-08-21
titulo: Retrieval vetorial multilíngue com pgvector
tipo: feature
escopo: retrieval, infra, evals
ferramenta: codex
arquivos:
  - compose.yaml
  - infra/postgres/init.sql
  - src/wcs_rag_evals/embeddings.py
  - src/wcs_rag_evals/vector_store.py
  - src/wcs_rag_evals/evaluate_vector.py
  - evals/results/dense-v0.1.json
---

## O que mudou

O projeto passou a gerar embeddings multilíngues em modelo local fixado, persistir 1.458 vetores em PostgreSQL com pgvector e avaliar retrieval denso sob o mesmo golden set do BM25. O relatório compara métricas agregadas e por caso, incluindo deltas contra o baseline lexical.

## Por que

O baseline BM25 expôs perda de cobertura na pergunta em português e em consultas com diferença de vocabulário. A nova estratégia testa semantic retrieval em um banco vetorial real sem alterar corpus, chunks ou rótulos depois de observar o baseline.

## Como usar

Instale `.[dev,vector]`, inicie o banco com `docker compose up -d --wait`, defina `WCS_DATABASE_URL` com o valor de `.env.example` e execute `wcs-build-vector-index` seguido de `wcs-eval-vector`.

## Notas

O modelo `intfloat/multilingual-e5-small` está fixado por revisão e usa os prefixos exigidos pelo treinamento. A busca medida é exata porque o corpus possui apenas 1.458 vetores; HNSW permanece disponível no schema para escala. O vetorial perdeu Recall@5 agregado para o BM25, mas ganhou Recall@10, melhorou o split de teste e dobrou o Recall@5 do caso pt-BR. O próximo experimento deve combinar os rankings.
