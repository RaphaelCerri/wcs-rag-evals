---
data: 2026-08-25
titulo: Reranker multilíngue com gates predefinidos
tipo: feature
escopo: retrieval, evals, benchmark
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/reranker.py
  - src/wcs_rag_evals/evaluate_reranker.py
  - evals/results/reranker-v0.1.json
  - evals/results/reranker-v0.1.md
  - evals/results/reranker-benchmark-v0.1.json
  - evals/results/reranker-benchmark-v0.1.md
  - tests/test_reranker.py
  - README.md
---

## O que mudou

O projeto passou a avaliar um cross-encoder multilíngue sobre os dez candidatos do Hybrid RRF. O pipeline reúne os melhores chunks lexical e vetorial de cada documento, mede o ranking resultante e publica qualidade e latência em artefatos separados.

## Por que

Reranking adiciona inferência, custo e latência. Gates definidos antes do resultado impedem que um componente mais sofisticado seja promovido por uma métrica isolada ou por ajuste posterior no conjunto de teste.

## Como usar

Execute `wcs-eval-reranker` depois que o índice BM25 e os relatórios BM25, dense e hybrid v0.1 existirem. O comando baixa o modelo fixado na primeira execução, roda em CPU e grava o relatório determinístico de qualidade e o benchmark local.

## Notas

O p95 do artefato final foi 13,99 segundos e passou no limite de 15 segundos. nDCG@10 caiu 0,083 em `dev` e 0,029 em `test`, portanto os gates de qualidade falharam e o reranker não foi aceito. O Hybrid RRF permanece como configuração recomendada. O benchmark depende da carga da máquina; o relatório de qualidade foi repetido com SHA-256 idêntico.
