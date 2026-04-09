# vibe canonical instruction

Use `vibe` when the task needs the governed runtime across planning, coding, debugging, review, or multi-agent execution.

Canonical rules:

- the canonical router remains authoritative
- the user-facing runtime path is fixed to skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
- `/vibe`, `$vibe`, and agent-invoked `vibe` are the same runtime contract
- discoverable wrapper labels may request an earlier terminal stage, but they never create a second runtime authority
- `M`, `L`, and `XL` are internal execution grades, not user-facing entry branches
- provider-assisted intelligence may advise but must not replace route authority
- explicit user tool choice overrides routing
- XL execution may use multi-agent orchestration, but must preserve requirement freeze, review, cleanup, and no-regression discipline
