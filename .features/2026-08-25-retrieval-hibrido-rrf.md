---
data: 2026-08-25
titulo: Retrieval híbrido com Reciprocal Rank Fusion
tipo: feature
escopo: retrieval, evals
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/rrf.py
  - src/wcs_rag_evals/evaluate_hybrid.py
  - evals/results/hybrid-v0.1.json
  - evals/results/hybrid-v0.1.md
  - tests/test_hybrid_evaluation.py
  - README.md
---

## O que mudou

O projeto passou a combinar rankings de BM25 e dense retrieval com Weighted Reciprocal Rank Fusion. Uma grade predefinida seleciona os parâmetros somente em `dev`, e o relatório compara as três estratégias no conjunto completo, por split, idioma e caso.

## Por que

Os baselines apresentaram erros complementares: BM25 teve melhor Recall@5 agregado, enquanto dense retrieval ampliou cobertura, teste e recuperação cross-lingual. A fusão testa se os sinais podem ser combinados sem adicionar um modelo de reranking.

## Como usar

Execute `wcs-eval-hybrid` depois que os relatórios BM25 e dense v0.1 existirem. O resultado Markdown apresenta a comparação; o JSON preserva os 20 trials de `dev`, a configuração selecionada, ranks e contribuição de cada fonte.

## Notas

A configuração selecionada foi RRF com constante 60 e pesos iguais. Recall@5 chegou a 0,873 no conjunto completo e 0,800 em `test`; nDCG@10 chegou a 0,809 no conjunto completo. Dense retrieval isolado permaneceu com o maior Recall@10 de teste, uma limitação mantida de forma explícita.
