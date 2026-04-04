# 2026-04-03 Adapter Registry Query Semantic Delegation Plan

## Goal

Make `adapter_registry_query.py` a thinner facade by moving bootstrap host catalog and target-root owner semantics into installer-core adapter registry helpers, leaving only argument parsing and output formatting in the script.

## Internal Grade

XL, executed serially for this microphase because the query script feeds bootstrap and check surfaces and must remain behaviorally identical.

## Frozen Scope

- Add bootstrap host catalog and target-root owner helpers to installer-core adapter registry.
- Refactor `scripts/common/adapter_registry_query.py` to delegate to those helpers.
- Update focused tests for the thinner query boundary.
- Run focused verification and then full regression.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Add the shared semantic helpers in installer-core adapter registry.
3. Remove local bootstrap and target-root owner logic from `adapter_registry_query.py` and delegate to installer-core.
4. Update focused architecture and behavior tests.
5. Run focused verification, then full regression and `git diff --check`.

## Verification Commands

- `python3 -m py_compile packages/installer-core/src/vgo_installer/adapter_registry.py scripts/common/adapter_registry_query.py`
- `python3 -m pytest tests/integration/test_adapter_registry_query_delegation.py tests/integration/test_bootstrap_host_catalog_shared_contract.py tests/integration/test_cli_installer_core_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
