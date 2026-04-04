# Quality Debt Overlay Integration (fuck-u-code x VCO)

## Purpose

Integrate `Done-0/fuck-u-code` ideas as a post-route quality-debt advisory layer without introducing a second router or changing current pack scoring.

This overlay is designed to:
- Keep `/vibe` as the only routing entrypoint
- Detect quality-debt intent (maintainability/test/security debt) from prompt signals
- Produce structured review advice and optional external analyzer hints

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the control plane.
2. **Advice-only first rollout**: overlay does not mutate `selected.pack_id` or `selected.skill`.
3. **Scoped surface**: default scope is `code-quality` pack with `coding/review` tasks.
4. **Optional external tool**: missing analyzer binary never blocks the core route.

## Config

Primary policy file:
- `config/quality-debt-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/quality-debt-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `risk_keywords`, `suppress_keywords`
- `focus_facets` (maintainability/test/security focus buckets)
- `thresholds` (risk and confirm thresholds)
- `external_analyzer` (optional CLI command + invocation mode)

## Runtime Behavior

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output addition:
- `quality_debt_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: advisory only, but highlights `confirm_recommended` for high-risk prompts.
- `strict`: marks high-risk prompts as `confirm_required` in advice metadata.
- `off`: overlay disabled.

Current rollout is intentionally **advice-first**: even in strict mode, route assignment is preserved.

## External Analyzer Integration

`fuck-u-code` is integrated as an optional backend:
- if tool is missing -> `external_analyzer.status = tool_unavailable`
- if mode/risk does not require invocation -> `skipped_mode` or `risk_below_threshold`
- in `manual_only` mode -> returns `manual_command_hint` and does not execute external commands

This keeps VCO deterministic and avoids hard dependency on external binaries.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-quality-debt-overlay-gate.ps1
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
