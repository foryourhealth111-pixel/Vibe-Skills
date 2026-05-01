# Binary Skill Usage Routing

> Historical / Retired Note: This document records the older cleanup step that separated routing from usage proof. The current routing model is `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Preserved Decision

The durable decision from this document is that route selection, old
recommendation fields, consultation records, and old dispatch records do not
prove skill use.

Current usage proof must come from `skill_usage.used` with evidence. A selected
skill is not counted as used unless the runtime writes usage evidence.

## Retired Context

Older wording in this area included `specialist_recommendations`,
`stage_assistant_hints`, consultation receipts, and dispatch records. Those names
remain historical audit vocabulary only.
