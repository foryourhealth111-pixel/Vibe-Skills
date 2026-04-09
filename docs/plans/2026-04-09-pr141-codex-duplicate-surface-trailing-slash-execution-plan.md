# PR141 Codex Duplicate Surface Trailing Slash Execution Plan

**Goal:** Close the trailing-separator bypass in the PowerShell duplicate-surface guard for Codex installs and prove the fix with a targeted regression test.

**Architecture:** Keep the current duplicate-surface detection flow, but normalize the incoming target root once before deriving the leaf and parent paths used to locate the legacy `.agents/skills/vibe` shadow surface.

**Tech Stack:** PowerShell check script, Python runtime-neutral unittest suite

---

### Task 1: Lock the bypass with a failing regression test

**Files:**
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] Add a PowerShell runtime-neutral test that installs to the default Codex root, appends a trailing path separator to `-TargetRoot`, seeds a legacy `.agents/skills/vibe/SKILL.md`, and asserts that duplicate-surface detection still fires.
- [ ] Run the targeted test and confirm it fails against the current branch for the expected reason.

### Task 2: Normalize the duplicate-surface target root

**Files:**
- Modify: `check.ps1`

- [ ] Normalize `TargetRoot` before deriving both the leaf name and the parent path in `Resolve-CodexDuplicateSkillRoot`.
- [ ] Keep the rest of the guard behavior unchanged.

### Task 3: Verify and commit

**Files:**
- Inspect: `check.ps1`
- Inspect: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] Run the targeted regression slice, including the existing non-trailing duplicate-surface PowerShell test.
- [ ] Review the diff for scope control.
- [ ] Commit the repair on `fix/check-codex-duplicate-surface`.
