# Contributor Default Runbooks

> Baseline: 2026-03-13  
> Scope: a safe, compressed “where do I start” path for contributors. Keep it additive and evidence-driven.

## Start Here (Compressed Entry)

1. `README.md`
2. `docs/README.md`
3. `docs/status/non-regression-proof-bundle.md` (what “no regression” means here)
4. `scripts/verify/gate-family-index.md` (which gates exist and how they group)
5. This document

## Default Contributor Workflow

### Step 1: Pick The Right Surface

This repository is a Tier-1 official runtime plus a growing universalization governance layer.

Rules of thumb:

- If you are not sure where your change belongs, start by adding docs or a verify gate.
- Do not rewrite routing authority for universalization convenience.

### Step 2: Minimal Proof Before You Open a PR

Run the router smoke + router contract gates.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-contract-gate.ps1
```

### Step 3: If You Touched Governance Entry Or Family Indexing

Run the entry compression and family convergence gates.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-governance-entry-compression-gate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-wave125-gate-family-convergence-gate.ps1
```

## Frozen Zones (Until Explicit Proof)

Do not touch these “control plane” surfaces in an entry-compression batch:

- `scripts/router/**`
- `install.ps1`, `check.ps1`, `install.sh`, `check.sh`
- `config/version-governance.json`

If you must touch a frozen zone, require:

- a written reason (what contract is broken)
- a replayable proof (which gate detects it)
- a rollback plan

