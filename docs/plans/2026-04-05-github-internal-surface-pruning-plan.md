# 2026-04-05 GitHub / Internal Surface Pruning Plan

## Internal Grade Decision

`M` narrow execution. The change set is small, local, and does not require delegation.

## Waves

### Wave 1: Freeze And Inspect

- confirm `origin/main` contains the latest merged slimming work
- inspect active references to `.github` and `.internal`
- separate active CI surfaces from low-value templates / internal notes

### Wave 2: Apply Pruning

- delete `.github/ISSUE_TEMPLATE/**`
- delete `.github/PULL_REQUEST_TEMPLATE.md`
- delete `.internal/vibe-maintenance-checklist.md`
- update generated bundled-surface tests so `.internal` is no longer expected

### Wave 3: Verify And Cleanup

- run targeted tests for GitHub workflow and bundled-surface expectations
- confirm `git diff --check` is clean
- audit temp files and node processes, then remove local residue if created

## Ownership Boundaries

- root pruning: canonical repo root only
- CI preservation: `.github/workflows/vco-gates.yml` stays untouched
- contract updates: only tests and pruning-wave docs may change

## Verification Commands

```bash
python3 -m pytest -q \
  /home/lqf/table/table9/Vibe-Skills-main/tests/runtime_neutral/test_python_validation_contract.py \
  /home/lqf/table/table9/Vibe-Skills-main/tests/runtime_neutral/test_generated_nested_bundled.py

git -C /home/lqf/table/table9/Vibe-Skills-main diff --check
```

## Delivery Acceptance Plan

- keep only `.github/workflows/` under the GitHub root surface
- remove `.internal/` completely
- ensure targeted tests reflect the slimmer bundled-surface contract

## Completion Language Rules

- only claim success if targeted tests pass and no active CI workflow was removed
- explicitly state any archival references left untouched

## Rollback Rules

- if CI validation tests require removed GitHub templates, restore the templates and reassess
- if bundled-surface tests reveal `.internal` still belongs to an active packaging contract, restore `.internal` and update the requirement doc

## Phase Cleanup Expectations

- remove `.pytest_cache` or transient `.tmp/*` residue created by verification
- do not kill node processes unless they are owned by this repo path
