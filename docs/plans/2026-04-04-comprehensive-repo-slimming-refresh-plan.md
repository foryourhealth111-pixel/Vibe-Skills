# 2026-04-04 Comprehensive Repo Slimming Refresh Plan

## Goal

Turn the refreshed repo audit into an executable, strong-slimming program that improves cohesion and lowers coupling without regressing install, runtime, release, adapter, or verification behavior.

## Requirement Doc

- [`../requirements/2026-04-04-comprehensive-repo-slimming-refresh.md`](../requirements/2026-04-04-comprehensive-repo-slimming-refresh.md)

## Internal Grade

XL wave-sequential execution.

This repo is too broad for a single cleanup PR. Strong slimming should proceed in narrow, reviewable waves with bounded write scopes and explicit rollback points.

## Frozen Architecture View

### Semantic Owners

- package-owned behavior: `packages/**`
- config-owned policies and inventories: `config/**`
- host-neutral core contracts: `core/**`

### Compatibility / Projection Surfaces

- `adapters/**`
- `dist/**`
- `distributions/**`
- selected wrapper scripts under `scripts/**`

### Historical / Evidence Surfaces

- `docs/archive/**`
- historical `docs/*.md`
- `references/proof-bundles/**`
- `references/fixtures/**`

### Payload Surface

- `bundled/skills/**`

## Repo Slimming Thesis

The strongest safe slimming outcome will not come from deleting semantic code first. It will come from:

1. shrinking live navigation surfaces
2. externalizing low-signal historical evidence
3. retiring dead or weakly owned helper scripts
4. introducing packaging tiers before touching the bundled payload

## Classification Matrix

### Class 1: Immediate Archive-First Candidates

These are high-value and relatively low-risk because they primarily affect navigation rather than behavior.

- weakly referenced root `docs/*.md` historical governance and overlay pages
- stale migration reports and rollout reports still sitting in live docs root
- standalone topical docs that should be regrouped under family subdirectories such as:
  - `docs/governance/`
  - `docs/design/`
  - `docs/external-tooling/`
  - `docs/archive/`

Representative families:

- anti-proxy-goal-drift historical packets
- overlay integration notes
- older upstream delta notes
- hard/soft migration reports
- historical overlap and audit matrices

### Class 2: Retention-Policy Reform Candidates

These require consumer proof but offer strong payoff.

- `references/proof-bundles/**`
- `references/fixtures/**`
- bulky changelog and ledger volumes that still accumulate historical detail in live paths

Recommended rule:

- keep manifests, README/indexes, and minimal receipts live
- archive or generate raw logs, duplicated verify outputs, and low-signal snapshots

### Class 3: Dead-Path Audit Candidates

These need exact caller mapping before deletion, but are strong candidates for aggressive cleanup.

- `scripts/setup/**`
- `scripts/research/**`
- `scripts/learn/**`
- weakly referenced helper scripts in `scripts/governance/**`

### Class 4: Contract-First Consolidation Candidates

These must not be strongly cut until shared contracts and family ownership are clearer.

- `scripts/verify/**`
- `scripts/router/**`
- `scripts/runtime/**`
- `references/fixtures/**` with ambiguous directory-level consumption

### Class 5: Protected Surfaces

Do not put these into early deletion waves:

- `packages/**`
- `core/**`
- `adapters/**`
- `dist/**`
- `tests/**`
- `config/skills-lock.json`
- live install entry surfaces under `docs/install/**`

## Risk-Tiered Strong Slimming Map

## Tier Low

- regroup or archive weakly referenced root docs
- move historical governance and migration pages behind family indexes
- compress root-level doc navigation into family overview pages
- archive proof-bundle raw logs while keeping manifests live
- add explicit keep/archive rules for fixtures and auxiliary scripts

## Tier Medium

- shrink `references/fixtures/**` after proving which families are active
- retire `scripts/setup/**` and `scripts/research/**` dead paths
- consolidate root docs into subdirectory family hubs
- reduce install-doc duplication only after preserving public bilingual paths

## Tier High

- broad verify-gate consolidation
- bundled skill payload reduction
- manifest path changes that affect adapters, install, or release surfaces
- any move that changes public install path semantics or current release proof paths

## Wave Plan

### Wave 0: Inventory Freeze Refresh

Goal:

- refresh and extend the path-role ledger from the earlier slimming pass

Work:

- classify root `docs/*.md` into `live-authority`, `family-overview`, `archive-first`, or `drop-candidate`
- classify proof-bundle artifacts into `manifest`, `summary`, `raw-log`, `duplicated-verify-output`
- classify fixtures into `active`, `ambiguous`, `historical-sample`
- classify setup and research scripts into `active`, `ambiguous`, `likely-dead`

Verification:

- `rg -n "/home/lqf/table|Plan complete and saved to|Two execution options:" docs references -g '*.md'`
- `rg -n "references/proof-bundles|references/fixtures|scripts/setup|scripts/research|scripts/learn" README.md docs scripts packages tests config adapters core .github`

Rollback:

- documentation-only; no runtime rollback needed

### Wave 1: Root Docs Strong Regrouping

Goal:

- cut live doc-root noise without losing current authority surfaces

Work:

- keep live root docs only for:
  - core public entry
  - current install/runtime governance
  - current long-lived architecture/governance overviews
- move historical governance notes, overlay notes, migration reports, and low-reference matrices into:
  - `docs/archive/**`
  - family subdirectories
  - family index pages
- replace thin leaf pages with grouped overview docs where appropriate

Expected Outcome:

- `docs/README.md` stays short and authoritative
- root `docs/*.md` count materially decreases

Verification:

- `git diff --check -- docs`
- link scan for `README.md`, `docs/README.md`, `docs/status/README.md`
- `rg -n "docs/<moved-file>" README.md docs references scripts packages tests config adapters core .github`

Rollback:

- restore moved docs and root index links in one revertable PR

### Wave 2: Proof-Bundle Surface Slimming

Goal:

- preserve auditability while removing raw-log clutter from the default live proof surface

Work:

- define a minimum tracked proof-bundle schema:
  - manifest
  - README or summary
  - minimum receipt
- archive or externalize:
  - raw shell logs
  - duplicated verify output copies
  - receipt-file inventories
  - environment and install transcripts unless actively referenced

Expected Outcome:

- `references/proof-bundles/**` keeps contract-significant files only

Verification:

- exact-path reference scans for every removed artifact
- adapter, test, and doc checks against kept manifests
- spot-check proof-bundle README navigation

Rollback:

- restore archived raw artifacts without semantic conflict

### Wave 3: Fixture Census and Reduction

Goal:

- turn `references/fixtures/**` into a clearly consumed regression surface instead of a default storage sink

Work:

- add a fixture-family consumer ledger
- separate actively consumed fixtures from historical scenario samples
- archive families with no active gate, test, or config consumer

Priority Families:

- `references/fixtures/anti-proxy-goal-drift/**`
- `references/fixtures/runtime-contract/**`
- `references/fixtures/retro-compare/**`
- `references/fixtures/external-corpus/**`

Verification:

- `rg -n "references/fixtures/" scripts tests packages config adapters core docs`
- targeted test or gate runs for families still in use

Rollback:

- restore archived fixture families by directory

### Wave 4: Auxiliary Script Retirement

Goal:

- remove low-value helper scripts without touching core runtime flow

Scope:

- `scripts/setup/**`
- `scripts/research/**`
- `scripts/learn/**`

Method:

1. map exact callers
2. identify owner
3. delete only zero-consumer or superseded scripts
4. update script indexes and docs

Examples to audit early:

- `scripts/setup/export-codex-settings-sanitized.ps1`
- `scripts/setup/show-windows-proof-media-options.sh`
- `scripts/setup/sync-codex-settings-to-user-env.ps1`
- `scripts/research/sync-mcp-catalog.ps1`

Verification:

- repo-wide exact-path reference scan
- spot-check `scripts/README.md`
- targeted tests for installer/setup or research consumers if they exist

Rollback:

- restore deleted scripts in a single PR revert

### Wave 5: Verify Surface Family Consolidation

Goal:

- reduce `scripts/verify/**` complexity without breaking contract coverage

Work:

- group gate families behind shared helpers
- merge wrappers only after proving equivalent coverage
- keep gate-family index authoritative instead of proliferating flat entrypoints

Precondition:

- no wrapper deletion until shared assertions and artifacts are extracted

Verification:

- targeted integration tests
- gate family smoke sequence from `scripts/verify/README.md`

Rollback:

- preserve gate names or restore deleted wrappers before release cuts

### Wave 6: Install-Doc Duplication Reduction

Goal:

- reduce doc duplication in `docs/install/**` while preserving bilingual public entrypoints

Work:

- classify public install docs into:
  - canonical entry
  - host-specific path
  - prompt library
  - duplication candidate
- keep one-click, framework-only, minimal, and recommended entrypoints live
- consider regrouping repetitive policy or prompt docs into family hubs

Risk:

- medium, because these pages are public and user-facing

Verification:

- manual navigation through `README.md`, `docs/README.md`, `docs/install/README.md`
- confirm bilingual parity for kept public entrypoints

### Wave 7: Bundled Skill Tiering Before Payload Cuts

Goal:

- create the precondition for later strong payload slimming

Work:

- define inventory tiers such as:
  - runtime-core
  - host-required
  - optional
  - research-heavy
- move packaging logic to manifest-driven allowlists
- only then propose removal or detached distribution of optional bundled skills

Blocked By:

- `config/skills-lock.json`
- installer consumers
- core skill references

Verification:

- packaging and installer tests
- adapter manifest checks
- skill-catalog integrity checks

### Wave 8: Third-Party and Snapshot Retention Hardening

Goal:

- ensure no bulky snapshot or mirror payload remains tracked by default without a retention rule

Work:

- review `vendor/**`, `third_party/**`, and remaining tracked research snapshots
- keep only contract-significant or legally required retained assets
- push reproducible pulls toward generated outputs or documented fetch flows

Verification:

- mirror and provenance checks
- release and cleanliness gates as relevant

## Execution Order Recommendation

Recommended order for implementation PRs:

1. root docs regrouping
2. proof-bundle minimum tracked surface
3. fixture census and archive split
4. auxiliary script retirement
5. verify family consolidation
6. install-doc duplication reduction
7. bundled-skill tiering
8. third-party and snapshot hardening

## Verification Contract

Every implementation wave must include:

- `git diff --check`
- exact-path reference audit for deleted or moved files
- README/index link validation for touched doc surfaces
- targeted tests or gates for any touched runtime, install, release, or verification contract
- phase cleanup:
  - no temporary planning files left behind
  - no worktree-owned zombie `node` processes left running

## Completion Language Rules

- Before implementation: only say the plan exists.
- After each wave: claim only the verified scope of that wave.
- Never claim full no-regression unless the affected contracts were actually re-verified.
