# Bounded Vibe Wrapper Entry Modes Requirement

## Goal
Make the public `vibe` wrapper family behave like bounded entry modes instead of mere wording biases.

The required user-facing behavior is:

- `vibe`: canonical governed runtime through `phase_cleanup`
- `vibe-what-do-i-want`: clarify intent and freeze the requirement, then stop
- `vibe-how-do-we-do`: produce the frozen requirement and execution plan, then stop
- `vibe-do-it`: execute the governed flow through completion without bypassing prior governed stages

## Problem Statement
The current wrapper skill implementation only says "bias canonical `vibe` toward ...".

That is insufficient because:

- canonical `vibe` still declares one fixed six-stage state machine
- wrapper skill text does not impose a hard stop boundary
- before this change, repo-level discoverable-entry metadata said `vibe-want` stopped at `deep_interview`; current truth must be `requirement_doc`
- wrapper wording, entry-surface config, quick-start docs, and install/check truth do not currently agree

This mismatch causes the observed failure mode:

- selecting `vibe-what-do-i-want` can still continue into planning, execution, cleanup, and PR completion

## Required Outcomes
- Wrapper semantics must be expressed as explicit stop-stage contracts, not only prose bias.
- Repo truth for wrapper stop behavior must be internally consistent across:
  - wrapper skill files
  - command shims
  - `config/vibe-entry-surfaces.json`
  - runtime/contract docs
  - install/check validation
  - regression tests
- Codex full-profile check logic must validate public wrapper skill roots directly rather than silently accepting hidden bundled copies.
- Aggregated runtime packaging truth must match the full-profile wrapper projection contract.
- Codex uninstall fallback inventory must not contain stale or impossible wrapper command names.

## Scope
In scope:

- wrapper skill contract wording
- discoverable entry stop targets
- canonical runtime documentation where wrapper/shortcut semantics are described
- packaging manifests
- Codex install/check/uninstall verification
- docs and tests required to keep the contract stable

Out of scope:

- introducing a second runtime authority
- changing the fixed stage order of canonical `vibe`
- making `vibe-do-it` skip `deep_interview`, `requirement_doc`, or `xl_plan`
- redesigning unrelated hosts beyond contract alignment that is already shared

## Acceptance Criteria
- `vibe-what-do-i-want` is documented and tested to stop after `requirement_doc`.
- `vibe-how-do-we-do` is documented and tested to stop after `xl_plan`.
- `vibe-do-it` is documented and tested to continue through `phase_cleanup`.
- `config/vibe-entry-surfaces.json` agrees with the wrapper contract.
- `check.sh` and `check.ps1` fail if the Codex public wrapper skill roots are missing even when hidden bundled copies exist.
- `config/runtime-core-packaging.json` and `config/runtime-core-packaging.full.json` agree on full-profile compatibility projections.
- Codex uninstall fallback inventory does not reference colon-named phantom wrapper commands.
- Focused regression tests cover stop-target truth, public-wrapper verification truth, packaging truth, and uninstall truth.

## Non-Goals
- Do not convert wrappers into separate runtime authorities.
- Do not add new public entry ids beyond the current canonical and wrapper family.
- Do not remove command shims in this turn if they are still needed for compatibility.
