# Framework Interop Overlay Integration (ivy x VCO)

## Purpose

Integrate `ivy-llc/ivy` as a cross-framework interoperability enhancement without adding a second router or changing current pack scoring behavior.

This overlay is designed to:
- Keep `/vibe` as the only routing entrypoint
- Detect framework migration intent (for example PyTorch -> TensorFlow/JAX)
- Surface Ivy interop guidance (`transpile`, optional `trace_graph`) as post-route advice

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the control plane.
2. **Advice-only first rollout**: overlay does not mutate `selected.pack_id` or `selected.skill`.
3. **Scoped to ML/LLM engineering surface**: default scope is `data-ml` + `ai-llm` for `coding/research`.
4. **No training-flow takeover**: does not replace model training/evaluation skills.
5. **Optional external tool**: missing Ivy runtime does not block core routing.

## Config

Primary policy file:
- `config/framework-interop-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/framework-interop-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `interop_signal_keywords`, `framework_keywords`, `suppress_keywords`
- `focus_facets` (transpile/graph/parity)
- `thresholds` (signal and confirm thresholds)
- `external_analyzer` (optional command + invocation mode)

## Runtime Behavior

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output addition:
- `framework_interop_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: keeps advisory mode, but sets `confirm_recommended` for strong migration intent.
- `strict`: strong migration intent becomes `confirm_required` in advice metadata.
- `off`: overlay disabled.

Current rollout is intentionally **advice-first**: strict mode still preserves route assignment.

## Signal Strategy

1. Score interop intent via migration/transpile keywords.
2. Penalize generic training-only requests via suppress keywords.
3. Detect framework entities and migration pairs (for example `pytorch->tensorflow`).
4. Recommend an interop profile:
   - `ivy_transpile` when migration pair is present
   - `ivy_trace_graph` when interop intent exists without explicit pair

## External Analyzer Integration

Ivy is integrated as an optional backend:
- if tool is missing -> `external_analyzer.status = tool_unavailable`
- if mode/signal does not require invocation -> `skipped_mode` or `signal_below_threshold`
- in `manual_only` mode -> returns `manual_command_hint` and does not execute external commands

This preserves deterministic routing and avoids hard runtime dependencies.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-framework-interop-gate.ps1
```

Run legacy-named packaging gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

- missing policy -> bypass overlay advice
- outside scope -> no enforcement, keep routing unchanged
- analyzer unavailable -> degrade to advisory metadata only
- overlay errors -> continue core VCO route path
