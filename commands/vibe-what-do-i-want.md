---
description: Compatibility shim for entering canonical vibe with an intent-clarification stop at requirement freeze.
---

This command is a compatibility shim.

Prefer the Codex skill surface when available.

Use the canonical `vibe` skill for intent clarification, scope freeze, and requirement-first discovery for this request.
This wrapper only selects the bounded stop at `requirement_doc`; canonical `vibe` still owns routing, `confirm_required`, and runtime authority.
Launch canonical-entry first; do not preflight-scan the current workspace or repository for canonical proof files before launch.
Validate canonical receipts only after canonical-entry returns a session root.
Stop at `requirement_doc`.
Do not continue into `xl_plan`, `plan_execute`, or `phase_cleanup` unless the user explicitly re-enters through canonical `vibe` or another approved wrapper.
When later wrappers intentionally continue from this bounded stop, forward `--continue-from-run-id <source_run_id>` and `--bounded-reentry-token <reentry_token>` from the latest `runtime-summary.json` `bounded_return_control` block.

Request:
$ARGUMENTS
