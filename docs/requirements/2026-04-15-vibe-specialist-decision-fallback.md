# Vibe Specialist Decision And Repo-Asset Fallback Requirement

## Summary

Add a first-class `specialist_decision` contract so governed `vibe` always records whether specialist execution was approved, stayed advisory, or required an explicit no-match resolution, including traceable repo-asset fallback when no dedicated specialist exists.

## Goal

Close the remaining governance gap where a run could truthfully have no matched specialist but still rely on repo-local assets without leaving a structured, reviewable fallback decision artifact.

## Deliverable

A governed runtime and delivery-acceptance update that:

- freezes a `specialist_decision` object in runtime artifacts
- surfaces specialist decision truth in requirement and plan documents
- allows explicit repo-asset fallback disclosure through `specialist-decision.json`
- blocks green completion when no-specialist runs leave the resolution undeclared

## Constraints

- `vibe` remains the only governed runtime authority
- do not introduce `AGENTS.md` or any second control plane
- reuse existing governed artifacts and optional sidecars instead of adding a parallel receipt system
- repo-asset fallback stays non-green even when it is explicit and traceable
- approved specialist dispatch must keep the existing `specialist_user_disclosure` contract unchanged

## Acceptance Criteria

- `runtime-input-packet.json` includes `specialist_decision`
- `execution-manifest.json`, `phase-execute.json`, and `runtime-summary.json` include `specialist_decision`
- requirement docs include `## Specialist Decision`
- execution plans include `## Specialist Decision Plan`
- delivery acceptance reports include `specialist_decision_truth`
- a no-specialist run without explicit resolution becomes non-green
- a declared repo-asset fallback without asset paths, reason, legal basis, or traceability fails delivery acceptance
- a declared, traceable repo-asset fallback produces `PASS_DEGRADED`

## Specialist Decision

- `runtime-input-packet.json` must freeze `specialist_decision` as the canonical structural decision surface for the run.
- `execution-manifest.json`, `phase-execute.json`, and `runtime-summary.json` must mirror the same `specialist_decision` payload instead of reopening the decision in prose.
- execution plans must include `## Specialist Decision Plan` so no-match handling stays explicit before `plan_execute`.
- delivery acceptance reports must evaluate the same payload through `specialist_decision_truth`.
- `specialist_decision` must record `decision_state` and `resolution_mode`.
- approved specialist execution must record `approved_dispatch_skill_ids`.
- repo-asset fallback must record `used`, `asset_paths`, `reason`, `legal_basis`, and `traceability_basis`.

## Product Acceptance Criteria

- users can always tell whether a specialist existed for the task
- users can always tell whether a no-match path was resolved as “no specialist needed” or “repo-asset fallback”
- repo-asset fallback remains visible as a governed compromise rather than silently collapsing into `PASS`

## Manual Spot Checks

- Run delivery acceptance with no specialist recommendations and no explicit resolution; confirm the result is non-green.
- Run delivery acceptance with explicit repo-asset fallback and complete traceability; confirm the result is `PASS_DEGRADED`.
- Run delivery acceptance with repo-asset fallback missing traceability fields; confirm the result is `FAIL`.

## Completion Language Policy

Do not claim this work is complete unless fresh verification proves the new `specialist_decision` contract in runtime artifacts, docs, and delivery acceptance.

## Delivery Truth Contract

Specialist governance transparency is successful only when the system can distinguish:

- approved specialist dispatch
- advisory-only or blocked specialist outcomes
- no-match runs that explicitly resolved to no-specialist-needed
- no-match runs that explicitly resolved to repo-asset fallback with traceability
- no-match runs that stayed unresolved and therefore cannot close green

## Artifact Review Requirements

No additional artifact review requirements were frozen for this run.

## Code Task TDD Evidence Requirements

- Add failing-first tests for missing no-match specialist resolution.
- Add failing-first tests for traceable repo-asset fallback.
- Add failing-first tests for incomplete repo-asset fallback disclosure.
- Verify runtime bridge artifacts expose `specialist_decision`.

## Code Task TDD Exceptions

No code-task TDD exceptions were frozen for this run.

## Baseline Document Quality Dimensions

No baseline document quality dimensions were frozen for this run.

## Baseline UI Quality Dimensions

No baseline UI quality dimensions were frozen for this run.

## Task-Specific Acceptance Extensions

- `specialist_decision_truth` must remain distinct from `specialist_disclosure_truth`.
- `repo_asset_fallback` must remain reviewable from governed artifact evidence, not chat-history inference.
- missing no-match resolution must not silently collapse into green completion.

## Research Augmentation Sources

- `SKILL.md`
- `scripts/runtime/VibeRuntime.Common.ps1`
- `scripts/runtime/Write-RequirementDoc.ps1`
- `scripts/runtime/Write-XlPlan.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`
- `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
- `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_support.py`
- `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
- `tests/runtime_neutral/test_governed_runtime_bridge.py`

## Primary Objective

Make no-match specialist resolution explicit enough that repo-asset fallback cannot hide behind the absence of a dedicated specialist skill.

## Non-Objective Proxy Signals

- increasing the number of surfaced specialist recommendations without resolving no-match cases
- treating repo-asset fallback as equivalent to approved specialist dispatch
- keeping fallback explanation only in prose instead of governed artifacts

## Validation Material Role

Runtime-neutral tests, governed runtime bridge tests, and generated runtime artifacts are the source of truth for this change.

## Anti-Proxy-Goal-Drift Tier

Tier 1 governance-truth preservation.

## Intended Scope

Canonical governed runtime artifacts and delivery-acceptance semantics for specialist no-match resolution under `vibe`.

## Abstraction Layer Target

Runtime artifact projection, governed docs, and verification-core delivery acceptance.

## Completion State

Complete only when runtime artifacts, requirement/plan surfaces, and delivery acceptance all carry the new specialist decision truth.

## Generalization Evidence Bundle

- targeted runtime-delivery tests
- governed runtime bridge test coverage
- delivery-acceptance contract alignment

## Non-Goals

- do not redesign specialist ranking or router matching
- do not auto-infer task-specific repo assets from arbitrary execution output
- do not add a second runtime or second requirement/plan surface

## Autonomy Mode

Interactive governed execution with bounded runtime and verification updates.

## Assumptions

- approved specialist dispatch disclosure already has its own enforced contract
- repo-asset fallback details can be carried by a governed session sidecar without creating a second authority surface
- non-green no-match handling is preferable to silent green completion

## Evidence Inputs

- Source task: Close the remaining no-match specialist fallback governance gap under `$vibe`
- Relevant runtime surfaces: `scripts/runtime/VibeRuntime.Common.ps1`, `scripts/runtime/Invoke-PlanExecute.ps1`
- Relevant verification surfaces: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`, `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
