# Calibração do LLM-as-judge

## Estado honesto

A infraestrutura está pronta, mas não existe ground truth humano especializado. Raphael declarou
não dominar o conteúdo WCS; portanto, seu primeiro rótulo foi descartado e o template humano
permanece vazio. Nenhum resultado deste piloto pode ser descrito como human calibration.

Três revisores em sessões separadas, CEA, CSA e um reviewer consultivo de fairness/assurance,
avaliaram os 13 casos sem ler o arquivo persistido de rótulos. Houve consenso integral: 2 `pass`
e 11 `fail`. O artefato identifica explicitamente essas decisões como
`model_assisted_adjudication`.

## Desenho do piloto

- 8 casos de `calibration` para analisar o comportamento do judge.
- 5 casos de `validation`, com arquivo de rótulos separado e execução bloqueada até existir selo.
- Rótulos `pass`, `fail` e `unsure`; `unsure` exige justificativa e não entra na concordância.
- Três ordens de evidência: retrieval, reversa e rotacionada.
- Voto majoritário, estabilidade posicional, concordância exata, matriz de confusão e Cohen's kappa.
- Cache persistido após cada chamada, invalidado por hash real do pacote e da configuração.
- Modelo, prompt, JSON Schema, esforço, limite de saída e política de ordenação selados por SHA-256.

A amostra é pequena, selecionada e desbalanceada. Ela valida o mecanismo, não sustenta inferência
estatística nem generalização para outros domínios. O dataset contém apenas um caso pt-BR e um caso
de recusa, ambos em validation; essa limitação impede alegações por idioma ou classe de segurança.

## Judge candidato

O candidato fixado é `gpt-5.4-mini-2026-03-17`, via Responses API e Structured Outputs. Tokens,
latência, IDs das respostas e custo estimado são registrados. O preço usado no relatório é USD
0,75 por milhão de tokens de entrada e USD 4,50 por milhão de tokens de saída. Consulte a
[documentação oficial do modelo](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

O modelo recebe evidências, resposta, lista documental de citações, referência e fatos esperados.
Ele não recebe o rótulo de referência nem a fase. `citation_support` mede o conjunto de documentos
citados; o sistema ainda não possui vínculo estruturado entre claim e passagem.

## Executar sem leakage

```powershell
python -m pip install -e ".[dev,judge]"
wcs-build-judge-packet
```

O pacote fica em `reports/judge/`, fora do Git porque contém trechos do corpus AGPL. A rubrica,
os rótulos por proxy e o template humano vazio ficam em `evals/judges/`.

Configure a chave sem colá-la no chat ou salvá-la no repositório:

```powershell
$secureKey = Read-Host "OPENAI_API_KEY" -AsSecureString
$env:OPENAI_API_KEY = [Net.NetworkCredential]::new("", $secureKey).Password
wcs-eval-judge --phase calibration
```

A primeira execução carrega apenas os oito rótulos de calibration. Ela grava
`judge-calibration-v0.1.json` e um selo que preserva também o hash pré-comprometido do arquivo de
validation, sem carregar seus rótulos no fluxo de calibration. Somente depois:

```powershell
wcs-eval-judge --phase validation
```

Validation recusa executar se configuração, rótulos ou relatório de calibration mudarem. O cache
retomável fica em `reports/judge-cache-v0.1.json`.

## Gates pré-registrados de validation

- concordância exata mínima: 0,80;
- Cohen's kappa mínimo: 0,60;
- estabilidade entre ordens de evidência mínima: 0,90;
- classificação correta do caso de recusa `wcs-test-004`.

Esses gates determinam somente se o judge pode auxiliar regression checks deste corpus. Eles não
transformam adjudicação por agentes em evidência humana nem certificam qualidade semântica geral.
