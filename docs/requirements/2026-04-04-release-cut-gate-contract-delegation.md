# 2026-04-04 Release-Cut Gate Contract Delegation

## Goal

Make the remaining release closure verification gates consume release gate membership from the operator preview contract instead of scraping `scripts/governance/release-cut.ps1` text.

## Scope

In scope:
- `config/operator-preview-contract.json`
- `scripts/verify/vibe-wave64-82-closure-gate.ps1`
- `scripts/verify/vibe-wave83-100-closure-gate.ps1`
- focused integration and runtime-neutral tests for contract-backed gate planning

Out of scope:
- changing the release-cut write flow
- changing the release gate set itself
- changing unrelated operator preview semantics

## Acceptance Criteria

1. `vibe-wave64-82-closure-gate.ps1` proves release gate membership from `config/operator-preview-contract.json`.
2. `vibe-wave83-100-closure-gate.ps1` proves release gate membership from `config/operator-preview-contract.json`.
3. Both closure gates keep a bounded fallback path for degraded contract availability, without restoring script text as the primary truth surface.
4. Focused tests lock the closure-gate contract cutover and preserve release-lane behavior.
