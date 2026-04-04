# System Design Overlay Integration (system-design-primer x VCO)

## Purpose

Integrate `donnemartin/system-design-primer` as a **post-route architecture advisory overlay** without introducing a second router or replacing existing pack-level selection.

This overlay focuses on architecture-quality completeness for `planning/research/review`:
- architecture intent signals (scalability, latency, consistency, partitioning, failover, observability)
- coverage dimensions (requirements, NFR, capacity, consistency/availability, caching, partitioning/replication, async/backpressure, recovery, observability, cost)
- mode-gated confirmation guidance when architecture completeness is weak or risky

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the only control plane.
2. **Advice-only rollout**: no mutation of `selected.pack_id` or `selected.skill`.
3. **Architecture scope only**:
   - OpenSpec handles `what/why/change governance`.
   - System-design overlay handles `how-to-scale/how-to-fail-safely` coverage.
4. **No runtime hard dependency**: methodology-based overlay, no required external binary.
5. **Route invariance first**: strict mode escalates only advice metadata (`confirm_required`) and preserves route assignment.

## Config

Primary policy:
- `config/system-design-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/system-design-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `positive_keywords`, `negative_keywords`
- `coverage_dimensions`
- `thresholds`, `strict_confirm_scope`
- `artifact_contract`, `recommendations_by_dimension`

## Runtime Behavior

Router:
- `scripts/router/resolve-pack-route.ps1`

New output:
- `system_design_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: advisory + `confirm_recommended` under stronger architecture risk/coverage signals.
- `strict`: in strict scope, weak architecture coverage can be escalated to `confirm_required`.
- `off`: overlay disabled.

Current rollout remains **advice-first** and does not alter pack/skill assignment.

## Trigger Strategy

Signal score combines:
1. architecture keyword intent (`positive_keywords`)
2. architecture-dimension coverage score (`coverage_dimensions`)
3. suppress penalty (`negative_keywords`, primarily interview-only contexts)

Goal: trigger reliably for architecture design work while suppressing noisy interview-prep prompts.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-system-design-overlay-gate.ps1
```

Run legacy-named packaging gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

Run routing stability gate:

```powershell
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

## Failure Semantics

- missing policy -> bypass overlay advice
- outside scope -> no enforcement, keep routing unchanged
- low architecture signal -> advisory metadata only
- overlay parsing/runtime errors -> continue core VCO route path
