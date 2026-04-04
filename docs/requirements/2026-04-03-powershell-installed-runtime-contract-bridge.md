# 2026-04-03 PowerShell Installed Runtime Contract Bridge

## Goal

Make PowerShell installed-runtime helpers consume contract-owned defaults instead of inlining a second installed-runtime semantic owner.

## Scope

In scope:
- `scripts/common/runtime_contracts.py`
- `scripts/common/vibe-governance-helpers.ps1`
- `scripts/verify/vibe-official-runtime-baseline-gate.ps1`
- focused unit and integration tests

Out of scope:
- changing installed-runtime governance schema
- changing CLI install behavior
- changing runtime-neutral gate implementations

## Acceptance Criteria

1. PowerShell installed-runtime config loading no longer hardcodes the default installed-runtime path bundle inline.
2. `scripts/common/runtime_contracts.py` exposes a machine-readable installed-runtime config bridge for wrapper consumers.
3. Official runtime baseline verification consumes effective runtime gate paths from runtime config instead of hardcoding the frontmatter gate path.
4. Existing governance merge behavior remains unchanged.
5. Focused tests lock the new contract boundary.
