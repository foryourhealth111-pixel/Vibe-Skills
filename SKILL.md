---
name: vibe
description: Vibe Code Orchestrator (VCO) is a governed runtime entry that freezes requirements, bounds execution, and enforces verification and phase cleanup.
---

# Vibe Governed Runtime Entry

This file is the host-facing SOP for entering canonical `vibe`. Keep it small:
runtime details belong in `protocols/runtime.md`, execution discipline belongs in `protocols/do.md`, and host wrapper recipes belong in installer-generated wrapper docs.

## Trigger Contract

Enter canonical `vibe` before ordinary execution when the user explicitly invokes
`$vibe`, `/vibe`, or the `vibe` skill, or when the host intentionally chooses
governed requirement/plan/execution closure for a complex task.

Do not route every loosely related task into `vibe`. Lightweight questions,
single-command checks, or tasks better served by another explicitly requested
skill may proceed outside `vibe` unless the user explicitly invoked this entry.

Installed-copy upgrades stay on the command path. Use the repo's `update`
entry with `--skills-dir` for the same managed skills directory instead of
introducing a second public runtime skill.

User instructions remain highest priority. If CLAUDE.md, GEMINI.md, AGENTS.md,
or the direct user request narrows or forbids a workflow such as TDD, follow the
user's instruction while preserving canonical launch and proof rules.

## Canonical Bootstrap

`vibe` is a host-syntax-neutral skill contract.

Before canonical launch, do only the minimum needed to launch:

- Resolve `skill_root`, `workspace_root`, and `host_id`.
- Extract core intent as keyword text. Do not pass the raw prompt, full chat history, or mixed-language filler to the router.

Do not search the current workspace, repository, or install root for canonical proof files before launch.
Do not inspect the repo, protocol docs, or prior run outputs before canonical launch returns.
Do not simulate stages, claim canonical entry from reading this file or wrapper text, or treat wrapper or AGENTS text as proof.
Do not manually create `outputs/runtime/vibe-sessions/<run-id>/`.
Do not use the Vibe installation root as the governed artifact root.

Local installed specialist recommender: semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`; compatibility bridge `scripts/router/resolve-pack-route.ps1`

Specialist recommender input rules:

This recommender runs inside canonical `vibe`; it may suggest specialist skills, but it does not decide whether `$vibe` is the public runtime entry.

- Include work type, domain/technology, deliverable, and explicit constraints.
- Reuse verified frozen requirement/plan facts when continuing a run.
- If the router returns `confirm_required`, surface the machine-readable route contract and convert the user's natural-language reply into a structured route decision.
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

For PowerShell, do not place `$env:PYTHONPATH=...` inside a double-quoted `-Command` string; host interpolation may corrupt it to `:PYTHONPATH`.

Bash-like hosts, including Claude Code, should avoid Bash-wrapped PowerShell.
Set `PYTHONPATH` in the outer shell and call Python directly. If `py -3` is unavailable, try `python` instead. If `python` is unavailable, try `python3`.

```bash
REPO_ROOT='<skill_root>'
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"
PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" python -m vgo_cli.main canonical-entry \
  --repo-root "$REPO_ROOT" \
  --artifact-root "$WORKSPACE_ROOT" \
  --host-id "<host_id>" \
  --entry-id "vibe" \
  --prompt "<extracted keyword intent text>"
```

Only validate canonical proof artifacts after canonical-entry returns a `session_root`.
`check` on an installed copy proves only `installed locally`.
It does not prove `runtime coherent` or `delivery accepted`.
Proof of canonical launch is post-launch and requires: `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json` under the returned `session_root`.
`local-agent-kernel` follows the same proof rule. If it cannot produce those truth artifacts, it may produce local work scaffolds, but it must not be treated as `canonical verified`.

## Hard Stop And Re-entry

`vibe` uses progressive governed stops:

1. `requirement_doc`
2. `xl_plan`
3. `phase_cleanup`

When `bounded_return_control.explicit_user_reentry_required = true`, stop the
current assistant turn. Do not consume re-entry credentials until a later user
message approves or revises the current boundary.

This is a hard runtime boundary, not a suggestion. It overrides ordinary host
autonomy rules such as "continue until done." A detailed original request is not
approval of the frozen requirement or frozen plan. After a hard stop, do not
perform equivalent manual work outside governed re-entry: no plan writing, task
execution, manual workaround delivery, or final artifact delivery in the same
assistant turn.

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

A structured approval from a later user message advances to the next progressive stop. A structured
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

## Unified Runtime Contract

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
grades, user-visible L/XL workflow confirmation, cleanup rules, and output inventory are defined in
`protocols/runtime.md`.

Public wrapper entries remain limited to:

- `vibe`

Installed-copy updates remain a command-path action:

- `update --skills-dir <skills-dir>`

Compatibility stage IDs are non-public metadata and must not be materialized as
host-visible command or skill wrappers:

- `vibe-what-do-i-want` -> `requirement_doc`
- `vibe-how-do-we-do` -> `xl_plan`
- `vibe-do-it` -> `phase_cleanup`

## Skill Execution

The router may surface selected skill execution candidates, but `vibe` remains
the runtime-selected skill and runtime authority.

The host must inspect surfaced candidates and make a structured skill execution
decision when curation is needed. It may approve, defer, or reject only surfaced
candidate ids. Unsuitable or noisy candidates should be rejected or deferred
with a reason rather than forced into execution.

For interactive L/XL work, surface the selected skill list before execution and
ask the user: "我将会在接下来的工作中使用这些 skills，你觉得 OK 吗？" This approval
only means the skills may be used; final material-use claims still require
`skill_usage.used` and evidence files. `skill_usage.bound` only means a skill was attached to a work unit; it is not a material-use claim.

Only selected skills become execution units. The host must not invent unsurfaced
skills, bypass runtime validation, create hidden skill sub-sessions, or open a
second requirement/plan/runtime surface. Selected skill work must preserve the
skill's own workflow, inputs, outputs, and validation style.

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
- Treat scaffold or draft artifacts as `needs_execution` with `proof_ready = false`; do not call them completed work.
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
- Version: 3.2.0
- Updated: 2026-07-08
- Local installed specialist recommender: semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`; compatibility bridge `scripts/router/resolve-pack-route.ps1`
- Primary contract metadata: `core/skill-contracts/v1/vibe.json`
