# Anti-Proxy-Goal-Drift Corpus Governance

## Purpose

The anti-proxy-goal-drift corpora are governance test instruments.
They exist to validate anti-drift detection behavior before any stronger enforcement is claimed.

## Corpus Families

### Tier Gold

Used to verify that the checker can distinguish:

- correct Tier A,
- correct Tier B,
- correct Tier C,
- under-classification,
- over-classification.

### Red Team

Used to verify that the checker can catch the failure modes it is meant to police:

- sample hardcoding temptation,
- demo-only bypass temptation,
- symptom-fix-only overclaim,
- test-green / broken-main-chain overclaim.

### Legitimate Specialization

Used to verify that scenario-specific work is not falsely escalated.

### Completion State

Used to verify that all honest completion labels are representable:

- `complete`
- `partial`
- `scenario-scoped`
- `blocked`
- `not-yet-generalized`

## Fixture Contract

Each corpus fixture should declare:

- `fixture_id`
- `corpus_family`
- `surface_class`
- `anti_proxy_goal_drift_tier`
- `primary_objective`
- `non_objective_proxy_signals`
- `validation_material_role`
- `intended_scope`
- `abstraction_layer_target`
- `completion_state`
- `generalization_evidence_bundle`
- `expected`

The `expected` block must encode the warning contract the report-only checker should produce.

## Review Rules

- Red-team fixtures should intentionally tempt proxy optimization.
- Legitimate specialization fixtures should remain clean under report-only checking.
- Corpus labels must be reviewed before they are used to justify enforcement.
- Poor corpus labeling is itself a governance failure.
