# 2026-04-04 Phase-Cleanup Operator Contract Delegation Plan

## Goal

Remove `phase-end-cleanup.ps1` as the semantic owner of protected-document preview/quarantine capability declarations by moving those declarations into the cleanup policy contract.

## Internal Grade

XL microphase executed serially because the cut crosses governance config, a PowerShell operator, a verification gate, and focused cross-language locks.

## Frozen Scope

- add an operator contract section to `config/phase-cleanup-policy.json`
- make `phase-end-cleanup.ps1` consume the operator contract and publish it in its JSON result
- refactor `vibe-document-asset-safety-gate.ps1` to read the policy contract instead of script text
- update focused docs and add focused integration/runtime-neutral locks
- run focused verification, direct gate execution, full regression, and cleanup
