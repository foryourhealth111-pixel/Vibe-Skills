# Governance Family Map

> Baseline snapshot: 2026-03-13  
> Purpose: compress human-facing entry without deleting machine-useful governance assets.

## Why This Exists

The repository has already accumulated a large governance surface:

- `config/`: 110 files
- `scripts/verify/`: 124 files

The current problem is no longer "governance is missing".
The current problem is "governance is hard to enter correctly".

This document is therefore an **entry compression map**, not a deletion order.

## Human Entry Order

When a maintainer or contributor needs to orient quickly, the default entry path should be:

1. `README.md`
2. `docs/README.md`
3. `docs/status/non-regression-proof-bundle.md`
4. `scripts/verify/gate-family-index.md`
5. `docs/operator-default-runbooks.md`
6. `docs/contributor-default-runbooks.md`

This order is also mirrored by the family index contract:

- `config/governance-family-index.json`

## Config Families

The current `config/` surface can already be coarsely grouped into four operator-facing families.
This is an inventory aid, not yet a physical directory refactor.

| Family | Approx Count | Meaning | Typical Assets |
| --- | ---: | --- | --- |
| `governance-and-runtime` | 39 | install, check, doctor, governance, lifecycle, runtime truth | `distribution-tiers.json`, `version-governance.json`, runtime policies |
| `routing-and-overlays` | 25 | routing thresholds, overlays, prompt/rerank/adaptive surfaces | `router-thresholds.json`, `skill-routing-rules.json`, overlay policies |
| `distribution-and-sources` | 11 | upstream, dependency, release, source retention | `dependency-map.json`, `upstream-lock.json`, source manifests |
| `other` | 35 | remaining specialized or legacy assets pending finer family convergence | mixed historical and specialized configs |

## Verify Families

The current `scripts/verify/` entry already has a better family model than `config/`.
The baseline family list comes from [`scripts/verify/gate-family-index.md`](../scripts/verify/gate-family-index.md).

| Family | Role |
| --- | --- |
| Runtime Integrity / Packaging | packaging, install, freshness, frontmatter, runtime coherence |
| Managed Runtime / Process Hygiene | node/process ownership and safe cleanup classification |
| Cleanliness / Outputs / Mirror Hygiene | repo cleanliness, output boundaries, mirror drift rejection |
| Plane Governance | browserops, desktopops, docling, connectors |
| Capability / Role / Upstream Value Ops | capability closure, role packs, provenance, upstream disclosure |
| Release / Promotion / Observability | promotion, release evidence, ops cockpit |
| Operator Preview / Apply Safety | manual apply and preview safety boundaries |
| Execution-Context / Wave Runner | wave runner, family convergence, execution context lock |

## Family-Level Rules

The convergence direction is:

- keep detailed assets machine-readable
- add family-level ownership and operator paths
- reduce the number of places a human must inspect first

The convergence direction is **not**:

- blind deletion of gates
- mass policy merging without proof
- hiding degraded states to simplify messaging

## Immediate Next Assets

The next stable family entry assets should be:

- `config/governance-family-index.json`
- `docs/operator-default-runbooks.md`
- `docs/contributor-default-runbooks.md`
- `scripts/verify/vibe-governance-entry-compression-gate.ps1`

These should make it possible for a contributor to answer:

- where do I start
- which gates are mandatory
- which areas are frozen
- which areas are safe to extend

without scanning the full repo surface first.

## Task 5 Mapping (Plan To Repo Layout)

The execution plan originally referenced a `docs/governance/*` subtree. The current repo already has a canonical verify-family index and operator entry surfaces.

To avoid inventing a second structure, Task 5 assets map as follows:

- planned `docs/governance/operator-runbook.md` -> actual `docs/operator-default-runbooks.md`
- planned `docs/governance/contributor-runbook.md` -> actual `docs/contributor-default-runbooks.md`
- planned `docs/governance/gate-family-index.md` -> actual `scripts/verify/gate-family-index.md`
- planned `docs/governance/config-family-index.md` -> actual `config/governance-family-index.json`
- planned `scripts/verify/vibe-governance-entry-compression-gate.ps1` -> actual `scripts/verify/vibe-governance-entry-compression-gate.ps1`

This slice is intentionally documentation-first: it compresses entry without deleting gates.
