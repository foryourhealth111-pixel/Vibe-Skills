# Anti-Proxy-Goal-Drift Formal Adoption

Date: 2026-03-17
Adoption class: official VCO governance rule
Enforcement posture: `report_only`

## Decision

Anti-proxy-goal-drift is formally adopted as an official VCO governance rule and governed packet step.

This adoption is based on:

- canonical rollout completion,
- template and checker integration,
- corpus and Tier A pilot stability,
- simulated usability evidence reaching `system_ok_for_simulated_pilot`.

## What Is Now Official

- Governed VCO requirement packets must carry the anti-drift declarations already embedded in the canonical templates.
- Governed VCO execution plans must carry the anti-drift control section already embedded in the canonical templates.
- Completion reporting should use the staged completion semantics (`complete`, `partial`, `scenario-scoped`, `blocked`, `not-yet-generalized`).
- The anti-drift checker is an official governance signal in report-only mode.

## What This Adoption Does Not Authorize

- It does not authorize Tier A hard enforcement.
- It does not authorize Tier B or Tier C hard enforcement.
- It does not claim real human burden evidence exists.
- It does not convert report-only warnings into hard blocks.

## Rationale

The strongest honest conclusion from the current evidence is:

- the design is good enough to be part of standard VCO governance,
- the design is not yet justified for hard enforcement.

That means the right move is formal adoption with boundary preservation, not delay and not overclaim.

## Resulting Operating Rule

Use anti-proxy-goal-drift as part of normal governed VCO operation now.

Treat it as:

- mandatory packet structure,
- mandatory completion honesty vocabulary,
- official report-only governance evidence.

Treat it not as:

- a hard gate,
- a reason to erase legitimate specialization,
- a claim that the live human burden question is already closed.
