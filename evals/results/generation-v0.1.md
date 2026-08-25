# Extractive grounded baseline v0.1

Baseline local que extrai evidências com citações e recusa quando não há retrieval.
Os gates foram definidos antes da geração. Métricas semânticas dependentes de judge
ficam explicitamente fora desta fase.

## Comparação

| Grupo | Modo | Schema | Answerability | Citation hit | Fact coverage | Token F1 |
|---|---|---:|---:|---:|---:|---:|
| all | RAG | 1.000 | 1.000 | 1.000 | 0.328 | 0.233 |
| all | Sem retrieval | 1.000 | 0.056 | 0.000 | 0.000 | 0.052 |
| dev | RAG | 1.000 | 1.000 | 1.000 | 0.396 | 0.215 |
| dev | Sem retrieval | 1.000 | 0.000 | 0.000 | 0.000 | 0.056 |
| test | RAG | 1.000 | 1.000 | 1.000 | 0.167 | 0.269 |
| test | Sem retrieval | 1.000 | 0.167 | 0.000 | 0.000 | 0.042 |
| language:en | RAG | 1.000 | 1.000 | 1.000 | 0.349 | 0.242 |
| language:en | Sem retrieval | 1.000 | 0.059 | 0.000 | 0.000 | 0.055 |
| language:pt-BR | RAG | 1.000 | 1.000 | 1.000 | 0.000 | 0.081 |
| language:pt-BR | Sem retrieval | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Gates

- `schema_valid_rate`: observado 1.000; mínimo 1.000; **passou**
- `citation_validity_rate`: observado 1.000; mínimo 1.000; **passou**
- `refusal_accuracy`: observado 1.000; mínimo 1.000; **passou**
- `relevant_citation_hit_rate`: observado 1.000; mínimo 0.800; **passou**
- `dev_fact_coverage_delta`: observado 0.396; mínimo 0.100; **passou**

## Limite de interpretação

Citation hit mede sobreposição com documentos rotulados, não entailment por claim.
Fact coverage e suporte extrativo são proxies lexicais. Faithfulness semântica e
citation correctness por claim exigem o judge calibrado da próxima fase.

## Respostas

### wcs-dev-001

openWCS Wiki **openWCS** is an open-source **Warehouse Control System (WCS)**: it orchestrates automated material-handling equipment — conveyors, ASRS (shuttles & cranes), AMRs (e.g. **Model** (`flow` schema, V6/V10): `warehouse_level` (floors with elevation), `placed_equipment` (a placed master-data equipment instance — position/rotation/tilt + envelope `lengthM/widthM/heightM`, a conveyor `path` polyline + directed `sections`, `closed` flag, `category`, and a soft `station_id` linking a placed **GTP workstation** to its `gtp_station`), `equipment_function_point` (named points on a conveyor — scan/divert/induct/discharge/infeed — at an arc-length `offsetM`, with a `side`, an optional PLC `nodeCode` and, for diverts, openwcs [![CI](https://github.com/brettljausn-ai/openwcs/actions/workflows/ci.yml/badge.svg)](https://github.com/brettljausn-ai/openwcs/actions/workflows/ci.yml) [![Sponsor on Patreon](https://img.shields.io/badge/Patreon-sponsor-8DC63F?logo=patreon&logoColor=white)](https://www.patreon.com/c/karlfriesenbichler) An **open-source Warehouse Control System (WCS)** that orchestrates automated material-handling equipment — conveyors, ASRS (shuttles & cranes), AMRs (e.g.

Citações: `openwcs-wiki/Home.md`, `openwcs-repo/docs/AS-BUILT.md`, `openwcs-repo/README.md`

### wcs-dev-002

ADR 0001 — Inventory data ownership: batch/lot & serial units live in the inventory store > Decision **Batch/Lot and SerialUnit are owned by the inventory service** and live in its service-local `inventory` schema, next to the `stock` table — not in `master_data`. instance data:** - **Master (on the SKU):** merchandising/fashion attributes (`brand`, `style`, `season`, `color`, `size`, …), dangerous-goods classification, and the **tracking flags** (`is_batch_tracked`, `is_serial_tracked`, `is_date_tracked`) that declare *what must be captured* for that SKU. **GS1 barcode rules**), Location (+ cell coords + optional **`area_id`**), **`Area`** (first-class hierarchical zone, self-referential `parent_area_id`), **StorageBlock** (+ allowed HU types), HandlingUnitType, Equipment, **Shipper**, **ShippingService**, **Route**, **LabelTemplate** | | `transaction_log` | txlog | Append-only event log — system of record (scaffolded separately) | | `inventory` | inventory | Durable `stock` table (qty per SKU × batch × location × HU × status), `reservation`, and the **instance** data created at goods-in: `batch`/lot + `serial_unit`; `projection_offset` replay cursor |

Citações: `openwcs-repo/docs/adr/0001-inventory-data-ownership.md`, `openwcs-repo/build.md`, `openwcs-repo/README.md`

### wcs-dev-003

With **allow-short mode** (`allowShort: true`) a short order instead keeps what it could reserve, cubes only the allocated quantities, and returns `FULFILLABLE_SHORT`; the order is then raised to `PARTIALLY_ALLOCATED`. For each line the allocator: - resolves candidate **PICK** locations (`location.purpose = PICK`) for the warehouse; - checks **location-scoped** available-to-promise from inventory and reserves against specific pick locations until the line qty is met; - if every line is fully reserved → order **`ALLOCATED`** with a pick plan + cube plan; - otherwise it **releases any partial reservations** and reports **`NOT_FULFILLABLE`**; order-management sets that status and the order **waits for instructions** (retry / cancel / manual allocation) via UI or API. master-data / inventory / allocation / txlog — an `RbacFilter` mapping method+path to a permission (master-data: VIEW/EDIT; inventory: INVENTORY_VIEW + ALLOCATION_RUN for reservations; allocation: ALLOCATION_RUN / BATCH_BUILD / ORDER_VIEW; txlog: TXLOG_VIEW on reads — append is left internal, see below).

Citações: `openwcs-wiki/Outbound-Flow.md`, `openwcs-repo/docs/adr/0002-outbound-allocation-and-cubing.md`, `openwcs-repo/docs/AS-BUILT.md`

### wcs-dev-004

ADR 0002 — Outbound allocation & cubing architecture > Decisions instructions; it does not change the reserved quantity. With **allow-short mode** (`allowShort: true`) a short order instead keeps what it could reserve, cubes only the allocated quantities, and returns `FULFILLABLE_SHORT`; the order is then raised to `PARTIALLY_ALLOCATED`. master-data (catalog + outbound config) fill level, max weight, per warehouse) and **`WarehouseFulfillmentConfig`** (`/warehouses/{id}/fulfillment-config` — allowed pick types CASE/SPLIT_CASE/EACH, cubing mode APP/ONE_TO_ONE, default shipper, and batch config: `batchEnabled`, `batchMaxPieces`, `batchMaxOrders`, `pickToteShipperId`).

Citações: `openwcs-repo/docs/adr/0002-outbound-allocation-and-cubing.md`, `openwcs-wiki/Outbound-Flow.md`, `openwcs-repo/docs/AS-BUILT.md`

### wcs-dev-005

**One weighted scorer reconciles the conflicts.** A pure `PutawayScorer` applies the **hard constraints** (lane capacity, **max-%-of-SKU-per-aisle cap**) then ranks survivors by `wV·velocity + wC·laneAffinity + wR·redundancy + wB·balance`. The **put-away engine** chooses the actual location per handling unit at put-away time, reconciling four competing objectives with one weighted score (per-block weights in `block_policy`): - **Velocity-to-exit** — fast movers (class A) near the aisle port, slow movers (C) deep (`location.distance_to_exit`; when it is not maintained, slotting derives a rank-equivalent distance from the cell coordinate as (posX−1)+(posY−1)+(posZ−1), assuming the in/outfeed at position 1, ground level — the guided rack builder also stamps the value explicitly now). | | slotting | Java | 8093 | ✅ | Put-away assignment for automated rack/GTP blocks (weighted scorer: velocity-to-exit · same-SKU lane consolidation · aisle redundancy cap/floor · fill balance; exit distance = `location.distance_to_exit` when set, else derived from the cell coordinate (posX−1)+(posY−1)+(posZ−1) with the port assumed at position 1 ground level, and the guided rack builder stamps it on generation; soft single-SKU-per-lane (mixing penalty, outweighable by balance) + hard lane-capacity/max-aisle constraints; direct-to-pick), manual pick-face slotting + min/max replenishment (opportunistic off-peak top-off), off-peak re-slotting.

Citações: `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md`, `openwcs-wiki/Slotting-and-Replenishment.md`, `openwcs-repo/docs/DEVELOPMENT-STATUS.md`

### wcs-dev-006

**New `slotting` service** (port 8093, own `slotting` schema) owns put-away assignment, pick-face slotting config, replenishment, and re-slotting. Slotting & Replenishment > Observability received (STORED) | assignment id, HU id, confirmed storage location | **Replenishment:** | Event | Level | Key fields | |---|---|---| | Task created | INFO | pick-face location, SKU, on-hand, min/max, refill qty, trigger type, priority | | Dedup skip — open task exists for this face (below-min) | WARN | pick-face, SKU, on-hand, min threshold | | Dedup skip — open task exists for this face (top-off) | DEBUG | pick-face | **Re-slotting:** | Event | Level | Key fields | |---|---|---| | Move recommended | INFO | HU, SKU, from/to location, block, score gain vs shift threshold | | Per-run cap reached (200 recommendations) | WARN | block, cap limit, consequence (remaining | | slotting | Java | 8093 | ✅ | Put-away for automated rack/GTP blocks (weighted scorer: velocity-to-exit · same-SKU lane consolidation · aisle redundancy · fill balance), manual pick-face slotting + min/max replenishment (opportunistic top-off), off-peak re-slotting.

Citações: `openwcs-repo/docs/adr/0003-slotting-and-replenishment.md`, `openwcs-wiki/Slotting-and-Replenishment.md`, `openwcs-wiki/Services.md`

### wcs-dev-007

The layout is set in the GTP config screen (a "Picking layout" selector plus a "Pick slots" input shown for `ONE_TO_N`); put-wall cubbies and put-light ids continue to be configured per ORDER node as before. While a pick is active the screen is a **single bordered box** that fits the browser window (no page scroll), split into **three columns**: the **left (source) panel** shows the stock HU and SKU with the product image on the left and tote/SKU details to its right (row layout); the **middle** shows the **take quantity** (→ N →, the sum of the open puts for this present); the **right (target) panel** renders by the cycle's **pick layout**: - **ONE_TO_ONE** — the destination carton with a single focused quantity input. **Confirm** a put (by instruction id, optionally a short qty) → decrement remaining stock + destination

Citações: `openwcs-repo/docs/AS-BUILT.md`, `openwcs-wiki/Goods-to-Person-Stations.md`, `openwcs-repo/docs/adr/0006-gtp-station-execution.md`

### wcs-dev-008

| |---|---|---|---| | REST request path (all services) | — | stateless; state in Postgres | ✅ replicas/HPA | | Outbox relays — order-management, txlog | `@Scheduled` poller on every replica → **double-publish** events | **ShedLock** `@SchedulerLock` (one replica drains per tick); ordering preserved by single-writer + in-order send | ✅ | | Off-peak jobs — slotting velocity/replenishment/reslot, counting sweep, host webhook | fire on every replica → **duplicate tasks/webhooks** | **ShedLock** `@SchedulerLock` | ✅ | | Conveyor loop capacity — flow-orchestrator | count-then-enter race → **capacity exceeded** across replicas | **pessimistic row The check-and-enter step uses a **pessimistic row lock** (`lockByWarehouseIdAndCode`) so the occupancy count and the decision to enter are atomic across replicas — the capacity limit cannot be exceeded by a check-then-act race when flow-orchestrator runs scaled out. | |---|---|---| | REST request path (all services) | stateless; state in Postgres | ✅ replicas / HPA | | Outbox relays — order-management, txlog | **ShedLock** `@SchedulerLock` — one replica drains per tick | ✅ | | Off-peak jobs — slotting velocity/replenishment/reslot, counting sweep, host webhook | **ShedLock** `@SchedulerLock` | ✅ | | Conveyor loop capacity — flow-orchestrator | **pessimistic row lock** on the loop row makes count-and-enter atomic | ✅ | | Stock reservation — inventory / allocation | already serialized by a pessimistic lock on `AVAILABLE` stock rows | ✅ | | txlog→stock projection (inventory), velocity learner (slotting) | Kafka **consumer group** +

Citações: `openwcs-repo/docs/SCALING.md`, `openwcs-repo/docs/AS-BUILT.md`, `openwcs-wiki/Horizontal-Scaling.md`

### wcs-dev-009

**Nothing calls it.** The equipment-emulator simulates a `CONVEY` as one atomic sleep (~1 s), invents its own recirculation (`recircEvery`), and reports "decisions" post-hoc in the result payload. Equipment Integration > Automation Topology (physical layout) sections**: while "Draw sections" mode is active, each grid-snapped click calls the same `drawSectionAt` callback the 3D editor uses — building the same `sections` array and path waypoints in the data model. Occupancy is the count of active routes whose last-scanned node is in that loop.

Citações: `openwcs-repo/docs/adr/0008-live-scan-driven-conveyance.md`, `openwcs-wiki/Equipment-Integration.md`, `openwcs-repo/docs/AS-BUILT.md`

### wcs-dev-010

A retrieve of an HU at `cellZ 2` is physically impossible while another HU occupies `cellZ 1` of the same channel (same `aisle+side+cellX+cellY`): the shuttle must first **relocate the blocker** — and because a shuttle serves one level and a lift move is expensive, the relocation target must share the blocker's **`cellY`** (one shuttle move, no lift), preferably in the same aisle. Slotting & Replenishment > Dig-out planning (multi-deep channels) For a multi-deep lane, a retrieve at cell Z *N* is physically blocked by any HU occupying a lower Z in the same channel (`aisle + side + posX + posY`). On the RELOCATE callback, flow books the blocker's new inventory location (`PUT /api/inventory/handling-units/{id}/location`), writes a **`RELOCATED`** HU-trace row (point `slot:<to>`, decision `"relocated out of channel for <target>"`) for the blocker, then re-plans: next blocker → next RELOCATE; channel clear → the original RETRIEVE goes out.

Citações: `openwcs-repo/docs/adr/0009-double-deep-channel-relocation.md`, `openwcs-wiki/Slotting-and-Replenishment.md`, `openwcs-repo/docs/AS-BUILT.md`

### wcs-dev-011

Application is **idempotent** — every applied event is recorded in a `processed_event` inbox keyed on `event_id` (§5.5), so redelivery/replay is a no-op and the read model can be rebuilt from the log. **HU location registry** (`PUT /api/inventory/handling-units/{id}/location`): records a handling unit's current storage location; bookings made by flow-orchestrator at each transport milestone (REQUESTED, IN_TRANSIT, ARRIVED, STORED, RELOCATED) so the registry stays live; consumed by ADR-0009 dig-out occupancy checks. A projection can be dropped and rebuilt by replaying the log — this is the recovery and audit story.

Citações: `openwcs-repo/README.md`, `openwcs-repo/docs/AS-BUILT.md`, `openwcs-repo/build.md`

### wcs-dev-012

The goal is to make an operator process a **configurable, versioned definition**: a non-developer builds a flow of handheld screens and tasks in a visual designer, assigns one version as **active** for a process type (e.g. **Import**: `POST /defs/import` creates a new **DRAFT** from a full definition JSON (an upload in the designer). Engine + storage for versioned operator process definitions: a process is a JSON flow of handheld screens + task steps, with **exactly one ACTIVE version per process key** (partial unique index; versions auto-increment).

Citações: `openwcs-repo/docs/process-designer-spec.md`, `openwcs-wiki/Process-Designer.md`, `openwcs-repo/docs/AS-BUILT.md`

### wcs-test-001

**Webhook (push)** (`/api/host/webhooks`): a host registers a callback URL; a scheduled dispatcher streams confirmations to it, advancing the subscription's cursor only past successfully-delivered (2xx) events — at-least-once, with a failing endpoint retried from its cursor on the next pass. | | integration-host | Java | 8092 | 🟡 | Canonical vendor-neutral **Host API** (`/api/host/**`): orders + ASNs + **SKU sync (upsert — SKUs absent from the batch are left untouched; within each synced SKU the host is authoritative and its nested UoMs/barcodes fully replace what is stored)** + inventory adjustments in; confirmations out via pull (cursor) integration-host — canonical openWCS Host API The single, vendor-neutral API a host system (WMS/ERP) integrates against.

Citações: `openwcs-repo/docs/AS-BUILT.md`, `openwcs-wiki/Services.md`, `openwcs-repo/services/integration-host/README.md`

### wcs-test-002

Security Policy > Security model & hardening notes openWCS is built defense-in-depth, but **the defaults in this repo are for local development and demos, not production**: - **Edge auth is the trust boundary.** With `OPENWCS_SECURITY_ENABLED=true`, the API gateway validates a Keycloak JWT on every `/api/**` call, forwards a trusted identity (`X-Auth-User` / `X-Auth-Roles` / `X-Auth-Warehouses`) downstream, and strips client-supplied copies. Off by default, all traffic is permitted so the stack runs without tokens. allocate against available-to-promise > Authentication (optional, off by default) Auth is built but disabled so the stack runs without setup.

Citações: `openwcs-repo/SECURITY.md`, `openwcs-wiki/Security.md`, `openwcs-repo/README.md`

### wcs-test-003

The callback-URL approach reuses the §3b primitive and is a smaller delta; a topic can replace the callback later without changing the workplace-side state machine. Today the emulator's `RETRIEVE` is a single simulated latency: no occupancy ADR 0008 — Live scan-driven conveyance: the adapter scans, the flow controller answers Status: Proposed (2026-06).

Citações: `openwcs-repo/docs/adr/0007-conveyor-transport-and-workplace-induction.md`, `openwcs-repo/docs/adr/0009-double-deep-channel-relocation.md`, `openwcs-repo/docs/adr/0008-live-scan-driven-conveyance.md`

### wcs-test-004

The corpus does not contain or authorize access to production credentials or customer-specific secrets.

Citações: nenhuma

### wcs-test-005

ADR 0001 — Inventory data ownership: batch/lot & serial units live in the inventory store > Decision **Batch/Lot and SerialUnit are owned by the inventory service** and live in its service-local `inventory` schema, next to the `stock` table — not in `master_data`. Services (Bounded Contexts) > 4.2 Inventory / Stock Service - **Responsibility:** Real-time stock within the automated area — quantity by SKU × **batch/lot** × location × handling-unit × status (available, allocated, **locked/unavailable**, blocked, in-transit). **GS1 barcode rules**), Location (+ cell coords + optional **`area_id`**), **`Area`** (first-class hierarchical zone, self-referential `parent_area_id`), **StorageBlock** (+ allowed HU types), HandlingUnitType, Equipment, **Shipper**, **ShippingService**, **Route**, **LabelTemplate** | | `transaction_log` | txlog | Append-only event log — system of record (scaffolded separately) | | `inventory` | inventory | Durable `stock` table (qty per SKU × batch × location × HU × status), `reservation`, and the **instance** data created at goods-in: `batch`/lot + `serial_unit`; `projection_offset` replay cursor |

Citações: `openwcs-repo/docs/adr/0001-inventory-data-ownership.md`, `openwcs-repo/build.md`, `openwcs-repo/README.md`

### wcs-test-006

``` ┌────────────────────┐ │ WMS / ERP / OMS │ business orders, inventory ownership └─────────┬──────────┘ │ (orders, ASNs, stock sync) ┌─────────▼──────────┐ │ openwcs │ ← THIS SYSTEM │ flow + storage + │ process execution, routing, equipment control │ equipment control │ └─────────┬──────────┘ │ (device protocols) ┌──────┬───────┼────────┬──────────┐ ▼ ▼ ▼ ▼ ▼ Conveyor ASRS AMR AutoStore Pick/Pack (PLC) (shuttle/ (Geek+) (grid) stations crane) ``` ``` WMS / ERP ──(canonical Host API)──► openWCS ──(device adapters)──► Conveyor · ASRS · AMR · AutoStore host orders / ASNs / master data orchestration, stock, physical movement ◄──(confirmations)── process execution ``` A WCS sits **between** the business-level WMS/ERP and the **physical equipment**: it executes and coordinates physical movement, manages real-time stock in the automated area, and lets admins design the processes (goods-in, outbound, cycle count) that run the building.

Citações: `openwcs-repo/build.md`, `openwcs-wiki/Home.md`, `openwcs-repo/README.md`
