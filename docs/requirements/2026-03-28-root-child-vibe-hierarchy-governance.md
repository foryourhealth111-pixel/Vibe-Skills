# Root/Child Vibe Hierarchy Governance

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

## Summary
Resolve the governance ambiguity introduced by recursive `vibe` usage in XL multi-agent work. Keep `vibe` as the only governed runtime authority at the root task level while allowing child agents to inherit `vibe` discipline as subordinate execution lanes instead of reopening a second top-level governed runtime.

## Goal
Design and land a hierarchy model where:

- one user task has exactly one root governed `vibe` runtime
- child agents still run under `vibe` discipline
- child agents do not create a second requirement or plan truth
- specialist skills remain usable as bounded native helpers without taking runtime ownership

## Deliverable
A repository change set and documentation bundle that adds:

- an explicit root/child governance-scope contract inside the runtime input packet
- subordinate child-lane rules for XL execution
- approved specialist dispatch versus child-local suggestion separation
- execution/accounting/proof surfaces for root-owned completion and child-owned local receipts
- protocol, requirement, plan, and stable governance docs for the hierarchy model
- regression tests and verification gates proving authority preservation, non-duplication of canonical surfaces, bounded specialist usage, and predictable escalation behavior

## Constraints
- Do not remove `$vibe` from child-agent prompts.
- Do not let child agents create a second visible governed startup surface.
- Do not let child agents freeze a second canonical requirement document or execution plan.
- Do not let child agents make global specialist-dispatch decisions on behalf of the root run.
- Do not let specialist skills become runtime owners or make final completion claims.
- Preserve existing explicit `vibe` authority invariants and current canonical router ownership.
- Prefer additive metadata and execution-policy changes over broad router rewrites.

## Acceptance Criteria
- Runtime input packet distinguishes `root` versus `child` governance scope with machine-readable authority flags.
- Root runs are the only runs allowed to freeze canonical requirement and plan surfaces under `docs/requirements/` and `docs/plans/`.
- Child runs inherit the frozen requirement/plan context and write only subordinate receipts or artifacts.
- Specialist dispatch is split into:
  - root-approved specialist dispatch
  - child-local specialist suggestions that require escalation before becoming globally active
- Execution manifests preserve:
  - single root completion authority
  - child-unit evidence
  - approved specialist dispatch accounting
  - escalation requests and their outcomes
- Protocol docs explain:
  - root-governed authority
  - child-governed subordinate execution
  - specialist boundedness rules
  - conflict-prevention rules for multi-agent work
- Tests and gates prove:
  - no duplicate canonical requirement/plan surfaces are created
  - child runs cannot widen scope silently
  - child runs cannot issue final completion claims
  - child specialist suggestions stay advisory until root approval
  - explicit `vibe` authority remains stable during hierarchical execution

## Primary Objective
Turn recursive multi-agent `vibe` usage from a layered-governance ambiguity into a single-root, subordinate-child execution model.

## Proxy Signal
Root runs freeze the only canonical requirement and plan, child runs inherit those surfaces as subordinate lanes, and specialist skills are executed or suggested without creating second governance truth.

## Scope
In scope:
- runtime input packet hierarchy metadata
- plan-execution handoff contract for child lanes
- specialist dispatch approval versus suggestion semantics
- execution manifest and proof surfacing
- protocol and stable-governance documentation
- regression tests and verification gates

Out of scope:
- redesigning the full canonical router ranking system
- host-level interception of arbitrary non-`vibe` requests
- per-skill metadata rewrites across the whole repository
- generalized memory-system redesign

## Completion
The work is complete when XL `vibe` orchestration can use child agents and specialist skills without creating recursive top-level governance, duplicate canonical surfaces, or ambiguous completion authority.

## Evidence
- updated runtime/config/protocol/test surfaces
- new governed requirement/plan docs for the hierarchy change
- new stable governance design doc
- passing targeted tests and gates
- explicit proof artifacts and cleanup receipts from the verification pass

## Non-Goals
- Do not make child `vibe` lanes governance-free.
- Do not replace `vibe` with specialist skills during explicit governed entry.
- Do not allow child lanes to silently re-plan the entire task.
- Do not hide escalation events or specialist conflict handling from execution evidence.

## Autonomy Mode
interactive_governed

## Assumptions
- Existing explicit `vibe` runtime surfaces are already strong enough to support a root/child extension.
- Child lanes can inherit frozen context rather than regenerate it.
- Specialist recommendations already present in the runtime packet can be separated into approved dispatch and local suggestions without a router redesign.
- Stable hierarchy behavior can be proven with targeted runtime-neutral tests and governed PowerShell gates.

## Evidence Inputs
- Source task: design the root/child `vibe` hierarchy model that preserves governance while allowing bounded specialist usage
