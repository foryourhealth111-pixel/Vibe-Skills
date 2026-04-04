# Subagent Handoff Governance

## Purpose

Wave90 formalizes the handoff envelope used between VCO-managed subagents so responsibility moves without losing evidence, rollback context, or done definitions.
The handoff contract packages work; it does not replace VCO as the orchestrator.

## Governance Scope

- Every handoff must declare upstream role, downstream role, bounded write scope, and explicit done definition.
- Handoffs must carry replay and rollback references when the task affects governed planes or release-facing assets.
- Implicit supervisor behavior and hidden auto-merge authority are forbidden.

## Required Invariants

- `execution_owner_remains_vco = true` for all handoff flows.
- `orchestrator_takeover_forbidden = true` for all worker patterns.
- Every handoff must include `input_contract`, `expected_outputs`, and `evidence_refs`.
- A handoff may reassign work, but may not silently change route, stage, or release policy.

## Non-Goals

- No standalone handoff runtime is created.
- No worker is allowed to claim final governance authority.

Validation is performed by `scripts/verify/vibe-subagent-handoff-gate.ps1`.
