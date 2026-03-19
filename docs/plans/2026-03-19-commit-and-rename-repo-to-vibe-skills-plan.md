# Commit And Rename Repo To Vibe-Skills Execution Plan

**Goal:** Safely publish the current unpublished local modifications first, then rename the GitHub repository to `Vibe-Skills`, without touching the dirty main worktree directly.

**Internal Grade:** M

**Wave Structure:**

1. Freeze the execution requirement and plan.
2. Create an isolated worktree from `origin/main`.
3. Copy the current dirty files into the isolated worktree.
4. Run diff/format verification, commit, and push to current remote main.
5. Rename the GitHub repository through authenticated API.
6. Update local `origin` remote to the new URL and verify fetch/access.
7. Remove temporary worktree and emit cleanup receipts.

**Safety Rules:**

- Do not commit directly on the current dirty main worktree.
- Do not run destructive reset/checkout operations.
- Do not rename the local filesystem checkout directory in the same run.
- Treat the isolated worktree as the only publish surface.

**Ownership Boundaries:**

- Source of truth for unpublished changes: `/home/lqf/table/table2/vco-skills-codex`
- Isolated publish surface: temporary worktree based on `origin/main`
- Remote target before rename: `https://github.com/foryourhealth111-pixel/vco-skills-codex`
- Remote target after rename: `https://github.com/foryourhealth111-pixel/Vibe-Skills`

**Verification Commands:**

- `git diff --check` in the isolated worktree for staged files
- `git push origin HEAD:main`
- authenticated GitHub API readback of repo metadata after rename
- `git remote -v`
- `git fetch origin`
- `git remote show origin`

**Rollback Rules:**

- If isolated-worktree verification fails, stop before commit.
- If push fails, do not attempt rename.
- If rename succeeds but local remote update fails, keep the repository renamed and repair local remote before claiming completion.
- If rename API returns a non-success status, leave the old repository name untouched and report the exact failure.

**Phase Cleanup Expectations:**

- Temporary worktree must be removed after publish/rename verification.
- Cleanup receipt must note whether the local main worktree was left unchanged.
