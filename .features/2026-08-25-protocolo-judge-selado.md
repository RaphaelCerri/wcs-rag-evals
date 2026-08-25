---
data: 2026-08-25
titulo: Protocolo selado de calibration e validation do judge
tipo: correcao
escopo: evals, judge, governança
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/evaluate_judge.py
  - src/wcs_rag_evals/judge.py
  - src/wcs_rag_evals/judge_contracts.py
  - evals/judges/agent-proxy-calibration-labels-v0.1.jsonl
  - evals/judges/agent-proxy-validation-labels-v0.1.jsonl
  - docs/JUDGE_CALIBRATION.md
---

## O que mudou

Calibration e validation passaram a executar separadamente, com validation bloqueada até um selo
SHA-256 fixar configuração, rótulos e relatório de calibration. O cache usa o hash real do prompt,
schema e parâmetros; três ordens de evidência medem sensibilidade posicional.

## Por que

A primeira versão poderia abrir os dois grupos na mesma execução e chamava um template vazio de
ground truth humano. Revisões independentes CFA, CEA e CSA identificaram leakage, proveniência
incorreta e ausência de thresholds pré-registrados.

## Como usar

Execute `wcs-eval-judge --phase calibration`. Depois que o selo for criado sem alterar os artifacts,
execute `wcs-eval-judge --phase validation`.

## Notas

Os 13 rótulos por agentes tiveram consenso integral, 2 `pass` e 11 `fail`, e estão declarados como
`model_assisted_adjudication`. Eles não são evidência humana. Os gates de validation foram fixados
antes da API: exact agreement 0,80, kappa 0,60, estabilidade 0,90 e acerto do caso de recusa.
