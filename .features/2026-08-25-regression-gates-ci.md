---
data: 2026-08-25
titulo: Regression gates de qualidade e proveniência no CI
tipo: feature
escopo: evals, ci, observabilidade
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/regression_gate.py
  - evals/regression-policy-v0.1.yaml
  - tests/test_regression_gate.py
  - .github/workflows/ci.yml
  - docs/REGRESSION_GATES.md
---

## O que mudou

Pushes e pull requests passaram a verificar pisos de retrieval e geração, teto de claims proibidos
e hashes da cadeia de proveniência. O comando retorna relatório JSON e exit code diferente de zero
quando qualquer regressão é detectada.

## Por que

Os relatórios publicados eram auditáveis, mas o CI não impedia uma mudança de artifact que
degradava as métricas aceitas. A Fase 7 exigia transformar os baselines em contratos executáveis.

## Como usar

Execute `wcs-check-regressions`. A política fica em `evals/regression-policy-v0.1.yaml` e o mesmo
comando roda automaticamente no GitHub Actions.

## Notas

O teste de controle reduz Recall@5 de test para zero e confirma a falha. O CI valida artifacts
versionados e proveniência, mas não regenera modelos ou pgvector. O gap pt-BR e o judge pendente
continuam declarados em vez de receber thresholds sem evidência. Hashes textuais tratam LF e CRLF
como representações portáveis do mesmo artifact e ainda reportam os bytes observados.
