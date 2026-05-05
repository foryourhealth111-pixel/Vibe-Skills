# Current Routing Contract

Date: 2026-05-01

## Purpose

This is the start-here document for current Vibe-Skills skill routing.

Use it to answer one question: after routing picks a skill, how does that skill
enter the six-stage work and become a real usage claim?

## Current Model

The current Vibe-Skills routing model is:

```text
skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused
```

This is the only model current user-facing docs and generated runtime outputs
should teach.

The model separates selection, approved-plan execution obligation, execution,
and material-use evidence. A skill can be selected and locked for execution
without being materially used yet.

## Operating Rules

1. Routing may list possible skills in `skill_candidates`.
2. The plan may choose skills through `skill_routing.selected`.
3. Plan approval may preserve selected skills across bounded re-entry through
   `skill_execution_lock`.
4. Execution may only treat selected or locked skills as work inputs through
   `selected_skill_execution`.
5. Completion may only claim a skill was used through `skill_usage.used` with
   matching `skill_usage.evidence`.

For compound tasks, split the work into bounded task segments and select the
directly relevant skill for each segment. Multiple selected skills are valid
when the task has multiple bounded segments; they do not create ranks or extra
states.

## Terms

| Term | Meaning |
| --- | --- |
| `candidate` | A skill was considered by routing. This is not a use claim. |
| `selected` | A skill was chosen into the work surface through `skill_routing.selected`. This is not a use claim. |
| `skill_execution_lock` | The approved-plan execution lock that preserves selected specialists across bounded re-entry. It is not a use claim. |
| `selected_skill_execution` | The selected skill list frozen into execution. This connects routing to actual work; it is still not a use claim. |
| `used` | A selected or loaded skill shaped an artifact and appears in `skill_usage.used` with evidence. |
| `unused` | A selected or loaded skill did not shape an artifact and appears in `skill_usage.unused`. |
| `evidence` | A stage, artifact reference, and impact summary proving material skill use. |
| `retired old-format fields` | Old routing, consultation, and dispatch fields are not current inputs, current outputs, or maintained compatibility targets. |

`skill_execution_lock` exists because bounded re-entry reruns the router. Once
a plan is approved, selected specialists become execution obligations and must
be executed, marked not applicable, deferred, or failed before delivery
acceptance can pass. The lock does not prove material skill use;
`skill_usage.used` remains the only material-use truth.

## Usage Proof

A skill may be reported as used only when all of these are true:

1. The skill appears in `skill_usage.used`.
2. The skill has at least one `skill_usage.evidence` record.
3. The evidence names a concrete stage and artifact impact.

Routing, selection, execution locks, old consultation receipts, and old dispatch
records are not usage proof.

## Current Output Rules

Current runtime outputs should use these names:

```text
skill_candidates
skill_routing.selected
skill_execution_lock
selected_skill_execution
skill_usage.used
skill_usage.unused
skill_usage.evidence
```

Current runtime outputs should not teach old routing mechanisms as active
behavior.

## Retired Old-Format Fields

The following old fields are retired. Current runtime code must not use them to
infer selected skills, material skill use, or current execution ownership:

```text
legacy_skill_routing
specialist_recommendations
specialist_dispatch
stage_assistant_hints
discussion_specialist_consultation
planning_specialist_consultation
approved_consultation
consulted_units
discussion_consultation
planning_consultation
```

When current and retired fields are both present in an old artifact, current
runtime code should prefer `skill_routing`, `skill_execution_lock`, and
`skill_usage` and ignore retired fields for current behavior.

## Non-Goals

This contract does not delete old artifacts. It defines how current routing and
current usage claims should be explained and verified.
