# ML Lifecycle Overlay Integration (Made-With-ML x VCO)

## Purpose

Integrate `GokuMohandas/Made-With-ML` lifecycle discipline into VCO as a **post-route advisory overlay**, without introducing a second router or replacing existing `data-ml` pack routing.

This overlay focuses on lifecycle governance signals:
- stage detection (`develop`, `evaluate`, `deploy`, `iterate`)
- evidence readiness (`run_id`, evaluation report, baseline comparison, tests/monitoring artifacts)
- mode-gated confirmation policy in higher-risk lifecycle stages

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the control plane.
2. **Advice-only rollout**: overlay does not mutate `selected.pack_id` or `selected.skill`.
3. **Lifecycle governance only**: does not replace model training/evaluation tooling.
4. **Compatible with existing overlays**:
   - `data-scale-overlay`: file-scale and tabular backend selection
   - `quality-debt-overlay`: code-quality debt risk
   - `framework-interop-overlay`: cross-framework migration guidance
5. **Optional external analyzer**: missing `mlflow` never blocks core routing.

## Config

Primary policy:
- `config/ml-lifecycle-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/ml-lifecycle-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `lifecycle_signal_keywords`, `stage_keywords`
- `artifact_keywords`, `required_checks_by_stage`, `artifacts_required_by_stage`
- `strict_confirm_scope`
- `thresholds`
- `external_analyzer`

## Runtime Behavior

Router:
- `scripts/router/resolve-pack-route.ps1`

New output:
- `ml_lifecycle_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: lifecycle risk remains advisory, may set `confirm_recommended`.
- `strict`: within strict scope and missing required lifecycle artifacts, advice escalates to `confirm_required`.
- `off`: overlay disabled.

Current rollout remains **advice-first** and preserves route assignment.

## Lifecycle Signal Strategy

1. Score lifecycle intent with `lifecycle_signal_keywords`.
2. Classify dominant lifecycle stage from `stage_keywords`.
3. Detect artifact evidence hits (run/eval/baseline/tests/monitoring).
4. Compute `deploy_readiness` and missing artifact ratio.
5. Emit mode-aware confirmation advice without mutating route selection.

## External Analyzer Integration

Optional `mlflow` presence probe behavior:
- missing tool -> `external_analyzer.status = tool_unavailable`
- out-of-mode or low signal -> `skipped_mode` / `signal_below_threshold`
- `manual_only` mode -> command hint only, no execution

This keeps routing deterministic and avoids hard runtime dependency.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-ml-lifecycle-overlay-gate.ps1
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
