# Hybrid retrieval with RRF v0.1

Comparação reproduzível entre BM25, dense retrieval e rank fusion.
Os parâmetros foram selecionados exclusivamente nos 12 casos respondíveis de `dev`;
o split `test` foi usado somente depois da seleção.

## Configuração selecionada

- Método: weighted Reciprocal Rank Fusion
- Constante de rank: 60
- Peso BM25: 1.0
- Peso dense: 1.0
- Profundidade de cada fonte: top 10 documentos
- Objetivo de seleção: nDCG@10, Recall@5 e MRR@10 em `dev`

## Comparação

| Grupo | Retriever | R@5 | R@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|
| all | BM25 | 0.819 | 0.892 | 0.696 | 0.718 |
| all | Dense | 0.784 | 0.946 | 0.688 | 0.710 |
| all | Hybrid RRF | 0.873 | 0.941 | 0.794 | 0.809 |
| dev | BM25 | 0.875 | 0.903 | 0.681 | 0.708 |
| dev | Dense | 0.819 | 0.944 | 0.669 | 0.699 |
| dev | Hybrid RRF | 0.903 | 0.944 | 0.819 | 0.823 |
| test | BM25 | 0.683 | 0.867 | 0.733 | 0.742 |
| test | Dense | 0.700 | 0.950 | 0.733 | 0.735 |
| test | Hybrid RRF | 0.800 | 0.933 | 0.733 | 0.775 |
| language:en | BM25 | 0.849 | 0.906 | 0.719 | 0.738 |
| language:en | Dense | 0.792 | 0.943 | 0.710 | 0.716 |
| language:en | Hybrid RRF | 0.885 | 0.938 | 0.823 | 0.823 |
| language:pt-BR | BM25 | 0.333 | 0.667 | 0.333 | 0.402 |
| language:pt-BR | Dense | 0.667 | 1.000 | 0.333 | 0.604 |
| language:pt-BR | Hybrid RRF | 0.667 | 1.000 | 0.333 | 0.578 |

## Resultado por caso

| Caso | Split | Idioma | Primeiro relevante | R@5 | Δ BM25 | Δ Dense | Top 1 |
|---|---|---|---:|---:|---:|---:|---|
| wcs-dev-001 | dev | en | 3 | 0.500 | +0.000 | +0.000 | `openwcs-wiki/Home.md` |
| wcs-dev-002 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0001-inventory-data-ownership.md` |
| wcs-dev-003 | dev | en | 2 | 1.000 | +0.000 | +0.000 | `openwcs-wiki/Outbound-Flow.md` |
| wcs-dev-004 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0002-outbound-allocation-and-cubing.md` |
| wcs-dev-005 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md` |
| wcs-dev-006 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md` |
| wcs-dev-007 | dev | en | 2 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-dev-008 | dev | en | 1 | 1.000 | +0.000 | +0.500 | `openwcs-repo/docs/SCALING.md` |
| wcs-dev-009 | dev | en | 1 | 1.000 | +0.000 | +0.500 | `openwcs-repo/docs/adr/0008-live-scan-driven-conveyance.md` |
| wcs-dev-010 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0009-double-deep-channel-relocation.md` |
| wcs-dev-011 | dev | en | 2 | 0.333 | +0.333 | +0.000 | `openwcs-repo/README.md` |
| wcs-dev-012 | dev | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/process-designer-spec.md` |
| wcs-test-001 | test | en | 1 | 1.000 | +0.250 | +0.500 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-test-002 | test | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/SECURITY.md` |
| wcs-test-003 | test | en | 3 | 0.333 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0007-conveyor-transport-and-workplace-induction.md` |
| wcs-test-005 | test | en | 1 | 1.000 | +0.000 | +0.000 | `openwcs-repo/docs/adr/0001-inventory-data-ownership.md` |
| wcs-test-006 | test | pt-BR | 3 | 0.667 | +0.333 | +0.000 | `openwcs-repo/build.md` |

## Reproduzir

```powershell
wcs-eval-hybrid
```

A execução usa os relatórios versionados de BM25 e dense retrieval.
O JSON registra os 20 trials de `dev`, ranks e contribuição de cada fonte.
