# Specialist Dispatch Governance

> Historical / Retired Note: This document records a retired execution-wording design. The current routing model is `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Preserved Decision

The durable decision from this document is that execution must be tied to the
skill selected for the task slice and must not be treated as hidden advisory
activity.

Current execution language is `selected_skill_execution`, `skill_execution_units`,
and `execution_skill_outcomes`.

## Retired Context

Older wording used `specialist dispatch`, `approved_dispatch`, and related
phrases. Those names remain historical audit vocabulary only and must not be
used as current routing truth.
