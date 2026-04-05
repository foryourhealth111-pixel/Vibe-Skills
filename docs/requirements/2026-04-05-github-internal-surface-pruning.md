# 2026-04-05 GitHub / Internal Surface Pruning

## Goal

Prune low-value repository-maintenance surfaces from the root while preserving active CI and runtime verification behavior.

## Deliverable

A verified repository cleanup that:

- keeps `.github/workflows/vco-gates.yml` as the active GitHub CI surface
- removes GitHub issue / pull-request templates that no longer justify root-level maintenance weight
- removes the `.internal/` maintenance checklist surface
- updates tests so packaging and generated-bundle expectations match the slimmer repo

## Constraints

- Work in `<repo-root>`.
- Do not remove `.github/workflows/vco-gates.yml`.
- Do not break active CI or runtime validation contracts.
- Treat historical plan / status docs as archival unless they are part of an active contract.

## In Scope

- `.github/ISSUE_TEMPLATE/**`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.internal/**`
- tests that still expect `.internal` as a bundled-only release surface

## Out Of Scope

- removing `.github/workflows/**`
- broader GitHub automation redesign
- rewriting archival docs that mention past GitHub template surfaces

## Acceptance Criteria

1. `.github/workflows/vco-gates.yml` remains present.
2. GitHub issue / pull-request templates are removed.
3. `.internal/` is removed from the canonical repo.
4. No active test still expects `.internal` to be present as a bundled-only release surface.
5. Targeted verification passes after the pruning.

## Product Acceptance Criteria

1. The root becomes slightly shorter without dropping active CI.
2. The repo keeps only GitHub-facing automation that still has enforcement value.
3. Internal-only notes that are not part of runtime, install, or verification contracts stop occupying root-level namespace.

## Manual Spot Checks

- Confirm `.github/workflows/vco-gates.yml` still exists.
- Confirm `.github/ISSUE_TEMPLATE/` is absent.
- Confirm `.github/PULL_REQUEST_TEMPLATE.md` is absent.
- Confirm `.internal/` is absent.

## Completion Language Policy

- Completion claims are limited to this pruning wave and the targeted verification run performed here.
- No claim may imply that all remaining root-directory simplification work is complete.

## Delivery Truth Contract

- This wave intentionally removes collaboration templates and internal-only maintenance notes, not active CI.
- Historical docs may still mention these surfaces as past state; active tests and live automation are the source of truth after this wave.

## Non-Goals

- no deletion of active CI workflows
- no rewrite of historical planning records for cosmetic consistency only
- no runtime-contract changes unrelated to this root-surface pruning

## Inferred Assumptions

- The user wants aggressive root slimming but does not want to lose GitHub Actions validation.
- `.internal/vibe-maintenance-checklist.md` is safe to retire because it is internal-only and not part of current runtime payload contracts.
