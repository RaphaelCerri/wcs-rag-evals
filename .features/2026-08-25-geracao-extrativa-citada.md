---
data: 2026-08-25
titulo: Baseline extrativo com citações e recusa
tipo: feature
escopo: generation, evals, safety
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/generation.py
  - src/wcs_rag_evals/evaluate_generation.py
  - evals/results/generation-v0.1.json
  - evals/results/generation-v0.1.md
  - evals/results/generation-benchmark-v0.1.json
  - evals/results/generation-benchmark-v0.1.md
  - tests/test_generation.py
  - docs/GENERATION.md
  - README.md
---

## O que mudou

O projeto passou a produzir respostas extrativas com citações estruturadas sobre o top 3 do Hybrid RRF. A avaliação compara esse caminho com recusa sem retrieval, mede proxies determinísticas, tokens e latência, e preserva os resultados por caso.

## Por que

Uma resposta citada precisa de um controle seguro antes de síntese por LLM. O baseline separa o que pode ser garantido deterministicamente do que exige avaliação semântica, além de expor limitações de completude e precisão sem inflar as métricas.

## Como usar

Execute `wcs-eval-generation` depois que o índice BM25 e os relatórios de retrieval v0.1 existirem. O comando grava relatórios de qualidade e benchmark. O cache por caso permite retomar uma execução interrompida.

## Notas

Os gates estruturais passaram e o p95 foi 5,8 ms. Fact coverage ficou em 0,328 e gold citation precision em 0,490, então o componente foi aceito apenas como baseline. Um Qwen 0.5B local foi testado em `dev` e rejeitado por estrutura, citações, cobertura e latência.
