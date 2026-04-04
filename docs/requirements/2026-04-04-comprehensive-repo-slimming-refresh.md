# 2026-04-04 Comprehensive Repo Slimming Refresh

## Goal

Refresh the repository-slimming program against the current latest checkout and produce a stronger, more comprehensive slimming plan that reduces repository noise while preserving runtime, install, release, adapter, packaging, and verification behavior.

## Deliverable

A governed planning packet that:

- explains the current repository architecture in path-role terms
- identifies strong slimming targets by directory family and file type
- separates archive-first cuts from contract-first refactors and protected surfaces
- defines a wave-sequenced execution plan with verification and rollback boundaries

## Constraints

- Plan against the latest available checkout in the current governed worktree.
- Preserve public install entrypoints, governed runtime behavior, adapter manifests, release cut flow, and verification contracts.
- Keep high cohesion and low coupling as explicit design criteria:
  - one semantic owner per concern
  - thin compatibility projections
  - historical material out of live entry surfaces
  - reproducible evidence and payloads separated from canonical source
- Do not treat file-count reduction as success unless semantic ownership becomes clearer.
- Do not recommend broad deletion of `packages/**`, `core/**`, `adapters/**`, `dist/**`, or active tests as an early slimming move.

## Current Evidence Snapshot

Observed during this planning refresh:

- repository size: about `45M`
- total tracked files: about `3779`
- `bundled/`: about `30M`, `2120` files
- `docs/`: about `3.7M`, `593` files
- `docs/archive/`: `262` files
- `docs/requirements/`: `48` files
- `docs/plans/`: `27` files
- `docs/status/`: `26` files
- `references/`: about `1.9M`, `178` files
- `references/proof-bundles/`: `43` files
- `references/fixtures/`: `45` files
- `scripts/`: about `3.4M`, `323` files
- `scripts/verify/`: `205` files
- `tests/`: about `1.1M`, `151` files

## Architecture Understanding

The current repository is not a single-code module. It is a governed mixed-surface repo with these primary layers:

1. public entry and explanation surfaces
   - `README.md`, `docs/**`, install docs, status docs, release notes
2. canonical policy and contract surfaces
   - `config/**`, `core/skill-contracts/**`, `references/**`
3. semantic implementation cores
   - `packages/runtime-core/**`, `packages/installer-core/**`, `packages/contracts/**`, `packages/verification-core/**`, `packages/skill-catalog/**`
4. compatibility and host projections
   - `adapters/**`, `dist/**`, `distributions/**`
5. operator and execution wrappers
   - `scripts/router/**`, `scripts/runtime/**`, `scripts/governance/**`, `scripts/install/**`, `scripts/setup/**`, `scripts/verify/**`
6. payload and catalog surfaces
   - `bundled/skills/**`, `config/skills-lock.json`
7. evidence and regression surfaces
   - `tests/**`, `references/proof-bundles/**`, `references/fixtures/**`

## Problem Statement

The repository has already completed one slimming pass, but the latest checkout still shows four remaining noise patterns:

1. live documentation remains too large outside the archived plan and release spines
2. proof and fixture families still retain bulky raw artifacts with weak direct consumption signals
3. setup and auxiliary script families likely contain low-frequency or dead paths that are not yet governed by an explicit retention rule
4. bundled skill payload is by far the largest surface, but it cannot be safely slimmed until tiered packaging ownership becomes explicit

## High-Value Findings

### Finding A: Root `docs/*.md` remains crowded

Many root-level docs currently show only very weak repo-wide linkage in preliminary exact-path and basename audits, which suggests that the live docs root still acts as a historical catch-all instead of a tightly curated entry surface.

Representative weak-link examples from this audit include:

- `docs/design/agency-agents-overlay.md`
- `docs/governance/anti-proxy-goal-drift-corpus-governance.md`
- `docs/archive/root-docs/compatibility-matrix.md`
- `docs/external-tooling/docling-upstream-delta-2026-03-16.md`
- `docs/design/node-zombie-guardian-design.md`

This does not prove they are deletable, but it does justify a family-level review of which root docs are still true live entry surfaces and which should be regrouped or archived.

### Finding B: Proof bundles are manifest-important but raw-log-heavy

`references/proof-bundles/**` still contains many raw logs and receipts with much weaker exact-path linkage than the manifests and baseline summaries that current docs, adapters, and tests actually mention.

Examples:

- keep-critical candidates:
  - `references/proof-bundles/linux-full-authoritative-candidate/manifest.json`
  - `references/proof-bundles/claude-code-managed-closure-candidate/manifest.json`
  - `references/proof-bundles/openclaw-runtime-core-preview-candidate/manifest.json`
  - `references/proof-bundles/official-runtime-baseline/baseline-manifest.json`
- likely archive-or-externalize candidates:
  - `command-log.txt`
  - `environment.log`
  - `install.log`
  - `receipt-files.txt`
  - duplicated `repo-outputs-verify/*.md|*.json` payload copies

### Finding C: Fixture retention rules are still weak

`references/fixtures/anti-proxy-goal-drift/**` and parts of `references/fixtures/runtime-contract/**` currently show very low direct reference counts by exact path, which suggests these fixture families may be directory-consumed, historically retained, or partially stale.

This surface needs a consumer-proof pass before deletion, but it is a strong candidate for:

- manifesting which fixture families are actively consumed
- archiving scenario fixtures that no longer back gates or tests
- moving bulky illustrative samples out of the default live fixture surface

### Finding D: Auxiliary script surfaces are promising low-risk slimming targets

Low-reference scripts already stand out in:

- `scripts/setup/**`
- `scripts/research/**`
- `scripts/learn/**`

Examples:

- `scripts/setup/export-codex-settings-sanitized.ps1`
- `scripts/setup/show-windows-proof-media-options.sh`
- `scripts/setup/sync-codex-settings-to-user-env.ps1`
- `scripts/research/sync-mcp-catalog.ps1`

These are not safe to delete purely from a text-reference scan, but they are ideal candidates for a dead-path audit and possible retirement in a later wave.

### Finding E: Bundled payload remains the dominant slimming frontier

`bundled/skills/**` is still about `30M` and is tightly coupled to:

- `config/skills-lock.json`
- `core/skills/*/skill.json`
- installer and runtime packaging logic

This means bundled reduction is still the largest eventual opportunity, but not an immediate deletion candidate.

## Acceptance Criteria

1. The planning output classifies slimming candidates into low-, medium-, and high-risk families.
2. The plan explicitly distinguishes:
   - live authority surfaces
   - archive-first surfaces
   - generate-on-demand surfaces
   - contract-first refactor surfaces
   - protected surfaces
3. The plan covers documents, references, proof bundles, fixtures, scripts, and bundled payloads rather than only one area.
4. Every strong cut proposal has a verification boundary and a rollback rule.
5. The plan keeps runtime, install, release, adapter, and verification behavior out of the early destructive waves.

## Product Acceptance Criteria

The planning refresh is acceptable only if maintainers can answer all of the following after reading it:

1. Which directories are semantic owners versus historical or compatibility surfaces?
2. Which slim-down opportunities are safe now versus blocked on consumer mapping?
3. Which live docs are truly current entry surfaces and which should be regrouped or archived?
4. How should proof bundles, fixtures, and bulky payloads be retained without losing auditability?
5. In what order should the strong-slimming program execute to keep blast radius low?

## Manual Spot Checks

- Confirm public install and quick-start pages remain outside the first destructive waves.
- Confirm `docs/status/**`, current release notes, and live architecture proof remain readable after any proposed doc regrouping.
- Confirm proof-bundle recommendations preserve manifest-level consumers even when raw logs are archived.
- Confirm bundled-skill recommendations do not alter packaging semantics before explicit inventory tiers exist.
- Confirm setup-script retirement requires reference audit plus at least one owner decision, not only grep evidence.

## Completion Language Policy

- This planning refresh may claim only that a stronger, evidence-based slimming plan has been produced.
- It must not claim that the repository has already been fully simplified or regression-safe after future implementation.
- Any future slimming wave must earn separate execution and verification evidence.

## Delivery Truth Contract

- Planning truth covers architecture understanding, candidate classification, sequencing, and risk boundaries.
- Implementation truth remains pending until each wave is landed and verified.

## Non-Goals

- No runtime refactor, installer rewrite, adapter redesign, or release-process rewrite in this planning run.
- No broad deletion of bundled skills, manifests, or tests.
- No semantic downgrading of historical evidence into unrecoverable deletion without retention-policy proof.

## Inferred Assumptions

- The maintainer wants a stronger slimming program than the earlier pass, but still wants behavior preservation.
- The biggest maintenance pain now comes from mixed live/archive semantics and low-signal evidence payloads, not from the semantic core packages.
- The repository will benefit most from explicit retention policy and packaging tiers before any aggressive payload cuts.
