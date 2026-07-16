# Historical Routing Terminology

> Historical / Retired Note: This document is an index for retired routing language. The current work-first truth model is `task_card -> work_plan -> module_assignments -> work_results -> verification`. `skill_routing.selected` may still appear only as an optional compatibility mirror.

This page exists so old routing vocabulary has one small place to live. It is not
a runtime contract, and it does not add another routing layer.

## Current Contract

Current readers should start here:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`

Current work-first truth:

- `task_card`
- `work_plan`
- `module_assignments`
- `work_results`
- `verification`

Compatibility and execution fields that may still appear:

- `skill_candidates`
- `skill_routing.selected`
- `module_skill_dispatch`
- `skill_usage.used`
- `skill_usage.unused`
- `skill_usage.evidence`

Read `module_assignments` first when asking what work was actually bound. Read
`skill_routing.selected` only as an optional compatibility mirror for older
readers and reports.

## Retired Terms

These terms appear in older requirements, specs, plans, and pack-cleanup notes.
They should not be used to describe current runtime state:

| Retired wording | Current reading rule |
| --- | --- |
| `primary skill` | Read as a historical way to say one selected skill. |
| `secondary skill` | Read as a historical way to say another candidate or selected skill. |
| `route owner` | Read as historical pack-cleanup language, not a runtime status. |
| `stage assistant` | Read as historical helper-role language, not a current role. |
| `consultation` | Read as historical planning/discussion input, not current skill usage. |
| `specialist dispatch` | Read as historical execution wording, not current routing truth. |
| `specialist_recommendations` | Read as retired old-format routing data, not current input. |
| `legacy_skill_routing` | Read as retired old-format routing data, not current input. |
| `stage_assistant_hints` | Read as retired old-format helper data, not current input. |

## Preserved Rationale

The older documents remain useful for audit history because they show why the
project removed advisory/helper/primary-secondary routing states and moved
current truth to the work-first chain above while keeping a few compatibility
fields readable.

When editing current docs, prefer the current contract links instead of copying
old terminology back into new prose.
