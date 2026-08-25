# WCS RAG Evals

Sistema de RAG orientado a avaliação sobre documentação pública de Warehouse Control Systems. O projeto evolui a partir de baselines mensuráveis: antes de promover embeddings, busca híbrida ou reranking, cada mudança precisa provar que melhorou retrieval, resposta ou custo contra um golden set versionado.

O domínio escolhido é logística e automação de armazéns. O corpus inicial usa a documentação pública do [openWCS](https://github.com/brettljausn-ai/openwcs), fixada por commit e baixada por script. Nenhum dado, documento ou nome de cliente da experiência profissional do autor faz parte do projeto.

## Estado atual

**Fase 4, reranker medido e rejeitado.** O projeto já contém:

- manifesto reproduzível de fontes e revisões;
- ingestão allowlist, sem republicar o corpus de terceiro;
- hashes SHA-256 de cada documento coletado;
- golden set inicial com respostas, fatos obrigatórios e claims proibidos;
- validação tipada dos contratos de fonte e avaliação;
- chunking determinístico e sensível a headings para Markdown e OpenAPI;
- implementação própria de BM25 com ranking por documento;
- embeddings multilíngues persistidos em PostgreSQL com pgvector;
- índice HNSW disponível para escala e busca exata usada no corpus atual;
- Reciprocal Rank Fusion com parâmetros selecionados exclusivamente em `dev`;
- Recall@k, Precision@k, MRR@10 e nDCG@k calculados por caso e por split;
- comparação reproduzível entre retrieval lexical, vetorial e híbrido;
- avaliação de cross-encoder multilíngue com modelo e revisão fixados;
- gates predefinidos de qualidade e latência que impediram promover uma regressão.

O reranker existe como experimento auditável, mas não integra a configuração recomendada porque piorou nDCG@10 em `dev` e `test`. Ainda não há geração por LLM ou API; esses componentes precisarão justificar sua complexidade sob os mesmos casos.

## Resultado do baseline

O BM25 v0.1 indexou **75 documentos em 1.458 chunks** e avaliou os 17 casos respondíveis do golden set. O caso não respondível foi preservado para a futura avaliação de recusa, mas não entrou nas métricas de retrieval por não possuir documento relevante.

| Split | Casos | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| Todos | 17 | 0,338 | **0,819** | **0,892** | **0,696** | **0,718** |
| Dev | 12 | 0,375 | 0,875 | 0,903 | 0,681 | 0,708 |
| Test | 5 | 0,250 | 0,683 | 0,867 | 0,733 | 0,742 |

O recorte em inglês atingiu Recall@5 de 0,849. O primeiro caso cross-lingual, com pergunta em português e corpus majoritariamente em inglês, atingiu apenas 0,333. Essa diferença registra uma limitação lexical concreta que embeddings e busca híbrida deverão resolver, sem alterar o conjunto de teste depois de observar o resultado.

Veja o [relatório legível](evals/results/bm25-v0.1.md) ou o [artefato completo em JSON](evals/results/bm25-v0.1.json).

## Resultado do retrieval vetorial

O baseline denso usa [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small) em revisão fixa, com prefixos assimétricos `query:` e `passage:`. Os vetores normalizados de 384 dimensões são persistidos em PostgreSQL 17 com [pgvector](https://github.com/pgvector/pgvector) 0.8.6.

| Grupo | BM25 R@5 | Vetorial R@5 | Δ | BM25 R@10 | Vetorial R@10 | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Todos | 0,819 | 0,784 | -0,034 | 0,892 | **0,946** | **+0,054** |
| Dev | 0,875 | 0,819 | -0,056 | 0,903 | **0,944** | **+0,042** |
| Test | 0,683 | **0,700** | **+0,017** | 0,867 | **0,950** | **+0,083** |
| pt-BR | 0,333 | **0,667** | **+0,333** | 0,667 | **1,000** | **+0,333** |

O vetorial não substitui o BM25: perde precisão no topo agregado, mas aumenta cobertura no top 10, melhora o split de teste e duplica o Recall@5 do caso pt-BR. Essa complementaridade é a hipótese mensurável da próxima fase, que combinará os dois rankings em vez de escolher um vencedor artificial.

Veja a [comparação vetorial](evals/results/dense-v0.1.md) ou o [resultado completo em JSON](evals/results/dense-v0.1.json).

## Resultado do retrieval híbrido

O RRF combina posições, não scores incompatíveis. Uma grade pequena de 20 configurações foi avaliada somente nos 12 casos respondíveis de `dev`, usando nDCG@10 como objetivo primário. A configuração selecionada foi a forma simétrica padrão: constante 60 e pesos 1:1.

| Grupo | Retriever | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|---:|
| Todos | BM25 | 0,819 | 0,892 | 0,696 | 0,718 |
| Todos | Vetorial | 0,784 | 0,946 | 0,688 | 0,710 |
| Todos | **Hybrid RRF** | **0,873** | 0,941 | **0,794** | **0,809** |
| Test | BM25 | 0,683 | 0,867 | 0,733 | 0,742 |
| Test | Vetorial | 0,700 | **0,950** | 0,733 | 0,735 |
| Test | **Hybrid RRF** | **0,800** | 0,933 | 0,733 | **0,775** |

O híbrido aumentou Recall@5 de teste em 0,117 contra BM25 e em 0,100 contra dense retrieval. Ele também obteve o melhor nDCG@10 e MRR@10 agregado. Dense retrieval isolado ainda preserva o maior Recall@10, portanto os três resultados permanecem publicados em vez de esconder o trade-off.

Veja o [relatório híbrido](evals/results/hybrid-v0.1.md) ou o [artefato auditável em JSON](evals/results/hybrid-v0.1.json).

## Resultado do reranker

O experimento reordenou o top 10 do Hybrid RRF com o cross-encoder multilíngue [`mmarco-mMiniLMv2-L12-H384-v1`](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1), fixado por revisão. Antes da execução foram definidos três gates: ganho mínimo de 0,010 em nDCG@10 de `dev`, nenhuma regressão em nDCG@10 de `test` e p95 de até 15 segundos por consulta em CPU.

| Grupo | Sistema | Recall@5 | MRR@10 | nDCG@10 |
|---|---|---:|---:|---:|
| Todos | **Hybrid RRF** | **0,873** | **0,794** | **0,809** |
| Todos | Reranker | 0,779 | 0,745 | 0,741 |
| Dev | **Hybrid RRF** | **0,903** | **0,819** | **0,823** |
| Dev | Reranker | 0,819 | 0,736 | 0,739 |
| Test | **Hybrid RRF** | **0,800** | 0,733 | **0,775** |
| Test | Reranker | 0,683 | **0,767** | 0,746 |

O p95 do artefato final foi 13,99 segundos e passou no orçamento, mas nDCG@10 caiu 0,083 em `dev` e 0,029 em `test`. O ganho isolado de MRR@10 em `test` não compensa a regressão ampla. A decisão foi manter o Hybrid RRF e publicar o resultado negativo, evitando custo e complexidade sem ganho comprovado.

Veja o [relatório do reranker](evals/results/reranker-v0.1.md), o [benchmark em CPU](evals/results/reranker-benchmark-v0.1.md) ou os artefatos JSON correspondentes.

## Por que avaliação primeiro

Uma demonstração de RAG pode produzir uma resposta convincente mesmo recuperando documentos errados. Este projeto separa quatro perguntas:

1. O documento correto apareceu no top-k?
2. A resposta está apoiada no corpus recuperado?
3. A arquitetura nova superou um baseline mais simples?
4. A melhora justificou o custo e a latência adicionados?

## Corpus

O corpus combina documentação autoritativa do repositório e páginas explicativas da wiki:

- arquitetura e estado *as-built*;
- ADRs de inventory, allocation, slotting, GTP e conveyance;
- contratos OpenAPI;
- serviços e integrações;
- segurança e horizontal scaling;
- fluxos inbound, outbound, host integration e equipment integration.

As revisões fixas e a allowlist vivem em [`corpus/sources.yaml`](corpus/sources.yaml). Os arquivos baixados ficam em `.data/`, ignorado pelo Git. O projeto publica apenas o manifesto de proveniência e o golden set próprio.

## Executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,vector]"
wcs-fetch-corpus
wcs-validate-evals
wcs-build-index
wcs-eval-bm25
docker compose up -d --wait
$env:WCS_DATABASE_URL = "postgresql://wcs:wcs_local_only@localhost:55432/wcs_rag"
wcs-build-vector-index
wcs-eval-vector
wcs-eval-hybrid
wcs-eval-reranker
pytest
```

## Roadmap técnico

| Fase | Entrega | Gate |
|---|---|---|
| 0 | Corpus fixo, golden set e contratos | dataset íntegro e reproduzível |
| 1 | Baseline lexical BM25 | concluída: métricas de retrieval publicadas |
| 2 | Embeddings e pgvector | concluída: ganhos de cobertura e gap pt-BR medidos |
| 3 | Retrieval híbrido e rank fusion | concluída: ganho de Recall@5 e nDCG em dev e test |
| 4 | Reranker | concluída: latência aprovada, qualidade reprovada; Hybrid RRF mantido |
| 5 | Geração com citações | faithfulness e citation correctness medidas |
| 6 | LLM-as-judge calibrado | concordância comparada com rótulo humano |
| 7 | Regression gate e observabilidade | CI falha em regressão deliberada |

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Estratégia de avaliação](docs/EVALS.md)
- [Política do corpus](corpus/README.md)

## Processo de desenvolvimento

O projeto foi concebido, especificado e validado por Raphael Caveagna com assistência de ferramentas de IA na implementação e revisão. As decisões de arquitetura, critérios de avaliação, seleção de trade-offs e aceite dos resultados permanecem sob responsabilidade do autor. Resultados publicados serão reproduzíveis pelos comandos deste repositório.

## Licença

O código deste repositório usa licença MIT. O openWCS é uma fonte externa sob AGPL-3.0; sua documentação não é relicenciada nem republicada aqui. Consulte o manifesto e a licença original antes de reutilizar o corpus.
