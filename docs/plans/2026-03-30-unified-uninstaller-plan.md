# Unified Uninstaller Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified owned-only uninstaller for the official install surface and all current host adapters without deleting host-managed user state.

**Architecture:** Add symmetric top-level uninstall entrypoints and a shared adapter-driven uninstall core. Use install-ledger-first ownership proof, fall back to host-closure metadata, and use conservative legacy heuristics only for pre-ledger installs.

**Tech Stack:** PowerShell, POSIX shell, Python 3, existing adapter registry/contracts, pytest runtime-neutral tests, PowerShell verify gates

---

### Task 1: Freeze uninstall ownership contract

**Files:**
- Modify: `adapters/codex/closure.json`
- Modify: `adapters/claude-code/closure.json`
- Modify: `adapters/cursor/closure.json`
- Modify: `adapters/windsurf/closure.json`
- Modify: `adapters/openclaw/closure.json`
- Modify: `adapters/opencode/closure.json`
- Create: `docs/uninstall-governance.md`

**Step 1: Write the failing documentation-oriented test**

- Add a test that loads each adapter closure and asserts uninstall-facing ownership keys or documented delete surfaces exist.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k adapter_contract`

Expected: FAIL because uninstall-facing contract fields do not exist yet.

**Step 3: Write minimal contract updates**

- Extend adapter closure docs so repo-managed uninstall surfaces are explicit and machine-readable enough for the uninstaller.
- Add `docs/uninstall-governance.md` describing ownership and shared-file mutation rules.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k adapter_contract`

Expected: PASS

### Task 2: Add install ledger output to installer

**Files:**
- Modify: `scripts/install/install_vgo_adapter.py`
- Modify: `scripts/install/Install-VgoAdapter.ps1`
- Test: `tests/runtime_neutral/test_installed_runtime_scripts.py`

**Step 1: Write the failing test**

- Add a test asserting install writes `.vibeskills/install-ledger.json` with created paths and managed JSON surfaces.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_installed_runtime_scripts.py -k install_ledger`

Expected: FAIL because no ledger is written yet.

**Step 3: Write minimal implementation**

- Teach installer to emit `install-ledger.json`.
- Record created directories/files, shared JSON mutation targets, wrapper paths, and runtime root.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_installed_runtime_scripts.py -k install_ledger`

Expected: PASS

### Task 3: Add top-level uninstall entrypoints

**Files:**
- Create: `uninstall.ps1`
- Create: `uninstall.sh`
- Create: `scripts/uninstall/Uninstall-VgoAdapter.ps1`
- Create: `scripts/uninstall/uninstall_vgo_adapter.py`

**Step 1: Write the failing smoke test**

- Add a test that invokes `uninstall.ps1` / `uninstall.sh --preview` and asserts argument routing mirrors install.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k entrypoint`

Expected: FAIL because uninstall entrypoints do not exist.

**Step 3: Write minimal implementation**

- Add argument parsing for `--host`, `--target-root`, `--profile`, `--preview`, `--purge-empty-dirs`, `--strict-owned-only`.
- Reuse host resolution and target-root guard patterns from install.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k entrypoint`

Expected: PASS

### Task 4: Implement shared uninstall planning engine

**Files:**
- Modify: `scripts/uninstall/uninstall_vgo_adapter.py`
- Modify: `scripts/uninstall/Uninstall-VgoAdapter.ps1`
- Test: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

**Step 1: Write the failing planner tests**

- Add tests for:
  - ledger-first deletion
  - host-closure fallback
  - legacy owned-only fallback
  - foreign path skip behavior

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k planner`

Expected: FAIL

**Step 3: Write minimal implementation**

- Build delete plan from:
  - install ledger
  - host closure
  - legacy heuristics
- Output preview plan and apply results in a single receipt schema.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k planner`

Expected: PASS

### Task 5: Implement shared JSON owned-only mutation

**Files:**
- Modify: `scripts/uninstall/uninstall_vgo_adapter.py`
- Test: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

**Step 1: Write the failing test**

- Add tests proving `settings.json` / `opencode.json` lose only the `vibeskills` node and preserve unrelated user keys.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k shared_json`

Expected: FAIL

**Step 3: Write minimal implementation**

- Add JSON mutation helper:
  - remove only `vibeskills`
  - never delete on parse failure
  - delete empty file only with ownership proof

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k shared_json`

Expected: PASS

### Task 6: Implement host-specific delete rules

**Files:**
- Modify: `scripts/uninstall/uninstall_vgo_adapter.py`
- Test: `tests/runtime_neutral/test_installed_runtime_uninstall.py`

**Step 1: Write the failing test**

- Add per-host installed-runtime fixtures covering `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, and `opencode`.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_installed_runtime_uninstall.py`

Expected: FAIL

**Step 3: Write minimal implementation**

- Encode host-specific owned surfaces:
  - codex payload
  - preview-managed host files
  - runtime-core-preview host files
  - opencode command/agent compatibility directories

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_installed_runtime_uninstall.py`

Expected: PASS

### Task 7: Add uninstall receipt and cleanup behavior

**Files:**
- Modify: `scripts/uninstall/uninstall_vgo_adapter.py`
- Modify: `scripts/uninstall/Uninstall-VgoAdapter.ps1`
- Test: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

**Step 1: Write the failing test**

- Add a test for uninstall receipt structure and empty-directory purge behavior.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k receipt`

Expected: FAIL

**Step 3: Write minimal implementation**

- Emit receipt with deleted paths, mutated JSON paths, skipped foreign paths, warnings, and ownership source.
- Support `--purge-empty-dirs`.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k receipt`

Expected: PASS

### Task 8: Add uninstall verification gate

**Files:**
- Create: `scripts/verify/vibe-uninstall-coherence-gate.ps1`
- Modify: `scripts/verify/README.md`
- Modify: `scripts/verify/gate-family-index.md`
- Test: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

**Step 1: Write the failing test**

- Add a test proving the new gate exists and validates uninstall/install symmetry.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k coherence_gate`

Expected: FAIL

**Step 3: Write minimal implementation**

- Gate should verify:
  - uninstall entrypoints exist
  - install ledger contract exists
  - uninstall does not claim host-managed rollback
  - per-host contract coverage is present

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k coherence_gate`

Expected: PASS

### Task 9: Update install/uninstall docs

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `docs/install/README.en.md`
- Modify: `docs/install/configuration-guide.en.md`
- Modify: `docs/uninstall-governance.md`
- Modify: `docs/universalization/install-matrix.md`

**Step 1: Write the failing documentation check**

- Add a test or gate assertion that install docs mention the authoritative uninstall path and owned-only boundary.

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k docs`

Expected: FAIL

**Step 3: Write minimal implementation**

- Add uninstall commands and host boundary wording.
- Explicitly say uninstall removes only Vibe-managed content.

**Step 4: Run test to verify it passes**

Run: `pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py -k docs`

Expected: PASS

### Task 10: Full verification and release readiness

**Files:**
- Modify: `docs/releases/<next-version>.md` when implementation actually ships
- Test: `tests/runtime_neutral/test_uninstall_vgo_adapter.py`
- Test: `tests/runtime_neutral/test_installed_runtime_uninstall.py`

**Step 1: Run targeted local verification**

Run:

```bash
pytest -q tests/runtime_neutral/test_uninstall_vgo_adapter.py
pytest -q tests/runtime_neutral/test_installed_runtime_uninstall.py
pytest -q tests/runtime_neutral/test_installed_runtime_scripts.py
pwsh -NoProfile -File scripts/verify/vibe-uninstall-coherence-gate.ps1
git diff --check
```

Expected: all PASS

**Step 2: Run cleanup**

Run:

```bash
pwsh -NoProfile -File scripts/governance/Invoke-NodeProcessAudit.ps1 -RepoRoot .
pwsh -NoProfile -File scripts/governance/Invoke-NodeZombieCleanup.ps1 -RepoRoot .
```

Expected: no managed node residue and no temporary uninstall artifacts left behind.

**Step 3: Commit**

```bash
git add uninstall.ps1 uninstall.sh scripts/uninstall scripts/verify docs README.md README.zh.md tests
git commit -m "feat: add unified owned-only uninstaller"
```

Plan complete and saved to `docs/plans/2026-03-30-unified-uninstaller-plan.md`. Two execution options:

1. Subagent-Driven (this session) - 我在当前会话按任务逐步实现并验证。
2. Parallel Session (separate) - 新开会话按这个计划批量执行。
