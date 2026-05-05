# Vibe Specialist Execution Lock Design

Date: 2026-05-05

## Goal

Make Vibe preserve approved specialist execution intent across bounded
re-entry. A skill that is selected into the approved plan must not disappear
from the final execution topology merely because a later re-entry reruns the
router and produces a narrower current route.

The design keeps the current honest usage model:

```text
candidate -> selected -> locked_for_execution -> executed / not_applicable / deferred
```

This does not mean every candidate skill must execute. It means every skill
that crosses the approved-plan boundary must be either executed or explicitly
resolved before the delivery gate can pass.

## Problem

The current runtime has the right pieces, but their authority is scoped too
narrowly to the current re-entry:

- `Freeze-RuntimeInputPacket.ps1` reruns the router on each bounded re-entry.
- `Freeze-RuntimeInputPacket.ps1` rebuilds `skill_routing` from the current
  router result, current recommendations, and current dispatch split.
- `Invoke-PlanExecute.ps1` converts only the current packet's
  `skill_routing.selected` into `selected_skill_execution`.
- If the current packet has any `skill_routing.selected`, plan execution treats
  that current selection as authoritative and disables auto absorption.
- `VibeRuntime.Common.ps1` already supports a host
  `skill_execution_decision`, but an ordinary plan approval does not
  automatically create a durable execution decision from the previously
  selected specialists.

The user-visible failure mode is easy to explain:

1. Requirement re-entry routes literature and research skills.
2. Plan re-entry routes experiment or reporting skills.
3. Final execution re-entry routes only a LaTeX skill.
4. The final execution topology contains only the LaTeX skill.
5. Earlier skills may have influenced requirement or plan artifacts, but they
   were not preserved as final execution work units.

That behavior is not a truthful multi-specialist execution model. It blurs
planned selection, approved dispatch, and material execution.

## Non-Goals

This change must not:

- execute every routed candidate skill;
- treat routing, loading, or dispatch alone as material skill use;
- weaken the existing `skill_usage.used` evidence standard;
- bypass destructive or incomplete skill dispatch checks;
- remove compatibility readers for old runtime packets;
- make child lanes self-approve new root specialists;
- require a public host to expose every internal bundled skill as a top-level
  host-visible skill.

## Design Summary

Add a durable execution lock between plan approval and plan execution.

The lock is a runtime-packet field that records which selected or approved
specialists have crossed the approved-plan boundary and therefore require
resolution in execution.

Recommended field:

```json
{
  "skill_execution_lock": {
    "schema_version": "v1",
    "state": "active",
    "source": "approved_plan_reentry",
    "source_run_id": "20260505T044250Z-609dce9c",
    "locked_skill_ids": [
      "scientific-reporting",
      "latex-submission-pipeline"
    ],
    "locked_dispatch": [],
    "resolution_required": true,
    "resolution_states": [
      "executed",
      "not_applicable",
      "deferred"
    ]
  }
}
```

The lock is not a usage claim. It is an execution obligation. A locked skill
can become `executed`, `not_applicable`, or `deferred`, but it cannot silently
vanish from accounting.

## Authority Model

The current authority chain should become:

```text
router ranked candidates
-> skill_routing.selected
-> approved plan boundary
-> skill_execution_lock
-> selected_skill_execution
-> specialist-execution.json
-> skill_usage.used / skill_usage.unused
```

Meaning:

- `candidate`: considered by routing or recommendation.
- `selected`: chosen into the current work surface.
- `locked_for_execution`: approved-plan boundary preserved the skill as an
  execution obligation.
- `executed`: native workflow was actually invoked and evidence exists.
- `not_applicable`: the lock was intentionally resolved without execution
  because the skill was no longer applicable, with a concrete reason.
- `deferred`: execution was intentionally postponed, with a concrete reason.
- `used`: material artifact-impact truth from `skill_usage.used`, not from the
  lock.

## Data Flow

### Requirement And Plan Stages

Requirement and plan generation continue to use the current packet's
`skill_routing.selected` and `skill_usage` behavior.

The XL plan should surface the specialists selected into the plan and label
them as pending execution resolution, not as already used.

### Plan Approval Re-Entry

When the host decision approves the plan and the runtime moves toward
`plan_execute`, `Freeze-RuntimeInputPacket.ps1` should construct or inherit a
`skill_execution_lock`.

The initial source order should be:

1. Explicit `host_decision.skill_execution_decision.approved_skill_ids`.
2. Previous run's `skill_execution_lock.locked_dispatch`, if present.
3. Previous run's `skill_routing.selected`, when the previous bounded stage was
   `xl_plan` or equivalent plan approval context.
4. Current run's `skill_routing.selected`.

This order preserves explicit host decisions first while keeping ordinary
approve-plan flows useful.

### Runtime Packet Freeze

`Freeze-RuntimeInputPacket.ps1` should add a normalized
`skill_execution_lock` projection to the new packet.

The lock should store dispatch records, not only ids, whenever dispatch records
are available. That avoids losing native entrypoint paths, write scopes,
dispatch phases, and verification expectations.

If a previous locked skill is no longer surfaced by the current router, the
runtime should still preserve it as locked, but mark reconciliation:

```json
{
  "skill_id": "literature-review",
  "reconciliation_state": "inherited_not_currently_surfaced",
  "requires_resolution": true
}
```

This prevents the current router from erasing approved-plan obligations.

### Plan Execution

`Invoke-PlanExecute.ps1` should build `selected_skill_execution` from the lock
when the lock is active. Current `skill_routing.selected` remains useful for
audit, but it no longer overrides the lock at execution time.

Execution dispatch order:

1. Active `skill_execution_lock.locked_dispatch`.
2. Explicit host `skill_execution_decision` dispatch if no lock exists.
3. Current `skill_routing.selected`.
4. Existing auto-absorb behavior for local suggestions, only when no canonical
   selected skills or active lock exist.

The existing destructive, degraded, and blocked dispatch handling remains
mandatory.

### Resolution Accounting

Each locked skill must be resolved before delivery acceptance can pass.

Accepted states:

```text
executed
not_applicable
deferred
failed
```

Delivery should pass only when there are no unresolved locked skills and no
failed locked skills, unless an explicit manual-review exception is recorded.

Recommended artifact fields:

```json
{
  "specialist_lock_resolution": {
    "locked_skill_ids": [],
    "executed_skill_ids": [],
    "not_applicable_skill_ids": [],
    "deferred_skill_ids": [],
    "failed_skill_ids": [],
    "unresolved_skill_ids": [],
    "delivery_blocking": true
  }
}
```

## Components

### `VibeRuntime.Common.ps1`

Add helper functions:

- `Get-VibeSkillExecutionLockFromRuntimeInputPacket`
- `New-VibeSkillExecutionLockProjection`
- `Merge-VibeSkillExecutionLock`
- `Resolve-VibeSkillExecutionLockSource`
- `New-VibeSkillExecutionLockSummaryProjection`

These helpers should normalize lock shape, preserve old packets safely, and
avoid putting re-entry inheritance logic directly into every stage script.

### `Freeze-RuntimeInputPacket.ps1`

Add lock construction during packet freeze.

Inputs:

- current host decision;
- continuation context;
- current `skill_routing`;
- previous runtime packet, when continuing from a bounded run;
- previous execution plan metadata, when available.

Outputs:

- `skill_execution_lock`;
- `specialist_dispatch.lock_applied`;
- explicit reconciliation metadata for inherited skills.

### `VibeSkillRouting.Common.ps1`

Add a single conversion path from selected or locked skill records to dispatch
records.

This avoids duplicating dispatch conversion in both freeze and execution.

Suggested helper:

```powershell
Convert-VibeSkillExecutionLockToDispatch
```

### `Invoke-PlanExecute.ps1`

Use the active lock as the first source of `selected_skill_execution`.

Add lock resolution accounting to:

- `execution-manifest.json`;
- `execution-topology.json`;
- `specialist-execution.json`;
- delivery acceptance inputs.

### Documentation

Update current docs that explain skill state to include:

```text
candidate -> selected -> locked_for_execution -> executed / not_applicable / deferred
```

The docs must still say that `used` requires `skill_usage.used` evidence.

## Error Handling

If a locked skill lacks a native entrypoint path:

- keep the lock;
- mark the dispatch as degraded;
- require explicit `not_applicable` or `deferred` resolution if it cannot run.

If a locked skill becomes destructive or contract-incomplete:

- do not auto-execute it;
- mark it blocked;
- require explicit resolution before delivery.

If the previous runtime packet cannot be read:

- continue with current `skill_routing.selected`;
- record `lock_source_state = previous_packet_unavailable`;
- do not claim inherited specialists were preserved.

If an explicit host decision rejects a previously locked skill:

- keep the lock entry for audit;
- resolve it as `not_applicable` or `deferred` with
  `resolution_source = host_decision`;
- do not execute it.

## Testing Plan

Add focused tests that cover the actual failure mode.

### Unit Tests

1. Lock creation from previous `skill_routing.selected`.
2. Lock preservation when current router selects a different skill.
3. Explicit host `skill_execution_decision` overrides inherited lock.
4. Rejected or deferred host decisions resolve inherited lock entries.
5. Locked dispatch preserves `native_skill_entrypoint`, `dispatch_phase`,
   `write_scope`, and `verification_expectation`.

### Runtime Simulation

Create a bounded re-entry fixture:

1. requirement run selects `literature-review`;
2. revised requirement run selects `hypothesis-generation`;
3. plan run selects `scientific-reporting`;
4. final execution run router selects only `latex-submission-pipeline`.

Expected result:

- final runtime packet has active `skill_execution_lock`;
- execution topology includes locked specialists, not only the final router
  skill;
- every locked skill is `executed`, `not_applicable`, `deferred`, or `failed`;
- unresolved locked skills block delivery acceptance.

### Regression Tests

Existing behavior should remain valid when:

- no previous selected specialists exist;
- the task is single-skill;
- the current router and previous selected skill are the same;
- old runtime packets do not contain `skill_execution_lock`;
- child governance scope receives root-approved specialists only.

## Acceptance Criteria

The implementation is complete only when:

1. A plan-approval re-entry preserves previous selected specialists into an
   active `skill_execution_lock`.
2. `Invoke-PlanExecute.ps1` prefers the lock over current router-only
   `skill_routing.selected`.
3. Final `execution-topology.json` exposes locked specialist units.
4. Final accounting distinguishes `selected`, `locked_for_execution`,
   `executed`, `not_applicable`, `deferred`, `failed`, `used`, and `unused`.
5. Delivery acceptance fails or requires manual review when locked specialists
   remain unresolved.
6. Existing binary `skill_usage` semantics remain unchanged.
7. Focused PowerShell tests pass.
8. A live or fixture run reproduces the original failure pattern and shows the
   lock preserving specialists across re-entry.

## Open Implementation Notes

The safest first implementation slice is intentionally narrow:

1. Add lock model helpers.
2. Inherit prior selected specialists on approve-plan re-entry.
3. Feed lock dispatch into plan execution.
4. Add unresolved-lock delivery accounting.
5. Add focused tests for the previous-loss failure mode.

Do not broaden this slice into router ranking changes or pack consolidation.
The problem is not that the router picked LaTeX in the final run. The problem
is that the final run was allowed to erase previously approved specialist
execution obligations.
