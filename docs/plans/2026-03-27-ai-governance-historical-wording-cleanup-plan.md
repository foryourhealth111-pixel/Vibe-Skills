# Plan: Clean Residual Historical Multi-Key Wording From Vibe Governance Docs

## Internal Grade

`M`

## Intent

Perform a focused cleanup pass over remaining `vibe` history and current governance artifacts so the repo no longer carries avoidable exact strings for the retired secondary model-key lanes.

## Execution Steps

1. Freeze the requirement and plan for the historical wording cleanup.
2. Update residual `vibe` change logs and older planning docs to use generic legacy wording instead of the retired key names.
3. Update current governance requirement and plan artifacts created in this run to use generic wording for removed lanes where exact names are no longer necessary.
4. Sync any changed shipped history docs into both bundled `vibe` mirrors.
5. Run repo-wide search to confirm the retired secondary model-key strings no longer appear in `vibe` docs or current governance artifacts.
6. Record any remaining out-of-scope matches outside `vibe`.

## Verification

- `git diff --check`
- `rg -n "<retired-secondary-model-key-pattern>" docs docs/requirements docs/plans bundled/skills/vibe`

## Rollback Rule

If a document becomes misleading after removing the exact legacy names, restore clarity first and only then complete the cleanup.

## Cleanup Expectation

Leave only the updated governance artifacts, synchronized bundled mirrors, and an explicit note for any out-of-scope non-`vibe` residue.
