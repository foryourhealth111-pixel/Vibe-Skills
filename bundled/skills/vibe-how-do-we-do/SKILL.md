---
name: vibe-how-do-we-do
description: Design the approach and execution plan by entering the canonical vibe runtime with a planning-first bias.
---

Use canonical `vibe` as the only governed runtime authority for this request.

Entry bias:

- choose an approach
- design execution structure
- sequence the work before implementation
- stop after canonical `xl_plan`

Execution rules:

- delegate to canonical `vibe`
- keep `vibe` as the only runtime authority
- let canonical `vibe` keep router selection and `confirm_required` ownership
- do not create a second requirement surface
- do not create a second plan surface
- do not create a parallel runtime
- do not preflight-scan the current workspace or repository for canonical proof files before launch
- Launch canonical-entry first; validate receipts only after it returns a session root
- do not continue into `plan_execute` or `phase_cleanup` unless the user explicitly re-enters through canonical `vibe` or another approved wrapper
- if the latest verified `runtime-summary.json` exposes `bounded_return_control.explicit_user_reentry_required = true`, forward `--continue-from-run-id <source_run_id>` and `--bounded-reentry-token <reentry_token>` before launching this wrapper

When this wrapper is chosen, enter canonical `vibe` with:

- approach selection
- explicit planning
- stronger transition into `xl_plan`
- a bounded terminal stage of `xl_plan`

Request:
$ARGUMENTS
