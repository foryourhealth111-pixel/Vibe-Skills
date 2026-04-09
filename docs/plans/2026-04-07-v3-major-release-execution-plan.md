# VibeSkills v3.0.0 Release Execution Plan

**Goal:** Cut a governed `v3.0.0` major release from `origin/main`, synchronize release/package version surfaces, and publish a detailed release narrative.

**Internal Grade:** L

**Why L Instead Of XL:** The work spans multiple steps but touches one tightly coupled release surface. Serial execution is safer than parallel fan-out because version synchronization, release-cut application, and verification all depend on one another.

## Ownership Boundaries

- Release metadata surfaces:
  `config/version-governance.json`, `SKILL.md`, `references/changelog.md`, `references/release-ledger.jsonl`, `docs/releases/README.md`, `docs/releases/v3.0.0.md`
- Package version surfaces:
  root `pyproject.toml`, `apps/vgo-cli/pyproject.toml`, and package `pyproject.toml` files under `packages/`
- Governed runtime artifacts:
  `outputs/runtime/vibe-sessions/20260407T214009-release-v3-0-0/*`

## Execution Steps

1. Freeze governed inputs and runtime lineage artifacts for the release run.
2. Use the isolated worktree on `release/v3.0.0` tracking `origin/main`.
3. Update all explicit package version markers from `0.1.0` to `3.0.0`.
4. Draft `docs/releases/v3.0.0.md` with major-release framing based on:
   - unpublished `v2.3.56` architecture baseline
   - `origin/main` changes since `v2.3.55`
   - PRs `#130`, `#131`, `#132`, and `#133`
5. Run the canonical release operator preview for `3.0.0`.
6. Apply the canonical release operator for `3.0.0`.
7. Run targeted release tests and stop-ship gates.
8. Review the resulting diff, commit, create tag, and push if transport/auth permit.
9. Emit cleanup and delivery acceptance receipts.

## Verification Commands

- `python3 -m pytest -q tests/integration/test_release_cut_gate_contract_cutover.py tests/integration/test_dist_manifest_generation.py tests/integration/test_dist_manifest_surface_roles.py tests/integration/test_version_governance_runtime_roles.py tests/runtime_neutral/test_release_cut_operator.py tests/runtime_neutral/test_release_notes_quality.py`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\governance\\release-cut.ps1 -Version 3.0.0 -Updated 2026-04-07 -Preview`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\governance\\release-cut.ps1 -Version 3.0.0 -Updated 2026-04-07`
- `pwsh -NoProfile -File scripts/verify/vibe-version-consistency-gate.ps1`
- `pwsh -NoProfile -File scripts/verify/vibe-dist-manifest-gate.ps1`
- `pwsh -NoProfile -File scripts/verify/vibe-version-packaging-gate.ps1`
- `pwsh -NoProfile -File scripts/verify/vibe-release-notes-quality-gate.ps1`
- `git diff --check`

## Delivery Acceptance Plan

- Check that current release surfaces point to `v3.0.0`.
- Check that the major-release note is detailed and non-placeholder.
- Check that no `0.1.0` package version markers remain.
- Check whether branch/tag push succeeded and report exact remote state.

## Completion Language Rules

- "Released" requires successful local release-cut apply and verification.
- "Published" requires successful remote branch/tag push.
- "GitHub release" may only be claimed if a release object is explicitly created, which is outside the repo-local release-cut operator.

## Rollback Rules

- If release-cut preview or apply fails, stop and report the failing gate/operator output.
- If package version synchronization causes release gates to fail, repair the mismatch in the release worktree and rerun verification before any commit.
- Do not modify or clean unrelated local worktrees.

## Phase Cleanup Expectations

- Write phase receipts for requirement freeze, plan freeze, execution, and cleanup.
- Record verification command outcomes and remote publish outcomes.
- Leave the worktree intact for review unless the user asks for cleanup.
