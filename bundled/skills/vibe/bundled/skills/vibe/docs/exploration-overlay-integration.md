# Exploration Overlay Integration (VCO)

## Goal

Add a lightweight exploration advisory layer to VCO so exploratory prompts ("why", "what it means", "next steps") and mixed-domain tasks become inspectable and controllable, without replacing pack routing.

## Design Boundary

- Post-route advisory overlay only.
- Default rollout is `soft` and non-mutating (`preserve_routing_assignment=true`).
- Mode-gated behavior:
  - `off`: disabled.
  - `shadow`: observe and report only.
  - `soft`: advisory + `confirm_recommended` on ambiguity/multi-domain.
  - `strict`: may raise `confirm_required` on ambiguity/multi-domain, still no hard route override.

## Config Surface

Main + bundled:

- `config/exploration-policy.json`
- `config/exploration-intent-profiles.json`
- `config/exploration-domain-map.json`

These configs define:

- scope controls (`task_allow`, `grade_allow`, `route_mode_allow`)
- intent selection thresholds and fallback
- domain detection thresholds and multi-domain decision
- mode-specific interview/confirm policy
- output contract and hypothesis budget

## Router Injection Point

Execution chain:

`... -> overlay.ai_rerank -> overlay.prompt -> overlay.data_scale -> overlay.exploration -> overlay.retrieval -> overlay.bundle -> router.final`

Implementation:

- module: `scripts/router/modules/44-exploration-overlay.ps1`
- route entry: `scripts/router/resolve-pack-route.ps1`
- output field: `exploration_advice`

Probe + heartbeat:

- probe stage: `overlay.exploration`
- heartbeat pulse: `overlay.exploration`

## Advice Contract

`exploration_advice` includes:

- scope and enforcement:
  - `enabled`, `mode`, `scope_applicable`, `enforcement`, `reason`
- intent assessment:
  - `intent_id`, `intent_confidence`, `intent_top_gap`, `intent_ambiguous`, `intent_ranking`
- domain assessment:
  - `domain_hits`, `dominant_domain`, `multi_domain`
- execution guidance:
  - `recommended_execution_mode`, `hypothesis_budget`, `recommended_output_sections`
- UX guard:
  - `confirm_recommended`, `confirm_required`
- route safety:
  - `preserve_routing_assignment`, `auto_override=false`, `route_override_applied=false`

## Observability and Runtime Prompt

Integrated into:

- `runtime_state_prompt`
- `runtime_state_prompt_digest`
- route probe final-state summary
- observability route event overlay fields

This keeps the exploration injection visible in probe traces and avoids blackbox behavior.

## Verification

New gate:

- `scripts/verify/vibe-exploration-overlay-gate.ps1`

Updated checks:

- `scripts/verify/vibe-config-parity-gate.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-routing-probe-research.ps1`
- `scripts/verify/vibe-deep-discovery-scenarios.ps1`

