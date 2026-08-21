# WCS RAG Evals

Sistema de RAG orientado a avaliação sobre documentação pública de Warehouse Control Systems. O projeto será construído a partir de baselines mensuráveis: antes de adicionar embeddings, busca híbrida ou reranking, cada mudança precisa provar que melhorou retrieval, resposta ou custo contra um golden set versionado.

O domínio escolhido é logística e automação de armazéns. O corpus inicial usa a documentação pública do [openWCS](https://github.com/brettljausn-ai/openwcs), fixada por commit e baixada por script. Nenhum dado, documento ou nome de cliente da experiência profissional do autor faz parte do projeto.

## Estado atual

**Fase 2, retrieval vetorial comparado.** O projeto já contém:

- manifesto reproduzível de fontes e revisões;
- ingestão allowlist, sem republicar o corpus de terceiro;
- hashes SHA-256 de cada documento coletado;
- golden set inicial com respostas, fatos obrigatórios e claims proibidos;
- validação tipada dos contratos de fonte e avaliação;
- chunking determinístico e sensível a headings para Markdown e OpenAPI;
- implementação própria de BM25 com ranking por documento;
- embeddings multilíngues persistidos em PostgreSQL com pgvector;
- índice HNSW disponível para escala e busca exata usada no corpus atual;
- Recall@k, Precision@k, MRR@10 e nDCG@k calculados por caso e por split;
- comparação reproduzível entre retrieval lexical e vetorial.

Ainda não há retrieval híbrido, reranker, geração por LLM ou API. Esses componentes entram nas próximas fases e precisarão justificar sua complexidade sob os mesmos casos.

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
pytest
```

## Roadmap técnico

| Fase | Entrega | Gate |
|---|---|---|
| 0 | Corpus fixo, golden set e contratos | dataset íntegro e reproduzível |
| 1 | Baseline lexical BM25 | concluída: métricas de retrieval publicadas |
| 2 | Embeddings e pgvector | concluída: ganhos de cobertura e gap pt-BR medidos |
| 3 | Retrieval híbrido e rank fusion | ganho consistente em dev e test |
| 4 | Reranker | melhoria maior que custo e latência adicionais |
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
