# Política do corpus

## Escopo

O corpus cobre decisões e operações de um Warehouse Control System: fronteiras WMS/WCS/equipamento, movimentação física, inventory, allocation, cubing, slotting, replenishment, GTP, integração de host, segurança e scaling.

Conteúdo de marketing, instruções para agentes do projeto-fonte, imagens, deployment e integrações proprietárias ficam fora da primeira versão.

## Proveniência

Cada fonte possui:

- URL pública;
- commit completo e imutável;
- licença declarada;
- nível de autoridade;
- allowlist e denylist de caminhos.

O coletor produz `.data/corpus-manifest.json` com caminho, origem, commit, tamanho e SHA-256 de cada documento. Esse arquivo é derivado e pode ser recriado.

## Hierarquia de evidência

Quando documentos divergem, a resposta deve preservar a divergência e seguir esta ordem:

1. `docs/AS-BUILT.md` para o que está implementado na revisão fixada;
2. `docs/DEVELOPMENT-STATUS.md` para estado recente declarado;
3. ADR aceito para decisão arquitetural;
4. ADR proposto para intenção ainda não necessariamente entregue;
5. wiki para explicação e navegação;
6. README para visão agregada.

O sistema não deve combinar um ADR proposto com um documento as-built e apresentar a proposta como entregue sem qualificar a evidência.

## Licença

O openWCS declara AGPL-3.0. Para reduzir redistribuição desnecessária:

- o corpus bruto fica fora do Git;
- o script baixa a revisão diretamente da origem;
- pequenos trechos não são copiados para o golden set;
- respostas de referência são paráfrases produzidas para avaliação;
- toda saída mantém source IDs e caminhos de origem.

## Atualização

Atualizar o corpus é uma mudança de dataset, não manutenção automática. Exige:

1. alterar a revisão no manifesto;
2. reconstruir e comparar hashes;
3. revisar documentos adicionados, removidos ou modificados;
4. revalidar o golden set;
5. publicar métricas antes e depois.

