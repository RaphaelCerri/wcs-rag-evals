# WCS RAG Evals

> [English](README.md) · **Português**

Sistema de RAG orientado a avaliação sobre documentação pública de Warehouse Control Systems. Cada
mudança de retrieval, reranking ou geração precisa superar um baseline registrado contra um golden
set versionado antes de ser promovida.

O corpus vem de uma revisão fixa por commit da documentação pública do
[openWCS](https://github.com/brettljausn-ai/openwcs). Nenhum material de empregador, cliente ou
fonte proprietária faz parte do projeto.

## O que o projeto demonstra

- Manifesto reproduzível, ingestão por allowlist e proveniência SHA-256.
- Chunking determinístico sensível a headings para Markdown e OpenAPI.
- Baseline BM25 próprio e retrieval denso multilíngue com PostgreSQL e pgvector.
- Reciprocal Rank Fusion ajustado somente no split `dev`.
- Recall, Precision, MRR e nDCG por caso, com fronteira imutável entre `dev` e `test`.
- Cross-encoder multilíngue avaliado e rejeitado por gates predefinidos.
- Baseline de resposta fundamentada com citações e recusa determinística.
- Protocolo selado de calibração do judge, separado dos artefatos de validação.
- Regression gates no GitHub Actions para retrieval, geração e hashes de proveniência.

## Arquitetura

```mermaid
flowchart LR
    S[Fontes públicas fixadas] --> I[Ingestão por allowlist]
    I --> C[Chunks determinísticos]
    C --> B[BM25]
    C --> V[Embeddings + pgvector]
    B --> H[Hybrid RRF]
    V --> H
    H --> G[Baseline fundamentado]
    H --> E[Avaliação versionada]
    G --> E
    E --> Q{Regression gates}
    Q -->|aprovado| P[Promover]
    Q -->|reprovado| R[Rejeitar e publicar]
```

## Resultados de retrieval

O corpus indexado contém **75 documentos e 1.458 chunks**. As métricas usam 17 casos respondíveis;
o caso não respondível fica reservado para avaliação de recusa.

| Grupo | Retriever | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|
| Todos | BM25 | 0,819 | 0,892 | 0,696 | 0,718 |
| Todos | Denso | 0,784 | **0,946** | 0,688 | 0,710 |
| Todos | **Hybrid RRF** | **0,873** | 0,941 | **0,794** | **0,809** |
| Test | BM25 | 0,683 | 0,867 | 0,733 | 0,742 |
| Test | Denso | 0,700 | **0,950** | 0,733 | 0,735 |
| Test | **Hybrid RRF** | **0,800** | 0,933 | 0,733 | **0,775** |

O retrieval denso dobrou o Recall@5 do caso em português, de 0,333 para 0,667, enquanto o BM25
preservou melhor precisão no topo em outros casos. O Hybrid RRF combina essa complementaridade e
permanece como retriever recomendado.

## Uma melhoria rejeitada também é resultado

Um cross-encoder multilíngue reordenou o top 10 do Hybrid RRF. Os gates exigiam ao menos +0,010 em
nDCG@10 de dev, nenhuma regressão em test e p95 de CPU abaixo de 15 segundos.

A latência passou em 13,99 segundos, mas nDCG@10 caiu **0,083 em dev** e **0,029 em test**. O
reranker foi rejeitado e o resultado negativo continua publicado.

## Baseline de resposta fundamentada

O primeiro gerador é deliberadamente determinístico e extrativo. Ele retorna evidência dos
documentos do Hybrid RRF, preserva IDs de citação e recusa perguntas sensíveis ou sem suporte.
Obteve 100% de schema válido, IDs válidos, tratamento de answerability e citação de documento
relevante, com p95 de 5,8 ms. A baixa cobertura factual permanece explícita.

Um candidato local Qwen2.5-0.5B falhou nos gates de `dev` e não foi aberto em `test`.

## Reproduzir

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

## Fronteira atual

- Hybrid RRF está promovido; reranker e candidato generativo local foram rejeitados.
- Nenhuma API de resposta por LLM é apresentada como pronta para produção.
- A execução do judge por API depende de `OPENAI_API_KEY`.
- Labels atuais são `model_assisted_adjudication`, não ground truth humano.
- O corpus é público e reproduzível, mas o conteúdo bruto de terceiro não é republicado.

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Estratégia de avaliação](docs/EVALS.md)
- [Protocolo de calibração](docs/JUDGE_CALIBRATION.md)
- [Regression gates](docs/REGRESSION_GATES.md)
- [Política do corpus](corpus/README.pt-BR.md) · [English](corpus/README.md)
- [Artefatos de avaliação](evals/results/)

## Assistência por IA e licença

Raphael Caveagna definiu arquitetura, critérios, trade-offs e gates de aceite com implementação e
revisão assistidas por IA. Claims publicadas estão ligadas a comandos reproduzíveis e artefatos
versionados.

O código usa licença MIT. openWCS é uma fonte externa AGPL-3.0, baixada da origem fixada e não
relicenciada ou republicada neste repositório.
