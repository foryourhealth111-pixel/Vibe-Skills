---
name: vibe
description: Vibe Code Orchestrator (VCO) is a governed runtime entry that freezes requirements, plans XL-first execution, and enforces verification and phase cleanup.
---

# Vibe Governed Runtime

`vibe` is a host-syntax-neutral skill contract.

`/vibe`, `$vibe`, and agent-invoked `vibe` all mean the same thing: enter the same governed runtime, not different runtime authorities.

## What `vibe` Does

`vibe` is the official governed runtime for tasks that need:

- requirement clarification before execution
- one-shot autonomous execution with retained governance
- multi-step planning and implementation
- multi-agent XL orchestration
- proof, verification, and mandatory cleanup

This runtime still has one canonical authority: `vibe`.

Hosts may expose discoverable labels such as:

- `Vibe`
- `Vibe: What Do I Want?`
- `Vibe: How Do We Do It?`
- `Vibe: Do It`

Those labels are presentational launch surfaces only.
They do not create a second runtime.

The user does not choose between `M`, `L`, or `XL` as entry branches.
Those grades still exist, but only as internal execution strategy, with only `--l` and `--xl` allowed as lightweight public grade-floor overrides.

## When To Use

Use `vibe` when the task is not a trivial one-line edit and you want the system to:

- inspect the repo and active skeleton first
- clarify or infer intent before building
- freeze a requirement document
- generate an XL-style execution plan
- execute in phases with explicit verification
- clean up phase artifacts and managed node residue

Do not use `vibe` for:

- casual Q and A
- simple explanation-only requests
- tiny edits where governed overhead is unnecessary

## Unified Runtime Contract

`vibe` always runs the same 6-stage state machine:

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

These stages are mandatory.
They may become lighter for simple work, but they are not skipped as a matter of policy.

Discoverable wrapper labels may request an earlier terminal stage.
That changes where the current run stops, not which runtime owns authority.
The bounded stop targets are:

- `Vibe: What Do I Want?` -> `requirement_doc`
- `Vibe: How Do We Do It?` -> `xl_plan`
- `Vibe` and `Vibe: Do It` -> `phase_cleanup`

Official governed entry also records runtime lineage:

- root or child entry writes `governance-capsule.json`
- each validated stage transition appends `stage-lineage.json`
- child-governed startup validates inherited context through `delegation-envelope.json`

## Runtime Mode

### `interactive_governed`

The only supported governed runtime mode.

Use this when the system should still ask the user high-value questions, confirm frozen requirements, and pause at plan approval boundaries.

## Governor And Specialist Contract

`vibe` owns runtime authority even when the canonical router surfaces a specialist skill.

That means:

- router-selected specialist skills may appear as bounded recommendations or route truth
- runtime-selected skill remains `vibe` for governed entry
- specialist help is allowed only as bounded native-mode assistance
- specialist help must preserve the specialist skill's own workflow, inputs, outputs, and validation style
- specialist help must not create a second requirement doc, second plan surface, or second runtime authority

## Root/Child Governance Lanes

For XL delegation, `vibe` runs with hierarchy semantics:

- `root_governed`: the only lane that may freeze canonical requirement and plan surfaces and issue final completion claims
- `child_governed`: subordinate execution lane that inherits frozen context and emits local receipts only

Child-governed lanes must:

- keep `$vibe` at prompt tail to preserve governed discipline
- inherit frozen requirement and plan context from the root lane
- stay within assigned ownership boundaries and write scopes
- validate a root-authored `delegation-envelope.json` and emit a `delegation-validation-receipt.json` before bounded execution

Child-governed lanes must not:

- create a second canonical requirement surface under `docs/requirements/`
- create a second canonical plan surface under `docs/plans/`
- publish final completion claims for the full root task

Specialist dispatch under hierarchy:

- `approved_dispatch`: root-approved specialist usage in the frozen plan
- `local_suggestion`: child-detected specialist suggestion that stays advisory until root escalation approval

## Internal Execution Grades

`M`, `L`, and `XL` remain active, but only as internal orchestration grades.

- `M`: narrow execution, single-agent or tightly scoped work
- `L`: native serial execution lane for staged work; delegated units stay bounded and sequence-first
- `XL`: wave-sequential execution with step-level bounded parallelism for independent units only

The governed runtime selects the internal grade after `deep_interview` and before `plan_execute`.

User-facing behavior stays the same regardless of host syntax:

- one governed runtime authority
- one frozen requirement surface
- one XL-style plan surface
- one execution and cleanup contract
- optional discoverable intent labels that still resolve to canonical `vibe`

Compatibility notes for downstream verification and host adapters:

- `M=single-agent`
- `L=serial native execution from frozen plan (no blanket fan-out).`
- `XL=wave-sequential execution; bounded parallelism only inside eligible steps.`
- XL native lifecycle APIs remain `spawn_agent`/`send_input`/`wait`/`close_agent`

## Stage Contract

### 1. `skeleton_check`

Check repo shape, active branch, existing plan or requirement artifacts, and runtime prerequisites before starting.

### 2. `deep_interview`

Produce a structured intent contract containing:

- goal
- deliverable
- constraints
- acceptance criteria
- product acceptance criteria
- manual spot checks
- completion language policy
- delivery truth contract
- non-goals
- autonomy mode
- inferred assumptions

In `interactive_governed`, this stage may ask direct questions.

### 3. `requirement_doc`

Freeze a single requirement document under `docs/requirements/`.

After this point, execution should trace back to the requirement document rather than to raw chat history.

### 4. `xl_plan`

Write the execution plan under `docs/plans/`.

The plan must contain:

- internal grade decision
- wave or batch structure
- ownership boundaries
- verification commands
- delivery acceptance plan
- completion language rules
- rollback rules
- phase cleanup expectations

### 5. `plan_execute`

Execute the approved plan.

L grade executes planned units serially in the native governed lane.
XL grade executes waves sequentially and may run only independent units in bounded parallel within a step.
If subagents are spawned, their prompts must end with `$vibe`.
If specialist skills are used, execute them as bounded native dispatch units only when root-approved in the frozen plan; otherwise keep them as advisory `local_suggestion` until escalation approval.
If subagents run in child-governed lanes, they must inherit root-frozen context and must not reopen canonical requirement or plan truth surfaces.

### 6. `phase_cleanup`

Cleanup is part of the runtime, not an afterthought.

Each phase must leave behind:

- cleanup receipt
- temp-file cleanup result
- node audit or cleanup result
- proof artifacts needed for later verification
- delivery-acceptance report proving whether full completion wording is allowed

## Router And Runtime Authority

The canonical router remains authoritative for route selection.

`vibe` does not create a second router.
It consumes the canonical route, confirm, unattended, and overlay surfaces and then executes the governed runtime contract around them.

Rules:

- explicit user tool choice still overrides routing
- `confirm_required` still uses the existing white-box `user_confirm interface`
- unattended behavior is mapped into governed runtime mode, not into a separate control plane
- provider-backed intelligence may advise but must not replace route authority

## Compatibility With Process Layers

Other workflow layers may shape discipline, but they must not become a parallel runtime.

Required ownership split:

- canonical router: route authority
- `vibe`: governed runtime authority
- host bridge: hidden hook wiring and artifact persistence
- superpowers or other process helpers: discipline and workflow advice only

Forbidden outcomes:

- second visible startup/runtime prompt surface
- second requirement freeze surface
- second execution-plan surface
- second route authority

## Protocol Map

Read these protocols on demand:

- `protocols/runtime.md`: governed runtime contract and stage ownership
- `protocols/think.md`: planning, research, and pre-execution analysis
- `protocols/do.md`: coding, debugging, and verification
- `protocols/review.md`: review and quality gates
- `protocols/team.md`: XL multi-agent orchestration
- `protocols/retro.md`: retrospective and learning capture

## Learn And Retro Surface

For LEARN / retrospective work, use the `Context Retro Advisor` vocabulary from `protocols/retro.md`.

- retro outputs should preserve `CER format` artifacts when that protocol is invoked
- completion-language corrections remain governed and evidence-backed

## Memory Rules

Memory remains runtime-neutral:

- `state_store (runtime-neutral)`: default session memory
- Serena: explicit decisions only
- ruflo: optional short-horizon vector memory
- Cognee: optional long-horizon graph memory
- episodic memory: disabled in governed routing

## Quality Rules

Never claim success without evidence.

Minimum invariants:

- verification before completion
- no silent no-regression claims
- requirement and plan artifacts remain traceable
- cleanup receipts are emitted before phase completion is claimed

## Outputs

The governed runtime should leave behind:

- `outputs/runtime/vibe-sessions/<run-id>/skeleton-receipt.json`
- `outputs/runtime/vibe-sessions/<run-id>/intent-contract.json`
- `docs/requirements/YYYY-MM-DD-<topic>.md`
- `docs/plans/YYYY-MM-DD-<topic>-execution-plan.md`
- `outputs/runtime/vibe-sessions/<run-id>/phase-*.json`
- `outputs/runtime/vibe-sessions/<run-id>/cleanup-receipt.json`
- specialist recommendation and dispatch accounting when bounded specialist help is planned

## Known Boundaries

- the canonical router still owns route selection
- install or check surfaces should not be rebaselined casually
- host adapters may shape capability declarations, but must not fork runtime truth
- benchmark autonomy does not mean governance-free execution

## Maintenance

- Runtime family: governed-runtime-first
- Version: 3.0.1
- Updated: 2026-04-09
- Canonical router: `scripts/router/resolve-pack-route.ps1`
- Primary contract metadata: `core/skill-contracts/v1/vibe.json`
