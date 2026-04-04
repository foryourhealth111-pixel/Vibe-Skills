# 2026-04-04 CLI Runtime Entrypoint Contract Delegation

## Goal

Make the CLI `runtime` surface consume the governed runtime entrypoint from the effective installed-runtime contract instead of hardcoding a second runtime entrypoint owner in `main.py`.

## Scope

In scope:
- `apps/vgo-cli/src/vgo_cli/main.py`
- `apps/vgo-cli/src/vgo_cli/commands.py`
- `apps/vgo-cli/src/vgo_cli/repo.py`
- `packages/contracts/src/vgo_contracts/installed_runtime_contract.py`
- `scripts/common/runtime_contracts.py`
- `scripts/common/vibe-governance-helpers.ps1`
- focused unit and integration tests for runtime dispatch

Out of scope:
- changing runtime execution semantics
- changing shell runtime fallback behavior
- changing governed runtime stage scripts themselves

## Acceptance Criteria

1. The CLI `runtime` command no longer hardcodes `scripts/runtime/invoke-vibe-runtime.ps1` in `main.py`.
2. PowerShell runtime dispatch resolves the entrypoint from the effective runtime contract.
3. The runtime contract and PowerShell fallback bridge declare the same runtime entrypoint default.
4. Focused tests lock the ownership boundary and dispatch behavior.
