# PR137 Discoverable Wrapper Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair PR `#137` so discoverable wrapper projection is real across the six supported hosts, discoverable-entry verification is truthful, and Linux/Windows checks agree on the same inventories.

**Architecture:** Keep the shared discoverable-entry config as the only public-entry truth, then generate host-visible wrappers by host surface type: command wrappers for command-menu hosts and skill wrappers for skill-menu hosts. Split install-ledger inventories so discoverable entries and host bridge launchers stop sharing one ambiguous path list.

**Tech Stack:** Python installer-core, Bash/PowerShell check scripts, JSON install ledger, unittest/pytest runtime-neutral tests

---

### Task 1: Lock the broken contract with failing tests

**Files:**
- Modify: `tests/unit/test_discoverable_wrappers.py`
- Modify: `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py`
- Modify: `tests/runtime_neutral/test_claude_preview_scaffold.py`
- Modify: `tests/runtime_neutral/test_windsurf_runtime_core.py`
- Modify: `tests/runtime_neutral/test_openclaw_runtime_core.py`

- [ ] Add a unit test proving skill-only hosts generate `skills/<entry>/SKILL.md` wrappers from the shared discoverable-entry contract.
- [ ] Add a runtime-neutral regression test proving that deleting only the specialist bridge launcher does not fail discoverable-entry validation.
- [ ] Update host install tests so `claude-code`, `windsurf`, and `openclaw` expect discoverable wrapper skills instead of asserting no wrapper surface exists.
- [ ] Run the targeted tests and confirm they fail against the current branch.

### Task 2: Implement real multi-host wrapper materialization

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/discoverable_wrappers.py`
- Modify: `packages/installer-core/src/vgo_installer/materializer.py`
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`

- [ ] Generate wrapper files by host surface type:
  `commands/*.md` for command-menu hosts and `skills/*/SKILL.md` for skill-menu hosts.
- [ ] Keep opencode dual command roots intact.
- [ ] Make installer failure explicit when a declared discoverable-entry surface yields zero materialized wrappers on a supported host.

### Task 3: Split discoverable-entry inventory from bridge-launcher inventory

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`
- Modify: `packages/installer-core/src/vgo_installer/ledger_service.py`
- Modify: `check.sh`
- Modify: `check.ps1`

- [ ] Record discoverable entry wrapper paths separately from host specialist bridge launchers.
- [ ] Derive `payload_summary.host_visible_entry_names` from discoverable entry inventory only.
- [ ] Make Bash and PowerShell discoverable-entry checks validate only discoverable entry paths.

### Task 4: Verify and push the repaired PR branch

**Files:**
- Inspect: touched tests and install ledger output

- [ ] Run targeted unit/runtime-neutral verification for the new wrapper and ledger contracts.
- [ ] Run a broader regression slice covering codex plus representative skill-only hosts.
- [ ] Review the final diff for cohesion and cross-platform consistency.
- [ ] Commit and push the repair to `feat/vibe-discoverable-entry`.
