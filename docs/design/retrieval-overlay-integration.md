# Retrieval Overlay Integration (VCO)

## Goal

Add a lean, non-redundant retrieval strategy layer to VCO so that different search scenarios (papers, code, docs, mixed tasks) receive explicit, inspectable query/source/rerank guidance without replacing existing pack routing.

## Design Boundary

- Post-route advisory overlay only.
- Does not mutate selected pack/skill by default (`preserve_routing_assignment=true`).
- Mode-gated behavior:
  - `off`: disabled.
  - `shadow`: advice only.
  - `soft`: advice + stronger confirm recommendation.
  - `strict`: can set `confirm_required` on ambiguity/coverage risk, still no hard route override.

## Config Surface

Main + bundled:

- `config/retrieval-policy.json`
- `config/retrieval-intent-profiles.json`
- `config/retrieval-source-registry.json`
- `config/retrieval-rerank-weights.json`

These configs define:

- scope controls (`task_allow`, `grade_allow`, `route_mode_allow`)
- profile selection thresholds
- query-variant budget by mode
- source catalog and quality hints
- rerank weight presets
- strict confirmation policy

## Router Injection Point

Execution chain:

`... -> overlay.ai_rerank -> overlay.prompt -> overlay.data_scale -> overlay.exploration -> overlay.retrieval -> overlay.bundle -> router.final`

Implementation:

- module: `scripts/router/modules/43-retrieval-overlay.ps1`
- route entry: `scripts/router/resolve-pack-route.ps1`
- output field: `retrieval_advice`

Probe + heartbeat:

- probe stage: `overlay.retrieval`
- heartbeat pulse: `overlay.retrieval`

## Advice Contract

`retrieval_advice` includes:

- scope and enforcement:
  - `enabled`, `mode`, `scope_applicable`, `enforcement`, `reason`
- profile routing:
  - `profile_id`, `profile_confidence`, `profile_top_gap`, `profile_ambiguous`, `profile_ranking`
- query plan:
  - `query_plan.max_query_variants`, templates, expansion terms
- source plan:
  - preferred source IDs and resolved source rows
- rerank plan:
  - `mode` + semantic/keyword/authority weights
- coverage gate:
  - `coverage_score`, `needs_requery`, `max_retrieve_rounds`, evidence/source targets
- UX guard:
  - `confirm_recommended`, `confirm_required`

## Observability and Runtime Prompt

Integrated into:

- `runtime_state_prompt`
- `runtime_state_prompt_digest`
- route probe final-state summary
- observability event overlays summary

This keeps the retrieval injection visible and debuggable in blackbox traces.

## Verification

New gate:

- `scripts/verify/vibe-retrieval-overlay-gate.ps1`

Updated gates:

- `scripts/verify/vibe-config-parity-gate.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- route-probe scripts now expect `overlay.exploration` + `overlay.retrieval` stages in chain.
