# Vgo Upgrade Self Repo Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the shared upgrader so official self-repo metadata is always available and failed refreshes cannot corrupt installed upgrade status.

**Architecture:** Restore the missing `official_self_repo` contract in release governance, then tighten the upgrade service so it resolves upstream fetch inputs from validated repo metadata and only persists installed or remote status after the required values are known-good. Cover the regression with focused unit tests plus one runtime-neutral contract test that reads the generated upgrade-status file.

**Tech Stack:** Python CLI runtime, JSON governance config, pytest unit tests, runtime-neutral install verification

---

## Chunk 1: Freeze the Contract and Write Red Tests

### Task 1: Encode the expected upgrade metadata contract

**Files:**
- Add: `docs/requirements/2026-04-15-vgo-upgrade-self-repo-hardening.md`
- Add: `docs/plans/2026-04-15-vgo-upgrade-self-repo-hardening-execution-plan.md`
- Modify: `tests/unit/test_vgo_cli_repo.py`
- Modify: `tests/unit/test_vgo_cli_upgrade_service.py`

- [ ] **Step 1: Add a repo-config guard test**

Write a failing test in `tests/unit/test_vgo_cli_repo.py` that reads the repository's real `config/version-governance.json` and asserts:

- `repo_url` ends with `/Vibe-Skills.git`
- `default_branch` is `main`
- `canonical_root` is `.`

- [ ] **Step 2: Add a failed-refresh persistence test**

Write a failing test in `tests/unit/test_vgo_cli_upgrade_service.py` that seeds `upgrade-status.json` with a known-good remote and branch, forces `git fetch` to fail, and asserts the file on disk still contains the old good values after the exception.

- [ ] **Step 3: Add a missing-persisted-metadata fallback test**

Write a failing test in `tests/unit/test_vgo_cli_upgrade_service.py` that passes `current_status` with blank `repo_remote` and `repo_default_branch`, stubs repo governance lookup, and asserts refresh uses governance-derived values for `git fetch`.

- [ ] **Step 4: Run the red test slice**

Run:

`python3 -m pytest tests/unit/test_vgo_cli_repo.py tests/unit/test_vgo_cli_upgrade_service.py -q`

Expected: FAIL until the repo config and upgrade-service changes are implemented.

## Chunk 2: Implement the Metadata and Persistence Fix

### Task 2: Make official self-repo metadata authoritative and safe

**Files:**
- Modify: `config/version-governance.json`
- Modify: `apps/vgo-cli/src/vgo_cli/repo.py`
- Modify: `apps/vgo-cli/src/vgo_cli/upgrade_service.py`
- Modify: `apps/vgo-cli/src/vgo_cli/install_support.py`

- [ ] **Step 1: Restore official self-repo metadata in governance**

Add `source_of_truth.official_self_repo` to `config/version-governance.json` with the official GitHub repository URL and default branch.

- [ ] **Step 2: Centralize metadata fallback behavior**

Update `get_official_self_repo_metadata()` or a helper alongside it so blank or missing persisted upgrade-status values can be replaced by repo-governance values before upstream refresh runs.

- [ ] **Step 3: Stop pre-failure status pollution**

Change the upgrade flow so a failed refresh does not write an empty `repo_remote` or `repo_default_branch` into `.vibeskills/upgrade-status.json`. Preserve last known-good state when refresh fails.

- [ ] **Step 4: Keep install postconditions truthful**

Ensure install-time upgrade-status writes also use the restored authoritative metadata and still record installed version and commit as before.

- [ ] **Step 5: Re-run the focused unit tests**

Run:

`python3 -m pytest tests/unit/test_vgo_cli_repo.py tests/unit/test_vgo_cli_upgrade_service.py -q`

Expected: PASS

## Chunk 3: Add the Release Guardrail and Final Verification

### Task 3: Prove the bug fix survives the packaged runtime path

**Files:**
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] **Step 1: Strengthen the runtime-neutral assertion if needed**

Keep or extend the existing assertion so installed runtime output proves `upgrade-status.json` contains `main` and an official repo URL derived from the patched governance contract.

- [ ] **Step 2: Run the focused verification slice**

Run:

`python3 -m pytest tests/unit/test_vgo_cli_repo.py tests/unit/test_vgo_cli_upgrade_service.py tests/runtime_neutral/test_installed_runtime_scripts.py -q`

Expected: PASS

- [ ] **Step 3: Review diff risk before completion**

Confirm the patch only changes:

- upgrade metadata contract
- status-persistence boundary
- regression tests tied to the bug

- [ ] **Step 4: Report release implications truthfully**

State explicitly that a new release can carry the fix forward, but already-installed users need the fixed upgrader path or a documented recovery path because the previous release shipped a broken self-upgrade contract.
