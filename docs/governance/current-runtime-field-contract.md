# Current Runtime Field Contract

Date: 2026-07-10

## Purpose

This document defines the current runtime truth vocabulary for Vibe-Skills.
The packet freezes approved plan inputs; later work-loop artifacts prove what
actually happened.

## Canonical Truth Chain

```text
requirement guidance: skill_search_guide
plan truth: agent_skill_organization -> module-work-plan.json
handoff truth: module-work-plan.json -> agent-execution-handoff.json
execution truth: agent-execution-handoff.json -> module-execution.json
acceptance truth: module-execution.json -> delivery-acceptance-report.json
```

Meaning:

- `skill_search_guide` tells the Agent how to search declared local skill roots.
- `agent_skill_organization` freezes modules, candidates, selected skills,
  responsibilities, reasons, workflow level, and uncovered modules.
- `module-work-plan.json` freezes module dependencies, work units, write scopes,
  skill roles, and acceptance criteria.
- `agent-execution-handoff.json` tells the current Agent which approved modules
  to complete and which `SKILL.md` applies to each work unit.
- `module-execution.json` returns the Agent's work-unit results, failures,
  blocking reasons, and module states against that exact approved plan.

## Stage Rules

At `requirement_doc`:

- `skill_search_guide` is required.
- `agent_skill_organization` may be null.
- route candidates must not enter `module_assignments`.

Before `xl_plan`, `plan_execute`, or `phase_cleanup`:

- `agent_skill_organization` is required.
- every selected skill must exist in a declared local root.
- each module must declare exactly one execution mode: covered by a selected
  local Skill (`skill_assigned`), assigned directly to the current Agent without
  a local Skill (`agent_direct`), or blocked by an explicit Skill gap
  (`blocked_gap`).
- `module_assignments` selected ids must exactly match the organization.

After plan approval, bounded re-entry reuses the frozen organization. It must
not rerun procedural skill selection or silently add candidates.

## Runtime Input Fields

Canonical packet fields:

```text
skill_search_guide
agent_skill_organization
```

No separate decision object may choose task skills, bind work, or claim that
work ran outside this canonical chain.

## Module Execution Truth

Preferred stable work-run surfaces:

```text
module-work-plan.json
agent-execution-handoff.json
module-execution.json
delivery-acceptance-report.json
```

- `module-work-plan.json`: the only dispatch authority after plan approval.
- `agent-execution-handoff.json`: the work instructions handed to the current Agent at `plan_execute`.
- `module-execution.json`: the Agent's returned work-unit results and module states bound to the approved plan.
- `delivery-acceptance-report.json`: module acceptance first, then task acceptance.

## Compatibility Audit Fields

These fields may remain readable for older hosts and proof readers:

```text
skill_routing.candidates
route_snapshot
canonical_router
divergence_shadow
```

They are audit mirrors only. Scores, order, route selection, and
`confirm_required` must not populate `agent_skill_organization`, bind work, or
stop the governed stage machine.

## Agent Execution Handoff

At `plan_execute`, Vibe organizes the approved work and writes
`agent-execution-handoff.json`. It then stops before cleanup with
`status = agent_action_required` and `control_owner = agent`.

The current Agent reads the listed `SKILL.md` files and completes the modules.
Vibe does not run those skills itself and does not manufacture successful
results on the Agent's behalf.

When the Agent finishes, it writes one complete `module-execution.json` and
returns it through canonical `vibe` re-entry. The runtime checks that the run,
modules, work units, and approved plan match before it can enter cleanup. This
return is not another requirement or plan approval step, and it does not search
for skills again.

Skill use is derived from completed work units in the approved module plan and
the returned module results. There is no separate Skill-use ledger, Skill-file
hash proof, or artifact-impact receipt.

## Retired Selection Fields

Current canonical code must not use these as task-skill truth:

```text
skill_selection
legacy_skill_routing
specialist_recommendations
specialist_dispatch
stage_assistant_hints
discussion_specialist_consultation
planning_specialist_consultation
```

Historical artifacts may still contain them. Current runtime behavior must use
`agent_skill_organization`, `module-work-plan.json`,
`agent-execution-handoff.json`, and `module-execution.json` instead. Retired
fields are not compatibility inputs for current execution.
