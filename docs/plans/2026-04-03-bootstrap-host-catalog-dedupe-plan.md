# 2026-04-03 Bootstrap Host Catalog Dedupe Plan

## Goal

Make bootstrap host-selection presentation a shared contract so supported hosts and prompt text do not need to be updated independently in shell and PowerShell entrypoints.

## Internal Grade

XL, executed serially for this microphase because the shell and PowerShell entrypoints both depend on the same shared helper contract and must be validated together.

## Frozen Scope

- Add shared helper/query surfaces for bootstrap host choices and supported-host list rendering.
- Refactor shell bootstrap to consume the shared contract.
- Refactor PowerShell bootstrap to consume the shared contract.
- Add focused tests that lock the new delegation shape.
- Run focused verification, then full regression.

## Implementation Steps

1. Extend the shared helper/query layer so bootstrap host choices and supported-host list can be resolved from the adapter registry without shell- or PowerShell-local duplication.
2. Refactor `scripts/bootstrap/one-shot-setup.sh` to render the prompt and missing-host guidance from the shared query contract.
3. Refactor `scripts/bootstrap/one-shot-setup.ps1` to render the prompt and missing-host guidance from the shared helper contract.
4. Add focused integration coverage for the new delegation path.
5. Run parser/syntax checks, focused bootstrap tests, and the full regression suite.

## Verification Commands

- `python3 -m pytest tests/integration/test_bootstrap_entrypoint_registry_cutover.py -q`
- `pwsh -NoProfile -Command '& { [void][System.Management.Automation.Language.Parser]::ParseFile("scripts/bootstrap/one-shot-setup.ps1", [ref]$null, [ref]$null) }'`
- `python3 -m py_compile scripts/common/adapter_registry_query.py`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`

## Rollback Rule

If the shared host-catalog helper changes interactive choice order, breaks `claude` alias acceptance, or changes non-interactive bootstrap behavior beyond message-source dedupe, revert the specific helper/entrypoint cut and restore the previous surface before proceeding.
