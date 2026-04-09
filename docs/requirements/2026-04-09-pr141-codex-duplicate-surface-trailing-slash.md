# PR141 Codex Duplicate Surface Trailing Slash Fix

## Goal
Repair PR `#141` so the Codex duplicate-surface guard remains authoritative when `check.ps1` receives the default Codex target root with a trailing path separator.

## Problem Statement
The branch adds `Resolve-CodexDuplicateSkillRoot`, but it derives the target leaf from `GetFileName(GetFullPath($TargetRoot))` without trimming trailing directory separators first. On PowerShell, a default Codex root such as `/tmp/home/.codex/` yields an empty leaf instead of `.codex`, so the duplicate-surface guard returns early and silently misses the legacy `.agents/skills/vibe` collision it was meant to catch.

## Required Outcomes
1. `check.ps1` must treat `.../.codex` and `.../.codex/` as the same default Codex root when deriving the duplicate-surface probe path.
2. The duplicate-surface failure must still trigger when a legacy `.agents/skills/vibe/SKILL.md` exists and `-TargetRoot` ends in a path separator.
3. A regression test must prove the trailing-separator case failed before the fix and passes after it.

## Constraints
- Keep the fix narrowly scoped to the duplicate-surface guard in `check.ps1`.
- Do not regress the existing null-inventory repair in this PR.
- Reuse the existing runtime-neutral PowerShell test surface instead of introducing a second ad hoc verification path.

## Acceptance Criteria
- A targeted PowerShell runtime-neutral test fails on the current branch when `-TargetRoot` ends with `/`.
- After the implementation change, that test passes and still reports the duplicate-surface failure.
- The existing duplicate-surface PowerShell test without a trailing separator remains green.
