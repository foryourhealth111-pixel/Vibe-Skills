---
name: vibe-do-it
description: Execute through the full governed path with an implementation-forward bias while keeping canonical vibe as the only governed runtime.
---

Use canonical `vibe` as the only governed runtime authority for this request.

Entry bias:

- move toward execution
- retain requirement and plan governance
- keep verification and cleanup mandatory
- continue through canonical `phase_cleanup`

Execution rules:

- delegate to canonical `vibe`
- keep `vibe` as the only runtime authority
- let canonical `vibe` keep router selection and `confirm_required` ownership
- do not create a second requirement surface
- do not create a second plan surface
- do not create a parallel runtime
- do not preflight-scan the current workspace or repository for canonical proof files before launch
- Launch canonical-entry first; validate receipts only after it returns a session root
- if the latest verified `runtime-summary.json` exposes `bounded_return_control.explicit_user_reentry_required = true`, forward `--continue-from-run-id <source_run_id>` and `--bounded-reentry-token <reentry_token>` before launching this wrapper

When this wrapper is chosen, bias canonical `vibe` toward:

- approved-plan execution
- `plan_execute` readiness
- preserving verification and cleanup gates
- a bounded terminal stage of `phase_cleanup`

Request:
$ARGUMENTS
