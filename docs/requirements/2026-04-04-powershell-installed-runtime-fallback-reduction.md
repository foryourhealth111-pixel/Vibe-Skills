# 2026-04-04 PowerShell Installed Runtime Fallback Reduction

## Goal

Reduce `scripts/common/vibe-governance-helpers.ps1` from owning a second installed-runtime semantic bundle to owning only a bounded emergency fallback shape.

## Scope

In scope:
- `scripts/common/vibe-governance-helpers.ps1`
- focused tests for PowerShell installed-runtime bridge and runtime-entrypoint helper behavior
- any small bridge-facing assertions needed to preserve compatibility guarantees

Out of scope:
- changing the package-owned installed-runtime contract in `packages/contracts`
- changing effective governed runtime config in `config/version-governance.json`
- broad runtime behavior changes

## Acceptance Criteria

1. PowerShell helper fallback no longer presents itself as a full semantic peer to the installed-runtime contract.
2. `Get-VgoRuntimeEntrypointPath` resolves from effective runtime config when available and only falls back when effective config is absent.
3. PowerShell fallback remains usable as a bounded emergency compatibility path when the Python bridge is unavailable.
4. Focused tests prove that contracts remain the primary owner and that fallback behavior still preserves runtime-entrypoint resolution.
