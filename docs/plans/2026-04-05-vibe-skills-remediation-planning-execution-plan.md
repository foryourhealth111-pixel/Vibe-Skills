# Vibe-Skills Remediation Planning Execution Plan

Date: 2026-04-05
Run ID: 20260405-vibe-skills-remediation-planning
Internal grade: L
Runtime lane: root_governed

## Planning Objective

Define an implementation-ready repair strategy for the audited issues without changing code in this turn.

## Frozen Inputs

- `docs/requirements/2026-04-05-vibe-skills-project-audit.md`
- `outputs/runtime/vibe-sessions/20260405-vibe-skills-audit/phase-plan-execute.json`
- `docs/requirements/2026-04-04-remaining-architecture-closure.md`
- `docs/plans/2026-04-04-remaining-architecture-closure-plan.md`
- `docs/requirements/2026-04-05-tests-derived-and-replay-hygiene.md`
- `docs/plans/2026-04-05-tests-derived-and-replay-hygiene-execution-plan.md`

## Internal Design Rules

### High Cohesion

- semantic ownership stays in `packages/contracts` for contract truth
- verification orchestration stays in `packages/verification-core`
- script wrappers and CLI entrypoints remain thin adapters
- hygiene policy should be centralized, not replicated per subtree

### Low Coupling

- avoid new script-local semantic fallbacks
- prefer shared bootstrap helpers for path setup over duplicating constant inventories
- keep repo-topology truth in one declarative surface or one bounded test helper, not in scattered literals
- CI should validate canonical invariants, not an arbitrary subset that can drift from repository truth

### No Functional Regression

- every cut gets focused verification first, then broader regression
- compatibility shims may remain, but only as delegates
- cross-platform behavior must be rechecked when changing path/bootstrap or workflow behavior

## Recommended Remediation Waves

### Wave 1: Rebuild Trust In Verification

Purpose:
Make CI and local verification represent real repository health before changing semantics.

Scope:
- close the CI blind spot in `.github/workflows/vco-gates.yml`
- define a canonical Python validation target set
- isolate hygiene-sensitive tests from self-generated residue

Implementation guidance:
- keep one fast validation lane, but ensure it includes the currently failing contract and integration invariants
- add a broader scheduled or PR gate only if runtime is acceptable; otherwise expand the existing gate to cover the architectural cutover tests
- do not weaken failing tests merely to regain green CI

Preferred outcome:
- CI fails on the same classes of drift that local `pytest -q --maxfail=3` exposed

### Wave 2: Remove Duplicate Runtime Surface Semantics

Purpose:
Restore single-source ownership for runtime packaging and ignore-policy semantics.

Scope:
- `scripts/common/runtime_contracts.py`
- any adjacent consumer or bridge code that still tolerates duplicated fallback semantics

Implementation guidance:
- preserve `runtime_contracts.py` only as a compatibility projection or import surface
- replace semantic fallback bodies with a thin bootstrap + import model
- if bootstrap is needed, make it responsible only for locating `packages/contracts/src`, not for re-owning contract data
- prefer fail-fast on missing shared contracts over silently re-materializing a second truth surface

Preferred outcome:
- `packages/contracts/src/vgo_contracts/runtime_surface_contract.py` is the only semantic owner of packaging and runtime-artifact ignore policy
- `scripts/common/runtime_contracts.py` becomes a thin adapter with no inline contract inventory

### Wave 3: Make Python Hygiene Hermetic

Purpose:
Ensure test execution does not dirty tracked source trees.

Scope:
- Python test execution behavior
- hygiene tests under `tests/runtime_neutral`
- repo-wide cache-writing policy where necessary

Implementation guidance:
- solve the cause, not only the symptom
- preferred first lever: configure test execution to avoid writing bytecode into repo-owned source trees
- if needed, add explicit cleanup only as secondary defense, not the primary contract
- broaden the policy from `apps/` to repo-owned Python source trees if that can be done without inflating scope excessively

Preferred outcome:
- running the intended Python test suites does not create `__pycache__` or `.pyc` residue under tracked source roots
- hygiene tests validate a hermetic invariant instead of fighting normal interpreter behavior

### Wave 4: Reconcile Repo Topology Truth

Purpose:
Eliminate stale architecture-root assertions.

Scope:
- `tests/contract/test_repo_layout_contract.py`
- any doc or helper that still encodes obsolete `platform/` or `tools/` roots as canonical topology

Implementation guidance:
- first determine whether `platform/` and `tools/` were intentionally retired or merely moved
- if retired, update the contract to current authoritative topology
- prefer a declarative topology owner or bounded helper over hard-coded literals in ad hoc tests
- ensure renamed roots such as `adapters/` and `scripts/` are treated as intentional architecture, not incidental implementation details

Preferred outcome:
- repo layout tests verify the actual architecture contract, not a stale transitional snapshot

### Wave 5: Architectural Proof And Cleanup

Purpose:
Prove the microphase reduced coupling and restored verification credibility.

Scope:
- focused verification
- broader regression
- artifact and cache cleanup
- residual-risk update

Implementation guidance:
- update closure/proof docs only after verification passes
- keep temporary cleanup bounded to artifacts created by the phase
- record any intentionally retained compatibility fallback as residual inventory

## Detailed Workstreams

### Workstream A: Canonical Validation Surface

Owner:
- CI workflow and verification maintainers

Changes to plan for:
- create one named Python validation matrix or a shared target list
- include:
  - `tests/contract/test_repo_layout_contract.py`
  - `tests/integration/test_runtime_surface_contract_cutover.py`
  - `tests/runtime_neutral/test_apps_surface_hygiene.py`
  - existing targeted runtime-neutral checks already in CI

Why:
- these tests guard architecture truth, contract cutover, and hygiene invariants

### Workstream B: Contract Bootstrap Boundary

Owner:
- contracts + verification/runtime common boundary

Changes to plan for:
- introduce or reuse a tiny bootstrap helper that only inserts `packages/contracts/src` on `sys.path`
- keep consumer modules importing semantic owners from `vgo_contracts.*`
- remove duplicated constants/functions from `scripts/common/runtime_contracts.py`

Why:
- this preserves compatibility entrypoints without preserving semantic duplication

### Workstream C: Hermetic Python Execution Policy

Owner:
- test/CI maintainers

Changes to plan for:
- set interpreter or pytest execution policy to prevent bytecode emission in repo-owned trees during validation
- optionally add pre/post test residue assertions as a guardrail
- extend hygiene coverage to other Python source roots if they are currently susceptible

Why:
- hygiene must be systemic, not directory-specific whack-a-mole

### Workstream D: Topology Contract Normalization

Owner:
- architecture/contract maintainers

Changes to plan for:
- define current top-level roots explicitly
- update the failing test to consume current topology truth
- document the retirement mapping:
  - former `tools/` -> current `scripts/build` and `scripts/release`
  - any former `platform/` ownership -> current `adapters/` or other canonical surfaces, if applicable

Why:
- outdated architectural assertions create noise and mask real regressions

## Sequencing Constraints

1. Fix verification credibility before or alongside semantic cutovers.
2. Do not refactor topology assertions before confirming the intended current architecture.
3. Do not merge the runtime-contract cutover without tests proving the new thin-boundary behavior.
4. Do not declare hygiene complete if tests still write cache residue in other repo-owned Python trees.

## Verification Plan For The Future Implementation Turn

### Focused Verification

```bash
pytest -q tests/contract/test_repo_layout_contract.py
pytest -q tests/integration/test_runtime_surface_contract_cutover.py
pytest -q tests/runtime_neutral/test_apps_surface_hygiene.py
pytest -q tests/unit/test_runtime_surface_contract.py
pytest -q tests/unit/test_vgo_cli_commands.py tests/unit/test_vgo_cli_repo.py
```

### Gate-Parity Verification

```bash
pytest -q \
  tests/runtime_neutral/test_custom_admission_bridge.py \
  tests/runtime_neutral/test_docs_readme_encoding.py \
  tests/runtime_neutral/test_governed_runtime_bridge.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_python_validation_contract.py
```

### Broader Regression

```bash
pytest -q --maxfail=1
git diff --check
find apps packages scripts tests -type d -name '__pycache__'
find apps packages scripts tests -type f \( -name '*.pyc' -o -name '*.pyo' \)
```

## Rollback Rules

- If CI widening causes unacceptable runtime cost, keep the expanded invariant set but split fast and broad lanes explicitly rather than dropping the new checks.
- If runtime-contract cutover breaks bootstrap/import behavior, revert to the last thin delegate state, not to duplicated semantic fallbacks.
- If hygiene controls affect user-facing install/runtime behavior, back out the execution-policy change and re-scope it to test-only environments.
- If topology normalization reveals a disputed architecture root, pause implementation and resolve the canonical owner surface before editing tests.

## Phase Cleanup Expectations

- remove any repo-generated bytecode or cache artifacts created during the implementation phase
- keep only intentional docs/tests/config changes
- update residual-risk notes if any compatibility fallback remains intentionally bounded
