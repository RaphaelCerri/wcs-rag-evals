# Geração fundamentada

## Objetivo

Estabelecer uma resposta auditável antes de adicionar síntese probabilística. O pipeline recebe os três primeiros documentos do Hybrid RRF, limita o contexto e produz resposta, classificação de answerability e citações estruturadas.

## Baseline extrativo

Para cada documento recuperado, o baseline seleciona a sentença com maior sobreposição lexical com a pergunta. A resposta concatena essas evidências e cita todos os documentos utilizados. Sem retrieval, ele recusa. Solicitações explícitas de senha, segredo, token, credencial ou dado proprietário também são recusadas.

Esse desenho garante que o texto veio do contexto, mas não garante completude, boa síntese ou entailment por claim. Por isso o relatório usa nomes como `required_fact_coverage_proxy` e `extractive_bigram_support_proxy`.

## Gates declarados antes da execução

- schema válido: 1,000;
- validade dos IDs de citação: 1,000;
- recusa correta: 1,000;
- pelo menos um documento relevante citado em 0,800 dos casos respondíveis;
- ganho mínimo de 0,100 em fact coverage de `dev` contra o controle sem retrieval;
- p95 máximo de 30.000 ms em CPU.

Todos passaram. Isso aceita o componente como baseline, não como resposta final. Os resultados absolutos de test, fact coverage 0,167 e gold citation precision 0,533, mostram o que ainda precisa melhorar.

## Candidato Qwen local rejeitado

O primeiro candidato generativo foi `Qwen/Qwen2.5-0.5B-Instruct`, fixado em `7ae557604adf67be50417f59c2c2f167def9a775`. O modelo foi escolhido por ser pequeno, instruction-tuned e multilíngue.

O backend PyTorch não foi viável nesta CPU: apenas o prefill de 2.636 tokens com oito tokens de saída ultrapassou 150 segundos. O runtime foi trocado para `llama.cpp` 0.3.35 usando o GGUF oficial Q5_K_M, fixado em `9217f5db79a29953eb74d5343926648285ec7e67`.

A configuração foi desenvolvida apenas em `dev`. O contexto caiu de cinco para três documentos, passagens foram limitadas a 120 palavras, a resposta recebeu limite de 55 palavras e uma gramática JSON passou a impor o contrato. Os gates não foram alterados.

Resultado nos 12 casos de `dev`:

| Métrica | Resultado | Gate |
|---|---:|---:|
| Schema válido | 0,667 | 1,000 |
| IDs de citação válidos | 0,333 | 1,000 |
| Caso com documento relevante citado | 0,000 | 0,800 |
| Delta de fact coverage | +0,021 | +0,100 |
| p95 | 59.238 ms | 30.000 ms |

O candidato falhou antes da abertura de `test`. A rejeição evita escolher modelo com base no conjunto reservado e evita promover complexidade porque o runtime é local ou porque o modelo parece mais sofisticado.

Para preparar o runtime experimental em Windows com wheel de CPU:

```powershell
python -m pip install huggingface-hub
python -m pip install llama-cpp-python==0.3.35 `
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

O baseline extrativo executado por `wcs-eval-generation` não depende desses pacotes.

## Próxima comparação

Um novo gerador deve superar o baseline em fact coverage e precisão de citações sem perder recusa, validade estrutural ou rastreabilidade. A afirmação de faithfulness semântica depende da Fase 6, com judge calibrado contra rótulos humanos.
