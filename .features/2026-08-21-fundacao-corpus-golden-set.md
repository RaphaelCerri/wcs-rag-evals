---
data: 2026-08-21
titulo: Fundação reproduzível do corpus e golden set WCS
tipo: feature
escopo: corpus, evals
ferramenta: codex
arquivos:
  - corpus/sources.yaml
  - evals/datasets/golden-v0.1.jsonl
  - src/wcs_rag_evals/fetch_corpus.py
  - src/wcs_rag_evals/contracts.py
  - docs/EVALS.md
  - README.md
---

## O que mudou

O projeto passou a ter um corpus openWCS fixado por commit, coleta por allowlist com hashes de proveniência e um golden set tipado com 18 casos. Os casos cobrem arquitetura, inventory, outbound, slotting, equipamentos, segurança, confiabilidade, integração e recusa de pergunta sem evidência.

## Por que

Sem um dataset de avaliação anterior à implementação, não seria possível provar se embeddings, retrieval híbrido ou reranking melhoram o sistema. A fundação cria o controle necessário para comparar cada arquitetura contra o mesmo conjunto versionado.

## Como usar

Instale o projeto com `python -m pip install -e ".[dev]"`, execute `wcs-fetch-corpus`, valide com `wcs-validate-evals` e rode `pytest`.

## Notas

O corpus bruto permanece em `.data/` e não é republicado. A revisão do repositório e da wiki, a licença e os caminhos selecionados vivem em `corpus/sources.yaml`.

