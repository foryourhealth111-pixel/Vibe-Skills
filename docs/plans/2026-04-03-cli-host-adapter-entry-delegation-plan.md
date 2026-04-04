# 2026-04-03 CLI Host Adapter Entry Delegation Plan

## Goal

Tighten the CLI host boundary by moving adapter entry enumeration into installer-core, leaving `vgo_cli.hosts` with only CLI-specific target-root semantics and error mapping.

## Internal Grade

XL, executed serially for this microphase because the host layer sits on install and uninstall command paths and the delegation must remain behaviorally identical.

## Frozen Scope

- Add a normalized adapter-entry enumeration helper to installer-core adapter registry.
- Refactor `vgo_cli.hosts` to consume that helper instead of traversing the registry payload directly.
- Update focused tests for the tighter boundary.
- Run focused verification and then full regression.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Add the adapter-entry enumeration helper in installer-core.
3. Remove local adapter-entry map construction from `vgo_cli.hosts` and delegate to installer-core.
4. Update focused architecture tests to lock the new boundary.
5. Run focused verification, then full regression and `git diff --check`.

## Verification Commands

- `python3 -m py_compile packages/installer-core/src/vgo_installer/adapter_registry.py apps/vgo-cli/src/vgo_cli/hosts.py`
- `python3 -m pytest tests/unit/test_vgo_cli_infra_split.py tests/integration/test_cli_host_registry_cutover.py tests/integration/test_cli_installer_core_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
