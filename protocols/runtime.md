# vibe-runtime Protocol

> **What this protocol does -- plain language overview**
>
> Every time you invoke `/vibe` or `$vibe`, the system runs this 6-stage process.
> You do not need to read this document to use VibeSkills -- it is reference material
> for contributors and advanced users who want to understand the runtime internals.
>
> **The 6 stages in plain terms:**
>
> | Stage | Internal name | What happens |
> |:---:|:---|:---|
> | 1 | `skeleton_check` | Check what is already in your repo before starting |
> | 2 | `deep_interview` | Clarify what you actually want (ask questions or infer) |
> | 3 | `requirement_doc` | Lock the agreed requirements into a document |
> | 4 | `xl_plan` | Write the execution plan |
> | 5 | `plan_execute` | Execute the plan |
> | 6 | `phase_cleanup` | Clean up temp artifacts and produce a final report |
>
> **Key terms used below:**
> - **Canonical router**: The internal logic that picks which skill handles your task.
> - **Root/Child lane**: In multi-agent tasks, "root" is the coordinator; "child" lanes are workers. Only root makes final completion claims.
> - **Frozen requirement/plan**: Once you approve the requirements or plan, they are locked -- the system will not silently change scope.
> - **Proof bundle**: Evidence that a task was actually completed -- test results, output logs, verification commands.
> - **Silent fallback**: Quietly switching to a degraded path without telling the user -- this is explicitly forbidden.


Governed runtime contract for `vibe`.

This protocol defines the user-facing runtime path that all host syntaxes share.
It does not replace the canonical router.
It defines what must happen after `vibe` is selected.

## Runtime Identity

`vibe` is one skill contract across all hosts:

- `/vibe`
- `$vibe`
- agent-invoked `vibe`

These are syntax variants for the same governed runtime, not separate entrypoints.

## Contract Priorities

1. Canonical router authority stays intact.
2. User-facing runtime path stays fixed.
3. `M`, `L`, `XL` remain internal execution grades only.
4. Requirement freezing happens before plan execution.
5. Cleanup is mandatory before a phase is considered complete.
6. Silent fallback and silent degradation are forbidden.
7. Fallback success is non-authoritative unless a requirement explicitly approves otherwise.
8. `L` runs serial native units; `XL` runs wave-sequential with step-level bounded parallel units only when dependency-safe.

## Official Runtime Modes

### `interactive_governed`

The only supported mode.

- ask direct high-value questions when needed
- freeze a requirement document with user-visible assumptions
- allow approval boundaries before execution

## Runtime Lineage Artifacts

Official governed entry is runtime-validated with artifact-backed lineage:

- `governance-capsule.json`: root-authored runtime authority capsule for the governed run
- `stage-lineage.json`: ordered stage-transition ledger for the current run
- `host-launch-receipt.json`: host-facing canonical entry receipt that must be `verified` before claiming canonical vibe entry
- `host-stage-disclosure.json`: append-only host-consumption event stream for confirmed specialist activity across discussion, planning, and execution
- `delegation-envelope.json`: root-authored child startup contract for inherited requirement/plan truth
- `delegation-validation-receipt.json`: child proof that envelope validation passed before bounded execution

These artifacts strengthen the official governed path only.
They do not claim OS-level or arbitrary shell-session enforcement.

Reading `SKILL.md`, wrapper markdown, or bootstrap text alone is not proof of canonical vibe entry.
Canonical claims require `host-launch-receipt.json`, `runtime-input-packet.json`, `governance-capsule.json`, and `stage-lineage.json`.

## Fixed 6-Stage State Machine

### Stage 1: `skeleton_check`

Purpose:

- verify repo skeleton and governed runtime prerequisites
- discover active requirement or plan artifacts
- detect conflicting dirty-state conditions

Required outputs:

- skeleton receipt
- repo-state summary

### Stage 2: `deep_interview`

Purpose:

- transform raw task text into a structured intent contract

Required fields:

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
- open questions
- inference notes

### Stage 3: `requirement_doc`

Purpose:

- freeze the single requirement source for the run

Rules:

- write under `docs/requirements/`
- execution and review trace back to this document
- freeze downstream delivery semantics here, including product acceptance criteria, manual spot checks, and completion-language limits
- when the canonical anti-proxy-goal-drift policy is active, governed requirement packets must carry its declared objective, proxy-signal, scope, abstraction, completion, and evidence fields

### Stage 4: `xl_plan`

Purpose:

- generate the execution plan under `docs/plans/`

Required contents:

- internal execution grade
- wave or batch structure
- ownership map
- verification commands
- delivery acceptance plan
- completion-language downgrade rules
- rollback strategy
- cleanup expectations
- when the canonical anti-proxy-goal-drift policy is active, governed plans must include the anti-drift control surface used by the canonical template

### Stage 5: `plan_execute`

Purpose:

- advance work strictly from the frozen plan

Rules:

- internal grade controls topology
- `L`: execute planned units serially by default; no blanket fan-out
- `XL`: execute waves sequentially; allow bounded parallelism only for independent units inside a step
- XL prefers Codex-native orchestration
- official entry writes a governance capsule before stage-lineage validation proceeds
- later stages must append a matching lineage entry for the same governed run
- spawned subagent prompts must end with `$vibe`
- milestone evidence must be written before phase completion
- governed `vibe` runs must record bounded native specialist recommendations under `vibe` governance and must not leave the recommendation surface empty
- eligible specialist recommendations should auto-promote into bounded native units; only blocked, degraded, or forced-escalation ideas remain advisory escalation requests
- when effective `approved_dispatch` is non-empty, governed `vibe` must emit one unified pre-execution disclosure that lists only actually executing specialist Skills and each real `native_skill_entrypoint`
- when routed or consulted specialist activity becomes stage-confirmed, governed `vibe` must append a host-stage disclosure event rather than waiting until the final runtime summary to expose that fact
- approved specialist dispatch must be phase-bound as `pre_execution`, `in_execution`, `post_execution`, or `verification`
- approved specialist dispatch must carry lane policy, write scope, and review mode so execution remains deterministic and conflict-aware
- `L` uses explicit serial specialist steps; `XL` may use bounded parallel specialist lanes only when root-approved and write-scope-safe
- runtime-selected skill stays `vibe` for governed entry even when route truth points at a specialist
- specialist use must preserve native workflow, required inputs, expected outputs, and validation style
- child-governed lanes inherit root-frozen requirement/plan context and must not open second canonical requirement or plan truth surfaces
- child-governed startup requires a root-authored `delegation-envelope.json`
- child-governed startup must emit `delegation-validation-receipt.json` before bounded work
- dangerous bulk deletion and blind recursive wipe commands against managed roots are forbidden by default during governed execution
- destructive removal must be narrowed to explicit unique paths, surfaced with a standalone hazard alert, and recorded in receipts rather than hidden behind convenience cleanup
- the run must emit a downstream delivery-acceptance report during closure so process success is not silently relabeled as project-delivery success

### Stage 6: `phase_cleanup`

Purpose:

- close the phase in a clean, auditable way

Minimum actions:

- temp artifact cleanup
- repo hygiene pass
- node audit or cleanup
- cleanup receipt write
- destructive cleanup, when exceptionally allowed, must remain path-bounded and receipt-backed; no blanket recursive wipe of managed roots
- delivery-acceptance report write with completion-language allowance or downgrade

## Protocol Delegation

The runtime may delegate stage internals to existing protocols:

- `think.md` for analysis, planning, and research
- `do.md` for execution, debugging, and verification
- `review.md` for quality review
- `team.md` for XL orchestration
- `retro.md` for retrospective learning after work closure

Delegation must not bypass the fixed stage order.

## Router Integration Rules

- route authority remains in `scripts/router/resolve-pack-route.ps1`
- `confirm_required` stays on the existing white-box confirm surface
- unattended routing is interpreted as a governed runtime mode choice, not as a second runtime
- provider-backed intelligence remains advice-only
- fallback or degraded paths must emit an explicit hazard alert rather than a silent warning
- fallback or degraded paths must downgrade runtime truth to `non_authoritative`

## Authority Boundary Contract

The ecosystem may carry multiple helpful layers, but runtime authority must stay single-owner.

Layer ownership is:

- canonical router: route selection authority
- VCO governed runtime: stage order, requirement freeze, plan traceability, execution receipts, cleanup receipts
- host bridge: hidden governance context attachment and host-hook wiring only
- superpowers and similar process layers: workflow discipline only

Explicitly forbidden:

- a second visible runtime entry ritual
- a second route authority
- a second requirement truth surface
- a second plan truth surface

Process-discipline layers may require that a workflow be followed.
They may not replace, shadow, or duplicate governed runtime truth.

## Root/Child Hierarchy Contract

During XL delegation, governed execution is hierarchical rather than recursive top-level governance:

- `root_governed` lane:
  - owns canonical requirement freeze
  - owns canonical plan freeze
  - owns global specialist dispatch approval
  - owns final completion claim for the full task
- `child_governed` lane:
  - inherits root-frozen requirement and plan context
  - runs bounded delegated units
  - emits local receipts and escalation requests only

Child-governed lanes are required to keep `$vibe` discipline but are forbidden from creating second canonical truth surfaces.

Explicitly forbidden for child-governed lanes:

- writing a second canonical requirement document under `docs/requirements/`
- writing a second canonical execution plan under `docs/plans/`
- issuing final completion claims for the root-governed task
- silently activating new global specialist dispatch without root approval

Specialist dispatch semantics under hierarchy:

- `approved_dispatch`: specialist execution approved by root and recorded in frozen plan, including same-round auto-absorb approval for safe child-lane recommendations
- approved dispatch must include phase binding, lane policy, write scope, and review mode so downstream child lanes do not improvise governance semantics
- `local_suggestion`: residual child-surfaced specialist suggestion that remains advisory only when root-governed execution blocks it, degrades it, or explicit policy forces escalation instead of same-round auto-absorb

## Artifact Contract

Expected runtime artifacts:

- `outputs/runtime/vibe-sessions/<run-id>/skeleton-receipt.json`
- `outputs/runtime/vibe-sessions/<run-id>/intent-contract.json`
- `outputs/runtime/vibe-sessions/<run-id>/runtime-input-packet.json` with non-empty `route_snapshot` and specialist surfaces
- requirement document
- execution plan
- phase receipts
- cleanup receipt
- execution-manifest specialist accounting/disclosure receipts
- runtime-input packet specialist recommendations when bounded specialist help is available
- execution-manifest specialist dispatch accounting when the plan uses bounded specialist help
- hierarchy-scoped authority markers indicating `root_governed` versus `child_governed` lane
- explicit escalation artifacts when child-governed lanes propose non-approved specialist dispatch
- delivery-acceptance report proving whether full downstream completion language is allowed

## Success Criteria

The governed runtime is considered healthy only when:

- the 6-stage sequence is preserved
- requirement and plan artifacts exist
- execution traces back to the plan
- cleanup is recorded
- no success claim is made without verification evidence
- anti-proxy-goal-drift completion semantics are not silently bypassed in governed packets
- downstream delivery truth is evaluated separately from runtime/process truth before full completion wording is allowed
- no fallback or degraded path is presented as equivalent success
- any fallback or degraded path emits a standalone hazard alert
- no run claims canonical vibe entry without runtime-input packet, route snapshot proof, and specialist dispatch accounting artifacts
