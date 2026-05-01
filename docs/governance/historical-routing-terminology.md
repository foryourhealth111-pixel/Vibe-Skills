# Historical Routing Terminology

> Historical / Retired Note: This document is an index for retired routing language. The current routing model is `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`.

This page exists so old routing vocabulary has one small place to live. It is not
a runtime contract, and it does not add another routing layer.

## Current Contract

Current readers should start here:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`

Current state names:

- `skill_candidates`
- `skill_routing.selected`
- `selected_skill_execution`
- `skill_usage.used`
- `skill_usage.unused`
- `skill_usage.evidence`

The runtime distinction is simple: a skill can be a candidate, selected for a
task slice, executed, and then counted as used only when usage evidence is
written.

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
project removed advisory/helper/primary-secondary routing states and kept a
smaller selected-versus-used model.

When editing current docs, prefer the current contract links instead of copying
old terminology back into new prose.
