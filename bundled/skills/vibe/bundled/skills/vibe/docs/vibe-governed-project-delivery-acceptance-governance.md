# Vibe-Governed Project Delivery Acceptance Governance

This document defines the stable rule set for judging work completed under `vibe` as a delivered project rather than as a merely well-governed runtime session.

## Why This Exists

`VibeSkills` already contains strong governance and runtime checks.
That is necessary, but not sufficient.

The missing question is:

> Did the downstream project actually become complete, usable, and trustworthy for the user?

Without a delivery-acceptance layer, the system can over-report success whenever:

- runtime stages completed
- requirement and plan artifacts exist
- some tests passed
- specialist units ran
- cleanup receipts were emitted

Those signals prove process health.
They do not by themselves prove downstream project quality.

## Core Rule

`vibe` may govern the work, but governance success is not delivery success.

Every governed project run must distinguish four truths:

1. governance truth
2. engineering verification truth
3. workflow completion truth
4. product acceptance truth

No lower truth may be reported as if it automatically implies a higher one.

## Mental Model

Short form:

`governance proves process, verification proves code, acceptance proves delivery`

## Delivery Truth Layers

### Governance Truth

Proves that:

- the governed stages ran correctly
- requirement and plan surfaces are traceable
- execution and cleanup evidence exist
- runtime authority rules were preserved

### Engineering Verification Truth

Proves that:

- code-level tests were run
- relevant verifiers passed or failed explicitly
- regressions were checked where appropriate

### Workflow Completion Truth

Proves that:

- the planned work items were actually executed
- required artifacts and outputs were produced
- specialist and child-lane work reconciled back into the root-governed task

### Product Acceptance Truth

Proves that:

- the delivered project behavior matches frozen acceptance criteria
- critical user flows work
- edge cases were considered
- residual risks are known
- completion wording is honest relative to evidence

## Forbidden Reporting Collapses

The following are forbidden:

- reporting governance truth as product acceptance truth
- reporting unit-test success as full downstream project acceptance
- reporting `completed_with_failures` as complete delivery
- reporting `degraded_non_authoritative` as equivalent success
- reporting `manual_actions_pending` as fully ready

## Stable Reporting Rule

The final governed report for project work must always answer:

1. What is proven about process?
2. What is proven about code and verification?
3. What is proven about actual project behavior?
4. What is still not proven?
5. What completion wording is therefore allowed?

## Acceptance Freezing Rule

Downstream project acceptance must be frozen in the governed requirement and plan.

At minimum, the frozen acceptance contract should identify:

- critical user flows
- functional checklist
- important edge cases
- regression expectations
- specialist-specific validation expectations
- manual spot checks when automation is insufficient

This is now a main-chain rule, not only an external verification convention:

- `requirement_doc` must freeze these acceptance surfaces
- `xl_plan` must schedule how they will be checked
- `phase_cleanup` must emit the per-run delivery-acceptance report

## Scenario Rule

Project-delivery proof must be grounded in scenario fixtures and benchmark repos that represent real downstream work.

The system must not rely only on:

- VibeSkills self-tests
- config parity
- contract artifacts
- runtime packet existence

## Human-Spot-Check Rule

When a domain cannot be credibly proven by automation alone, the system must record a bounded manual acceptance checklist.

The correct state is:

- `automation_partial_manual_required`

not:

- “done”

## Specialist Acceptance Rule

If a specialist skill meaningfully contributes to project delivery, acceptance must check the output in the specialist's own domain terms.

Examples:

- writing output must be checked for writing-quality and structure
- scientific analysis must be checked for method/output sanity
- data-processing work must be checked for functional correctness and regression safety

The system must not flatten all specialist output into a generic “some unit executed” success signal.

## Stability Rule

A single happy-path run is not enough.

Delivery proof must include some combination of:

- repeated execution
- failure injection
- flake accounting
- scenario replay

## Usability Rule

Operators must be able to determine project state without reading raw runtime internals.

Therefore delivery reports must state, in plain terms:

- what works
- what does not
- what remains risky
- whether the project is actually acceptable for handoff

## Intelligence Rule

The acceptance framework should also judge whether the governed system made good choices, including:

- grade selection
- specialist selection
- verification depth
- escalation behavior
- honesty of completion-language downgrades

This is how the system proves not only activity, but judgment.

## What Success Looks Like

When `vibe` finishes a downstream project task:

- the runtime is governed correctly
- the implementation is verified appropriately
- the delivered project is tested against frozen acceptance criteria
- the final report says only what the evidence supports

## Operator Rule Of Thumb

If a run only proves that `vibe` behaved correctly, then it has not yet proved the project is complete.
