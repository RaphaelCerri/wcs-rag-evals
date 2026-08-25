# Corpus policy

> **English** · [Português](README.pt-BR.md)

## Scope

The corpus covers Warehouse Control System decisions and operations: WMS/WCS/equipment boundaries,
physical movement, inventory, allocation, cubing, slotting, replenishment, GTP, host integration,
security, and horizontal scaling.

Marketing content, source-project agent instructions, images, deployment material, and proprietary
integrations are excluded.

## Provenance

Every source records its public URL, immutable commit, declared license, authority level, and path
allowlist or denylist. The collector derives `.data/corpus-manifest.json` with origin, path, commit,
size, and SHA-256 for each document.

## Evidence hierarchy

When sources disagree, the answer preserves the disagreement and uses this order:

1. `docs/AS-BUILT.md` for implemented behavior at the pinned revision;
2. `docs/DEVELOPMENT-STATUS.md` for recently declared status;
3. accepted ADR for an architectural decision;
4. proposed ADR for intent not necessarily delivered;
5. wiki for explanation and navigation;
6. README for an aggregate overview.

A proposal must never be presented as delivered behavior without qualifying the evidence.

## License and updates

openWCS declares AGPL-3.0. Raw content stays outside Git, the fetcher downloads directly from the
pinned origin, reference answers are original paraphrases, and outputs retain source IDs.

Changing the pinned revision is a dataset change. It requires rebuilding hashes, reviewing changed
documents, revalidating the golden set, and publishing before-and-after metrics.
