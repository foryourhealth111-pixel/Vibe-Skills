# Current Skill Discovery Compatibility Contract

Date: 2026-07-10

## Purpose

This document explains the remaining route-era compatibility fields after the
Agent-led skill discovery cutover. It is not the main runtime truth contract.

Read [`current-runtime-field-contract.md`](current-runtime-field-contract.md)
first. Normal runs should be understandable from the frozen requirement, the
Agent-confirmed skill organization, the execution plan, work results, and
verification evidence.

## Current Truth Chain

The canonical skill flow is:

```text
requirement: skill_search_guide
plan truth: agent_skill_organization -> module-work-plan.json
execution truth: module-work-plan.json -> module-execution.json
acceptance truth: module-execution.json -> delivery-acceptance-report.json
```

`agent_skill_organization` is produced by the Agent after it:

1. splits the approved task into modules,
2. searches every declared local skill root per module,
3. reads each retained candidate's `SKILL.md`,
4. records selected skills, responsibilities, reasons, and uncovered modules.

The organization must be present before `xl_plan`. Plan approval freezes it for
`plan_execute` and cleanup. `plan_execute` writes the Agent execution handoff;
it does not run skills. Later re-entry must not rerun procedural skill selection
or silently add route candidates.

## Route Compatibility Role

The retained router is a compatibility candidate audit. It may expose:

- candidate skill ids,
- evidence snippets,
- scores or ordering,
- legacy `confirm_required` metadata.

Those fields do not choose task skills, bind work, stop stage progression, or
prove that work happened. A route candidate becomes assigned work only after
the Agent has read its `SKILL.md` and included it in a user-approved
`agent_skill_organization`.

A route candidate becomes executable only after the Agent performs that review
and the approved organization assigns it to module work. "Executable" means
eligible for the Agent handoff; the runtime does not execute the Skill.

## Operating Rules

1. Read `agent_skill_organization` before any route-era field.
2. Require `module_assignments` skill ids to match the organization's selected skill ids.
3. Treat uncovered modules as explicit gaps; do not fabricate coverage.
4. Preserve the frozen organization across bounded re-entry after plan approval.
5. At `plan_execute`, emit `agent-execution-handoff.json` and return control to the Agent.
6. Accept work only from a complete `module-execution.json` returned through canonical `vibe` re-entry.
7. Derive Skill use from completed module work; do not maintain a separate usage ledger.

## Terms

| Term | Meaning |
| --- | --- |
| `skill_search_guide` | Requirement-stage instructions for Agent-led local skill discovery. |
| `agent_skill_organization` | Agent-confirmed plan truth for modules, candidates, selected skills, responsibilities, reasons, and gaps. |
| `module-work-plan.json` | User-approved modules, dependencies, work units, write scopes, roles, and acceptance criteria. |
| `agent-execution-handoff.json` | Instructions for the current Agent to read assigned `SKILL.md` files and complete the approved module work. |
| `module-execution.json` | Work-unit and module results returned by the Agent against the approved plan. |
| `skill_routing.candidates` | Compatibility audit candidates. They are not selected task skills. |
| `skill_routing.rejected` | The subset of compatibility candidates not selected by the Agent organization. These rows remain audit-only and carry no dispatch, write, or completion authority. |

## Compatibility Fields

Current packets may retain these optional audit mirrors for older readers:

```text
canonical_router
route_snapshot
skill_routing.candidates
skill_routing.rejected
divergence_shadow
```

They remain non-canonical. Readers must not reconstruct task-skill truth from
scores, rankings, route selection, or confirmation metadata.

## Retired Selection Fields

Current canonical packets and execution logic must not use these fields as
skill truth:

```text
skill_selection
legacy_skill_routing
specialist_recommendations
specialist_dispatch
stage_assistant_hints
discussion_specialist_consultation
planning_specialist_consultation
```

Old artifacts may still contain them as historical data. Current readers must
not use them as fallbacks; current execution follows `agent_skill_organization`,
`module-work-plan.json`, `agent-execution-handoff.json`, and
`module-execution.json`.

## Non-Goals

This contract does not delete the local candidate audit or historical artifacts.
It prevents those surfaces from becoming a second skill selector or a second
runtime authority.
