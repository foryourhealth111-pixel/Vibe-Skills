---
name: vibe
description: Vibe Code Orchestrator (VCO) is a governed runtime entry that freezes requirements, plans XL-first execution, and enforces verification and phase cleanup.
---

# Vibe Governed Runtime Entry

This file is the host-facing SOP for entering canonical `vibe`. Keep it small:
runtime details belong in `protocols/runtime.md`, execution discipline belongs in
`protocols/do.md`, and host wrapper recipes belong in installer-generated wrapper
docs.

## Trigger Contract

Enter canonical `vibe` before ordinary execution when the user explicitly invokes
`$vibe`, `/vibe`, or the `vibe` skill, or when the host intentionally chooses
governed requirement/plan/execution closure for a complex task.

Do not route every loosely related task into `vibe`. Lightweight questions,
single-command checks, or tasks better served by another explicitly requested
skill may proceed outside `vibe` unless the user explicitly invoked this entry.

`vibe-upgrade` is a separate public skill for upgrading the installed
Vibe-Skills project. Do not relaunch an upgrade request as `entry_id = vibe`;
use the `vibe-upgrade` skill and its backend instead.

User instructions remain highest priority. If CLAUDE.md, GEMINI.md, AGENTS.md,
or the direct user request narrows or forbids a workflow such as TDD, follow the
user's instruction while preserving canonical launch and proof rules.

## Canonical Launch SOP

Before canonical launch, do only the minimum needed to launch:

- Resolve `skill_root`: the directory containing this `SKILL.md`.
- Resolve `workspace_root`: the task workspace where governed artifacts should
  be written.
- Resolve `host_id`: `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`,
  or `opencode`.
- Extract core intent as keyword text. Do not pass the raw prompt, full chat
  history, or mixed-language filler to the router.

Do not inspect repository files, protocol docs, previous run outputs, or old
proof artifacts before canonical launch returns. Reading this file, a wrapper,
or an AGENTS/CLAUDE bootstrap block is not proof of canonical entry.

Internal specialist recommendation router: `scripts/router/resolve-pack-route.ps1`

Specialist recommender input rules:

This recommender runs inside canonical `vibe`; it may suggest specialist skills, but it does not decide whether `$vibe` is the public runtime entry.

- Include work type, domain/technology, deliverable, and explicit constraints.
- Reuse verified frozen requirement/plan facts when continuing a run.
- If the router returns `confirm_required`, surface the machine-readable route
  contract and convert the user's natural-language reply into a structured route
  decision.
- If the router fails, report `blocked` with the concrete failure reason.

Canonical entry command shape:

```powershell
$env:PYTHONPATH = "<skill_root>/apps/vgo-cli/src"
py -3 -m vgo_cli.main canonical-entry `
  --repo-root "<skill_root>" `
  --artifact-root "<workspace_root>" `
  --host-id "<host_id>" `
  --entry-id "vibe" `
  --prompt "<extracted keyword intent text>"
```

Bash-like hosts, including Claude Code, should avoid Bash-wrapped PowerShell.
Set `PYTHONPATH` in the outer shell and call Python directly:

```bash
REPO_ROOT='<skill_root>'
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"
PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main canonical-entry \
  --repo-root "$REPO_ROOT" \
  --artifact-root "$WORKSPACE_ROOT" \
  --host-id "<host_id>" \
  --entry-id "vibe" \
  --prompt "<extracted keyword intent text>"
```

After canonical-entry returns a `session_root`, validate proof artifacts only
inside that launched session:

- `host-launch-receipt.json`
- `runtime-input-packet.json`
- `governance-capsule.json`
- `stage-lineage.json`

## Bounded Stop And Re-entry

`vibe` uses progressive governed stops:

1. `requirement_doc`
2. `xl_plan`
3. `phase_cleanup`

When `bounded_return_control.explicit_user_reentry_required = true`, stop the
current assistant turn. Do not consume re-entry credentials until a later user
message approves or revises the current boundary.

For re-entry, inspect `runtime-summary.json ->
bounded_return_control.host_decision_contract`, infer the user's intent, and
write a structured host decision JSON file. Use the same `run_id`,
`bounded_reentry_token`, and stable `workspace_root`:

```bash
REPO_ROOT='<skill_root>'
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"
DECISION_JSON="$WORKSPACE_ROOT/.vibeskills/tmp/host-decision.json"
mkdir -p "$(dirname "$DECISION_JSON")"

cat > "$DECISION_JSON" <<'JSON'
{
  "decision_kind": "approval_response",
  "decision_action": "approve_requirement",
  "approval_decision": "approve"
}
JSON

PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main canonical-entry \
  --repo-root "$REPO_ROOT" \
  --artifact-root "$WORKSPACE_ROOT" \
  --host-id "<host_id>" \
  --entry-id "vibe" \
  --prompt "<stable continuation intent, not just the user's short reply>" \
  --continue-from-run-id "<source_run_id>" \
  --bounded-reentry-token "<reentry_token>" \
  --host-decision-json-file "$DECISION_JSON"
```

A structured approval advances to the next progressive stop. A structured
revision must include non-empty `revision_delta` and refreezes the same bounded
stage without asking the user for a separate approval first:

```json
{
  "decision_kind": "approval_response",
  "decision_action": "revise_requirement",
  "approval_decision": "revise",
  "revision_delta": [
    "Freeze one public small/medium face dataset downloaded locally.",
    "Require a polished LaTeX paper and compiled PDF."
  ]
}
```

Route confirmations must stay inside surfaced confirm options. Bounded approvals
or revisions must stay inside the surfaced bounded-stage action contract.

## Runtime Contract Summary

Canonical `vibe` owns one runtime authority and one visible requirement/plan
surface. The fixed state machine is:

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

These stages may be light for simple work, but they are not silently skipped.
The full runtime contract, stage ownership, lineage rules, internal `M`/`L`/`XL`
grades, cleanup rules, and output inventory are defined in
`protocols/runtime.md`.

Public wrapper entries remain limited to:

- `vibe`
- `vibe-upgrade`

Compatibility stage IDs are non-public metadata and must not be materialized as
host-visible command or skill wrappers:

- `vibe-what-do-i-want` -> `requirement_doc`
- `vibe-how-do-we-do` -> `xl_plan`
- `vibe-do-it` -> `phase_cleanup`

## Specialist Dispatch

The router may surface specialist recommendations, but `vibe` remains the
runtime-selected skill and runtime authority.

The host must inspect surfaced specialist recommendations and make a structured
dispatch decision when curation is needed. It may approve, defer, or reject only
surfaced recommendation ids. Unsuitable or noisy specialists should be rejected
or deferred with a reason rather than forced into execution.

Only approved specialists become execution units. The host must not invent
unsurfaced specialists, bypass runtime validation, create hidden specialist
sub-sessions, or open a second requirement/plan/runtime surface. Specialist work
must preserve the specialist skill's own workflow, inputs, outputs, and
validation style.

For XL delegation, root/child hierarchy remains governed: only `root_governed`
may freeze canonical requirements/plans or make final completion claims.
`child_governed` lanes inherit the frozen context, stay inside assigned write
scopes, validate `delegation-envelope.json`, and emit local receipts only.

## Quality Rules

Never claim success without evidence. Minimum invariants:

- Verify before completion.
- Do not make silent no-regression claims.
- Keep requirement and plan artifacts traceable to the launched run.
- Emit cleanup receipts before claiming phase completion.
- Expose failures, fallback, degraded status, or blocked state explicitly.
- Do not add mock success paths, swallowed errors, or template-only pass results.
- Do not use fallback or boundary behavior to bypass real execution,
  verification, or root-cause repair.

## Protocol Map

Read these references only after canonical launch or when maintaining the repo:

- `protocols/runtime.md`: governed runtime contract and stage ownership
- `protocols/think.md`: planning, research, and pre-execution analysis
- `protocols/do.md`: coding, debugging, and verification
- `protocols/review.md`: review and quality gates
- `protocols/team.md`: XL multi-agent orchestration
- `protocols/retro.md`: retrospective and evidence-backed corrections

## Maintenance

- Runtime family: governed-runtime-first
- Version: 3.1.0
- Updated: 2026-04-25
- Internal specialist recommendation router: `scripts/router/resolve-pack-route.ps1`
- Primary contract metadata: `core/skill-contracts/v1/vibe.json`
