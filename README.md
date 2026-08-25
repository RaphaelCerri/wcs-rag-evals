# WCS RAG Evals

> **English** · [Português](README.pt-BR.md)

[![CI](https://github.com/RaphaelCerri/wcs-rag-evals/actions/workflows/ci.yml/badge.svg)](https://github.com/RaphaelCerri/wcs-rag-evals/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An evaluation-first RAG system over public Warehouse Control System documentation. Every retrieval,
reranking, and generation change must beat a recorded baseline against a versioned golden set
before it can be promoted.

The corpus comes from a commit-pinned revision of public
[openWCS](https://github.com/brettljausn-ai/openwcs) documentation. No employer, client, or
proprietary material is included.

## What this project demonstrates

- Reproducible source manifest, allowlisted ingestion, and SHA-256 provenance.
- Deterministic heading-aware chunking for Markdown and OpenAPI documents.
- A custom BM25 baseline and multilingual dense retrieval with PostgreSQL and pgvector.
- Hybrid Reciprocal Rank Fusion tuned only on the `dev` split.
- Per-case Recall, Precision, MRR, and nDCG with immutable `dev` and `test` boundaries.
- A multilingual cross-encoder evaluated and rejected through predefined quality and latency gates.
- A deterministic grounded-answer baseline with citations and refusal behavior.
- A sealed judge calibration protocol that separates calibration from validation artifacts.
- GitHub Actions regression gates for retrieval, generation, and provenance hashes.

## Architecture

```mermaid
flowchart LR
    S[Commit-pinned public sources] --> I[Allowlisted ingestion]
    I --> C[Deterministic chunks]
    C --> B[BM25]
    C --> V[Multilingual embeddings + pgvector]
    B --> H[Hybrid RRF]
    V --> H
    H --> G[Grounded answer baseline]
    H --> E[Versioned evaluation]
    G --> E
    E --> Q{Regression gates}
    Q -->|pass| P[Promote]
    Q -->|fail| R[Reject and publish result]
```

## Measured retrieval results

The indexed corpus contains **75 documents and 1,458 chunks**. Retrieval metrics use 17 answerable
golden-set cases; the unanswerable case is reserved for refusal evaluation.

| Group | Retriever | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|
| All | BM25 | 0.819 | 0.892 | 0.696 | 0.718 |
| All | Dense | 0.784 | **0.946** | 0.688 | 0.710 |
| All | **Hybrid RRF** | **0.873** | 0.941 | **0.794** | **0.809** |
| Test | BM25 | 0.683 | 0.867 | 0.733 | 0.742 |
| Test | Dense | 0.700 | **0.950** | 0.733 | 0.735 |
| Test | **Hybrid RRF** | **0.800** | 0.933 | 0.733 | **0.775** |

Dense retrieval doubled Recall@5 for the Portuguese case from 0.333 to 0.667, while BM25 retained
stronger top-rank precision elsewhere. Hybrid RRF preserved that complementarity and remains the
recommended retriever.

## A rejected improvement is still a result

A multilingual cross-encoder reranked the Hybrid RRF top 10. Before running it, the project fixed
three gates: at least +0.010 dev nDCG@10, no test nDCG@10 regression, and CPU p95 below 15 seconds.

Latency passed at 13.99 seconds, but nDCG@10 fell by **0.083 on dev** and **0.029 on test**. The
reranker was rejected. The negative artifact remains published because additional complexity is not
an improvement when measured quality declines.

## Grounded-answer baseline

The first answer generator is intentionally deterministic and extractive. It returns evidence from
the top Hybrid RRF documents, preserves citation IDs, and refuses sensitive or unsupported queries.
It reached 100% schema validity, citation-ID validity, answerability handling, and relevant-document
citation, with 5.8 ms p95. Its low fact coverage remains explicit, so it is a safe control rather
than a claimed final answer system.

A local Qwen2.5-0.5B candidate failed the predefined dev gates and was never opened on `test`.

## Reproduce

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,vector]"
wcs-fetch-corpus
wcs-validate-evals
wcs-build-index
wcs-eval-bm25
docker compose up -d --wait
$env:WCS_DATABASE_URL = "postgresql://wcs:wcs_local_only@localhost:55432/wcs_rag"
wcs-build-vector-index
wcs-eval-vector
wcs-eval-hybrid
wcs-eval-reranker
wcs-eval-generation
wcs-build-judge-packet
wcs-check-regressions
pytest
```

## Current boundary

- Hybrid RRF is promoted; the reranker and local generative candidate are rejected.
- No LLM-backed answer API is presented as production-ready.
- API judge execution is pending an `OPENAI_API_KEY`.
- Current semantic labels are `model_assisted_adjudication`, not human ground truth.
- The corpus is public and reproducible, but raw third-party content is not republished here.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Evaluation strategy](docs/EVALS.md)
- [Judge calibration protocol](docs/JUDGE_CALIBRATION.md)
- [Regression gates](docs/REGRESSION_GATES.md)
- [Corpus policy](corpus/README.md) · [Português](corpus/README.pt-BR.md)
- [Machine-readable evaluation artifacts](evals/results/)

## AI assistance and license

Raphael Caveagna designed the architecture, evaluation criteria, trade-offs, and acceptance gates
with AI-assisted implementation and review. Published claims are tied to reproducible commands and
versioned artifacts.

Repository code is MIT licensed. openWCS is an external AGPL-3.0 source; its documentation is
downloaded from the pinned origin and is neither relicensed nor republished by this repository.
