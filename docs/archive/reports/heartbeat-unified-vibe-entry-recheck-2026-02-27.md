# Heartbeat Unified `$vibe` Entry Recheck (2026-02-27)

## Scope

This report verifies whether heartbeat runtime integration can be triggered correctly and appropriately through the unified VCO entry (`$vibe`).

## Baseline Decision

To make heartbeat observable in normal routing while keeping routing non-mutating, policy is set to:

- `config/heartbeat-policy.json`: `enabled=true`, `mode=shadow`
- `bundled/skills/vibe/config/heartbeat-policy.json`: `enabled=true`, `mode=shadow`

This keeps heartbeat advisory-only by default and avoids route mutation.

## Verification Commands

```powershell
& ".\scripts\verify\vibe-heartbeat-gate.ps1"
& ".\scripts\verify\vibe-config-parity-gate.ps1"
& ".\scripts\verify\vibe-pack-routing-smoke.ps1"
```

All three checks passed.

## Unified `$vibe` Scenario Matrix

Router command used for each case:

```powershell
& ".\scripts\router\resolve-pack-route.ps1" -Prompt "<$vibe prompt>" -Grade <M|L|XL> -TaskType <planning|coding>
```

| Case | Grade | Task Type | Route Mode | Selected Skill | Heartbeat Mode | Heartbeat Status | Pulse Count | Confirm Required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `m_clear` | `M` | `coding` | `legacy_fallback` | `autonomous-builder` | `shadow` | `completed` | `7` | `false` |
| `l_design` | `L` | `planning` | `legacy_fallback` | `writing-plans` | `shadow` | `completed` | `7` | `false` |
| `xl_parallel` | `XL` | `coding` | `legacy_fallback` | `subagent-driven-development` | `shadow` | `completed` | `7` | `false` |
| `ambiguous` | `L` | `planning` | `legacy_fallback` | `writing-plans` | `shadow` | `completed` | `7` | `false` |

Observations:

- `$vibe` entry is normalized correctly and routed into the VCO path.
- Heartbeat activates in `shadow` mode without introducing confirmation noise in healthy scenarios.
- `heartbeat_runtime_digest.enabled` remains `true` for diagnostics.

## Stress Trigger Check (Strict Mode)

`vibe-heartbeat-gate.ps1` includes strict-mode stress conditions (zero thresholds) and validated:

- `hard_stall=true`
- `confirm_required=true`
- `auto_diagnosis_triggered=true`

This confirms escalation behavior is available when explicitly required, while normal mode remains non-intrusive.

## Conclusion

Heartbeat integration is correctly injected through unified `$vibe` entry and behaves as intended:

1. Normal path: visible, advisory, non-blocking (`shadow`).
2. Stress path: escalates correctly in `strict`.
3. Governance path: config parity and pack routing safety checks remain green.
