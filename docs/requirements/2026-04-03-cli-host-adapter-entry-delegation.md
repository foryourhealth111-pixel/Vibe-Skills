# 2026-04-03 CLI Host Adapter Entry Delegation

## Goal

Remove the remaining adapter-entry enumeration logic from `apps/vgo-cli/src/vgo_cli/hosts.py` so installer-core adapter registry helpers own both authoritative host resolution and adapter entry listing.

## Scope

In scope:
- `packages/installer-core/src/vgo_installer/adapter_registry.py`
- `apps/vgo-cli/src/vgo_cli/hosts.py`
- focused tests that prove `vgo_cli.hosts` delegates adapter entry enumeration to installer-core

Out of scope:
- changing CLI command flow
- changing adapter registry schema
- changing target-root mismatch behavior or message text
- changing install/uninstall payload semantics

## Acceptance Criteria

1. `vgo_cli.hosts` no longer builds adapter entry maps from raw registry payloads.
2. Installer-core adapter registry exposes a shared helper for normalized adapter entry enumeration.
3. `resolve_adapter` behavior remains unchanged.
4. CLI target-root guard behavior remains unchanged.
5. Focused tests prove the new delegation boundary.
6. Verification includes focused tests and a full regression sweep.
