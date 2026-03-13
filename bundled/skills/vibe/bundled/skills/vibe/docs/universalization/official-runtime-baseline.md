# Official Runtime Baseline

> Baseline frozen on: 2026-03-13  
> Scope: protect the current official `vco-skills-codex` runtime from silent regression during universalization.
>
> This is a runtime baseline, not a roadmap. It is intentionally conservative.

## Purpose

This document defines the minimum official-runtime truth that all universalization waves must preserve.

It is not a migration dream-state.
It is the current reference runtime that already has:

- governed install entrypoints
- governed check entrypoints
- governed router ownership
- governed version packaging
- governed runtime freshness and coherence gates

If later work weakens any of these surfaces, the work is considered regression even if new universalization assets are added.

## Tier-1 Official Runtime

The current Tier-1 official runtime remains the existing repository runtime rooted in:

- `install.ps1`
- `install.sh`
- `check.ps1`
- `check.sh`
- `scripts/bootstrap/**`
- `scripts/router/**`
- `config/version-governance.json`

During early universalization phases, these surfaces are frozen by governance and may only receive bug fixes or verification-safe hardening.
Any broader migration on these surfaces must be declared in
`config/official-runtime-main-chain-policy.json` as a file-scoped, plan-backed exception window.

## What "Official Runtime" Means (And Does Not Mean)

Official runtime baseline means:

- The canonical repo (this repository) contains the authoritative install/check surfaces and governance contract.
- `install.ps1` can stage an installed runtime closure under a host-managed Codex home (default `~/.codex`) without rewriting host state.
- `check.ps1` can validate that installed closure and run the governed runtime gates.

Official runtime baseline does not mean:

- "One-shot installs all host dependencies." Some dependencies are host-managed or optional (`npm`, external CLIs, MCP servers, IDE-specific wiring).
- "All platforms are equally authoritative." Windows PowerShell is the current authoritative lane; Linux/macOS depends on `pwsh`.
- "Offline-only by default." Offline installs are supported, but may require explicit flags and/or prior vendoring.

## Canonical Runtime Authority

The following assets remain authoritative for the official runtime:

| Surface | Authority |
| --- | --- |
| Install orchestration | `install.ps1`, `install.sh` |
| Health / doctor entry | `check.ps1`, `check.sh` |
| Router ownership | `scripts/router/resolve-pack-route.ps1` |
| Version and packaging truth | `config/version-governance.json` |
| Installed runtime closure and coherence | `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`, `scripts/verify/vibe-bom-frontmatter-gate.ps1`, `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1` |

## Baseline Command Set

The minimum non-regression command set is:

```powershell
git diff --check
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-contract-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-version-consistency-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-version-packaging-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-bom-frontmatter-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1
```

`check.ps1 -Profile full -Deep` remains an optional stronger lane when host prerequisites are present.

## Runtime Truth Boundaries

The baseline intentionally preserves these truths:

- The canonical router remains the local authority (`scripts/router/resolve-pack-route.ps1`).
- Windows remains the current authoritative lane (PowerShell-based gates are the reference truth).
- Linux/macOS can be strong, but `pwsh` absence is still a degraded state (warn-and-skip for authoritative runtime gates).
- Host plugins and some MCP surfaces remain host-managed rather than repo-closed.
- Provider-assisted routing intelligence is allowed, but canonical router ownership stays local.

## What Counts As Regression

The following are regressions against baseline:

1. weakening install/check closure of the official runtime
2. introducing a second router or bypassing router authority
3. changing version governance semantics without explicit re-baselining
4. claiming cross-host or cross-platform parity not backed by proof
5. silently converting degraded states into implicit "supported" states

## Required Evidence Bundle

The frozen evidence bundle for this baseline is tracked in:

- `references/proof-bundles/official-runtime-baseline/README.md`
- `references/proof-bundles/official-runtime-baseline/baseline-manifest.json`

The bundle is verified by:

- `scripts/verify/vibe-official-runtime-baseline-gate.ps1`

## Gate Semantics (Conservative)

`vibe-official-runtime-baseline-gate.ps1` is a conservative, proof-oriented gate:

- It verifies the presence and basic integrity of the baseline documents and manifest.
- It verifies that `config/version-governance.json` exposes the official runtime contract (`runtime.installed_runtime.*`) and that its required runtime markers exist in the repo.
- It verifies that `install.ps1` and `check.ps1` still reference the governed runtime gates (string-level evidence).
- It may inspect the installed runtime receipt if present (warning only if absent).

It does not:

- install dependencies
- rewrite runtime state
- claim full host readiness
