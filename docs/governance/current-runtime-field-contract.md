# Current Runtime Field Contract

Date: 2026-05-01

## Purpose

This document defines the current Vibe-Skills runtime field vocabulary.

The current routing and usage model is:

```text
skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused
```

Current docs, runtime packets, generated plans, tests, and gates should use
this model unless they are explicitly marked as historical or retired-behavior
fixtures.

## Routing Layer

Allowed current routing fields:

```text
skill_candidates
skill_routing
skill_routing.candidates
skill_routing.selected
skill_routing.rejected
```

Meaning:

- `candidate`: a skill was considered by routing. This is not a use claim.
- `selected`: a skill was chosen into the governed work surface. This is not a
  use claim.
- `rejected`: a skill was considered but not selected.

## Usage Layer

Allowed current usage fields:

```text
skill_usage
skill_usage.used
skill_usage.unused
skill_usage.evidence
```

Meaning:

- `used`: a selected or loaded skill materially shaped an artifact.
- `unused`: a selected or loaded skill did not materially shape an artifact.
- `evidence`: the stage, artifact, and impact proof for material use.

Final used claims require `skill_usage.used` plus matching
`skill_usage.evidence`. Routing and selection alone are not use proof.

## Execution Layer

Preferred current execution vocabulary:

```text
skill_execution_lock
selected_skill_execution
skill_execution_units
execution_skill_outcomes
```

Execution anchors: `skill_execution_lock`, `selected_skill_execution`,
`skill_execution_units`, and `execution_skill_outcomes`.

### `skill_execution_lock`

`skill_execution_lock` records specialists that crossed the approved-plan boundary and therefore require execution resolution. It contains `locked_skill_ids`, `locked_dispatch`, `source_run_id`, and `resolution_required`. It is an execution-obligation field, not a material-use field.

`selected_skill_execution` is the execution-side copy of
the active execution source. When `skill_execution_lock` is active, execution
uses the locked dispatch; otherwise it uses `skill_routing.selected`. It
connects selected skills to real work, but it is not material-use proof by
itself.

Current root runtime packets should not expose retired dispatch fields as a
routing contract surface.

## Retired Layer

Retired current-routing fields and sections:

```text
legacy_skill_routing
specialist_recommendations
stage_assistant_hints
specialist_dispatch as root routing packet field
approved_dispatch as current execution accounting field
approved_skill_execution
approved_specialist_dispatch_count as current receipt field
## Specialist Consultation
discussion_specialist_consultation
planning_specialist_consultation
approved_consultation
consulted_units
discussion_consultation
planning_consultation
consultation expert
auxiliary expert
```

Older human-role labels are also retired. They may appear only in
retired-behavior tests, historical fixtures, archived historical docs, or
narrow execution-internal allowlists with an explicit scan reason.

## Current Behavior Rule

Current runtime behavior must derive selected skills from
`skill_routing.selected`, preserve approved-plan obligations in
`skill_execution_lock`, carry the active execution source into
`selected_skill_execution`, and record material use in `skill_usage.used`,
`skill_usage.unused`, and `skill_usage.evidence`.

Old routing, old consultation, old recommendation, and old stage-assistant
fields are not maintained compatibility inputs.
