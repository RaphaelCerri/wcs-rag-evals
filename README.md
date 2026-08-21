# WCS RAG Evals

Sistema de RAG orientado a avaliação sobre documentação pública de Warehouse Control Systems. O projeto será construído a partir de baselines mensuráveis: antes de adicionar embeddings, busca híbrida ou reranking, cada mudança precisa provar que melhorou retrieval, resposta ou custo contra um golden set versionado.

O domínio escolhido é logística e automação de armazéns. O corpus inicial usa a documentação pública do [openWCS](https://github.com/brettljausn-ai/openwcs), fixada por commit e baixada por script. Nenhum dado, documento ou nome de cliente da experiência profissional do autor faz parte do projeto.

## Estado atual

**Fase 0, fundação de avaliação.** Esta entrega contém:

- manifesto reproduzível de fontes e revisões;
- ingestão allowlist, sem republicar o corpus de terceiro;
- hashes SHA-256 de cada documento coletado;
- golden set inicial com respostas, fatos obrigatórios e claims proibidos;
- validação tipada dos contratos de fonte e avaliação;
- testes de integridade e rastreabilidade.

Ainda não há banco vetorial, embeddings, geração por LLM ou API. Esses componentes entram somente depois de existir um baseline lexical medido.

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
python -m pip install -e ".[dev]"
wcs-fetch-corpus
wcs-validate-evals
pytest
```

## Roadmap técnico

| Fase | Entrega | Gate |
|---|---|---|
| 0 | Corpus fixo, golden set e contratos | dataset íntegro e reproduzível |
| 1 | Baseline lexical BM25 | métricas de retrieval publicadas |
| 2 | Embeddings e pgvector | superar baseline dentro do orçamento |
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

