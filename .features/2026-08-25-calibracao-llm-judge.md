---
data: 2026-08-25
titulo: Infraestrutura de calibração humana do LLM-as-judge
tipo: feature
escopo: evals, judge, observabilidade
ferramenta: codex
arquivos:
  - src/wcs_rag_evals/build_judge_packet.py
  - src/wcs_rag_evals/evaluate_judge.py
  - src/wcs_rag_evals/judge.py
  - evals/judges/RUBRIC.md
  - docs/JUDGE_CALIBRATION.md
---

## O que mudou

O projeto passou a gerar um pacote de 13 casos para anotação humana e a executar um judge
estruturado três vezes por caso. O relatório calcula concordância exata, Cohen's kappa, matriz de
confusão, estabilidade, tokens, custo e latência, com cache retomável depois de cada chamada.

## Por que

As proxies lexicais da geração não medem faithfulness, relevância semântica ou suporte real das
citações. Era necessário comparar o judge com decisões humanas independentes antes de usar suas
métricas para promover modelos.

## Como usar

Execute `wcs-build-judge-packet`, rotule os casos em
`evals/judges/human-labels-v0.1.jsonl` conforme a rubrica e, com `OPENAI_API_KEY` configurada,
execute `wcs-eval-judge`.

## Notas

Oito casos pertencem à calibração e cinco à validação intocada. O builder não sobrescreve rótulos
humanos existentes. O pacote com trechos do corpus é gerado em `reports/` e não é publicado no
repositório MIT. A Fase 6 permanece em andamento até os rótulos serem concluídos e o judge ser
executado; esta entrega registra a infraestrutura utilizável, não um resultado de concordância.
