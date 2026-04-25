---
description: Compatibility shim for entering canonical vibe with an approach-and-planning stop at xl_plan.
---

This command is a compatibility shim.

Prefer the Codex skill surface when available.

Use the canonical `vibe` skill for approach selection, plan design, and execution sequencing for this request.
This wrapper only selects the bounded stop at `xl_plan`; canonical `vibe` still owns routing, `confirm_required`, and runtime authority.
Launch canonical-entry first; do not preflight-scan the current workspace or repository for canonical proof files before launch.
Validate canonical receipts only after canonical-entry returns a session root.
Stop at `xl_plan`.
Do not continue into `plan_execute` or `phase_cleanup` unless the user explicitly re-enters through canonical `vibe` or another approved wrapper.
If the latest verified `runtime-summary.json` exposes `bounded_return_control.explicit_user_reentry_required = true`, forward `--continue-from-run-id <source_run_id>` and `--bounded-reentry-token <reentry_token>` before launching this wrapper.

Request:
$ARGUMENTS
