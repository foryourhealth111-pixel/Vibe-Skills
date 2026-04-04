# 2026-04-03 Contracts Adapter Registry Support Extraction

## Goal

Extract low-level adapter registry path, load, host-normalization, and raw entry-resolution semantics into the contracts package so `adapter-sdk` and `installer-core` can share a neutral registry support layer without introducing a new direct package coupling.

## Scope

In scope:
- `packages/contracts/src/vgo_contracts/adapter_registry_support.py`
- `packages/contracts/src/vgo_contracts/__init__.py`
- `packages/installer-core/src/vgo_installer/adapter_registry.py`
- `packages/adapter-sdk/src/vgo_adapters/descriptor_loader.py`
- focused tests for the new shared boundary

Out of scope:
- changing adapter registry schema
- changing enriched installer-core adapter payload semantics
- changing adapter-sdk public API names
- changing CLI, bootstrap, or runtime UX

## Acceptance Criteria

1. Low-level adapter-registry path/load/normalize/raw-entry semantics live in a contracts-owned shared module.
2. `adapter-sdk` no longer implements its own registry path/load/alias normalization logic.
3. `installer-core` no longer implements its own low-level registry path/load/alias normalization logic.
4. `adapter-sdk` does not gain a direct dependency on `installer-core`.
5. Existing public behaviors and outputs remain unchanged.
6. Focused tests lock both the shared support layer and the new dependency direction.
7. Verification includes focused tests and a full regression sweep.
