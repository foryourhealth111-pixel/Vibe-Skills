# 2026-04-01 PR96 Gate Follow-up Closure Plan

## Goal

Close the remaining PR `#96` risks by fixing workflow exit propagation and making bundled skill locking deterministic and current.

## Grade

- Internal grade: L

## Batches

### Batch 1: Freeze governance
- Record the bounded requirement and plan for the follow-up closure batch

### Batch 2: Workflow honesty fix
- harden `.github/workflows/vco-gates.yml` so each gate invocation checks `$LASTEXITCODE`
- add test coverage for the workflow contract

### Batch 3: Deterministic lock hashing
- replace platform-sensitive file ordering in the skills-lock generator and offline gate
- regenerate `config/skills-lock.json`

### Batch 4: Regression coverage
- extend tests so mixed-case bundled skill layouts produce deterministic lock hashes
- verify offline-skills behavior against the refreshed lock

### Batch 5: Verification and PR update
- run targeted PowerShell and pytest checks
- update the PR branch and confirm GitHub checks remain green

## Verification Commands

- `pwsh -NoProfile -File ./scripts/verify/vibe-offline-skills-gate.ps1`
- `pwsh -NoProfile -File ./scripts/verify/vibe-generate-skills-lock.ps1 -OutputPath /tmp/skills-lock.json`
- `python3 -m pytest -q tests/runtime_neutral/test_offline_skills_gate.py tests/runtime_neutral/test_python_validation_contract.py`
- `git diff --check`

## Rollback Rules

- If deterministic ordering changes more lock entries than expected, inspect the ordering delta before accepting the regenerated lock
- If the workflow hardening breaks gate invocation syntax, keep the old gate list but preserve explicit exit-code checks in the final shape
