# 2026-04-01 Issue31 Git Diff Task Gating Plan

## Goal

Carry forward the highest-signal Issue #31 runtime reduction into the existing LLM acceleration path without introducing any parallel context system or changing route authority.

The targeted change is:

- keep explicit `/vibe` / `@vibe-skills` LLM intervention intact
- keep the current runtime path intact
- reduce context weight by allowing `git diff` only for code-oriented tasks:
  - `coding`
  - `debug`
  - `review`

This plan intentionally does not carry forward:

- `trigger.max_confidence_for_llm` retuning
- `trigger.always_on_explicit_vibe` retuning
- clean-repo diff skip as a standalone optimization

## Grade

- Internal grade: M

## Batches

### Batch 1: Freeze Issue31 scope and runtime boundary
- Keep Issue #31 scoped to runtime-surface reduction inside the existing acceleration path
- Keep explicit `/vibe` / `@vibe-skills` LLM intervention as a justified path, not an optimization target for removal
- Confirm that the live change surface remains:
  - `config/llm-acceleration-policy.json`
  - `scripts/router/modules/48-llm-acceleration-overlay.ps1`

### Batch 2: Validate candidate reductions and choose the carry-forward change
- Compare the pre-change baseline, current baseline, single-variable profiles, and the combined profile
- Confirm that `context.git_diff_task_allow = ["coding", "debug", "review"]` is the strongest single-variable reduction
- Confirm that `planning` and `research` are the clearest cases where default diff injection is not justified
- Leave threshold tuning, `always_on_explicit_vibe`, and clean-repo skip out of scope for this PR because they did not show comparable value in the current evidence set

### Batch 3: Land runtime policy and overlay wiring
- Add `context.git_diff_task_allow = ["coding", "debug", "review"]` to runtime policy
- Resolve `git_diff_task_allow` through the overlay context path
- Pass `TaskType` into `Get-VcoGitContextSnippet`
- Skip diff injection for task types outside the allow-list
- Surface `diff_mode = "skipped_task_type"` when diff is intentionally excluded by task type

### Batch 4: Verify guarded-surface behavior stays narrow
- Confirm that `planning` and `research` can skip diff injection through the new task-type gate
- Confirm that `coding`, `debug`, and `review` remain eligible for diff injection
- Confirm that the change does not alter route-authority semantics
- Keep the PR limited to the validated context-weight reduction rather than bundling other Issue #31 candidates

## Verification Commands

- `git diff --check`
- `git status --short`
- `rg -n "git_diff_task_allow|skipped_task_type|Get-VcoGitContextSnippet -PolicyResolved .* -TaskType" config/llm-acceleration-policy.json scripts/router/modules/48-llm-acceleration-overlay.ps1`

## Rollback Rules

- If the change affects route-authority behavior instead of only context-weight behavior, stop and revert to the narrower Issue #31 scope
- If `planning` / `research` lose diff injection but `coding` / `debug` / `review` do not remain eligible, block merge until the allow-list wiring is corrected
- If additional Issue #31 candidates are required to justify the PR, stop and split them into a separate evidence track instead of bundling them into this change
- If the runtime diff spreads beyond the policy file and overlay task-type gate without clear necessity, keep the PR narrow and revert unrelated edits
