# 2026-04-03 Adapter Registry Query Delegation Plan

## Goal

Make `adapter_registry_query.py` a thin query facade by delegating registry and adapter resolution to installer-core, leaving only query-specific formatting and host-catalog derivation in the script.

## Internal Grade

XL, executed serially for this microphase because the helper is consumed by shell bootstrap/check flows and must remain behaviorally stable.

## Frozen Scope

- Refactor `scripts/common/adapter_registry_query.py` to import and delegate to installer-core registry helpers.
- Add focused tests proving delegation shape and output stability.
- Run focused verification and then the full regression suite.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Replace local registry-loading logic in `adapter_registry_query.py` with delegation to `vgo_installer.adapter_registry`.
3. Keep query-specific functions local: property lookup, bootstrap choice formatting, target-root owner lookup, and output formatting.
4. Add focused tests to lock the new delegation shape.
5. Run py_compile, focused tests, and full regression.

## Verification Commands

- `python3 -m py_compile scripts/common/adapter_registry_query.py`
- `python3 -m pytest tests/integration/test_adapter_registry_query_delegation.py tests/integration/test_bootstrap_host_catalog_shared_contract.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
