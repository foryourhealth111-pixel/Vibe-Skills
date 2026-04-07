# Codex Host-Ready And MCP Truth Separation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make install and check surfaces report `$vibe` host readiness separately from MCP readiness, using real Codex host-active surfaces instead of payload-only or PATH-only signals.

**Architecture:** Introduce a single truth model for install/check/bootstrap reporting with two independent axes: base governed runtime host readiness and per-MCP host visibility. Codex-specific host-ready detection should be grounded in `~/.codex` active surfaces, while MCP status should distinguish host registration, host-native pending, local CLI presence, and online readiness without collapsing them into one `ready` bit.

**Tech Stack:** Python installer/reporting code, JSON receipts, Codex host materialization logic, pytest runtime-neutral and unit tests.

---

### Task 1: Freeze the new readiness vocabulary in tests

**Files:**
- Modify: `tests/runtime_neutral/test_mcp_auto_provision.py`
- Modify: `tests/runtime_neutral/test_bootstrap_doctor.py`
- Modify: `tests/unit/test_vgo_cli_commands.py`
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] **Step 1: Write failing tests for split reporting**

Add assertions that install reporting distinguishes:
- `installed_locally`
- `vibe_host_ready`
- per-MCP readiness
- `online_ready`

Include a Codex case where local payload exists but host-active-surface evidence is insufficient, and assert that overall wording cannot collapse to generic install-complete language.

- [ ] **Step 2: Run the targeted tests to verify RED**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_mcp_auto_provision.py \
  tests/runtime_neutral/test_bootstrap_doctor.py \
  tests/unit/test_vgo_cli_commands.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q
```

Expected:
- at least one failure proving the current implementation still treats PATH-only or payload-only signals as sufficient

- [ ] **Step 3: Add fixture coverage for Codex host-active-surface validation**

Model:
- a real-host-ready Codex target with discoverable `skills/vibe`, `commands`, closure, and active MCP/profile surfaces
- a payload-only target where receipts exist but host-active-surface evidence is incomplete

### Task 2: Add a Codex host-ready evaluator for `$vibe`

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/host_closure.py`
- Modify: `apps/vgo-cli/src/vgo_cli/install_support.py`
- Modify: `apps/vgo-cli/src/vgo_cli/commands.py`
- Add or modify: shared helper module near the existing install/report support if needed

- [ ] **Step 1: Write the failing tests for host-ready evaluation**

Encode the rule that `vibe_host_ready=true` for `codex` requires host-visible evidence from the real target root, not just installer receipts or file parity.

- [ ] **Step 2: Run the relevant tests and confirm failure**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_installed_runtime_scripts.py \
  tests/unit/test_vgo_cli_commands.py -q
```

Expected:
- failure proving the current closure/install pipeline cannot yet compute the stricter host-ready state

- [ ] **Step 3: Implement a host-ready evaluator**

The evaluator should:
- read the normalized host id and target root
- for `codex`, validate the active skill/command/runtime surfaces used by the real host
- emit a structured result that downstream reporters can consume
- avoid conflating specialist wrapper readiness with `$vibe` host readiness

### Task 3: Replace PATH-only MCP `ready` with host-visible MCP readiness states

**Files:**
- Modify: `apps/vgo-cli/src/vgo_cli/mcp_provision.py`
- Modify: `apps/vgo-cli/src/vgo_cli/output.py`
- Modify: `packages/verification-core/src/vgo_verify/bootstrap_doctor_runtime.py`
- Modify: `packages/installer-core/src/vgo_installer/materializer.py`
- Modify: `packages/installer-core/src/vgo_installer/ledger_service.py` if receipt ownership changes

- [ ] **Step 1: Write failing tests for MCP truth separation**

Add cases where:
- `scrapling` exists on PATH but is not yet host-visible in the relevant active surface
- `claude-flow` exists on PATH but still requires host registration/activation semantics
- `github`, `context7`, or `serena` remain pending because host-native registration is unavailable

Require the receipt and doctor/report output to distinguish "tool present" from "host ready".

- [ ] **Step 2: Run the targeted MCP tests and verify RED**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_mcp_auto_provision.py \
  tests/runtime_neutral/test_bootstrap_doctor.py -q
```

Expected:
- failures showing the current `ready` meaning is too broad

- [ ] **Step 3: Implement a stricter MCP state model**

Adjust receipt generation so statuses communicate host truth, for example by separating:
- host-native pending
- host-visible ready
- local tool present but not host-registered
- attempt failed
- not attempted

### Task 4: Verify the end-to-end install/check language against a real Codex target

**Files:**
- Modify as needed based on failing verification
- Test/verify against: real or simulated Codex target fixtures

- [ ] **Step 1: Run the full targeted verification matrix**

Run:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_mcp_auto_provision.py \
  tests/runtime_neutral/test_bootstrap_doctor.py \
  tests/unit/test_vgo_cli_commands.py \
  tests/unit/test_installer_ledger_service.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q
```

Expected:
- all tests pass

- [ ] **Step 2: Perform a real-host manual spot check**

On a real Codex root, verify:
- `$vibe` host-ready is only reported when the active host surface is complete
- partial MCP state is rendered as partial MCP state
- no overall wording implies "everything installed" when MCPs still need host follow-up

## Ownership Boundaries

- Install/report pipeline:
  - `apps/vgo-cli/src/vgo_cli/commands.py`
  - `apps/vgo-cli/src/vgo_cli/install_support.py`
  - `apps/vgo-cli/src/vgo_cli/output.py`
  - `apps/vgo-cli/src/vgo_cli/mcp_provision.py`
- Host truth surfaces:
  - `packages/installer-core/src/vgo_installer/host_closure.py`
  - `packages/installer-core/src/vgo_installer/materializer.py`
  - `packages/installer-core/src/vgo_installer/ledger_service.py`
- Verification:
  - `packages/verification-core/src/vgo_verify/bootstrap_doctor_runtime.py`
  - `tests/runtime_neutral/test_mcp_auto_provision.py`
  - `tests/runtime_neutral/test_bootstrap_doctor.py`
  - `tests/runtime_neutral/test_installed_runtime_scripts.py`
  - `tests/unit/test_vgo_cli_commands.py`
  - `tests/unit/test_installer_ledger_service.py`

## Verification Commands

```bash
python3 -m pytest \
  tests/runtime_neutral/test_mcp_auto_provision.py \
  tests/runtime_neutral/test_bootstrap_doctor.py \
  tests/unit/test_vgo_cli_commands.py \
  tests/unit/test_installer_ledger_service.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q
```

## Delivery Acceptance Plan

- Accept only if the targeted test suite passes.
- Accept only if `codex` install reporting can separately answer:
  - is the runtime installed locally?
  - is `$vibe` host-ready?
  - which MCPs are actually host-ready?
  - which MCPs still require follow-up?
- Accept only if no install/check surface uses wording that suggests full MCP installation when only local CLIs were installed.

## Completion Language Rules

- Do not say "安装完成" without immediately specifying whether that means local payload only or `$vibe` host-ready.
- Do not say an MCP is ready unless the host-active-surface evidence supports it.
- Report remaining manual follow-up as a separate section, not as a footnote hidden behind success language.

## Rollback Rules

- If the stricter truth model breaks unrelated host flows, stop and isolate whether the failure is in shared reporting vocabulary or host-specific surface detection.
- Roll back only the new truth-model code paths, not unrelated install/freshness/runtime changes already present in the worktree.

## Phase Cleanup Expectations

- Leave behind the requirement doc, the execution plan, updated receipts/tests/code, and explicit verification evidence.
- Do not delete or rewrite unrelated planning docs or dirty worktree files.
