# Vibe Discussion-Time Specialist Consultation Requirement

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

## Summary

Add a governed consultation layer so `vibe` can truly consult appropriate routed specialist Skills during discussion and plan formation, then disclose those consultations progressively while remaining the only runtime authority and the only front-facing speaker.

## Goal

Stop treating routed planning specialists as metadata-only participants before execution.

Instead, allow `vibe` to approve and consult suitable specialists during the discussion and planning chain before requirement and plan freeze complete.

## Deliverable

A governed specialist-consultation design and runtime contract that:

- approves discussion-time and plan-time consultation from frozen specialist recommendations
- keeps consultation truth separate from execution dispatch truth
- emits progressive user-facing consultation disclosures under `vibe`
- feeds consultation results into requirement and plan generation

## Constraints

- `vibe` remains the only runtime authority
- the canonical router remains the only route authority
- no second requirement surface may be created
- no second execution-plan surface may be created
- consultation truth must not be merged into execution `approved_dispatch`
- specialist consultation must preserve each skill's native workflow and contract expectations
- the public six-stage governed runtime contract should remain unchanged

## Acceptance Criteria

- governed `vibe` runs can approve suitable specialists for discussion-time consultation after routing truth is frozen
- governed `vibe` runs can approve suitable specialists for plan-time consultation before final plan freeze
- only specialists actually approved for consultation are disclosed as consulted
- each disclosed consultation shows the real `native_skill_entrypoint` path
- requirement artifacts reflect real pre-freeze consultation input
- plan artifacts reflect real pre-plan consultation input
- execution-time specialist dispatch truth remains separate and unblurred

## Product Acceptance Criteria

- a user can tell that specialist reasoning helped shape the discussion before execution starts
- a user can tell which specialist Skills were truly consulted rather than merely recommended
- a user can see where each consulted Skill is loaded from
- the user still experiences one governed runtime speaker, not a swarm of peer authorities

## Manual Spot Checks

- Trigger a governed planning-oriented run and confirm `vibe` discloses consultation of an approved planning specialist before requirement freeze.
- Confirm the requirement document records which consulted specialists influenced requirement shaping.
- Confirm a plan-oriented run discloses planning consultation before final plan freeze when a planning specialist is approved.
- Confirm execution-only specialist disclosure still appears only in execution contexts and is not confused with consultation disclosure.

## Completion Language Policy

Do not claim this behavior exists unless fresh runtime verification proves that specialist consultation happened before requirement or plan freeze and that consultation disclosure remained separate from execution dispatch disclosure.

## Delivery Truth Contract

Success means routed specialists can truly influence the governed discussion and planning chain before execution, not merely that their metadata appears in frozen artifacts.

## Artifact Review Requirements

- Review the consultation receipts, requirement doc, and plan doc together to verify that consultation truth is propagated consistently.

## Code Task TDD Evidence Requirements

- Record failing-first evidence for missing consultation truth in discussion or planning stages.
- Prove consultation approval is derived from frozen specialist recommendations, not raw router candidate lists.
- Prove consultation disclosure uses real `native_skill_entrypoint`.
- Prove execution-time `approved_dispatch` semantics remain unchanged.

## Code Task TDD Exceptions

No code-task TDD exceptions were frozen for this run.

## Baseline Document Quality Dimensions

- discussion-time consultation wording must stay distinct from execution dispatch wording
- requirement and plan docs must explain adoption versus non-adoption of consultation input

## Baseline UI Quality Dimensions

- consultation disclosure must be progressive and concise
- disclosure must remain clearly attributed to `vibe`

## Task-Specific Acceptance Extensions

- do not add a seventh public governed runtime stage
- keep consultation logic internally cohesive in a dedicated runtime module and policy surface
- defer unapproved but still viable specialists to later execution surfaces rather than silently dropping them

## Research Augmentation Sources

- `SKILL.md`
- `protocols/runtime.md`
- `protocols/think.md`
- `protocols/team.md`
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `scripts/runtime/Invoke-DeepInterview.ps1`
- `scripts/runtime/Write-RequirementDoc.ps1`
- `scripts/runtime/Write-XlPlan.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`
- `scripts/runtime/VibeRuntime.Common.ps1`

## Primary Objective

Introduce governed discussion-time and plan-time specialist consultation under `vibe`.

## Non-Objective Proxy Signals

- merely increasing specialist recommendation counts
- merely listing specialist names in frozen documents
- exposing raw router candidates earlier
- treating consultation disclosure as execution disclosure

## Validation Material Role

Runtime consultation receipts, requirement/plan documents, and focused runtime-neutral tests are the source of truth for this change.

## Anti-Proxy-Goal-Drift Tier

Tier 1 authority and truth-layer separation preservation.

## Intended Scope

Governed specialist consultation for discussion and plan formation.

## Abstraction Layer Target

Governed runtime orchestration and artifact truth surfaces.

## Completion State

Complete only when governed runtime artifacts and tests prove real specialist consultation before requirement or plan freeze, with separate consultation and execution truth.

## Generalization Evidence Bundle

- runtime-neutral consultation behavior tests
- requirement and plan artifact assertions
- consultation receipt and runtime summary evidence
- regression evidence that execution dispatch disclosure still behaves as before

## Non-Goals

- do not redesign router scoring or pack selection
- do not expose specialists as separate user-facing authorities
- do not replace execution-time specialist dispatch with consultation
- do not implement host-specific streaming UI as the only proof surface

## Autonomy Mode

Interactive governed execution with bounded discussion-time specialist consultation and explicit plan discipline.

## Assumptions

- frozen specialist recommendations are already rich enough to approve initial consultation candidates
- the current host adapter path can support consultation-style native specialist invocation with a consultation-specific prompt/schema contract
- requirement and plan artifact writers can consume consultation receipts without taking ownership of consultation execution

## Evidence Inputs

- Source task: Add governed discussion-time specialist consultation with progressive disclosure under `vibe`
- Relevant runtime surfaces: `Freeze-RuntimeInputPacket.ps1`, `Invoke-DeepInterview.ps1`, `Write-RequirementDoc.ps1`, `Write-XlPlan.ps1`, `Invoke-PlanExecute.ps1`
- Design spec: `docs/superpowers/specs/2026-04-12-vibe-discussion-time-specialist-consultation-design.md`
