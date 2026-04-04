# GSD-Lite Overlay Integration (VCO)

## Purpose

Integrate selected `get-shit-done` methodology into VCO as a lightweight planning overlay without introducing a second orchestrator.

This overlay is explicitly designed to:
- Improve L/XL planning stability and handoff quality
- Preserve VCO as the single routing authority
- Avoid dual command surfaces and dual state trees

## Non-Redundancy Boundaries

1. **Single entrypoint**: `/vibe` remains the only routing entrypoint.
2. **Post-route only**: overlay runs after grade/task/pack are decided.
3. **No `/gsd:*` workflow cloning**: do not introduce alternate top-level lifecycle commands.
4. **No second source-of-truth**: overlay artifacts are advisory metadata under VCO paths.

## Config

Primary policy file:
- `config/gsd-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/gsd-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow` (default: `planning`)
- `grade_allow` (default: `L`, `XL`)
- `brownfield_context` (optional context snapshot)
- `assumption_gate` (pre-plan assumption check + confirm scope)
- `wave_contract` (XL wave metadata)
- `profiles` (quality/balanced/budget toggles)

## Hook Points

### 1) think protocol

File:
- `protocols/think.md`

Hook:
- `B5: GSD-Lite Preflight Hook`

Behavior:
- Optional brownfield snapshot
- Assumption preflight artifact
- Mode-aware confirm policy
- Advisory fallback on hook failure

### 2) team protocol

File:
- `protocols/team.md`

Hook:
- `GSD-Lite Wave Contract Hook`

Behavior:
- Generates wave contract metadata (`waves.json`)
- Parallel-in-wave, sequential-by-dependency
- Falls back to standard Option A/B orchestration if generation fails

## Rollout Control

Script:
- `scripts/governance/set-gsd-overlay-rollout.ps1`

Stages:
- `off`
- `shadow`
- `soft-lxl-planning`
- `strict-lxl-planning`

Examples:

```powershell
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage shadow
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage soft-lxl-planning
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage strict-lxl-planning
```

## Verification

Use legacy-named packaging gate to guarantee retired bundled copies stay absent:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

Overlay failures are non-fatal by default:
- Missing/invalid overlay config -> bypass overlay
- Brownfield snapshot failure -> continue planning flow
- Assumption hook failure -> continue standard B1-B4
- Wave contract failure -> revert to normal XL orchestration

Strict-mode escalation is allowed only when explicitly configured by policy.
