# 2026-04-01 PR96 Gate Review And Hardening Plan

## Goal

Repair the failing PR `#96` gate and leave behind a review-grade diagnosis of any adjacent CI or packaging risks discovered during the repair.

## Grade

- Internal grade: L

## Batches

### Batch 1: Freeze governance
- Record the bounded requirement and execution plan for the PR gate repair

### Batch 2: Diagnose the hard failure
- Reproduce the failing `gates` job locally
- isolate the exact PowerShell parser failure in `vibe-skill-catalog-profile-gate.ps1`

### Batch 3: Implement minimal repair
- fix the syntax error in the new catalog gate
- add targeted regression coverage so CI wiring plus artifact-writing syntax remain protected

### Batch 4: Adjacent risk review
- inspect whether other gate outputs indicate fresh regressions or pre-existing debt
- separate true blockers from latent workflow or lock-governance issues

### Batch 5: Verification
- run the repaired catalog gate directly
- run targeted python validation tests
- summarize residual risks with evidence

## Verification Commands

- `pwsh -NoProfile -File ./scripts/verify/vibe-skill-catalog-profile-gate.ps1`
- `python3 -m pytest -q tests/runtime_neutral/test_python_validation_contract.py`

## Rollback Rules

- If the added regression check is too brittle, prefer a narrower assertion that still catches the parser regression over removing coverage entirely
- If adjacent CI debt requires broader repository churn, keep that work out of this repair batch and report it explicitly as follow-up risk
