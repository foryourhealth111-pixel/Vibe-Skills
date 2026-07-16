# Simplified Skill Routing

> Historical / Retired Note: This document records the older simplification pass. The current work-first truth model is `task_card -> work_plan -> module_assignments -> work_results -> verification`. `skill_routing.selected` may remain visible only as an optional compatibility mirror.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Preserved Decision

The durable decision from this document is that Vibe-Skills should not expose a
multi-state helper architecture to users. The current model keeps a small
work-first truth chain, with `module_assignments` as the first runtime truth and
compatibility fields such as `skill_routing.selected` staying secondary.

## Retired Context

Older drafts used names such as `primary skill`, `secondary skill`,
`consultation_bucket`, and helper-style routing labels. These are historical
notes, not current route states.
