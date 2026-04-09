# VibeSkills v3.0.0 Release Requirement

## Goal

Cut a governed major release `v3.0.0` from the latest GitHub `origin/main` baseline, synchronize the repository's release/version surfaces, and produce a detailed release note that truthfully combines the unpublished `v2.3.56` local baseline with the additional changes already merged after it.

## Deliverables

- Repository version surfaces updated to `3.0.0` where this repo treats them as release or package version markers.
- Governed release metadata updated through the canonical release path.
- A new detailed release note at `docs/releases/v3.0.0.md`.
- Live release navigator surfaces updated to point at `v3.0.0`.
- Runtime/session proof artifacts for this governed run under `outputs/runtime/vibe-sessions/20260407T214009-release-v3-0-0/`.
- A pushed release branch and tag if remote permissions and transport succeed.

## Constraints

- Use the latest remote `origin/main` code as the release base.
- Do not modify the user's dirty local branches.
- Preserve governed release truth: do not claim a GitHub release object exists unless it was actually created.
- Keep release notes explicit about what came from the unpublished `v2.3.56` baseline and what came from the subsequent merged changes.
- Prefer the repository's canonical release operator instead of hand-editing generated release surfaces where the operator owns them.

## Acceptance Criteria

- `config/version-governance.json` points to `3.0.0` with the release date for this cut.
- `SKILL.md` maintenance metadata is updated to `Version: 3.0.0`.
- All repo package `pyproject.toml` version markers move from `0.1.0` to `3.0.0`.
- `docs/releases/README.md`, `references/changelog.md`, `references/release-ledger.jsonl`, and dist manifest release surfaces are updated consistently.
- `docs/releases/v3.0.0.md` exists and contains detailed highlights, change comparison, validation notes, and migration notes.
- Targeted release tests and gates run fresh and their actual outcomes are recorded.
- If push succeeds, branch `release/v3.0.0` and tag `v3.0.0` exist on `origin`.

## Product Acceptance Criteria

- The release note reads like a major version announcement rather than a placeholder.
- User-facing install/runtime changes are grouped into coherent themes.
- The release narrative is honest about scope, breaking-surface risk, and operational migration expectations.

## Manual Spot Checks

- Inspect the generated `docs/releases/v3.0.0.md` for structure and factual consistency.
- Confirm `docs/releases/README.md` shows `v3.0.0` as the current release surface.
- Confirm `references/changelog.md` and `references/release-ledger.jsonl` contain a `v3.0.0` entry.
- Confirm package version markers no longer show `0.1.0`.

## Completion Language Policy

Do not claim the release is published until tag push and any remote publication step have actually succeeded. If only branch/tag push succeeds, report exactly that.

## Delivery Truth Contract

- "Version synchronized" means the modified version files were inspected in the release worktree.
- "Verified" means the listed commands were run in this session and their outputs were checked.
- "Published" means the remote branch/tag push succeeded; GitHub release object creation is a separate claim.

## Non-Goals

- Rewriting unrelated historical release notes.
- Refactoring release tooling outside what is required for `v3.0.0`.
- Claiming compatibility guarantees broader than the executed gates support.

## Autonomy Mode

Interactive governed execution with user-approved version target `v3.0.0`.

## Inferred Assumptions

- The user wants a major version cut directly from current `origin/main`.
- The unpublished `v2.3.56` content should be absorbed into the major release rather than retro-published first.
- Updating package `pyproject.toml` versions is desired because the user asked to synchronize all version numbers.
