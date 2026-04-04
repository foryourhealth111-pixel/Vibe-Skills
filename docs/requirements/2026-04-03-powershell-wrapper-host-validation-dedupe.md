# 2026-04-03 PowerShell Wrapper Host Validation Dedupe

## Goal

Remove hard-coded PowerShell wrapper host validation lists so `install.ps1`, `check.ps1`, and `uninstall.ps1` derive supported host validation from the shared governance helper contract instead of maintaining duplicate `ValidateSet` host catalogs.

## Scope

In scope:
- `install.ps1`
- `check.ps1`
- `uninstall.ps1`
- focused tests that prove PowerShell wrapper host validation delegates to shared helper logic

Out of scope:
- shell wrappers
- CLI argument schema changes
- adapter registry schema changes
- install/check/uninstall behavior changes beyond host validation source dedupe

## Acceptance Criteria

1. `install.ps1`, `check.ps1`, and `uninstall.ps1` no longer hard-code the supported host list via `ValidateSet`.
2. All three wrappers normalize and validate `HostId` via `Resolve-VgoHostId`.
3. The default host remains `codex`.
4. Invalid host values still fail before claiming wrapper success.
5. Existing install/check/uninstall behavior for valid hosts remains unchanged.
6. Verification includes focused wrapper tests plus a full regression sweep.

## Product Acceptance Checks

1. Valid hosts such as `codex` and `claude` still resolve correctly through the shared helper path.
2. Invalid hosts fail with the shared unsupported-host message rather than a wrapper-local list.
3. Full regression remains green after the cutover.
