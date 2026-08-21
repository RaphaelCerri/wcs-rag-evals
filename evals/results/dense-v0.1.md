# Dense retrieval baseline v0.1

Resultado do retrieval vetorial multilíngue persistido em PostgreSQL com pgvector.
As métricas usam o mesmo corpus, chunks, golden set e ranking por documento do BM25.

## Configuração

- Corpus: 75 documentos e 1458 chunks
- Golden set: 17 casos respondíveis e 1 não respondível
- Modelo: `intfloat/multilingual-e5-small` em revisão fixa
- Embeddings: 384 dimensões, normalizados
- Banco: PostgreSQL 17 e pgvector 0.8.6, com cosine distance
- Execução medida: busca exata; HNSW disponível no schema para volumes maiores
- Candidatos: 100 chunks, agregados pelo maior score

## Comparação com BM25

| Grupo | Casos | R@5 | Δ R@5 | R@10 | Δ R@10 | MRR@10 | Δ MRR | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 17 | 0.784 | -0.034 | 0.946 | +0.054 | 0.688 | -0.008 | 0.710 |
| dev | 12 | 0.819 | -0.056 | 0.944 | +0.042 | 0.669 | -0.011 | 0.699 |
| test | 5 | 0.700 | +0.017 | 0.950 | +0.083 | 0.733 | +0.000 | 0.735 |
| language:en | 16 | 0.792 | -0.057 | 0.943 | +0.036 | 0.710 | -0.008 | 0.716 |
| language:pt-BR | 1 | 0.667 | +0.333 | 1.000 | +0.333 | 0.333 | +0.000 | 0.604 |

## Resultado por caso

| Caso | Split | Idioma | Primeiro relevante | Recall@5 | Δ BM25 | Top 1 |
|---|---|---|---:|---:|---:|---|
| wcs-dev-001 | dev | en | 5 | 0.500 | +0.000 | `openwcs-repo/SECURITY.md` |
| wcs-dev-002 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0001-inventory-data-ownership.md` |
| wcs-dev-003 | dev | en | 3 | 1.000 | +0.000 | `openwcs-wiki/Outbound-Flow.md` |
| wcs-dev-004 | dev | en | 3 | 1.000 | +0.000 | `openwcs-wiki/Hardware-Visualisation.md` |
| wcs-dev-005 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md` |
| wcs-dev-006 | dev | en | 1 | 1.000 | +0.000 | `openwcs-wiki/Slotting-and-Replenishment.md` |
| wcs-dev-007 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0006-gtp-station-execution.md` |
| wcs-dev-008 | dev | en | 3 | 0.500 | -0.500 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-dev-009 | dev | en | 2 | 0.500 | -0.500 | `openwcs-repo/contracts/openapi/flow-orchestrator.yaml` |
| wcs-dev-010 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0009-double-deep-channel-relocation.md` |
| wcs-dev-011 | dev | en | 1 | 0.333 | +0.333 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-dev-012 | dev | en | 3 | 1.000 | +0.000 | `openwcs-wiki/Process-Designer.md` |
| wcs-test-001 | test | en | 1 | 0.500 | -0.250 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-test-002 | test | en | 1 | 1.000 | +0.000 | `openwcs-wiki/Security.md` |
| wcs-test-003 | test | en | 3 | 0.333 | +0.000 | `openwcs-repo/docs/adr/0002-outbound-allocation-and-cubing.md` |
| wcs-test-005 | test | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0001-inventory-data-ownership.md` |
| wcs-test-006 | test | pt-BR | 3 | 0.667 | +0.333 | `openwcs-repo/build.md` |

## Reproduzir

```powershell
docker compose up -d --wait
$env:WCS_DATABASE_URL = "postgresql://wcs:wcs_local_only@localhost:55432/wcs_rag"
wcs-build-index
wcs-build-vector-index
wcs-eval-vector
```

O JSON ao lado preserva configuração, hashes, rankings, scores e deltas completos.
