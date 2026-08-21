---
data: 2026-08-21
titulo: Baseline lexical BM25 com avaliação reproduzível
tipo: feature
escopo: retrieval, evals
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/chunking.py
  - src/wcs_rag_evals/bm25.py
  - src/wcs_rag_evals/build_index.py
  - src/wcs_rag_evals/evaluate_bm25.py
  - evals/results/bm25-v0.1.json
  - README.md
---

## O que mudou

O projeto passou a construir chunks determinísticos para Markdown e OpenAPI, indexá-los com BM25 e avaliar o ranking em nível de documento. A execução publica Recall@k, Precision@k, MRR@10, nDCG@k, rankings e scores para cada caso do golden set.

## Por que

Embeddings, busca híbrida e reranking precisam ser comparados contra uma referência simples e mensurável. O baseline lexical cria esse controle e expõe limitações concretas, incluindo a perda no primeiro caso cross-lingual.

## Como usar

Depois de instalar o projeto, execute `wcs-fetch-corpus`, `wcs-build-index` e `wcs-eval-bm25`. O índice reconstruível fica em `.data/index/`; os resultados versionados ficam em `evals/results/`.

## Notas

O BM25 usa tokenização Unicode sem stemming ou tradução. O documento recebe o maior score entre seus chunks. Os 17 casos respondíveis entram nas métricas; o caso não respondível permanece no relatório para uma fase futura de avaliação de recusa.
