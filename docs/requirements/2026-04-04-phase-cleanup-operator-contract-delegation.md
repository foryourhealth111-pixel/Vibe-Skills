# 2026-04-04 Phase-Cleanup Operator Contract Delegation

## Goal

Make the protected-document cleanup capability declaration come from `config/phase-cleanup-policy.json` instead of from text scraping of `scripts/governance/phase-end-cleanup.ps1`.

## Scope

In scope:
- `config/phase-cleanup-policy.json`
- `scripts/governance/phase-end-cleanup.ps1`
- `scripts/verify/vibe-document-asset-safety-gate.ps1`
- focused docs and tests for the new contract boundary

Out of scope:
- changing the cleanup batch topology beyond contract wiring
- broad refactors of node audit or repo cleanliness gates
- destructive cleanup policy changes

## Acceptance Criteria

1. The document asset safety gate no longer reads `phase-end-cleanup.ps1` text to prove preview/quarantine support.
2. Cleanup operator capabilities are declared in `config/phase-cleanup-policy.json`.
3. `phase-end-cleanup.ps1` consumes and publishes that operator contract instead of silently owning it.
4. Focused tests lock the new ownership boundary, and the safety gate still passes.
