# 2026-04-03 Contracts Adapter Registry Support Extraction Plan

## Goal

Create a neutral adapter-registry support layer in contracts so `adapter-sdk` and `installer-core` share one low-level registry truth without introducing a new direct dependency between those packages.

## Internal Grade

XL, executed serially for this microphase because the change crosses package boundaries and must preserve both architecture direction and existing runtime behavior.

## Frozen Scope

- Add `vgo_contracts.adapter_registry_support` for registry path/load/normalize/raw-entry support.
- Refactor `installer-core` adapter registry helpers to consume the shared support layer while keeping their enriched public API stable.
- Refactor `adapter-sdk` descriptor loading to consume the shared support layer.
- Add or update focused tests for the new ownership boundary.
- Run focused verification and then full regression.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Add the contracts-owned adapter registry support module.
3. Update `installer-core` adapter registry helpers to delegate low-level semantics to contracts support.
4. Update `adapter-sdk` descriptor loading to delegate low-level semantics to contracts support.
5. Update focused unit/integration tests to lock the neutral shared boundary.
6. Run focused verification, then full regression and `git diff --check`.

## Verification Commands

- `python3 -m py_compile packages/contracts/src/vgo_contracts/adapter_registry_support.py packages/installer-core/src/vgo_installer/adapter_registry.py packages/adapter-sdk/src/vgo_adapters/descriptor_loader.py`
- `python3 -m pytest tests/unit/test_adapter_sdk.py tests/unit/test_adapter_registry_support.py tests/integration/test_adapter_sdk_registry_cutover.py tests/integration/test_cli_installer_core_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
