# Simplified Skill Routing

> Historical / Retired Note: This document records the older simplification pass. The current routing model is `skill_candidates -> skill_routing.selected -> selected_skill_execution -> skill_usage`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Preserved Decision

The durable decision from this document is that Vibe-Skills should not expose a
multi-state helper architecture to users. The current model keeps only candidate,
selected, executed, used, and unused states.

## Retired Context

Older drafts used names such as `primary skill`, `secondary skill`,
`consultation_bucket`, and helper-style routing labels. These are historical
notes, not current route states.
