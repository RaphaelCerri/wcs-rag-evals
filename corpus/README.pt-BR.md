# Política do corpus

> [English](README.md) · **Português**

## Escopo

O corpus cobre decisões e operações de Warehouse Control Systems: fronteiras WMS/WCS/equipamento,
movimentação física, inventory, allocation, cubing, slotting, replenishment, GTP, integração de
host, segurança e horizontal scaling.

Conteúdo de marketing, instruções para agentes do projeto-fonte, imagens, deployment e integrações
proprietárias ficam fora do corpus.

## Proveniência

Cada fonte registra URL pública, commit imutável, licença, nível de autoridade e allowlist ou
denylist de caminhos. O coletor deriva `.data/corpus-manifest.json` com origem, caminho, commit,
tamanho e SHA-256 de cada documento.

## Hierarquia de evidência

Quando fontes divergem, a resposta preserva a divergência e segue esta ordem:

1. `docs/AS-BUILT.md` para comportamento implementado na revisão fixada;
2. `docs/DEVELOPMENT-STATUS.md` para estado recente declarado;
3. ADR aceito para decisão arquitetural;
4. ADR proposto para intenção ainda não necessariamente entregue;
5. wiki para explicação e navegação;
6. README para visão agregada.

Uma proposta nunca deve ser apresentada como entrega sem qualificar a evidência.

## Licença e atualização

openWCS declara AGPL-3.0. O conteúdo bruto fica fora do Git, o coletor baixa diretamente da origem
fixada, respostas de referência são paráfrases próprias e saídas preservam source IDs.

Alterar a revisão fixada é uma mudança de dataset. Exige reconstruir hashes, revisar documentos,
revalidar o golden set e publicar métricas antes e depois.
