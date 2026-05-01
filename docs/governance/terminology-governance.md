# Terminology Governance

> Historical / Retired Note: This document records prior terminology cleanup. The current routing model is `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Current Rule

Use current names in active docs, runtime output, tests, and user-visible
messages:

- `skill_candidates`
- `skill_routing.selected`
- `selected_skill_execution`
- `skill_usage.used`
- `skill_usage.unused`
- `skill_usage.evidence`

## Retired Context

Older wording such as `route owner`, `primary skill`, `secondary skill`,
`stage assistant`, `consultation`, `specialist_recommendations`, and
`legacy_skill_routing` is historical only. Do not copy it into current surfaces
as active design language.
