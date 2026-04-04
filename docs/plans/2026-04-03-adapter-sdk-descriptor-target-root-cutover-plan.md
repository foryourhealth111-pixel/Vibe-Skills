# 2026-04-03 Adapter SDK Descriptor Target Root Cutover Plan

## Goal

Make `adapter-sdk` internally cohesive by letting target-root resolution consume only the adapter descriptor contract instead of re-reading raw adapter-registry payload.

## Internal Grade

XL, executed serially for this microphase because the change crosses contract and package boundaries and must preserve all existing host behaviors.

## Frozen Scope

- Enrich `AdapterDescriptor` with the target-root metadata needed by runtime resolution.
- Update `descriptor_loader.py` to map registry payload into the enriched descriptor contract.
- Refactor `target_root_resolver.py` to consume only descriptor fields.
- Update focused contract, unit, and integration tests to lock the new boundary.
- Run focused verification, then full regression and diff hygiene.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Extend the descriptor contract with explicit target-root env and kind fields.
3. Update adapter-sdk descriptor loading to populate the enriched contract from the registry.
4. Remove raw registry payload reloading from target-root resolution.
5. Update focused tests for contract shape, behavior preservation, and internal separation.
6. Run focused verification, full regression, and `git diff --check`.

## Verification Commands

- `python3 -m py_compile packages/contracts/src/vgo_contracts/adapter_descriptor.py packages/adapter-sdk/src/vgo_adapters/descriptor_loader.py packages/adapter-sdk/src/vgo_adapters/target_root_resolver.py`
- `python3 -m pytest tests/contract/test_adapter_descriptor_contract.py tests/unit/test_adapter_sdk.py tests/integration/test_adapter_sdk_registry_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
