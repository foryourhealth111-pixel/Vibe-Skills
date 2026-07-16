---
name: vibe
description: Vibe Code Orchestrator (VCO) is a governed runtime entry that freezes requirements, bounds execution, and enforces verification and phase cleanup.
---

# Vibe Governed Runtime Entry

This file is the host-facing SOP for entering canonical `vibe`. Keep it small: runtime details belong in `protocols/runtime.md`, execution discipline belongs in `protocols/do.md`, and host wrapper recipes belong in installer-generated wrapper docs.

## Trigger Contract

Enter canonical `vibe` before ordinary execution when the user explicitly invokes `$vibe`, `/vibe`, or the `vibe` skill, or when the host intentionally chooses governed requirement/plan/execution closure for a complex task.

Do not route every loosely related task into `vibe`. Lightweight questions,
single-command checks, or tasks better served by another explicitly requested
skill may proceed outside `vibe` unless the user explicitly invoked this entry.

Installed-copy upgrades stay on the command path. Use the repo's `update`
entry with `--skills-dir` for the same managed skills directory instead of
starting a separate skill flow.

User instructions remain highest priority. If CLAUDE.md, GEMINI.md, AGENTS.md,
or the direct user request narrows or forbids a workflow such as TDD, follow the
user's instruction while preserving canonical launch and proof rules.

## Canonical Bootstrap

`vibe` is a host-syntax-neutral skill contract. Before canonical launch, do only the minimum needed to launch:

- Resolve `skill_root` and `workspace_root`.
- Pass the current user task verbatim as the task specification; unrelated chat history may be excluded. Do not summarize, rewrite, or reduce it to keywords. Preserve exact input paths, input immutability constraints, exact output roots, synthetic-data evidence boundaries, module dependencies and safe parallel boundaries, and acceptance criteria.

Do not search the current workspace, repository, or install root for canonical proof files before launch.
Do not inspect the repo, protocol docs, or prior run outputs before canonical launch returns.
Do not simulate stages, claim canonical entry from reading this file or wrapper text, or treat wrapper or AGENTS text as proof.
Do not manually create `outputs/runtime/vibe-sessions/<run-id>/`.
Do not use the Vibe installation root as the governed artifact root.

Local skill candidate audit: semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`; compatibility bridge `scripts/router/resolve-pack-route.ps1`

Specialist recommender input rules:

This audit runs inside canonical `vibe`; it may expose candidates for inspection, but it does not choose task skills, bind execution, or control stage progression.

- Include work type, domain/technology, deliverable, and explicit constraints.
- Reuse verified frozen requirement/plan facts when continuing a run.
- Treat its output as compatibility evidence only; never relabel a routed candidate as an Agent choice.

Canonical entry command shape:

```powershell
$env:PYTHONPATH = "<skill_root>/apps/vgo-cli/src"
py -3 -m vgo_cli.main canonical-entry `
  --repo-root "<skill_root>" `
  --artifact-root "<workspace_root>" `
  --prompt "<current user task, verbatim>"
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
  --prompt "<current user task, verbatim>"
```

A normal launch does not need explicit `--host-id` or `--entry-id`.
Those flags remain compatibility-only for wrappers or older automation that already carries them.

Only validate canonical proof artifacts after canonical-entry returns a `session_root`.
`check` on an installed copy proves only `installed locally`.
It does not prove `runtime coherent` or `delivery accepted`.
Proof of canonical launch is post-launch and requires: `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json` under the returned `session_root`.
`local-agent-kernel` follows the same proof rule. If it cannot produce those truth artifacts, it may produce local work scaffolds, but it must not be treated as `canonical verified`.
If canonical launch fails, report `blocked` with the concrete failure reason instead of simulating the missing stages or proof artifacts.

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

At a requirement stop, build `agent_skill_organization` directly from `agent_skill_organization_contract`; `preferred_payload` is incomplete until then, and the schema must not be learned through failed retries or runtime source inspection.
```bash
REPO_ROOT='<skill_root>'
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"
DECISION_JSON="$WORKSPACE_ROOT/.vibeskills/tmp/host-decision.json"
mkdir -p "$(dirname "$DECISION_JSON")"

cat > "$DECISION_JSON" <<'JSON'
{
  "decision_kind": "approval_response",
  "decision_action": "approve_requirement",
  "approval_decision": "approve",
  "agent_skill_organization": {
    "schema_version": "agent_skill_organization_v1", "derived_by": "agent", "workflow_level": "L",
    "modules": [{"module_id": "module-a", "goal": "...", "candidate_skill_ids": ["skill-a"], "execution_mode": "skill_assigned", "acceptance_criteria": [{"criterion_id": "module-a-result", "description": "The module result satisfies the frozen requirement.", "verification_mode": "automated"}]}],
    "selected_skills": [{"skill_id": "skill-a", "module_ids": ["module-a"], "responsibility": "...", "reason": "..."}],
    "uncovered_modules": [],
    "workflow_level_contract": {"L": "smallest complete organization", "XL": "bounded multi-lane organization"}
  }
}
JSON

PYTHONPATH="$REPO_ROOT/apps/vgo-cli/src" py -3 -m vgo_cli.main canonical-entry \
  --repo-root "$REPO_ROOT" \
  --artifact-root "$WORKSPACE_ROOT" \
  --prompt "<current user task, verbatim>" \
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

Bounded approvals or revisions must stay inside the surfaced bounded-stage action contract.

At `requirement_doc`, read `runtime-summary.json -> host_user_briefing` and use `host_user_briefing.rendered_text` as the backbone of the user reply. Keep the same field order.
Frame that stop around the Agent-led skill search guide: split the task into modules, search local skills per module, read candidate `SKILL.md`, organize both `L` / `XL` plans, and disclose uncovered modules honestly. Do not surface shortlist size, selected-skill rankings, or raw router ordering at requirement freeze.
Do not ask the user to choose L or XL until the reply explains each task-specific workflow and names the task-specific candidate skill names for that option. Label every named skill as a candidate that is not yet selected or used; formal selection still belongs to the Agent organization produced after requirement approval.

After requirement approval, the Agent must split the approved work into modules, search every declared local skill root for each module, and read each retained candidate's `SKILL.md`. The host must, before entering `xl_plan`, put the validated result in `HostDecisionJson.agent_skill_organization`; route output may remain candidate audit evidence but cannot populate this field. If one selected Skill owns multiple modules, include one `module_assignments` entry per module with the exact module id, an `owner`, `support`, or `verifier` role, module-specific responsibility, one concrete write scope, expected outputs, and verification. Role order is executable: `support` runs before and feeds the `owner`; `verifier` runs only after the `owner`. A post-owner review or minimality check must use `verifier`, not `support`. An `agent_direct` module must declare its own concrete `write_scope`, `expected_outputs`, and `verification`; the runtime must not replace them with a generic module label or restated goal. A task work scope must not claim canonical runtime artifacts such as `module-execution.json`; use a stable task-owned output scope or `no task-file writes` for read-only work. A plan revision that changes modules, Skills, roles, dependencies, write scopes, outputs, verification, or workflow level must resubmit the complete updated `agent_skill_organization`; `revision_delta` alone records text and does not mutate the frozen organization.
Use the directory name that directly contains the retained `SKILL.md` as the exact `skill_id` in both `candidate_skill_ids` and `selected_skills[].skill_id`. A displayed Skill name or frontmatter `name` is descriptive, not an execution identifier. A nested retained `SKILL.md` uses its own containing directory name. Resolve this from the candidate path before submission instead of learning the identifier through failed retries.
Module acceptance criteria must be satisfiable before canonical module-result re-entry. They must not require cleanup receipts, delivery acceptance, or completion-language permission, because canonical `phase_cleanup` creates those only after `module-execution.json` is accepted. Verify ordinary modules from their actual deliverables and normal command or test output. Do not invent task-specific hashes, receipts, ledgers, matrices, scans, or proof files solely to prove execution order, Skill use, or file scope. Only require an extra evidence artifact when the user or domain contract needs that artifact.
After plan approval, reuse the frozen `agent_skill_organization` for `plan_execute` and cleanup, and do not rerun procedural skill selection, silently add skills, or replace declared gaps unless the user revises the frozen requirement or plan. `stage_order` records dependency depth, not permission to run in parallel; L still emits one-unit sequential waves even when independent units share a dependency stage. XL may place at most two dependency-ready units in one wave, and nested or overlapping write scopes must remain serial.

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

Compatibility stage wrappers stay internal-only. If an old caller still sends
one, collapse it to canonical `vibe` before runtime launch and keep it out of
the host-visible skill surface.

## Skill Execution

The frozen `agent_skill_organization` is the only task-skill truth. Before plan
approval, disclose modules, candidates, selected skills and reasons, gaps, and the L / XL difference.

Only selected skills become module-bound execution units. The host must not
invent skills, promote route candidates, hide skill sessions, or open another
requirement/plan/runtime surface. Selection, loading, planning, dispatch, or a
generic manifest is not contribution proof; completion requires observable
module results and the module acceptance defined in `protocols/runtime.md`.
After plan approval, `module-work-plan.json` is the only dispatch authority.
`agent-execution-handoff.json.result_contract` freezes the `module_execution_v1` submission bindings; after handoff, copy `result_contract.submission_template`, preserve every frozen binding, and fill only the result fields. `criterion_results` states must be exactly `passing`, `failing`, or `blocked`. If canonical rejects the format before cleanup, correct the same `module-execution.json` and reuse the same return command instead of creating another handoff. Code-task TDD evidence belongs inside the same `module-execution.json` when the handoff template includes `tdd_evidence`; fill that structured section before canonical return and do not create a separate `tdd-evidence.json` sidecar. The contract is not execution evidence.
The Agent still does the real work and creates `module-execution.json`; required failure, blocking,
missing evidence, or pending human review blocks task completion.

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
- Local skill candidate audit: semantic owner `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`; compatibility bridge `scripts/router/resolve-pack-route.ps1`
- Primary contract metadata: `core/skill-contracts/v1/vibe.json`
