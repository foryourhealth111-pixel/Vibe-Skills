# Root/Child Vibe Hierarchy Governance

This document defines the stable authority model for governed multi-agent `vibe` execution.

## Why This Exists

Recursive use of `$vibe` inside child-agent prompts is desirable for discipline, but dangerous when each child starts behaving like a fresh top-level governed runtime. Without a hierarchy contract, the system risks:

- duplicate requirement freezes
- duplicate execution-plan surfaces
- repeated Skill reorganization
- ambiguous completion authority
- soft loss of governance despite every lane "using `vibe`"

The fix is not to remove child `$vibe`.
The fix is to distinguish root governance from child execution.

## Mental Model

- Root `vibe`: the only top-level governor
- Child `vibe`: a subordinate execution lane
- Agent: the executor of approved module work
- Skill: module-bound workflow guidance, never runtime authority

Short form:

`root vibe governs, child vibe stays subordinate, the Agent executes approved modules`

## Grade Execution Alignment

- `L`: serial execution of approved module work units (sequence-first, no blanket fan-out).
- `XL`: wave-sequential execution, with step-level bounded parallelism only for independent units.
- Both grades use the same module plan, handoff, result, and acceptance chain.

## Authority Layers

### Root-Governed Lane

Only the root-governed lane may:

- freeze the canonical requirement document
- freeze the canonical execution plan
- approve the global Skill organization and module plan
- aggregate overall execution status
- issue final completion claims

### Child-Governed Lane

Child-governed lanes must:

- inherit frozen requirement and plan context from the root lane
- stay inside assigned scope and write boundaries
- emit local receipts and proof only
- escalate when a new Skill is needed outside the approved module plan

Child-governed lanes must not:

- create a second requirement truth
- create a second plan truth
- widen the task silently
- make final completion claims

### Agent Module Execution

After plan approval, the current Agent receives temporary control of the approved module work.

The Agent must:

- execute only the work units in `agent-execution-handoff.json`
- read and follow each Skill assigned to a work unit
- record work-unit results and evidence in `module-execution.json`
- return those results through the canonical `vibe` entry

The Agent must not:

- change the frozen requirement or module plan while executing
- treat Skill selection or handoff as proof of a result
- claim task completion before `vibe` accepts the returned module results

## Control And Result Chain

The governed execution chain is:

```text
agent_skill_organization
-> module-work-plan.json
-> execution-manifest.json: module_handoff
-> agent-execution-handoff.json
-> module-execution.json
-> canonical vibe acceptance and cleanup
```

Each artifact has one job:

- `module-work-plan.json` is the approved scheduling authority. It defines modules, dependencies, work units, Skill assignments, and acceptance criteria.
- `module_handoff` records that execution control has moved to the Agent and summarizes the approved work units.
- `agent-execution-handoff.json` gives the Agent the exact units, waves, boundaries, and canonical return path.
- `module-execution.json` records actual work-unit and module results. It is the result input for acceptance; the handoff itself is not a result.

Root and child lanes use this same chain. The difference is authority: a root lane can own canonical truth and final completion, while a child lane can only execute its inherited assignment and return local results.

## Skill Organization And Escalation

Skills are selected for modules before the module plan is frozen. A selected Skill contributes workflow guidance to its assigned work unit; it does not become a runtime lane or gain governance authority.

A child lane may detect that another Skill is needed. The request remains a suggestion until the root Agent explicitly updates the Skill organization and a new module plan is frozen.

Properties:

- advisory in the frozen packet
- executable only after explicit root approval and a newly frozen module plan
- cannot mutate root authority by itself

## Conflict Prevention Rules

To prevent skills from "fighting", the system enforces:

1. one runtime owner
2. one canonical requirement surface
3. one canonical execution-plan surface
4. one final completion authority
5. module-bound Skill usage
6. explicit escalation instead of silent self-expansion
7. explicit handoff and result return instead of implicit execution

## Artifact Rules

Canonical root artifacts:

- `docs/requirements/YYYY-MM-DD-<topic>.md`
- `docs/plans/YYYY-MM-DD-<topic>-execution-plan.md`
- `outputs/runtime/vibe-sessions/<root-run-id>/module-work-plan.json`
- `outputs/runtime/vibe-sessions/<root-run-id>/execution-manifest.json`
- `outputs/runtime/vibe-sessions/<root-run-id>/agent-execution-handoff.json`
- `outputs/runtime/vibe-sessions/<root-run-id>/module-execution.json`

Child artifacts:

- subordinate handoff, result, receipts, and proof tied to the root run
- no child-owned canonical docs

## Safety Properties

This hierarchy must preserve:

- explicit `vibe` runtime authority
- no silent fallback guarantees
- no duplicate truth surfaces
- one approved module plan as execution authority
- visible transfer and return of execution control
- module results, not Skill selection, as completion evidence
- explicit escalation for new Skill needs
- root-owned completion claims only

## What Success Looks Like

When a root `vibe` task spawns children:

- every child still behaves with `vibe` discipline
- no child behaves like a second top-level governor
- the Agent executes only approved module work units
- child results return through `module-execution.json`
- root evidence remains the single source of completion truth

## Operator Rule Of Thumb

If a child needs another Skill, it may ask.
It may not self-upgrade into a new governor.
