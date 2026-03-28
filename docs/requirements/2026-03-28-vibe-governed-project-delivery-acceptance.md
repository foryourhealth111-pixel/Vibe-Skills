# Vibe-Governed Project Delivery Acceptance

## Summary
Close the current gap between `vibe` runtime correctness and downstream project delivery correctness. The repository already proves many governance and runtime contracts, but it does not yet prove strongly enough that a project completed under `vibe` is functionally complete, user-usable, regression-safe, and honestly reported as such.

## Goal
Design and land a governed acceptance architecture where work completed under `vibe` is evaluated as a delivered project, not only as a correctly governed runtime session.

## Deliverable
A repository change program and documentation bundle that adds:

- a delivery-truth model separating governance, engineering verification, workflow completion, and product acceptance
- scenario-based acceptance fixtures for real project work completed under `vibe`
- benchmark repositories and gold-task corpora that simulate real downstream work rather than only VibeSkills self-tests
- a workflow-acceptance runner that executes governed tasks and judges project outcomes against frozen acceptance criteria
- stronger completion semantics so `completed_with_failures`, `manual_actions_pending`, and degraded paths cannot be reported as full delivery success
- release and operator documentation for how project delivery under `vibe` is validated and proved

## Constraints
- This project is about testing downstream work completed under `vibe`, not about host installation correctness or adapter parity by themselves.
- Preserve existing single-router and single-runtime-owner invariants.
- Do not create a second visible runtime, second requirement truth, or second execution-plan truth.
- Prefer additive acceptance and proof surfaces over a disruptive router/runtime rewrite.
- Preserve current governance evidence while making project-delivery evidence a first-class required surface.
- Do not claim that runtime success alone proves project success.
- Keep domain-specific expert workflows intact when the acceptance framework evaluates specialist-assisted work.

## Acceptance Criteria
- The repository defines four separate delivery truth states:
  - governance truth
  - engineering verification truth
  - workflow completion truth
  - product acceptance truth
- `vibe`-governed requirement and plan surfaces can freeze downstream acceptance criteria for project work, not only runtime/process expectations.
- The repository includes scenario fixtures that cover:
  - single-skill project work
  - L-grade staged work
  - XL-grade composite work
  - specialist-heavy work
  - intentionally failing or drifting work
- Benchmark repositories exist so the acceptance framework tests `vibe` governing other projects, not just VibeSkills governing itself.
- A workflow-acceptance runner can:
  - execute a governed scenario
  - collect runtime artifacts
  - run project-level validation
  - produce a structured acceptance report
- Completion/reporting rules prevent the system from presenting the following states as full success:
  - `completed_with_failures`
  - `degraded_non_authoritative`
  - `manual_actions_pending`
  - missing product acceptance evidence
- Stability proof requires repeated scenario execution, failure injection, and flake accounting rather than a single happy-path pass.
- Usability proof requires operator-readable acceptance reports and bounded manual spot-check contracts.
- Intelligence proof requires evidence that `vibe` selected an appropriate execution grade, specialist usage, verification depth, and escalation behavior for the project scenario.

## Primary Objective
Make `vibe` accountable for the actual delivered quality of downstream project work, not only for the correctness of its own governance process.

## Proxy Signal
Every governed project run produces a delivery report that clearly distinguishes:

- process correctness
- code/test correctness
- workflow completeness
- final user-facing acceptance

## Scope
In scope:
- delivery-truth model
- downstream acceptance contracts
- scenario corpus design
- benchmark repository design
- workflow-acceptance runner design
- completion-language hardening
- release proof and reporting rules
- documentation and rollout plan

Out of scope:
- redesigning host installation flows
- reworking the canonical router scoring model
- replacing existing runtime artifacts with an entirely new runtime
- promising full automation for every domain without bounded human spot-check contracts

## Completion
The work is complete when `vibe` can no longer honestly report a project as complete without downstream acceptance evidence showing that the delivered work is functionally sufficient, user-usable, and regression-aware.

## Evidence
- new or updated requirement/plan/stable governance docs
- scenario schema and benchmark-repo design
- verification and acceptance runner design
- release-gate and reporting design
- proof strategy covering stability, usability, and intelligence

## Non-Goals
- Do not reduce project delivery quality to runtime artifact existence.
- Do not let unit tests alone stand in for downstream project acceptance.
- Do not hide missing functionality behind broad “done” wording.
- Do not flatten specialist-assisted tasks into generic acceptance logic that ignores domain-specific verification needs.

## Autonomy Mode
interactive_governed

## Assumptions
- Existing `vibe` requirement and plan stages are strong enough to freeze downstream acceptance criteria once the contract is extended.
- Current runtime/session artifacts can be reused as evidence inputs rather than replaced.
- The largest missing layer is downstream project acceptance, not basic runtime sequencing.
- The current repository structure can host benchmark repositories and scenario fixtures without breaking canonical governance surfaces.

## Evidence Inputs
- Source task: plan a full delivery-acceptance enhancement program for work completed under `vibe`
- Prior finding: current runtime-neutral and gate-heavy tests validate governance/runtime strongly but validate downstream project success weakly
