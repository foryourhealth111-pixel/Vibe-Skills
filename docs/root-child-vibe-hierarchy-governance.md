# Root/Child Vibe Hierarchy Governance

This document defines the stable authority model for governed multi-agent `vibe` execution.

## Why This Exists

Recursive use of `$vibe` inside child-agent prompts is desirable for discipline, but dangerous when each child starts behaving like a fresh top-level governed runtime. Without a hierarchy contract, the system risks:

- duplicate requirement freezes
- duplicate execution-plan surfaces
- repeated expert re-dispatch
- ambiguous completion authority
- soft loss of governance despite every lane "using `vibe`"

The fix is not to remove child `$vibe`.
The fix is to distinguish root governance from child execution.

## Mental Model

- Root `vibe`: the only top-level governor
- Child `vibe`: a subordinate execution lane
- Specialist skill: a bounded native helper

Short form:

`root vibe governs, child vibe executes, specialists assist`

## Grade Execution Alignment

- `L`: serial native execution from the frozen plan (sequence-first, no blanket fan-out).
- `XL`: wave-sequential execution, with step-level bounded parallelism only for independent units.
- Specialist dispatch: executable as bounded native units only when root-approved in the frozen plan.

## Authority Layers

### Root-Governed Lane

Only the root-governed lane may:

- freeze the canonical requirement document
- freeze the canonical execution plan
- approve global specialist dispatch
- aggregate overall execution status
- issue final completion claims

### Child-Governed Lane

Child-governed lanes must:

- inherit frozen requirement and plan context from the root lane
- stay inside assigned scope and write boundaries
- emit local receipts and proof only
- escalate when a new specialist is needed outside approved dispatch

Child-governed lanes must not:

- create a second requirement truth
- create a second plan truth
- widen the task silently
- make final completion claims

### Specialist-Native Lane

Specialists are not runtime owners.

They may:

- execute bounded professional subtasks
- preserve native workflow expectations
- preserve native input/output contracts
- emit skill-specific verification notes

They may not:

- take over stage ownership
- replace `vibe` as runtime authority
- create separate top-level planning truth

## Dispatch Model

Approved specialist dispatch is phase-bound rather than “call it whenever”.
The stable phase vocabulary is:

- `pre_execution`
- `in_execution`
- `post_execution`
- `verification`

This keeps expert help aligned with the governed task stage instead of turning specialist calls into ad-hoc afterthoughts.

### Approved Specialist Dispatch

Specialist usage approved by the root-governed lane and written into the frozen plan.

Properties:

- executable without extra authority negotiation
- carried into child-lane inputs
- tracked in execution accounting
- bound to an explicit phase, lane policy, write scope, and review mode

### Local Specialist Suggestion

A child lane may detect that more specialist help is useful. The frozen packet keeps that request as a suggestion first, and the root-governed execute stage may same-round auto-approve safe suggestions without handing authority to the child lane.

Properties:

- advisory in the frozen packet
- executable only after root-governed approval or same-round auto-absorb
- cannot mutate root authority by itself

## Conflict Prevention Rules

To prevent skills from "fighting", the system enforces:

1. one runtime owner
2. one canonical requirement surface
3. one canonical execution-plan surface
4. one final completion authority
5. bounded specialist usage
6. explicit escalation instead of silent self-expansion
7. stage-bound dispatch instead of random specialist timing

## Artifact Rules

Canonical root artifacts:

- `docs/requirements/YYYY-MM-DD-<topic>.md`
- `docs/plans/YYYY-MM-DD-<topic>-execution-plan.md`
- `outputs/runtime/vibe-sessions/<root-run-id>/...`

Child artifacts:

- subordinate receipts and proof nested under the root runtime session
- no child-owned canonical docs

## Safety Properties

This hierarchy must preserve:

- explicit `vibe` runtime authority
- no silent fallback guarantees
- no duplicate truth surfaces
- specialist boundedness
- explicit escalation for new specialist needs
- root-owned completion claims only

## What Success Looks Like

When a root `vibe` task spawns children:

- every child still behaves with `vibe` discipline
- no child behaves like a second top-level governor
- approved specialists can execute as bounded native units
- root evidence remains the single source of completion truth

## Operator Rule Of Thumb

If a child needs a new expert, it may ask.
It may not self-upgrade into a new governor.
