# Regression gates

## O que o CI protege

`wcs-check-regressions` lê a política versionada em `evals/regression-policy-v0.1.yaml` e falha
quando um artifact publicado cruza um limite predefinido. O gate cobre:

- Recall@5 e nDCG@10 do Hybrid RRF nos grupos agregado e test;
- validade estrutural, answerability e citações da geração;
- proxies mínimas de cobertura e precision/recall documental;
- ausência de claims proibidos detectados lexicalmente;
- hashes de proveniência entre golden set, BM25, dense, hybrid e geração.

O teste automatizado injeta uma regressão deliberada em Recall@5 de test e confirma que somente o
gate correspondente falha. Isso testa o mecanismo, não apenas o caminho feliz.

## Limites predefinidos

| Métrica | Piso ou teto | Baseline observado |
|---|---:|---:|
| Hybrid Recall@5 agregado | >= 0,85 | 0,873 |
| Hybrid nDCG@10 agregado | >= 0,79 | 0,809 |
| Hybrid Recall@5 test | >= 0,78 | 0,800 |
| Hybrid nDCG@10 test | >= 0,75 | 0,775 |
| Generation fact coverage proxy | >= 0,30 | 0,328 |
| Generation citation precision | >= 0,45 | 0,490 |
| Generation citation recall | >= 0,80 | 0,824 |
| Forbidden claim lexical hits | <= 0 | 0 |

Schema, answerability e validade das citações devem permanecer em 1,0.

## Executar

```powershell
wcs-check-regressions
```

O comando retorna JSON auditável e exit code 1 quando qualquer check ou hash falha. O mesmo comando
é executado em push e pull request pelo GitHub Actions.

## Limitação explícita

O CI leve valida os artifacts versionados e sua cadeia de proveniência. Ele não baixa modelos,
reconstrói pgvector ou regenera o pipeline full-stack em cada commit. Mudanças no pipeline exigem
regeneração explícita dos relatórios antes de atualizar a política. O gap pt-BR e as métricas
semânticas do judge permanecem declarados, não convertidos em thresholds artificiais.
