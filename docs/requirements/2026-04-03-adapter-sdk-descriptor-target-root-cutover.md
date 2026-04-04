# 2026-04-03 Adapter SDK Descriptor Target Root Cutover

## Goal

Refactor `adapter-sdk` so default target-root resolution depends only on the adapter descriptor contract, eliminating the package-internal fallback that re-reads raw adapter-registry payload after descriptor loading.

## Scope

In scope:
- `packages/contracts/src/vgo_contracts/adapter_descriptor.py`
- `packages/adapter-sdk/src/vgo_adapters/descriptor_loader.py`
- `packages/adapter-sdk/src/vgo_adapters/target_root_resolver.py`
- focused contract, unit, and integration tests for the descriptor boundary

Out of scope:
- changing adapter registry schema
- changing adapter-sdk public API names
- changing installer-core enriched registry semantics
- changing CLI, wrapper, bootstrap, or runtime user flows

## Acceptance Criteria

1. `AdapterDescriptor` carries the target-root data needed by `adapter-sdk` runtime resolution.
2. `target_root_resolver.py` no longer reloads raw registry payload or imports descriptor-payload helpers.
3. `descriptor_loader.py` remains the only `adapter-sdk` module that translates raw registry payload into the descriptor contract.
4. Existing target-root behavior remains unchanged for env override and home-relative fallback paths.
5. Focused tests lock the new descriptor contract and the adapter-sdk internal ownership boundary.
6. Verification includes focused checks, full regression, and diff hygiene.
