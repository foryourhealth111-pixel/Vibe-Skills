# 2026-04-03 PowerShell Wrapper Host Validation Dedupe Plan

## Goal

Make PowerShell wrapper host validation a shared contract by removing wrapper-local `ValidateSet` host catalogs and delegating host normalization to `Resolve-VgoHostId`.

## Internal Grade

XL, executed serially for this microphase because the affected wrappers share the same validation concern and must be verified together.

## Frozen Scope

- Refactor `install.ps1`, `check.ps1`, and `uninstall.ps1` to remove wrapper-local `ValidateSet` host catalogs.
- Ensure each wrapper validates `HostId` through the shared governance helper.
- Add focused tests for delegation shape and invalid-host behavior.
- Run focused verification, then full regression.

## Implementation Steps

1. Freeze the wrapper-host-validation scope in a dedicated requirement/plan pair.
2. Refactor the three PowerShell wrappers so `HostId` is a plain string parameter with default `codex`, then normalize it through `Resolve-VgoHostId`.
3. Add focused integration/runtime coverage for wrapper delegation and invalid-host failure.
4. Run parser checks, focused wrapper tests, and the full regression suite.

## Verification Commands

- `pwsh -NoProfile -Command '& { [void][System.Management.Automation.Language.Parser]::ParseFile("install.ps1", [ref]$null, [ref]$null); [void][System.Management.Automation.Language.Parser]::ParseFile("check.ps1", [ref]$null, [ref]$null); [void][System.Management.Automation.Language.Parser]::ParseFile("uninstall.ps1", [ref]$null, [ref]$null) }'`
- `python3 -m pytest tests/integration/test_powershell_wrapper_host_validation_dedupe.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`

## Rollback Rule

If removing `ValidateSet` changes valid-host behavior, breaks default `codex` handling, or defers invalid-host failures too far downstream, revert the specific wrapper cut and restore the previous validation surface before proceeding.
