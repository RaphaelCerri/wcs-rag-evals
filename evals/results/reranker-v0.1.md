# Cross-encoder reranker v0.1

Reordenação dos dez documentos do Hybrid RRF com um cross-encoder multilíngue
fixado por revisão. Os critérios foram declarados antes da execução e o split `test`
não foi usado para selecionar configuração.

## Configuração

- Modelo: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- Revisão: `1427fd652930e4ba29e8149678df786c240d8825`
- Execução: CPU, batch 16
- Candidatos: top 10 do Hybrid RRF
- Passagens: melhor chunk BM25 e dense por documento; prevalece o maior score

## Resultado

| Grupo | Sistema | R@5 | R@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|
| all | Hybrid RRF | 0.873 | 0.941 | 0.794 | 0.809 |
| all | Reranker | 0.779 | 0.941 | 0.745 | 0.741 |
| dev | Hybrid RRF | 0.903 | 0.944 | 0.819 | 0.823 |
| dev | Reranker | 0.819 | 0.944 | 0.736 | 0.739 |
| test | Hybrid RRF | 0.800 | 0.933 | 0.733 | 0.775 |
| test | Reranker | 0.683 | 0.933 | 0.767 | 0.746 |
| language:en | Hybrid RRF | 0.885 | 0.938 | 0.823 | 0.823 |
| language:en | Reranker | 0.807 | 0.938 | 0.771 | 0.753 |
| language:pt-BR | Hybrid RRF | 0.667 | 1.000 | 0.333 | 0.578 |
| language:pt-BR | Reranker | 0.333 | 1.000 | 0.333 | 0.550 |

## Gates de qualidade

- `dev_ndcg_at_10`: delta -0.083; mínimo +0.010; **falhou**
- `test_ndcg_at_10`: delta -0.029; mínimo +0.000; **falhou**

O gate de latência e a decisão agregada ficam no benchmark separado, pois tempos
de execução variam por máquina e não pertencem ao artefato determinístico.

## Resultado por caso

| Caso | Split | Idioma | Primeiro relevante | nDCG@10 | Delta | Top 1 |
|---|---|---|---:|---:|---:|---|
| wcs-dev-001 | dev | en | 2 | 0.580 | +0.089 | `openwcs-repo/build.md` |
| wcs-dev-002 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0001-inventory-data-ownership.md` |
| wcs-dev-003 | dev | en | 2 | 0.631 | +0.000 | `openwcs-wiki/Outbound-Flow.md` |
| wcs-dev-004 | dev | en | 1 | 1.000 | +0.000 | `openwcs-repo/docs/adr/0002-outbound-allocation-and-cubing.md` |
| wcs-dev-005 | dev | en | 3 | 0.500 | -0.500 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-dev-006 | dev | en | 1 | 1.000 | +0.000 | `openwcs-wiki/Slotting-and-Replenishment.md` |
| wcs-dev-007 | dev | en | 1 | 0.920 | +0.226 | `openwcs-repo/docs/adr/0006-gtp-station-execution.md` |
| wcs-dev-008 | dev | en | 1 | 0.920 | +0.000 | `openwcs-repo/docs/SCALING.md` |
| wcs-dev-009 | dev | en | 1 | 0.850 | -0.069 | `openwcs-repo/docs/adr/0008-live-scan-driven-conveyance.md` |
| wcs-dev-010 | dev | en | 1 | 0.877 | -0.043 | `openwcs-repo/docs/adr/0009-double-deep-channel-relocation.md` |
| wcs-dev-011 | dev | en | 3 | 0.235 | -0.061 | `openwcs-repo/build.md` |
| wcs-dev-012 | dev | en | 6 | 0.356 | -0.644 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-test-001 | test | en | 1 | 0.971 | +0.066 | `openwcs-repo/docs/AS-BUILT.md` |
| wcs-test-002 | test | en | 1 | 0.920 | -0.080 | `openwcs-repo/SECURITY.md` |
| wcs-test-003 | test | en | 2 | 0.437 | +0.046 | `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md` |
| wcs-test-005 | test | en | 1 | 0.850 | -0.150 | `openwcs-repo/build.md` |
| wcs-test-006 | test | pt-BR | 3 | 0.550 | -0.028 | `openwcs-repo/build.md` |

## Reproduzir

```powershell
wcs-eval-reranker
```
