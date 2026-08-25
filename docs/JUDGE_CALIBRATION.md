# Calibração do LLM-as-judge

## Objetivo

A Fase 6 mede se um judge semântico concorda com decisões humanas sobre groundedness,
relevância, suporte das citações e completude. O judge não substitui o revisor humano: ele só pode
ser promovido depois de comparação explícita com rótulos independentes.

## Desenho do piloto

- 8 casos de `calibration` para diagnosticar divergências e ajustar a rubrica.
- 5 casos de `validation`, preservados até a medição final.
- Rótulos humanos `pass`, `fail` e `unsure`.
- Casos `unsure` documentados e excluídos da concordância.
- Três execuções independentes do judge por caso.
- Voto majoritário, estabilidade, concordância exata, matriz de confusão e Cohen's kappa.
- Cache persistido depois de cada chamada para retomar sem repetir custo.

A amostra é pequena e serve para validar o mecanismo. Ela não sustenta alegações de generalização
estatística fora deste corpus.

## Judge candidato

O candidato fixado é `gpt-5.4-mini-2026-03-17`, via Responses API e Structured Outputs. Modelo,
snapshot, versão do prompt, tokens, latência, IDs das respostas e custo estimado são registrados.
O preço usado no relatório é USD 0,75 por milhão de tokens de entrada e USD 4,50 por milhão de
tokens de saída. Consulte a [documentação oficial do modelo](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

O modelo recebe as evidências recuperadas, a resposta avaliada, as citações, a referência e os
fatos esperados. Ele nunca recebe o rótulo humano nem a indicação de grupo de calibração.

## Reproduzir

```powershell
python -m pip install -e ".[dev,judge]"
wcs-build-judge-packet
```

O pacote completo fica em `reports/judge/`, fora do Git porque contém trechos do corpus AGPL.
Preencha `evals/judges/human-labels-v0.1.jsonl` usando `evals/judges/RUBRIC.md`. O gerador nunca
sobrescreve o arquivo de rótulos quando ele já existe.

Depois de concluir os rótulos, configure a chave sem colá-la no chat nem salvá-la no repositório:

```powershell
$secureKey = Read-Host "OPENAI_API_KEY" -AsSecureString
$env:OPENAI_API_KEY = [Net.NetworkCredential]::new("", $secureKey).Password
wcs-eval-judge
```

O resultado versionável será gravado em `evals/results/judge-v0.1.json`. O cache retomável fica em
`reports/judge-cache-v0.1.json`, diretório ignorado pelo Git.

## Critério de promoção

Nenhum limiar é declarado como aprovado antes dos rótulos. Primeiro são publicados concordância,
kappa, estabilidade e divergências. Só depois o resultado sustenta uma decisão de promover,
revisar ou rejeitar o judge.
