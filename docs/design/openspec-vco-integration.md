# OpenSpec x VCO Integration (Zero-Conflict)

## Design Goal

Integrate OpenSpec as a governance overlay without changing existing VCO route assignment behavior.

- OpenSpec owns `what/why` artifacts.
- VCO owns `who/how` routing and execution orchestration.
- AIOS consumes OpenSpec artifacts and executes role-based delivery.

## Non-Conflict Principles

1. OpenSpec does not participate in pack scoring.
2. Existing pack and skill selection in `resolve-pack-route.ps1` remains unchanged.
3. OpenSpec advice is appended as metadata (`openspec_advice`) only.
4. Explicit user skill requests keep highest priority.

## Policy File

Path: `config/openspec-policy.json`

Key fields:

- `mode`: `off | shadow | soft | strict`
- `profile_by_grade`: default `M=lite`, `L=full`, `XL=full`
- `required_task_types_by_profile`: `lite` and `full` applicability
- `soft_confirm_scope`: where `mode=soft` should enforce `confirm_required`
- `m_lite`: lightweight card generation settings
- `full`: `specs_dir` and `changes_dir`
- `preserve_routing_assignment`: must remain `true`

Current recommended stage:

- `mode=soft`
- `soft_confirm_scope.grades=[L, XL]`
- `soft_confirm_scope.task_types=[planning]`

## Runtime Behavior

### Router

`scripts/router/resolve-pack-route.ps1` now emits:

- `openspec_advice.mode`
- `openspec_advice.profile`
- `openspec_advice.enforcement`
- `openspec_advice.recommended_artifact`
- `openspec_advice.should_upgrade_to_full`

This metadata does not alter `route_mode`, selected pack, or selected skill.

### Governance Hook

`scripts/governance/invoke-openspec-governance.ps1` performs post-route governance:

- `M` + applicable task -> OpenSpec-Lite card (`openspec/micro/<task-id>.md`)
- `L/XL planning` -> OpenSpec-Full readiness check (`openspec/specs`, `openspec/changes`)
- Supports optional artifact creation with `-WriteArtifacts`

## Verification

Use:

```powershell
pwsh -File .\scripts\verify\vibe-openspec-governance-gate.ps1
pwsh -File .\scripts\verify\vibe-pack-regression-matrix.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict -WriteArtifacts
```

Rollout stage switch:

```powershell
pwsh -File .\scripts\governance\set-openspec-rollout.ps1 -Stage soft-lxl-planning
```

Recommended single-command publish (normal path first, manual rollback only on confirmed need):

```powershell
pwsh -File .\scripts\governance\publish-openspec-soft-rollout.ps1
```

Behavior contract:

1. Precheck must pass before switch (`vibe-pack-regression-matrix` + strict `vibe-routing-stability-gate`).
2. After switch, postcheck must pass (`pack-regression` + strict stability + `vibe-openspec-governance-gate`).
3. Default on postcheck failure is fail-fast without rollback, so issues are visible.
4. Automatic rollback is disabled. On failure, the script prints a rollback command and requires explicit user confirmation before execution.
5. Manual rollback command (run only after confirmation):

```powershell
pwsh -File .\scripts\governance\set-openspec-rollout.ps1 -Stage shadow
```

Acceptance criteria:

1. Pack selection for baseline regression prompts is unchanged.
2. `openspec_advice` exists and profile/enforcement are grade-correct.
3. `preserve_routing_assignment` remains `true`.
4. Stability gate metrics do not regress.
