# 2026-04-03 Adapter Registry Query Delegation

## Goal

Remove duplicated registry-loading logic from `scripts/common/adapter_registry_query.py` so the query helper delegates authoritative registry and adapter resolution to `packages/installer-core/src/vgo_installer/adapter_registry.py`.

## Scope

In scope:
- `scripts/common/adapter_registry_query.py`
- focused tests that prove the query helper delegates core registry loading to installer-core

Out of scope:
- changing query CLI flags or output shapes
- changing bootstrap host catalog semantics
- changing target-root owner guard behavior
- changing installer-core registry contract itself

## Acceptance Criteria

1. `adapter_registry_query.py` no longer defines its own registry-loading and adapter-resolution implementation.
2. Registry path resolution, registry loading, and adapter resolution are delegated to `vgo_installer.adapter_registry`.
3. Existing query flags and outputs remain unchanged.
4. Bootstrap host catalog behavior remains unchanged.
5. Target-root owner resolution behavior remains unchanged.
6. Verification includes focused query tests and a full regression sweep.
