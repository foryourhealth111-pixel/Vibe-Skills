# 2026-04-03 CLI Target Root Delegation Plan

## Goal

Make `vgo-cli` a thinner bridge by delegating registry-backed target-root semantics to `installer-core.adapter_registry`.

## Internal Grade

XL, executed serially for this microphase because the change crosses CLI and core-package boundaries and must preserve current install and preview behavior.

## Frozen Scope

- Add installer-core helpers for target-root spec resolution, default target-root resolution, and target-root host matching.
- Refactor CLI host helpers to delegate those semantics to installer-core.
- Update focused unit and integration tests to lock the new ownership boundary.
- Run focused verification, then full regression and diff hygiene.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Extend `installer-core.adapter_registry` with target-root semantic helpers.
3. Remove duplicated target-root interpretation logic from `vgo_cli.hosts`.
4. Update focused unit and integration tests for the new boundary.
5. Run focused verification, full regression, and `git diff --check`.

## Verification Commands

- `python3 -m py_compile packages/installer-core/src/vgo_installer/adapter_registry.py apps/vgo-cli/src/vgo_cli/hosts.py`
- `python3 -m pytest tests/unit/test_vgo_cli_infra_split.py tests/unit/test_installer_adapter_registry_target_roots.py tests/integration/test_cli_host_registry_cutover.py tests/integration/test_cli_installer_core_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
