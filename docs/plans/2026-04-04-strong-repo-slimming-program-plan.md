# 2026-04-04 Strong Repo Slimming Program Plan

## Goal

Produce a strong but safe slimming roadmap for the latest `main` checkout, reducing stale and low-signal repository surfaces while preserving behavior and clarifying ownership boundaries.

## Requirement Doc

- [`../requirements/2026-04-04-strong-repo-slimming-program.md`](../requirements/2026-04-04-strong-repo-slimming-program.md)

## Internal Grade

XL wave-sequential planning and later execution.

The repo has enough breadth and coupling that implementation should happen in reviewable waves, with bounded parallel audit work only where write scopes do not overlap.

## Architectural Lens

Strong slimming in this repository must follow four owner rules:

1. semantic owners live in package-owned cores or config-owned contracts
2. compatibility shims stay thin and must not keep second truth surfaces alive
3. active navigation surfaces stay short and current
4. reproducible snapshots and historical packets need explicit retention policy, not indefinite default retention

## Current Priority Snapshot

The latest repository state changes the priority order from the original broad cleanup framing.

The strongest remaining slimming pressure is concentrated in:

1. `bundled/skills/**`
   - `2120` files and about `30M`
   - largest structural hotspot in the repo
2. `scripts/verify/**`
   - `205` files
   - active but highly fragmented gate surface
3. `docs/**`
   - `593` files even after the first archive pass
   - root and live knowledge surfaces still need a second-pass consolidation
4. `references/**`
   - smaller than before, but still carries active proof, fixture, and historical bundle pressure

By contrast, these are not first-order slimming targets:

- `dist/**`: only `17` files and explicitly contract-linked generated projections
- `vendor/**`: only `3` files
- `benchmarks/**`: only `9` files
- `third_party/**`: only `7` files and compliance-sensitive

Those smaller trees should be treated as monitor-only unless a specific contract simplification proves worthwhile.

## Architecture Layers And Live Status

| Layer | Current Paths | Live Status | Slimming Rule |
| --- | --- | --- | --- |
| semantic authority | `packages/**`, `core/**`, `config/**` | must stay live | refactor only, no repo-slimming deletion objective |
| execution and routing | `apps/vgo-cli/**`, `scripts/runtime/**`, `scripts/router/**`, install wrappers | must stay live | slim only after owner-to-consumer proof |
| host compatibility | `adapters/**` | must stay live | keep projections honest, avoid churn for size only |
| generated release projection | `dist/**`, `distributions/**` | must stay live | regenerate or narrow only if contracts are updated |
| verification contract | `scripts/verify/**`, `tests/**` | must stay live | reduce by family convergence, not by blind deletion |
| bundled product payload | `bundled/skills/**` | live but overgrown | partition, deduplicate, alias-normalize |
| maintainer knowledge | `docs/**`, `references/**`, `protocols/**`, `templates/**` | mixed live/archive | strongest archive and dedup target |
| compliance/sample edges | `third_party/**`, `vendor/**`, `benchmarks/**` | keep minimal | very low value for current slimming waves |

## Core Design Rules

The program must preserve high cohesion and low coupling through explicit path roles.

### Path Role Taxonomy

Every candidate path must be classified into exactly one primary role:

| Role | Meaning | Allowed Operations | Forbidden Operations |
| --- | --- | --- | --- |
| canonical source | semantic owner of behavior or contract | refactor, split by module, add tests | replace with generated projection, duplicate semantics elsewhere |
| generated projection | generated or compatibility-facing derivative | regenerate, move, re-materialize, slim duplicates | let it become the only truth surface |
| compatibility shim | thin bridge to protect callers during migration | narrow, delegate, delete after callers are gone | keep inline semantic ownership |
| fixture / proof | evidence or regression baseline | retain only what tests or contracts consume | keep bulky historical payload without retention policy |
| archive | historical but still recoverable material | move behind archive index, compress, de-emphasize | crowd active navigation surfaces |
| dead surface | no active consumers and no retention value | delete | keep “just in case” without an owner |

### Cohesion Rules

- One semantic owner per concern.
- Policy lives in `config/**`, semantic code lives in `packages/**` or `core/**`, execution wrappers stay thin.
- Active docs should explain current behavior, not carry historical execution transcripts.
- Fixtures and proof bundles must exist only when they back a real test, contract, or release requirement.

### Coupling Reduction Rules

- Delete or archive consumers only after reference scans prove no active callers.
- Prefer manifest-driven allowlists over broad directory scanning.
- Prefer family-level overview docs plus archive indexes over many parallel leaf pages at the root.
- Do not allow release, runtime, or install behavior to depend on historical docs remaining in active locations.

## Repository Classification

### Tier A: Immediate High-Value Slimming Candidates

These surfaces are the best first cuts because they are still bulky, noisy, or structurally duplicated after the first archive wave.

- root live docs outside the archive spine
  - Problem: the first archive cut reduced `docs/plans/**`, `docs/requirements/**`, and `docs/releases/**`, but the repo still carries many root or family docs that overlap in governance, rollout, or historical explanation.
  - Strategy: identify current navigators versus historical leaves; merge or archive leaves that duplicate a stronger family doc.
- `references/proof-bundles/**`
  - Problem: proof bundles are now one of the densest remaining historical surfaces.
  - Strategy: keep manifests, README, and active candidate bundles live; archive raw logs and old bundle detail behind a retention contract.
- `references/fixtures/**`
  - Problem: fixtures are canonical only when tests or boundary policies consume them; otherwise they become long-lived tracked outputs in disguise.
  - Strategy: separate test-backed fixture roots from obsolete or over-wide regression samples.
- `scripts/verify/**`
  - Problem: `205` verification scripts create review noise and suggest overlapping gate families.
  - Strategy: map gate families, centralize family metadata, and retire dead or superseded wrappers only after caller proof.
- large bundled payload duplication
  - Problem: the biggest structural duplication now sits in the bundled corpus, especially document tooling and alias-like skill families.
  - Strategy: deduplicate shared assets, normalize skill aliases, and move heavyweight references to better retention tiers.

### Tier B: Archive-First or Shrink-by-Policy Surfaces

- `docs/changes/**` and historical migration or rollout reports under `docs/*.md`
  - Consolidate by family or move behind archive indexes.
- legacy standalone governance or integration notes that duplicate newer family docs
  - Merge into a family overview or replace with a short redirect note.
- large single-skill references under `bundled/skills/**`
  - Example class: oversized `references/*.md`, example payloads, generated JSON, or PDF showcase files that do not need to remain in the primary shipped repo forever.
  - Strategy: classify into required-at-runtime, required-for-authoring, and archive-or-downloadable.

### Tier C: Contract-First Refactor Before Slimming

- `scripts/governance/**`, `scripts/runtime/**`, `scripts/router/**`
  - Problem: some ownership duplication remains, but these are live execution surfaces.
  - Strategy: continue owner-to-consumer cutovers first; delete only dead wrappers after proof.
- `third_party/system-prompts-mirror` and `third_party/vco-ecosystem-mirror`
  - Problem: still treated as local default evidence roots.
  - Strategy: parameterize roots via config and scripts before any shrinkage.
- `bundled/skills/**`
  - Problem: largest payload, but still installer and packaging input.
  - Strategy: introduce release-tier payload partitions, shared-asset ownership, and alias policy before attempting any broad removal.

### Tier D: Protected Surfaces

These should not be part of a strong deletion wave until deeper cutovers happen first.

- `dist/**`
- `packages/**`
- `core/**`
- `adapters/**`
- `tests/runtime_neutral/**`
- `tests/integration/**`
- `config/outputs-boundary-policy.json` and its dependent migration fixtures
- `vendor/**`, `benchmarks/**`, and `third_party/**` as current low-yield surfaces unless a specific contract proves otherwise

## Candidate Retention Policy

### Keep Live

- any path consumed by installer, runtime, release, adapter, verification, or catalog contracts
- active status / proof / release navigation spines
- package-owned semantic code and config-owned policy

### Archive Behind Index

- dated plans, dated requirement packets, old release notes, migration reports, postmortems, review reports
- proof logs and bulky receipts that are still useful historically but not needed on the active surface

### Generate On Demand

- large third-party snapshots
- bulky compatibility projections that can be reconstructed from config and manifests
- any raw evidence artifact whose manifest and summary are sufficient for repository truth

### Delete

- dead scripts with zero active references
- duplicate docs replaced by a canonical family overview
- obsolete fixtures or proof artifacts with no test, config, doc, or adapter consumer

## Explicit Risk Map

### Low Risk

- archive or relocate dated docs with no active README or test dependencies
- remove absolute local path leakage from historical docs
- split oversized historical ledgers into current plus archive volumes
- delete dead helper scripts with zero active consumers

### Medium Risk

- reorganize release-history and proof-bundle layout
- trim fixtures whose callers are ambiguous
- merge overlapping governance docs into family overviews

### High Risk

- bundled skill payload reduction
- verify gate consolidation without contract extraction
- third-party mirror removal before parameterization
- anything that changes installer packaging defaults or runtime freshness contracts

## Wave Structure

### Wave 0: Inventory Freeze and Guardrails

- generate a path-classification matrix for `docs`, `references`, `scripts`, `bundled`, and `third_party`
- mark every candidate path as `live`, `archive-first`, `generated`, `fixture`, or `dead`
- add a pruning policy note so future cleanup does not recreate ambiguity

Ownership boundaries:

- writes limited to planning docs, census docs, and maybe a new retention-policy doc
- no runtime, installer, or release logic changes

Deliverables:

- path-role matrix
- keep / archive / generate / delete candidate ledger
- batch backlog with risk labels

Verification:

- `rg -n "/home/lqf/table|Plan complete and saved to|Two execution options:" docs/plans docs/requirements docs/releases -g '*.md'`
- `rg -n "bundled/skills|references/proof-bundles|references/changelog.md|docs/plans/|docs/requirements/" README.md docs scripts packages tests config adapters core dist .github -g '!node_modules/**'`

### Wave 1: Live Docs Second-Pass Reduction

- audit live `docs/**` after the first archive cut
- merge or archive root-level governance, rollout, and migration notes that duplicate stronger family pages
- shorten live navigators so each family has one current entry page and archive pointers
- remove remaining absolute local path leakage or process transcript residue from live docs

Ownership boundaries:

- selected live `docs/*.md`
- `docs/status/**`
- `docs/install/**`
- `docs/external-tooling/**`
- `docs/README.md` and family README pages

Batch decomposition:

1. live root-doc census
2. family-doc merge and archive cut
3. README/index cleanup
4. path-leakage cleanup for surviving live pages

Expected outcome:

- live docs surface becomes shorter and more legible without reopening already archived families

Verification:

- `git diff --check -- docs`
- `rg -n "/home/lqf/table" docs -g '*.md'`
- targeted README and index spot checks

### Wave 2: References Retention Reform

- classify each `references/**` family as `contract-backed`, `fixture-backed`, `active-proof`, `historical-proof`, or `dead`
- shrink proof bundles to minimum tracked surfaces
- archive raw logs and low-signal receipts
- keep fixtures only where tests or policy explicitly consume them

Ownership boundaries:

- `references/proof-bundles/**`
- `references/fixtures/**`
- `references/promotion-memos/**`
- `references/candidate-case-files/**`
- `references/archive/**`

Batch decomposition:

1. proof-bundle minimum tracked schema
2. fixture consumer matrix
3. memo/case-file retention review
4. archive relocation for historical detail

Verification:

- `tests/runtime_neutral/test_outputs_boundary_migration.py`
- proof-bundle manifest consumer checks
- exact-path reference audit for relocated reference families

### Wave 3: Verify Surface Family Convergence

- create a machine-readable family map for `scripts/verify/**`
- separate active release/install/runtime/catalog gates from historical wave or pilot gates
- retire dead wrappers and merge family-local helpers only after contract evidence is explicit
- keep path-stable shims where tests or release policies still require them

Ownership boundaries:

- `scripts/verify/**`
- `config/governance-family-index.json`
- `scripts/verify/gate-family-index.md`
- directly coupled tests, config policies, and release docs

Batch decomposition:

1. gate family census
2. dead/superseded gate candidate list
3. family helper extraction
4. wrapper retirement or re-homing

Verification:

- targeted release, runtime, and install bridge tests
- exact-path scans for deleted gate files
- `git diff --check`

### Wave 4: Bundled Shared-Asset Deduplication

- deduplicate triplicated OOXML schema payloads across document-related skills
- centralize shared authoring assets used by multiple document skills
- keep path compatibility via generated copies, thin redirects, or manifest-driven materialization if direct path stability is needed

Ownership boundaries:

- `bundled/skills/docx/**`
- `bundled/skills/document-skills/**`
- packaging and consumer manifests
- any tests or docs that reference those assets directly

Batch decomposition:

1. duplicate-asset fingerprint inventory
2. shared-asset owner introduction
3. path compatibility decision
4. payload shrink and parity verification

Verification:

- packaging and skill-surface tests
- document-skill smoke checks
- exact-path scans for moved shared assets

### Wave 5: Bundled Skill Alias And Payload Tiering

- resolve alias-like duplicate skill families such as:
  - `pymc` vs `pymc-bayesian-modeling`
  - `torch-geometric` vs `torch_geometric`
- define `core`, `profile-required`, `authoring-only`, and `optional` skill tiers
- move heavyweight references, examples, and assets out of the default shipped surface where runtime does not need them

Ownership boundaries:

- `config/runtime-core-packaging*.json`
- `config/skills-lock.json`
- any future alias map or skill-tier manifest
- installer and catalog consumers
- `bundled/skills/**`
- tests that freeze packaging semantics

Batch decomposition:

1. alias census and canonical-name policy
2. tier manifest introduction
3. packaging migration to tier-aware allowlists
4. optional payload reduction
5. heavyweight reference retention reform

### Wave 6: Third-Party Root Decoupling

- parameterize mirror roots now treated as fixed local evidence sources
- move research helpers away from hardcoded mirror assumptions
- document supported external checkout or fetch-time behavior

Ownership boundaries:

- `third_party/**`
- `scripts/research/**`
- `config/upstream-corpus-manifest.json`
- docs or examples that hardcode mirror paths

### Wave 7: Final Consistency and Residual-Risk Closure

- refresh path dependency census
- refresh docs information architecture and retention policy docs
- rerun cross-surface regression
- document what remains intentionally retained and why

Verification:

- installer-core packaging tests
- catalog consumption tests
- offline or freshness-related skill lock tests

## Candidate Actions by Path Family

### `docs/plans/**`

- keep only active root and microphase plans live
- archive dated execution transcripts, closure reports, and completed technical-debt plans
- remove local absolute path leakage and “Plan complete and saved to ...” boilerplate from any page that stays live

### `docs/requirements/**`

- keep only active or recently relevant requirement packets live
- archive closed release, README, rename, and one-off delivery requirements
- keep filename stability inside archive so history remains traceable

### `docs/releases/**`

- keep current version and recent governed release window live
- archive older notes and historical packetization artifacts
- preserve `docs/releases/README.md` as the active release navigator

### `references/**`

- split current ledgers from deep history
- retain only test-backed fixtures and contract-backed proof manifests in the main repo surface
- reduce oversized snapshots to reproducible or summarized forms

### `scripts/**`

- delete only when exact-path and basename scans prove no live consumers
- for active script families, reduce by extracting shared logic first and deleting wrappers second
- prioritize `scripts/verify/**` family convergence over tiny script directories, because that is where the real review and maintenance cost sits

### `bundled/skills/**`

- do not delete by topical instinct alone
- first classify by installer/runtime requirement tier
- separate shared assets from skill-local semantics
- normalize alias and duplicate-family ownership before removing payload
- only optional or archive-tier payloads are eligible for later repository shrinkage

### `dist/**`, `vendor/**`, `benchmarks/**`, `third_party/**`

- treat as low-yield monitor surfaces in the near term
- avoid spending early slimming budget here unless a specific contract simplification or compliance fix justifies it
- do not use tiny-directory deletion as a substitute for harder bundled or verify-surface work

### Delete

- dead helper scripts with zero live references
- obsolete historical reports once their content is archived or absorbed
- stale duplicate docs that are neither active navigation nor referenced governance

### Archive

- most dated items in `docs/plans/**`
- most dated items in `docs/requirements/**`
- old release notes beyond the active governed release window
- bulky historical proof logs and migration report packets

### Merge

- overlapping governance family docs under the same theme
- release or migration reports that only repeat an already canonical governance note
- duplicate install or rollout guidance that differs only by historical context

### Keep

- package-owned semantic cores
- distribution manifests and adapter projections
- active proof and status spine
- outputs boundary contracts and fixtures
- active verification bridges and installer/runtime contract tests

## Verification Commands for Future Execution Batches

Minimum batch-level verification:

- `git diff --check`
- `pytest -q tests/integration/test_dist_manifest_generation.py tests/integration/test_release_cut_gate_contract_cutover.py tests/runtime_neutral/test_release_cut_operator.py`
- `pytest -q tests/runtime_neutral/test_outputs_boundary_migration.py tests/integration/test_catalog_contract_consumption.py tests/integration/test_runtime_core_packaging_roles.py`
- targeted `rg` scans proving removed paths have no live consumers

Extended verification by wave:

- doc-heavy waves: README and link scans, plus release and index contract checks
- script-heavy waves: targeted runtime, release, and installer bridge tests
- payload-heavy waves: packaging, catalog, offline skill, and freshness tests

Reference-audit probes that should be reused:

- `rg -n "/home/lqf/table|Plan complete and saved to|Two execution options:" docs -g '*.md'`
- `rg -n "references/changelog.md|references/proof-bundles|docs/plans/|docs/requirements/|bundled/skills|third_party/system-prompts-mirror|third_party/vco-ecosystem-mirror" README.md docs scripts packages tests config adapters core dist .github -g '!node_modules/**'`
- `for f in $(git diff --name-only | rg '^scripts/'); do rg -n --fixed-strings "$f" . -g '!node_modules/**' -g '!outputs/**' || true; done`

Recommended regression matrix by batch type:

| Batch Type | Minimum Tests |
| --- | --- |
| docs-only archive batch | docs link scans, release README checks, `git diff --check` |
| release-surface batch | `tests/integration/test_release_cut_gate_contract_cutover.py`, `tests/runtime_neutral/test_release_cut_operator.py` |
| proof / fixture batch | `tests/runtime_neutral/test_outputs_boundary_migration.py`, replay and manifest consumers |
| script retirement batch | targeted gate / runtime / installer bridge tests for touched families |
| bundled packaging batch | `tests/integration/test_runtime_core_packaging_roles.py`, `tests/integration/test_catalog_contract_consumption.py`, freshness / offline gate coverage |

## PR Strategy

Each implementation PR must satisfy all of the following:

1. one path family or one owner-boundary cut only
2. docs-only and executable/runtime-impacting changes must not be mixed
3. each PR description must state:
   - target family
   - why the cut is safe
   - exact verification commands run
   - retained risks or deferred items
4. each PR must be independently revertible

Preferred PR sequence:

1. live docs second-pass reduction
2. references retention reform
3. verify family convergence
4. bundled shared-asset dedup
5. bundled alias and payload tiering
6. third-party root parameterization

## Rollback Rules

- Every slimming batch must be split so that one PR corresponds to one path family or one owner-boundary cut.
- Do not mix archive-heavy doc changes with runtime or installer changes in the same PR.
- If any candidate deletion is still referenced by active config, tests, adapters, or release surfaces, downgrade from delete to archive or defer.
- If a wave weakens discoverability, restore the previous README or index surface before continuing.
- If a batch changes packaging, runtime freshness, release-cut, or installer behavior, require a dedicated revert path and restore manifest/index surfaces immediately on failure.

## Batch-Level Exit Criteria

No batch may be called complete unless all are true:

1. reference scans show no unintended live callers of removed paths
2. batch-specific tests pass
3. `git diff --check` passes
4. active indexes remain navigable
5. cleanup removed temporary caches and audit residue

## Phase Cleanup Expectations

- remove temporary audit files and test caches after each planning or implementation phase
- audit for worktree-local zombie Node processes before phase close
- keep only intentional docs, config, tests, and scripts in the final diff

## Success Condition

The program is successful only when:

1. active entry surfaces are short and current
2. historical material is still recoverable but no longer crowds active navigation
3. semantic ownership is clearer after each batch, not more fragmented
4. repo size drops through principled removal or externalization, not through accidental contract loss
5. installer, runtime, release, and verification behavior remain regression-backed after every wave
