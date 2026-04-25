---
name: vibe
description: Vibe Code Orchestrator (VCO) is a governed runtime entry that freezes requirements, plans XL-first execution, and enforces verification and phase cleanup.
---
<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Vibe skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **vibe skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool for public discoverable skills that are explicitly exposed in the current Claude host registry. Exception: when governed `vibe` routes an internal specialist and declares a real `native_skill_entrypoint` path such as `.../SKILL.runtime-mirror.md`, do not rewrite that path into `Skill(<skill-id>)` unless that skill name is visibly registered in the current host session. In that case the disclosed `native_skill_entrypoint` path is the source of truth for same-session specialist loading, and reading that declared path is allowed.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In OpenCode:** Use the `skill` tool. OpenCode natively supports skills from `.claude/skills/`, `.opencode/skills/`, and `.agents/skills/`. Invoke via `skill({ name: "skill-name" })`.

**In other environments:** Check your platform's documentation for how skills are loaded.


## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |


# Vibe Governed Runtime

## Mandatory Router Invocation With Intent Optimization

When AI activates (reads and acts on) the `vibe` skill, AI MUST call the canonical
router before entering any governed runtime stage. This is not an automatic trigger --
it is a mandatory self-discipline requirement.

Canonical router: `scripts/router/resolve-pack-route.ps1`

### Router Input: Extract Core Intent as Keyword Text

When calling the router, AI must NOT pass the raw user prompt, language mix, or full
context. Instead, AI must extract and distill the core intent into a structured keyword
text block. This improves router intent hit rate.

Prompt extraction rules:
1. Extract nouns/verbs that describe the WORK TYPE (e.g., "refactor", "debug", "plan", "review", "research", "implement")
2. Extract nouns that describe the DOMAIN/TECHNOLOGY (e.g., "typescript", "react", "database", "api")
3. Extract nouns that describe the DELIVERABLE (e.g., "feature", "fix", "migration", "documentation")
4. Remove filler language, politeness, meta-commentary, and system-level framing
5. If the user gave explicit constraints or requirements, encode them as keyword tags

Bad example (raw prompt passed through):
"Hi! I've been working on a React project lately and sometimes I encounter some performance issues, like component re-rendering problems. Could you help me analyze and give optimization suggestions? Thank you so much!"

Good example (keyword text extracted):
"debug performance-react component-re-render optimization analysis coding typescript react"

Required router call steps at vibe entry:
1. Extract core intent as keyword text (do NOT pass raw prompt)
2. Call router with extracted keyword text
3. If route_mode == "confirm_required", present confirm surface to user
4. If router returns hazard alert or fallback_active, surface it explicitly
5. If router call fails, report "blocked" with failure reason -- do NOT continue

The fact that the router may internally enter "auto_route" mode does NOT mean the
router was skipped. The router was called and made that decision. AI must invoke
it explicitly every time.

### Continuation-Aware Router Input

When continuing a prior run that records a legacy compatibility entry ID such as
`vibe-what-do-i-want`, `vibe-how-do-we-do`, or `vibe-do-it`, do not pretend this is a brand-new task if the same thread
already has a verified governed requirement or plan. These IDs are retained as non-public compatibility metadata, not as host-visible public entries.

Continuation rules:
1. Reuse the latest verified frozen requirement/plan from the same thread or workspace as continuation context when it exists.
2. Build the router keyword text from the frozen goal, deliverable, constraints, and capability hints plus the current delta, not from a bare summary such as `execute plan`.
3. Treat previously frozen requirement/plan facts as authoritative context for deliverable, constraints, and capability coverage.
4. Reopen generic clarification only when the user changed scope, the frozen artifacts are missing, or the prior artifacts are clearly stale or mismatched.

Bad continuation example:
`execute plan facial-recognition phase-cleanup`

Better continuation example:
`execute governed-plan facial-recognition dataset-download literature-review few-shot-modeling training evaluation latex-paper gpu-aware constraints-public-dataset deliverable-report-and-paper`

## Canonical Bootstrap

Bootstrap sequence (run canonical launch before reading repo files, protocol docs, or writing any artifact):

1. Resolve `skill_root` (directory containing this `SKILL.md`) and `workspace_root` (current task working root; governed artifacts go here when working outside the Vibe installation).
2. Resolve host adapter id: `codex` in Codex, `claude-code` in Claude Code, `cursor` in Cursor, `windsurf` in Windsurf, `openclaw` in OpenClaw, `opencode` in OpenCode.
3. Launch the proof-complete canonical entry.

Windows PowerShell launch (primary):

```powershell
$env:PYTHONPATH = "<skill_root>/apps/vgo-cli/src"
py -3 -m vgo_cli.main canonical-entry `
  --repo-root "<skill_root>" `
  --artifact-root "<workspace_root>" `
  --host-id "<host_id>" `
  --entry-id "vibe" `
  --prompt "<extracted keyword intent text>"
```

If `py -3` is unavailable, try `python` instead.

If you must invoke PowerShell through a Bash-like tool surface, do not place `$env:PYTHONPATH=...` inside a double-quoted `-Command` string. The outer shell can expand `$env` first and corrupt it to `:PYTHONPATH`, leaving `PYTHONPATH` unset and causing `ModuleNotFoundError: No module named 'vgo_cli'`. In that situation, either set `PYTHONPATH=...` in the outer shell before invoking `py -3 -m ...`, or single-quote / escape the PowerShell payload so `$env:` reaches PowerShell literally.

Public discoverable entries still enter canonical `vibe`; only the bounded stop contract changes:
- `vibe` uses progressive governed stops: first `requirement_doc`, then `xl_plan`, then `phase_cleanup` after explicit re-entry approval at each boundary
- `vibe-upgrade` is the public governed upgrade entry.
- compatibility stage IDs are non-public and must not be materialized as host-visible command or skill wrappers: `vibe-what-do-i-want` -> `requirement_doc`, `vibe-how-do-we-do` -> `xl_plan --requested-grade-floor XL`, `vibe-do-it` -> `phase_cleanup`

Hard rules:
- Do not inspect the repo, protocol docs, or prior run outputs before canonical launch returns, except to resolve `skill_root` and current host id.
- Do not use the Vibe installation root as the governed artifact root when the user asked you to work in another workspace or repository.
- Do not manually create `outputs/runtime/vibe-sessions/<run-id>/`, `docs/requirements/`, or `docs/plans/` as a substitute for launch.
- Do not search the current workspace, repository, or install root for canonical proof files before launch; those artifacts are emitted by canonical-entry after the run session is created.
- Only validate canonical proof artifacts after canonical-entry returns a `session_root`, and only against that launched session root.
- Do not simulate stages, claim canonical entry from reading this file or wrapper text, or silently continue if canonical launch fails -- report `blocked` with the concrete failure reason.

Proof of canonical launch is post-launch and requires: `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json` under the returned `session_root`.

`vibe` is a host-syntax-neutral skill contract. `/vibe`, `$vibe`, and agent-invoked `vibe` all mean the same thing: enter the same governed runtime.

## Unified Runtime Contract

`vibe` always runs the same 6-stage state machine:

1. `skeleton_check` -- verify repo shape, prerequisites, and existing artifacts
2. `deep_interview` -- clarify intent and infer constraints
3. `requirement_doc` -- freeze the single requirement source under `docs/requirements/`
4. `xl_plan` -- write execution plan under `docs/plans/`
5. `plan_execute` -- execute from the frozen plan
6. `phase_cleanup` -- cleanup temp artifacts, write receipts, delivery-acceptance report

These stages are mandatory. They may become lighter for simple work, but they are not skipped as a matter of policy.

Runtime mode: only `interactive_governed` is supported. The system asks high-value questions, confirms frozen requirements, and pauses at plan approval boundaries.

If a canonical run returns `bounded_return_control.explicit_user_reentry_required = true`, stop in the current assistant turn and hand control back to the user. Do not consume the returned re-entry credentials until a later user message explicitly approves or revises the frozen requirement/plan boundary.

Structured host decision SOP:
- Do not ask the user to repeat magic words such as `approve`, `continue`, `1`, or `enter unattended mode` just to satisfy routing or bounded re-entry.
- For complex or obviously multi-part work, the host should decompose the task into execution phases before launch. Keep that decomposition inside `--host-decision-json -> phase_decomposition` so canonical `vibe` can freeze it under the single requirement/plan surface. Do not create a second runtime, second requirement doc, or second plan.
- If the surfaced specialist set needs curation, keep it inside `--host-decision-json -> specialist_dispatch_decision`. Host curation stays bounded to the surfaced recommendation ids from the current governed run; do not invent unsurfaced specialists or bypass runtime validation.
- For routing confirmation, inspect the returned machine-readable route contract under `runtime-summary.json -> host_user_briefing.route_decision_contract` when present. Convert the user's natural-language reply into a structured route decision and relaunch canonical `vibe` with `--host-decision-json`.
- For bounded stage re-entry, inspect `runtime-summary.json -> bounded_return_control.host_decision_contract` when present. Convert the user's natural-language approval or revision into a structured decision and relaunch canonical `vibe` with `--host-decision-json`, `--continue-from-run-id`, and `--bounded-reentry-token`.
- Route decisions must stay inside the surfaced confirm options. Bounded stage approvals must stay inside the surfaced approval action contract. Specialist curation must stay inside the surfaced specialist recommendation ids. Runtime validation remains authoritative.
- Keep the task context stable across re-entry. Do not reduce the next canonical launch prompt to the user's short approval text alone when the governed task context is already known.

Public wrapper entries remain limited to `vibe` and `vibe-upgrade`.
Non-public compatibility stage metadata may request an earlier terminal stage (that changes where a legacy run stops, not which runtime owns authority):
- `vibe-what-do-i-want` -> `requirement_doc`
- `vibe-how-do-we-do` -> `xl_plan`
- `vibe` progresses through `requirement_doc -> xl_plan -> phase_cleanup`
- `vibe-do-it` -> `phase_cleanup`

Official governed entry records lineage:
- root or child entry writes `governance-capsule.json`
- each validated stage transition appends `stage-lineage.json`
- child-governed startup validates inherited context through `delegation-envelope.json`

The user does not choose between `M`, `L`, or `XL` as entry branches. Those grades exist only as internal execution strategy; only `--l` and `--xl` are allowed as lightweight public grade-floor overrides.

## Governor And Specialist Contract

`vibe` owns runtime authority even when the canonical router surfaces a specialist skill.

That means:
- governed `vibe` runs must surface bounded specialist recommendations and treat router-selected specialist skills as route truth or executable recommendation candidates
- direct specialist handling should stay in the current host session by default; do not create hidden specialist sub-sessions unless policy explicitly opts back into that bridge path
- runtime-selected skill remains `vibe` for governed entry
- eligible specialist help MUST be promoted (elevated) into bounded native-mode dispatch as the default governance policy unless a valid structured host specialist dispatch decision curates the surfaced set
- host orchestration power is bounded: it may approve, defer, or reject only surfaced specialist recommendation ids, and runtime validation still decides blocked/degraded outcomes
- specialist help must preserve the specialist skill's own workflow, inputs, outputs, and validation style
- specialist help must not create a second requirement doc, second plan surface, or second runtime authority

## Root/Child Governance Lanes

For XL delegation, `vibe` runs with hierarchy semantics:

- `root_governed`: the only lane that may freeze canonical requirement and plan surfaces and issue final completion claims
- `child_governed`: subordinate execution lane that inherits frozen context and emits local receipts only

Child-governed lanes must: keep `$vibe` at prompt tail, inherit frozen requirement and plan context, stay within assigned ownership boundaries and write scopes, and validate a root-authored `delegation-envelope.json` before bounded execution.

Child-governed lanes must not: create a second canonical requirement or plan surface, or publish final completion claims for the full root task.

Specialist dispatch under hierarchy:
- `approved_dispatch`: root-approved specialist usage in the frozen plan
- `local_suggestion`: residual child-detected specialist suggestion that only remains advisory when blocked, degraded, or explicitly forced to escalate

## Internal Execution Grades

`M`, `L`, and `XL` remain active, but only as internal orchestration grades.

- `M`: narrow execution, single-agent or tightly scoped work
- `L`: native serial execution lane for staged work; delegated units stay bounded and sequence-first
- `XL`: wave-sequential execution with step-level bounded parallelism for independent units only

The governed runtime selects the internal grade after `deep_interview` and before `plan_execute`. User-facing behavior stays the same regardless of host syntax: one governed runtime authority, one frozen requirement surface, one XL-style plan surface, one execution and cleanup contract.

## Stage Contract

### 1. `skeleton_check`

Check repo shape, active branch, existing plan or requirement artifacts, and runtime prerequisites before starting. Produce a skeleton receipt.

### 2. `deep_interview`

Produce a structured intent contract containing: goal, deliverable, constraints, acceptance criteria, product acceptance criteria, manual spot checks, completion language policy, delivery truth contract, non-goals, autonomy mode, inferred assumptions. In `interactive_governed`, this stage may ask direct questions.

### 3. `requirement_doc`

Freeze a single requirement document under `docs/requirements/`. After this point, execution traces back to this document rather than to raw chat history.

### 4. `xl_plan`

Write the execution plan under `docs/plans/`. The plan must contain: internal grade decision, wave or batch structure, ownership boundaries, verification commands, delivery acceptance plan, completion language rules, rollback rules, phase cleanup expectations.

### 5. `plan_execute`

Execute from the approved plan. L grade executes serially; XL grade executes waves sequentially with bounded parallel independent units only. Spawned subagent prompts must end with `$vibe`. Bounded specialist recommendations must be promoted into native dispatch units per the skill promotion policy; only blocked, degraded, or forced-escalation cases remain `local_suggestion`. Child-governed lanes inherit root-frozen context and must not reopen canonical requirement or plan truth surfaces.

### 6. `phase_cleanup`

Each phase must leave behind: cleanup receipt, temp-file cleanup result, node audit or cleanup result, proof artifacts needed for later verification, delivery-acceptance report proving whether full completion wording is allowed.

## Router Invocation At Entry

See "Mandatory Router Invocation With Intent Optimization" above for the required router call protocol (intent extraction + mandatory invocation). This section covers how vibe consumes the router output.

Rules:
- always extract core intent as keyword text before calling router (never pass raw prompt)
- explicit user tool choice overrides routing
- `confirm_required` surfaces via existing user_confirm interface
- unattended behavior maps to governed runtime mode, not a separate control plane
- provider-backed intelligence may advise but must not replace route authority
- the router may internally enter "auto_route" mode when confidence exceeds threshold -- this is a router-internal behavior, not evidence that AI skipped the router call

## Protocol Map

Read these protocols on demand:
- `protocols/runtime.md`: governed runtime contract and stage ownership
- `protocols/think.md`: planning, research, and pre-execution analysis
- `protocols/do.md`: coding, debugging, and verification
- `protocols/review.md`: review and quality gates
- `protocols/team.md`: XL multi-agent orchestration
- `protocols/retro.md`: retrospective and learning capture; retro outputs should preserve `CER format` artifacts when that protocol is invoked; completion-language corrections remain governed and evidence-backed

## Quality Rules

Never claim success without evidence. Minimum invariants:
- verification before completion
- no silent no-regression claims
- requirement and plan artifacts remain traceable
- cleanup receipts are emitted before phase completion is claimed
- Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry; canonical vibe claims require `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json`

### Failure Exposure And Fallback Discipline

- Do not introduce new fallback, degraded-success, or boundary behavior just to keep a path running when it would otherwise fail.
- Do not add mock success paths, template-only success outputs, swallowed errors, or any other fake-success behavior that hides the root cause.
- Prefer full exposure: surface real failures with explicit errors, exceptions, logs, failing verification, or downgraded closure wording instead of pretending the primary path succeeded.
- Only introduce or retain fallback / degraded behavior when the active requirement explicitly asks for it.
- Any allowed fallback or boundary behavior must be explicit, traceable in artifacts or logs, documented in the relevant contract or requirement surface, and easy to disable.
- Fallback or boundary behavior must not be used to bypass real execution, verification, or root-cause repair.

## Outputs

The governed runtime should leave behind:
- `outputs/runtime/vibe-sessions/<run-id>/skeleton-receipt.json`
- `outputs/runtime/vibe-sessions/<run-id>/intent-contract.json`
- `outputs/runtime/vibe-sessions/<run-id>/runtime-input-packet.json` with `route_snapshot` and specialist surfaces
- `docs/requirements/YYYY-MM-DD-<topic>.md`
- `docs/plans/YYYY-MM-DD-<topic>-execution-plan.md`
- `outputs/runtime/vibe-sessions/<run-id>/phase-*.json`
- `outputs/runtime/vibe-sessions/<run-id>/cleanup-receipt.json`
- specialist recommendation and dispatch accounting when bounded specialist help is planned
- canonical host-entry receipts (`host-launch-receipt.json`)

## Known Boundaries

- canonical router must be called at vibe entry (mandatory self-discipline, not auto-trigger); router may enter auto_route mode internally -- this does NOT mean AI skips the router call
- memory remains runtime-neutral: `state_store` (default session), `Serena` (explicit decisions only), `ruflo` (optional short-horizon), `Cognee` (optional long-horizon), episodic memory disabled in governed routing
- install or check surfaces should not be rebaselined casually
- host adapters may shape capability declarations but must not fork runtime truth
- benchmark autonomy does not mean governance-free execution
- other workflow layers may shape discipline but must not become a parallel runtime; explicitly forbidden: second visible runtime entry surface, second requirement freeze surface, second execution-plan surface, second route authority

## Maintenance

- Runtime family: governed-runtime-first
- Version: 3.0.4
- Updated: 2026-04-19
- Canonical router: `scripts/router/resolve-pack-route.ps1`
- Primary contract metadata: `core/skill-contracts/v1/vibe.json`
