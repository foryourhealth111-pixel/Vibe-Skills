# Terminology Governance

> Historical / Retired Note: This document records prior terminology cleanup. The current execution path is `task_card -> agent_skill_organization -> module-work-plan.json -> agent-execution-handoff.json -> module-execution.json -> delivery-acceptance-report.json`.

Current readers should use:

- `docs/governance/current-routing-contract.md`
- `docs/governance/current-runtime-field-contract.md`
- `docs/governance/historical-routing-terminology.md`

## Current Rule

Use the Agent handoff and module result names in active docs, runtime output,
tests, and user-visible messages. Route-era fields may appear in historical
records, but current execution must not read them as fallbacks.

| Current term | Meaning |
| --- | --- |
| `task_card` | Kernel-owned statement of the job the run is trying to complete. |
| `agent_skill_organization` | Agent-confirmed modules, selected Skills, responsibilities, and explicit gaps. |
| `module-work-plan.json` | The approved work authority after plan approval. |
| `module_assignments` | Validated projection of the approved Skill assignments into module work units. |
| `agent-execution-handoff.json` | Instructions that return control to the current Agent so it can complete the approved modules. |
| `module-execution.json` | The Agent's returned work-unit results and module states. |
| `delivery-acceptance-report.json` | Runtime decision about whether the returned module work satisfies the task. |
| `skill_routing.candidates` | Non-authoritative compatibility audit candidates. |

## Retired Context

Older terms are retired vocabulary. They can appear in historical records,
compatibility readers, and negative tests, but active docs and reports must not
use them as current architecture names.
