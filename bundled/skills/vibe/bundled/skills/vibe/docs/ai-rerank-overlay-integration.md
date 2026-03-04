# AI Rerank Overlay Integration (B+ Recall-Safe Dual Stage)

## Purpose

Add a second-stage rerank overlay to improve ambiguous routing stability without reducing stage-1 recall.

This integration keeps VCO's deterministic pack scoring as the control plane and adds a constrained rerank layer only in ambiguity windows.

## Non-Redundancy Boundaries

1. **Stage-1 router remains authoritative**: pack scoring and candidate generation are unchanged.
2. **Top-K bounded rerank only**: rerank cannot introduce packs outside stage-1 Top-K when `require_candidate_in_top_k=true`.
3. **Task boundary preserved**: rerank suggestion must satisfy task allow constraints when `enforce_task_allow=true`.
4. **Safety-first rollout**: default mode is `shadow` and `preserve_routing_assignment=true`, so no route mutation by default.

## Config

Primary policy file:
- `config/ai-rerank-policy.json`

Bundled mirror:
- `bundled/skills/vibe/config/ai-rerank-policy.json`

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `scope.grade_allow`, `scope.task_allow`, `scope.route_mode_allow`
- `trigger.top_k`, `trigger.max_top1_top2_gap`, `trigger.max_confidence_for_rerank`, `trigger.confusion_groups`
- `provider.type` (current default: `heuristic`)
- `safety.require_candidate_in_top_k`, `safety.enforce_task_allow`, `safety.min_rerank_confidence`, `safety.allow_abstain`
- `preserve_routing_assignment`
- `rollout.apply_in_modes`, `rollout.shadow_compare_in_shadow_mode`, `rollout.max_live_apply_rate`

## Runtime Behavior

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output additions:
- `ai_rerank_advice`
- `ai_rerank_route_override`

Semantics:
- In `shadow`: compute advice and `would_override`, but no route mutation.
- In `soft/strict`: override is allowed only when all hard constraints pass, rollout mode allows apply, and sample gate passes.
- If `preserve_routing_assignment=true`, override stays blocked even in `soft/strict`.
- If rerank abstains or constraints fail, stage-1 route is kept.

## Safety Contract

A rerank override must satisfy all of:

1. Suggested pack is inside Top-K (when enabled).
2. Suggested pack is task-allowed (when enabled).
3. Suggested confidence >= `min_rerank_confidence`.
4. Rollout mode allows apply and sample gate passes.
5. `preserve_routing_assignment=false`.

Any violation results in no route mutation.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-ai-rerank-gate.ps1
```

Run config parity gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

- policy missing/invalid: rerank is bypassed safely.
- provider unsupported/error: rerank abstains, route unchanged.
- low-confidence or constraint mismatch: no route mutation.
- rollout set to `shadow`: advisory only.
