# Terminology Governance

> Historical / Retired Note: This document records prior terminology cleanup. The current routing model is `skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Current Rule

Use current names in active docs, runtime output, tests, and user-visible
messages:

| Current term | Meaning |
| --- | --- |
| `skill_candidates` | Candidate skills available to a pack or route decision. |
| `skill_routing.selected` | The selected skill decisions produced by routing. |
| `skill_execution_lock` | Current execution-obligation field that preserves approved specialists across bounded re-entry; not evidence of material skill use. |
| `selected_skill_execution` | The current execution-intent projection shown to users and hosts. |
| `skill_usage.used` | Skills materially used in the run. |
| `skill_usage.unused` | Candidate or selected skills that were not materially used. |
| `skill_usage.evidence` | Evidence tying usage claims to concrete artifacts, files, or receipts. |

## Retired Context

Older terms are retired vocabulary. They can appear in historical records,
compatibility readers, and negative tests, but active docs and reports must not
use them as current architecture names.
