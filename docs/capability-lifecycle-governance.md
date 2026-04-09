# Capability Lifecycle Governance

## Purpose

Wave92 adds a lifecycle policy for governed capabilities so intake, shadow, soft review, ceiling, and retirement are explicit rather than implicit.
The lifecycle layer sits above capability catalog and dedup evidence, and below promotion board decisions.

## Governance Scope

- Lifecycle state changes remain manual-review events, never auto-routing events.
- Every lifecycle row must name owner lane, current state, next allowed state, and ceiling reason.
- Productization may only occur after dedup, no-go boundary, and evidence requirements are satisfied.

## Required Invariants

- `productize_only_after_dedup = true` remains fixed.
- States are bounded to `intake`, `shadow`, `soft_review`, `strict_review`, `ceiling`, and `retire`.
- Lifecycle transitions cannot rewrite pack routing or board stage automatically.
- Every lifecycle row must preserve `explicit_no_go` and `promotion_ceiling` semantics.

## Non-Goals

- No hidden promotion engine is introduced.
- No capability may skip from intake to release-facing posture without evidence layers in between.

Validation is performed by `scripts/verify/vibe-capability-lifecycle-gate.ps1`.
