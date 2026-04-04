# 2026-04-03 CLI Host Registry Delegation

## Goal

Remove duplicated adapter registry loading and host normalization logic from `apps/vgo-cli/src/vgo_cli/hosts.py` so the CLI host facade delegates authoritative host resolution to `packages/installer-core/src/vgo_installer/adapter_registry.py`.

## Scope

In scope:
- `apps/vgo-cli/src/vgo_cli/hosts.py`
- focused CLI host tests that lock the new delegation boundary
- the existing integration cutover test for CLI host registry ownership

Out of scope:
- changing CLI flags or command flow
- changing adapter registry schema
- changing target-root mismatch semantics or user-facing CLI error intent
- changing install/uninstall/router execution paths

## Acceptance Criteria

1. `vgo_cli.hosts` no longer performs authoritative registry loading through `vgo_cli.repo.load_adapter_registry`.
2. Authoritative adapter and host resolution are delegated to installer-core registry helpers.
3. `vgo_cli.hosts` keeps only CLI-specific behavior: default target-root resolution, target-root signature matching, and `CliError` presentation.
4. Alias handling, default host fallback, install mode lookup, and target-root defaults remain behaviorally unchanged.
5. Existing Cursor/OpenCode mismatch guard messages remain intact.
6. Verification includes focused CLI host tests plus the full regression suite.
