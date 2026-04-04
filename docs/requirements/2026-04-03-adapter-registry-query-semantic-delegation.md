# 2026-04-03 Adapter Registry Query Semantic Delegation

## Goal

Remove the remaining bootstrap host catalog and target-root owner semantics from `scripts/common/adapter_registry_query.py` so installer-core adapter registry helpers own those behaviors as part of the authoritative registry surface.

## Scope

In scope:
- `packages/installer-core/src/vgo_installer/adapter_registry.py`
- `scripts/common/adapter_registry_query.py`
- focused tests that prove the query script delegates bootstrap catalog and target-root owner behavior to installer-core

Out of scope:
- changing query CLI flags or output shapes
- changing PowerShell governance helper behavior
- changing bootstrap entrypoint UX
- changing adapter registry schema

## Acceptance Criteria

1. `adapter_registry_query.py` no longer implements bootstrap host catalog derivation locally.
2. `adapter_registry_query.py` no longer implements target-root owner resolution locally.
3. Installer-core adapter registry exposes shared helpers for those semantics.
4. Query outputs remain unchanged.
5. Focused tests lock the thinner query-script boundary.
6. Verification includes focused tests and a full regression sweep.
