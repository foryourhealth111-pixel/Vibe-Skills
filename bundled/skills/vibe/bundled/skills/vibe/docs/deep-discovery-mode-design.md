# VCO Deep Discovery Mode Design

## 1. Goal

Deep Discovery Mode solves a common VCO routing blind spot: prompts that are ambiguous, composite, or cross-domain can look valid at logic level but behave like a blackbox in runtime.  
This mode adds a deterministic prepack inspection chain to expose:

- what capability signals were detected,
- what interview clarifications were inferred,
- what intent contract was synthesized,
- whether candidate filtering would apply (or actually applied).

Default rollout is `shadow`, so existing routing remains stable unless explicitly moved to `soft/strict`.

## 2. New Runtime Chain

Deep Discovery inserts four stages between `router.prepack` and `router.pack_scoring`:

1. `deep_discovery.trigger`
2. `deep_discovery.interview`
3. `deep_discovery.contract`
4. `deep_discovery.filter`

Full chain:

`router.init -> router.config -> router.prepack -> deep_discovery.trigger -> deep_discovery.interview -> deep_discovery.contract -> deep_discovery.filter -> router.pack_scoring -> overlay.ai_rerank -> overlay.prompt -> overlay.data_scale -> overlay.exploration -> overlay.retrieval -> overlay.bundle -> router.final`

## 3. Core Files

### Router modules

- `scripts/router/modules/21-capability-interview.ps1`
- `scripts/router/modules/22-intent-contract.ps1`

### Config

- `config/deep-discovery-policy.json`
- `config/capability-catalog.json`
- bundled mirrors:
  - `bundled/skills/vibe/config/deep-discovery-policy.json`
  - `bundled/skills/vibe/config/capability-catalog.json`

### Router entry integration

- `scripts/router/resolve-pack-route.ps1`

## 4. Data Contract

Route output now includes:

- `deep_discovery_advice`
  - trigger signal, capability hits, interview questions, enforcement/confirm hints.
- `intent_contract`
  - goal, deliverable, constraints, capabilities, execution mode, completeness.
- `deep_discovery_filter`
  - mode-gated filter decision and summary.
- `deep_discovery_route_filter_applied`
  - true only when filter actually mutates candidate set (typically strict + preserve disabled).
- `deep_discovery_route_mode_override`
  - true when deep discovery escalates route mode to `confirm_required`.
- `runtime_state_prompt_digest`
  - compact model-visible state digest (route + deep discovery + overlay folding summary).

## 5. Mode Behavior

### `off`

- No deep discovery behavior.

### `shadow` (default)

- Emits full advice/contract/filter simulation.
- Never mutates route assignment.

### `soft`

- Can escalate to `confirm_required` for ambiguous composite prompts.
- Keeps route assignment if `preserve_routing_assignment=true`.

### `strict`

- Can apply capability-based candidate filtering when:
  - trigger active,
  - contract completeness >= threshold,
  - filtered candidate set is non-empty,
  - `preserve_routing_assignment=false`.

## 6. Probe and Observability

### Probe artifact visibility

`scripts/router/modules/11-route-probe.ps1` now records deep-discovery fields in:

- event stream (`deep_discovery.*` stages),
- `final_state` summary,
- runtime state prompt text.

### Observability event visibility

`scripts/router/modules/10-observability.ps1` now writes deep-discovery telemetry fields:

- `deep_discovery_triggered`,
- `deep_discovery_confirm_required`,
- `deep_discovery_route_filter_applied`,
- `deep_discovery_route_mode_override`.

## 7. Verification Entry Points

```powershell
& ".\scripts\verify\vibe-deep-discovery-gate.ps1"
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode shadow
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode soft
& ".\scripts\verify\vibe-deep-discovery-scenarios.ps1" -Mode strict
```

Recommended regression chain:

```powershell
& ".\scripts\verify\vibe-config-parity-gate.ps1" -WriteArtifacts
& ".\scripts\verify\vibe-pack-routing-smoke.ps1"
& ".\scripts\verify\vibe-routing-smoke.ps1"
& ".\scripts\verify\vibe-routing-probe-research.ps1" -DefaultIncludePrompt
```

