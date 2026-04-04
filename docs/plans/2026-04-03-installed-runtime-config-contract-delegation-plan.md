# 2026-04-03 Installed Runtime Config Contract Delegation Plan

## Goal

Consolidate installed-runtime configuration ownership in contracts so CLI and verification-core consume the same default and merge semantics.

## Internal Grade

XL wave, executed serially for this microphase because the change crosses contracts, verification-core, and CLI boundaries but should preserve behavior.

## Frozen Scope

- Extend installed-runtime contracts with a full default config surface and a merge helper.
- Refactor verification-core policies to delegate installed-runtime config merging to contracts.
- Refactor CLI repo helpers to delegate installed-runtime defaults and merging to contracts.
- Update focused unit and integration tests.
- Run focused verification; full regression will happen at wave boundary.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Add contract-owned installed-runtime defaults and merge helpers.
3. Update verification-core policies to consume the contract helper.
4. Update CLI repo helpers to consume the contract helper.
5. Update focused tests for contract ownership and non-regression.
6. Run focused verification and diff hygiene.
