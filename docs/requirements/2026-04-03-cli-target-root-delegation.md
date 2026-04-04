# 2026-04-03 CLI Target Root Delegation

## Goal

Remove CLI-owned target-root semantics by delegating default target-root resolution and target-root ownership matching to `installer-core.adapter_registry`.

## Scope

In scope:
- `apps/vgo-cli/src/vgo_cli/hosts.py`
- `packages/installer-core/src/vgo_installer/adapter_registry.py`
- focused unit and integration tests for the new ownership boundary

Out of scope:
- changing adapter registry schema
- changing host mismatch user-facing messages
- changing wrapper or bootstrap behavior
- changing adapter-sdk public APIs

## Acceptance Criteria

1. CLI no longer implements target-root signature matching logic inline.
2. CLI no longer implements default target-root resolution semantics inline.
3. `installer-core.adapter_registry` owns target-root spec, default-resolution, and matching semantics for registry-backed hosts.
4. Existing CLI behavior remains unchanged for env override, home-relative fallback, and mismatch detection.
5. Focused tests lock the new dependency direction and semantic owner.
6. Verification includes focused checks, full regression, and diff hygiene.
