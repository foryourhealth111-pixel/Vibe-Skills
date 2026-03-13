# Operator Default Runbooks

> Baseline: 2026-03-13  
> Scope: human entry compression for maintainers/operators. This is a runbook, not a new governance structure.

## Start Here (Compressed Entry)

1. `README.md`
2. `docs/README.md`
3. `docs/status/non-regression-proof-bundle.md` (closure contract)
4. `scripts/verify/gate-family-index.md` (gate families + typical run order)
5. This document

## Default Operator Modes

### Mode A: Quick Health (Before Doing Anything Risky)

Run the fast router and contract checks first.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-contract-gate.ps1
```

### Mode B: Closure / Release Evidence (Zero Regression Budget)

The authoritative closure contract is `docs/status/non-regression-proof-bundle.md`.
If you do not have time to read it fully, use `scripts/verify/gate-family-index.md` to run the typical closure order.

Suggested starting sequence:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-version-packaging-gate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-repo-cleanliness-gate.ps1
```

### Mode C: Governance-Family Convergence (Entry Compression Only)

This is documentation-first. Do not delete gates in this phase.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-governance-entry-compression-gate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-wave125-gate-family-convergence-gate.ps1
```

## Hard Boundaries (Operator Discipline)

- Do not invent a second “docs/governance/*” tree while the repo already uses `scripts/verify/gate-family-index.md` as the family index.
- Treat verify gates as the evidence-running surface; docs are the contract and interpretation.
- When in doubt: prefer additive docs and new gates over mass refactors.

