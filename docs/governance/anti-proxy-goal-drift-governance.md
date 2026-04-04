# Anti-Proxy-Goal-Drift Governance

Status: official VCO governance rule
Effective posture: `report_only`
Effective scope: governed VCO requirement packets, execution plans, and completion reporting

## Purpose

This document turns anti-proxy-goal-drift from a discussion topic into an official canonical VCO governance rule and packet contract.

The goal is not to make work ceremonially heavy.
The goal is to stop local success signals from being silently upgraded into false claims of generalized capability.

Formal adoption means:

- anti-proxy-goal-drift is now part of standard governed VCO use,
- governed requirement and plan packets are expected to carry its declarations,
- completion reporting is expected to respect its staged-completion semantics,
- the current checker remains official governance evidence in `report_only` mode.

Formal adoption does not mean hard enforcement is active.

## Required Packet Declarations

Governed requirement and plan packets must now declare:

- `primary_objective`
- `non_objective_proxy_signals`
- `validation_material_role`
- `anti_proxy_goal_drift_tier`
- `intended_scope`
- `abstraction_layer_target`
- `completion_state`
- `generalization_evidence_bundle`

These declarations make the real objective, the proxy-risk surface, and the claimed proof boundary explicit.

These declarations are now part of the standard governed packet surface for VCO, not an experimental add-on.

## Tier Contract

### Tier A

Use for governance, runtime, router, protocol, and tooling-core changes.

Minimum expectation:
- generalized claims require stronger evidence,
- proof bundles must go beyond the trigger sample,
- Tier A is the only tier that may later be considered for hard enforcement in the first pilot.

### Tier B

Use for shared capabilities or reusable product-facing capability changes that do not alter the control-plane core.

### Tier C

Use for scenario-local or explicitly bounded work.

Tier C is not failure.
Tier C is the honest label for work that should not be over-universalized.

## Completion States

Allowed completion states:

- `complete`
- `partial`
- `scenario-scoped`
- `blocked`
- `not-yet-generalized`

The purpose of these labels is to prevent single-case success from being silently reported as universal completion.

## Report-Only Checker Posture

The anti-drift checker is officially adopted in `report_only` mode.

It may warn on:

- missing required declarations,
- tier under-classification or over-classification,
- completion/proof bundle mismatch,
- generalized completion claims backed only by local evidence,
- proxy-signal overclaim patterns.

Warnings are official governance evidence, not yet hard blocks.

## Anti-Abuse Rules

Anti-drift must not be used to:

- protect the incumbent trunk without comparative evidence,
- erase legitimate specialization,
- create pseudo-rigor through empty paperwork,
- claim intelligent detection before the pilot proves it.

## Pilot Boundary

Tier A hard enforcement is not active by default.
It requires:

- a bounded Tier A pilot,
- evidence on stability, usability, and intelligence,
- explicit review of specialization false positives,
- an enforcement decision packet.

Until that later decision exists, the correct VCO posture is:

- official report-only governance: yes,
- hard enforcement: no.
