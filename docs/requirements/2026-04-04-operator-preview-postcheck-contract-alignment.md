# 2026-04-04 Operator Preview Postcheck Contract Alignment

## Goal

Make the operator preview receipt consume a distinct postcheck gate surface from the operator preview contract instead of duplicating the apply-time gate list into the postcheck section.

## Scope

In scope:
- `scripts/governance/release-cut.ps1`
- `config/operator-preview-contract.json`
- focused tests for preview artifact structure and contract consumption

Out of scope:
- changing the release gate inventory itself
- changing the release-cut write flow
- changing unrelated governance operators

## Acceptance Criteria

1. `release-cut` preview receipts use contract-backed `postcheck_gates` for `postcheck.verify_after_apply`.
2. `release-cut` continues to use contract-backed `apply_gates` for the gated apply flow.
3. If `postcheck_gates` is absent, compatibility behavior falls back to the apply gate list.
4. Focused tests lock the split between preview planned gates and postcheck verification expectations.
