# Vibe-Governed Project Delivery Acceptance Plan

## Execution Summary
Shift the repository from “runtime/governance self-proof” to “downstream project delivery proof”. The smallest coherent path is not a router rewrite. It is a new acceptance layer that sits on top of the existing governed runtime: freeze downstream acceptance criteria, execute real benchmark scenarios, verify the delivered project state, and report completion truth honestly.

## Frozen Inputs
- Requirement doc: [2026-03-28-vibe-governed-project-delivery-acceptance.md](../requirements/2026-03-28-vibe-governed-project-delivery-acceptance.md)
- Current reality:
  - runtime/governance tests are much stronger than downstream project acceptance tests
  - project delivery can still be under-verified even when runtime artifacts and some tests pass
  - completion wording is too easy to overstate relative to real delivered quality
- Invariants that must stay unchanged:
  - canonical router remains route authority
  - `vibe` remains runtime authority
  - root retains canonical requirement/plan truth
  - no second runtime/control plane is introduced

## Internal Grade Decision
- Grade: XL
- The work spans contracts, docs, verification architecture, benchmark projects, workflow runners, release semantics, and proof methodology.
- The design must coordinate multiple repository areas but still preserve one governed runtime model.

## Design Overview

### Design Principle 1: Delivery Truth Must Be Layered
Runtime correctness is not project correctness.
The repository must report four separate truths:

- governance truth
- engineering verification truth
- workflow completion truth
- product acceptance truth

No lower layer may silently stand in for a higher layer.

### Design Principle 2: Acceptance Must Be Frozen Up Front
If a downstream project is to be judged honestly, acceptance criteria must be frozen in the governed requirement and plan, not improvised at the end.

Required new frozen fields:

- user-facing goals
- critical functional checklist
- failure boundaries
- required verification commands
- required manual spot checks
- completion-reporting rules

### Design Principle 3: Real Scenarios Beat Repository Self-Reference
The acceptance framework must test `vibe` governing real project work in benchmark repos and scenario fixtures, not only VibeSkills exercising its own contracts.

### Design Principle 4: Completion Language Must Be Evidence-Scoped
Statuses such as `completed_with_failures`, `degraded_non_authoritative`, and `manual_actions_pending` are report states, not success synonyms.

### Design Principle 5: Stability, Usability, and Intelligence Need Different Proofs
- Stability is about repeatability and low flake.
- Usability is about operator clarity and real user-path success.
- Intelligence is about making good governance/execution choices, not only producing artifacts.

## Target Architecture

### A. Delivery Truth Model
Introduce one machine-readable delivery report contract with at least:

- `governance_truth`
- `engineering_verification_truth`
- `workflow_completion_truth`
- `product_acceptance_truth`
- `completion_language_allowed`
- `residual_risks`
- `manual_spot_checks`

This becomes the authoritative truth surface for downstream project completion reporting.

### B. Downstream Acceptance Contract Extension
Extend governed requirement and plan surfaces so downstream project work freezes:

- critical user flows
- edge-case expectations
- domain-specific specialist validation expectations
- mandatory regression checks
- manual acceptance checklist when full automation is not credible

### C. Scenario Corpus
Add a dedicated scenario family such as:

- `tests/scenarios/project_delivery/`
- `tests/scenarios/project_delivery/l-grade/`
- `tests/scenarios/project_delivery/xl-grade/`
- `tests/scenarios/project_delivery/specialist/`
- `tests/scenarios/project_delivery/failure_injection/`

Each scenario should include:

- prompt/task
- explicit `$vibe` usage expectation
- expected grade
- expected specialist set or allowance
- frozen acceptance criteria
- automated verification commands
- manual spot-check checklist
- forbidden outcomes

### D. Benchmark Repositories
Add benchmark repos under a bounded directory such as:

- `benchmarks/todo-webapp`
- `benchmarks/python-lib`
- `benchmarks/bioinformatics-mini`
- `benchmarks/docs-project`

Purpose:

- prove `vibe` can govern real downstream work
- validate functional completeness and regression behavior
- exercise specialist-assisted composite tasks

### E. Workflow Acceptance Runner
Add a workflow-acceptance harness, preferably runtime-neutral where possible, that:

1. loads a scenario
2. loads a benchmark repo
3. executes the governed run or replayable simulation
4. collects runtime/session artifacts
5. runs project-level validations
6. writes one delivery acceptance report

Expected output families:

- scenario execution receipt
- verification command log
- acceptance checklist result
- residual-risk summary
- completion-language disposition

### F. Completion Semantics Hardening
Harden runtime/reporting so the following are never flattened into “done”:

- partial execution success
- degraded specialist execution
- pending manual actions
- missing user-flow acceptance evidence

This requires explicit mapping from execution state to allowed completion language.

### G. Release Truth Gate
Add a release-facing gate that refuses full-success release wording unless:

- governance truth is passing
- engineering verification truth is passing
- workflow completion truth is passing
- product acceptance truth is passing

## Wave Plan

### Wave 1: Freeze Delivery Truth Contract
- Define the four-layer truth model.
- Define report vocabulary and forbidden completion mappings.
- Write stable governance documentation for downstream project delivery acceptance.

### Wave 2: Extend Requirement / Plan Acceptance Surfaces
- Add downstream acceptance sections to governed requirement expectations.
- Add delivery-specific DoD, regression, and manual-check sections to governed plans.
- Define how specialist-assisted scenarios carry domain-specific acceptance rules.

### Wave 3: Create Scenario Schema And Gold Corpus
- Design a machine-readable scenario schema.
- Create an initial gold corpus covering:
  - narrow feature work
  - bugfix/regression work
  - L staged execution
  - XL composite work
  - specialist-heavy work
  - failure/drift cases

### Wave 4: Add Benchmark Repositories
- Create or import bounded benchmark repos.
- Attach scenario-to-benchmark mappings.
- Ensure each benchmark has a small, credible acceptance surface.

### Wave 5: Implement Workflow Acceptance Runner
- Load scenario + repo fixtures.
- Execute governed runs or replayable harnesses.
- Run automated acceptance checks.
- Emit one delivery-truth report per scenario.

### Wave 6: Harden Completion Reporting
- Connect execution/reporting surfaces to the new truth model.
- Prevent runtime-only success from being reported as full project completion.
- Surface residual risk and manual actions in a mandatory way.

### Wave 7: Prove Stability / Usability / Intelligence
- Stability:
  - repeated-run matrix
  - failure injection
  - flake accounting
- Usability:
  - operator-readable report audit
  - manual spot-check contract audit
  - benchmark user-flow walkthroughs
- Intelligence:
  - grade-selection sanity checks
  - specialist-selection appropriateness checks
  - verification-depth adequacy checks
  - drift/escalation behavior checks

### Wave 8: Release Gate Integration And Rollout
- Add release truth gate.
- Add operator runbook.
- Define minimum passing suite before public completion claims or release notes can overclaim.

## Detailed Test Program

### 1. Functional Acceptance Tests
- Critical user story completion
- required outputs exist and are usable
- changed feature behaves as specified

### 2. Boundary And Error Tests
- malformed input
- empty input
- conflicting requirements
- missing dependency / provider / file / environment

### 3. Regression Tests
- reproduce prior bug
- confirm failure before fix when possible
- confirm pass after fix
- preserve unrelated core behavior

### 4. Workflow Tests
- requirement freeze matches final work
- plan steps match actual execution
- specialist dispatch stays bounded
- child lanes do not reopen root truth

### 5. Composite XL Tests
- multiple specialist domains
- step-level bounded parallelism
- disjoint write scopes
- escalation and same-round absorption behavior

### 6. Human-Like Acceptance Tests
- manual spot checks on benchmark repos
- artifact readability
- result usefulness
- final completion report honesty

## Proof Strategy

### Stability Proof
- repeated execution across multiple runs
- failure injection for selected specialist/unit paths
- flake-rate tracking
- deterministic artifact comparison where credible

Target proof:
- no hidden “one-pass only” success
- clear accounting for unstable cases

### Usability Proof
- acceptance reports must be operator-readable in one pass
- each scenario must state:
  - what works
  - what failed
  - what still needs manual confirmation
  - whether completion wording is allowed

Target proof:
- an operator can tell the true project state without reading raw logs

### Intelligence Proof
- verify that `vibe` chose a plausible grade
- verify that specialist usage was appropriate and bounded
- verify that verification depth matched task risk
- verify that drift or missing evidence downgraded completion wording

Target proof:
- the system is not only active; it is choosing wisely

## Ownership Boundaries
- Contracts and policy:
  - `config/*delivery*`
  - runtime/reporting policy surfaces
- Requirement/plan docs:
  - `docs/requirements/*`
  - `docs/plans/*`
- Stable governance docs:
  - `docs/*delivery*governance.md`
- Scenario corpus:
  - `tests/scenarios/project_delivery/*`
- Benchmark repos:
  - `benchmarks/*`
- Acceptance runner and gates:
  - `scripts/verify/runtime_neutral/*`
  - `scripts/verify/*delivery*gate.ps1`

## Verification Commands
- `git diff --check`
- `python3 -m pytest tests/runtime_neutral -v`
- `python3 -m pytest tests/scenarios/project_delivery -v`
- `pwsh -NoLogo -NoProfile -File scripts/verify/vibe-workflow-acceptance-gate.ps1`
- `pwsh -NoLogo -NoProfile -File scripts/verify/vibe-release-truth-gate.ps1`
- targeted benchmark acceptance commands per scenario

## Rollback Plan
- If the new acceptance layer causes ambiguity, keep existing runtime proof surfaces and disable only the new release-enforcement mapping.
- If benchmark repos become too heavy, retain the scenario schema and keep a smaller gold corpus.
- If fully automated acceptance is not credible for a scenario, force explicit manual spot-check state rather than pretending automation coverage exists.
- Never revert unrelated user changes.

## Success Metrics
- reduced false-completion rate
- increased scenario coverage of real project work
- explicit accounting of residual risks
- lower gap between “reported complete” and “user can actually use it”

## Phase Cleanup Contract
- clean temporary scenario outputs after each implementation batch
- audit and clear managed node/python residue created by acceptance harnesses
- preserve only intended docs, fixtures, benchmark repos, and proof artifacts
- emit cleanup receipts before claiming a wave is closed
