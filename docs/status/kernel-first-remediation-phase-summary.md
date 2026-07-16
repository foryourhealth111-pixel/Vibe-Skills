# Kernel-First Remediation Phase Summary

## What authority moved

The live runtime meaning is now narrower and more honest.

- task meaning moved into kernel-owned Python modules
- router output was reduced to candidate discovery and compatibility shaping
- skill-use proof now depends on work results and evidence, not route-era mirrors
- PowerShell wrappers no longer rebuild runtime truth or user-facing summary meaning
- starter-set truth is now published from packaging inventory instead of raw bundled folder count

## What stayed compatibility-only

Some older surfaces still remain readable, but they are no longer allowed to act like first truth.

- route-era routing mirrors stay readable only as compatibility projections
- PowerShell still owns launch, receipts, shell-native checks, and host-facing bridge work
- the large repo-owned bundled tree still exists on disk, but it is now documented as reference or migration material unless packaging marks it live
- dated zero-route-authority governance records were moved into archive rather than kept as current entry docs

## What was deferred

This pass did not force every possible cleanup into one change.

- no broad physical move of the remaining repo-owned bundled skill corpus
- only the first bounded governance-history batch was archived
- repo cleanliness is still expected to fail until the current remediation work is committed
- the largest remaining stability risk is parallel install or check interference under `pytest -n auto`, not the original kernel-first blockers

Current closeout status:

- The original false blocker from local `pwsh` script policy is fixed. Runtime-neutral tests that directly invoke PowerShell entrypoints now pass `ExecutionPolicy Bypass` and the shell wrappers preserve that behavior.
- The local canonical smoke fixture was refreshed and now contains the newer kernel-first artifacts needed by `vibe-canonical-entry-truth-gate.ps1`, including `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json`.
- `scripts/verify/vibe-repo-cleanliness-gate.ps1` still correctly reports the repo as not clean while the remediation work remains uncommitted. On the latest rerun it reported `Dirty paths: 168`.
- A wide parallel slice `py -3 -m pytest tests/unit tests/runtime_neutral -x -n auto` no longer reproduces the original Task 8 blockers. The remaining red state comes from install/check tests that pass when rerun individually, which points to parallel interference rather than the kernel-first remediation defects addressed here.

## Which proof commands passed

Focused proof that passed during this phase:

- `py -3 -m pytest tests/unit/test_canonical_vibe_entry_launcher.py tests/runtime_neutral/test_governed_runtime_bridge.py -q`
  observed result: `99 passed`
- `py -3 -m pytest tests/runtime_neutral/test_retired_agent_execution_surfaces.py -q`
  observed result in this checkout: `5 passed`
- `py -3 -m pytest tests/runtime_neutral/test_workflow_acceptance_runner.py -q`
  observed result in this checkout: `6 passed`; direct fixture replay keeps L at `PASS` and XL at `MANUAL_REVIEW_REQUIRED`
- `py -3 -m pytest tests/unit -q`
  observed result: `497 passed, 1 warning`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-governed-runtime-contract-gate.ps1`
  observed result in this checkout: `gate_passed = True`, `98 assertions`, `0 failures`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-canonical-entry-truth-gate.ps1 -SessionRoot (Resolve-Path '.tmp\canonical-local-smoke\vibe\runs\canon-local-smoke') -WriteArtifacts`
  observed result: all printed assertions passed
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-runtime-execution-proof-gate.ps1`
  observed result in this checkout: `gate_passed = True`, `39 assertions`, `0 failures`; scope is the approved module plan, Agent handoff, and returned module-result contract
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-release-truth-consistency-gate.ps1`
  observed result: all printed assertions passed
- `py -3 -m pytest tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py::DiscoverableWrapperHostVisibilityTests::test_install_ledger_exposes_host_visible_discoverable_entries_for_supported_hosts tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py::DiscoverableWrapperHostVisibilityTests::test_shell_check_accepts_supported_host_discoverable_surfaces tests/runtime_neutral/test_installed_runtime_uninstall.py::InstalledRuntimeUninstallTests::test_codex_uninstall_removes_issue_167_governed_runtime_dependency_surfaces -q`
  observed result: `3 passed`
- `git diff --check`
  observed result: no whitespace or conflict-marker errors; only CRLF normalization warnings from Git
- `py -3 -m pytest -q --maxfail=40`
  observed result in this checkout: `1254 passed, 6 skipped`

## Next step

The remaining release work is operational:

- update both managed live installs from this checkout and prove source/receipt parity
- run fresh Codex black-box tasks through requirement choice, plan approval, Agent work, canonical result re-entry, acceptance, and cleanup
- repeat the research-document and XL composite scenarios in new tasks before making a final completion claim
