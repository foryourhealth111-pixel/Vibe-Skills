# 2026-04-04 Release-Cut Gate Contract Delegation Plan

## Goal

Remove the last two release closure gates as script-text consumers so the operator preview contract is the semantic owner of release gate membership.

## Internal Grade

XL wave, executed serially for this microphase because the cut crosses governance config, a PowerShell operator, verification gates, and runtime-neutral operator tests.

## Frozen Scope

- Keep `config/operator-preview-contract.json` as the canonical `release-cut` gate inventory.
- Refactor `scripts/verify/vibe-wave64-82-closure-gate.ps1` and `scripts/verify/vibe-wave83-100-closure-gate.ps1` to assert contract membership instead of script-text membership.
- Preserve bounded fallback behavior only for degraded contract cases.
- Add focused tests for closure-gate contract cutover.
- Run focused verification first, then full regression and hygiene.
