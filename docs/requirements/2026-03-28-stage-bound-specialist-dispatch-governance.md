# Stage-Bound Specialist Dispatch Governance

## Summary
Extend the governed `vibe` runtime so specialist skills are no longer just recommended or counted, but are frozen as stage-bound execution contracts with explicit authority, phase binding, lane policy, write scope, and verification expectations. The design must preserve one runtime owner while making specialist skills materially useful during real work.

## Goal
Implement a governed specialist-dispatch model where:

- `vibe` remains the sole runtime authority for requirement freeze, plan freeze, execution receipts, verification, and cleanup.
- specialist skills are routed as candidates, approved as bounded dispatch contracts, and executed in the correct runtime phase.
- `L` executes specialist help as explicit serial native steps.
- `XL` executes specialist help as bounded child lanes, including parallel specialist lanes only when write scopes and governance rules allow it.
- child `vibe` lanes can surface new specialist suggestions without gaining top-level authority.

## Deliverable
A repository change set and documentation bundle that adds:

- machine-readable specialist binding policy for phase binding, lane policy, write scope, and review mode
- frozen runtime-input specialist contracts carrying stage-bound execution metadata
- requirement and plan surfaces that document phase-bound specialist dispatch
- runtime topology support for `pre_execution`, `in_execution`, `post_execution`, and `verification` specialist phases
- `L` serial specialist execution and `XL` bounded-parallel specialist lane execution
- manifest accounting and proof surfaces that show where specialist work ran and under what authority
- runtime-neutral tests and proof artifacts that demonstrate stability, usability, and intelligent specialist use

## Constraints
- Do not create a second router, second requirement truth, second plan truth, or second runtime owner.
- Keep `runtime_selected_skill=vibe` for explicit governed entry.
- Do not let specialist skills self-approve or self-upgrade into global runtime authority.
- Preserve native specialist workflow, input contract, expected outputs, and validation style.
- Allow parallel specialist execution only under root governance, only in `XL`, and only for disjoint write scopes.
- Keep child local specialist suggestions advisory-first and escalation-first unless the existing same-round root auto-absorb gate approves them.

## Acceptance Criteria
- Runtime input packet recommendations carry specialist binding metadata:
  - `binding_profile`
  - `dispatch_phase`
  - `execution_priority`
  - `lane_policy`
  - `parallelizable_in_root_xl`
  - `write_scope`
  - `review_mode`
- Requirement documents surface specialist binding truth, not only skill names.
- Execution plans surface a concrete specialist dispatch plan with phase binding, lane policy, and write scope.
- `L` topology no longer lumps approved specialists into one generic final step; specialist units appear as phase-bound serial steps.
- `XL` topology can place eligible specialists into bounded parallel steps while preserving serial fallback for conflicting scopes.
- Execution manifests expose phase-binding and specialist topology evidence sufficient to prove where and how specialists ran.
- Existing root/child hierarchy guarantees remain true:
  - child cannot freeze canonical requirement or plan
  - child cannot make final completion claims
  - zero-overlap new specialist suggestions remain escalation-only
  - same-round absorb still requires root-owned approval semantics

## Primary Objective
Make specialist skills useful inside `vibe` without letting them blur runtime ownership or fight each other.

## Proxy Signal
Specialist skills are invoked neither randomly nor only in theory. They appear in frozen runtime packets, are bound to explicit phases, execute in bounded lanes, and leave manifest evidence proving whether they ran live, degraded, serially, or in bounded parallel.

## Scope
In scope:
- runtime-input packet specialist binding policy
- requirement/plan surfacing
- execution-topology specialist phase placement
- manifest and proof accounting
- runtime-neutral test expansion
- stable governance documentation

Out of scope:
- redesigning canonical router scoring
- host-wide interception of non-`vibe` entrypoints
- granting child lanes top-level planning authority
- unbounded automatic expert fan-out

## Completion
The work is complete when explicit `vibe` runs can freeze, plan, and execute phase-bound specialist help with artifact-backed proof that the result is stable, usable, and governed.

## Evidence
- updated config/runtime/protocol/test surfaces
- new or updated requirement, plan, and stable governance docs
- passing targeted runtime-neutral tests
- replay or proof artifacts showing serial and bounded-parallel specialist execution

## Non-Goals
- Do not make every specialist recommendation executable by default.
- Do not make `$vibe` inside child lanes mean “child may govern everything”.
- Do not hide degraded specialist execution behind success wording.

## Autonomy Mode
interactive_governed

## Assumptions
- Existing ranked specialist recommendations are sufficient to seed deterministic phase binding.
- Binding profiles can be kept simple and deterministic at first by classifying specialists into planning, implementation, deliverable, and verification phases.
- Current bounded parallel scheduler already provides enough machinery to support specialist parallel lanes once dispatch units expose proper write scopes and parallel eligibility.

## Evidence Inputs
- Source task: make specialist skills useful inside `vibe` without conflict or authority drift
