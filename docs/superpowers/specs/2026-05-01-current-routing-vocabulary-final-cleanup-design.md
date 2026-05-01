# Current Routing Vocabulary Final Cleanup Design

Date: 2026-05-01

## Goal

Finish the current routing vocabulary cleanup without changing routing
behavior, pack membership, skill execution, or the six governed stages.

The current model remains:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused
```

The current execution-join vocabulary remains:

```text
selected_skill_execution -> skill_execution_units -> execution_skill_outcomes
```

This slice targets only the current behavior surface and active policy fields
that still expose historical dispatch vocabulary. It should make the project
easier to understand without adding another routing layer or another role name.

## Current Findings

The previous cleanup passes established a stable checkpoint:

- Active pack manifests use `skill_candidates`.
- Current runtime packets use `skill_routing` and `skill_usage`.
- Current execution accounting uses `selected_skill_execution`,
  `direct_routed_skill_execution_units`, and `execution_skill_outcomes`.
- Root current packets are guarded against `legacy_skill_routing`,
  `stage_assistant_hints`, and root `specialist_dispatch`.
- The execution-internal hard-cleanup scan reports zero current
  `specialist_dispatch` references in its protected execution files.
- Runtime, delivery acceptance, pack routing smoke, config parity, offline
  skills, and version gates pass on `main`.

Remaining confusion is not primarily in active pack routing. It is in current
policy and helper surfaces that still use old names:

- `config/runtime-input-packet-policy.json` still declares
  `specialist_dispatch`, `specialist_dispatch_contract`, and
  `host_specialist_dispatch_contract` as current policy names.
- `scripts/runtime/VibeRuntime.Common.ps1` still exposes
  `Get-VibeRuntimeSpecialistDispatchProjection` as a current helper name.
- Some current generated receipts and handoff text still use
  `approved_specialist_dispatch_count` or similar wording.
- Some current tests still use `specialist_dispatch` in active behavior test
  names even when the asserted behavior now comes from
  `skill_routing.selected`.
- `specialist_recommendations` remains present in current policy and artifacts
  as a bridge term. It should not be expanded as a new current state.

These names no longer define the main routing model, but they continue to make
the codebase look like it has more routing concepts than it should.

## Non-Goals

This slice must not:

- Rename the six governed stages:

```text
skeleton_check
deep_interview
requirement_doc
xl_plan
plan_execute
phase_cleanup
```

- Delete skills or packs.
- Change pack routing scores, thresholds, selected skills, or task boundaries.
- Reintroduce old root packet compatibility.
- Keep old-format compatibility as a current runtime behavior.
- Rewrite historical docs or retired plans.
- Rename every occurrence of `specialist` in the repository.
- Claim a selected skill was used without `skill_usage.used` and evidence.
- Deploy changes to a live Codex host.

## Target Vocabulary

Use only the existing current vocabulary. Do not introduce replacement role
systems.

| Current confusing name | Target current name |
| --- | --- |
| `specialist_dispatch` as current root/policy field | remove or replace with `skill_execution` |
| `specialist_dispatch_contract` | `skill_execution_contract` |
| `host_specialist_dispatch_contract` | `host_skill_execution_contract` |
| `approved_dispatch` in current execution accounting | `selected_skill_execution` |
| `approved_specialist_dispatch_count` in current receipts | `selected_skill_execution_count` |
| `Get-VibeRuntimeSpecialistDispatchProjection` | `Get-VibeRuntimeSelectedSkillExecutionProjection` |
| direct-routed specialist execution units | `direct_routed_skill_execution_units` |
| degraded specialist execution units | `degraded_skill_execution_units` |
| blocked specialist execution units | `blocked_skill_execution_units` |

`specialist_recommendations` should not become a new public state. If it cannot
be removed in this slice, it should be treated as a compatibility or planning
bridge that feeds `skill_routing.selected`, not as a third state between
candidate and selected.

## Current Contract

After this cleanup, the current route contract should be explainable in one
line:

```text
packs offer skill_candidates; the runtime freezes skill_routing.selected; final claims come only from skill_usage.used / skill_usage.unused.
```

Execution joining remains separate from use proof:

```text
skill_routing.selected
  -> selected_skill_execution
  -> skill_execution_units
  -> execution_skill_outcomes
  -> skill_usage.used / skill_usage.unused with evidence
```

A selected skill is allowed to shape the work, but selected is not the same as
used. A skill is only used when the usage artifact records it under
`skill_usage.used` with evidence.

## Compatibility Boundary

Compatibility is allowed only when it is clearly isolated and not presented as
current authority.

Allowed:

- Read old artifacts in explicitly legacy tests.
- Preserve old fixture coverage when the fixture is marked as legacy.
- Keep retired docs and historical plans unchanged.
- Use a compatibility helper only when its name or surrounding test makes the
  legacy boundary clear.

Disallowed:

- Add new fallback from current runtime input to root `specialist_dispatch`.
- Add new current output fields using `approved_dispatch`,
  `specialist_dispatch`, or `stage_assistant`.
- Present `specialist_recommendations` or dispatch fields as a current route
  state.
- Use old fields as proof that a skill was materially used.

## Architecture

This cleanup has one current layer and one compatibility boundary.

### Current Layer

The current layer owns new runtime behavior and user-visible artifacts:

```text
config/pack-manifest.json
scripts/router/resolve-pack-route.ps1
scripts/runtime/Freeze-RuntimeInputPacket.ps1
scripts/runtime/Write-RequirementDoc.ps1
scripts/runtime/Write-XlPlan.ps1
scripts/runtime/Invoke-PlanExecute.ps1
scripts/runtime/Invoke-PhaseCleanup.ps1
packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py
```

These files should prefer current fields and should not expose old dispatch
names as active output.

### Compatibility Boundary

Compatibility may remain only behind explicit readers or retired tests. The
boundary should be visible from naming, test names, or scan allowlists.

For this slice, the preferred direction is not to add compatibility. If an old
reader already exists and removal is too risky, it should be moved out of the
current naming path or renamed so developers can see that it is not the current
contract.

## Expected Implementation Slices

Implementation should be split into small commits:

1. Add guard tests for current policy/helper/output vocabulary.
2. Rename active policy fields from dispatch contract names to skill execution
   contract names.
3. Rename current helper APIs that still expose `SpecialistDispatch` as the
   current projection.
4. Rename current receipt, handoff, and report fields that still say approved
   dispatch when they mean selected skill execution.
5. Tighten terminology scans so active policy/helper surfaces cannot regress.
6. Run focused and broad gates.

Each slice must leave `main` behavior recoverable and testable.

## Affected Files

Likely source files:

- `config/runtime-input-packet-policy.json`
- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `scripts/runtime/VibeRuntime.Common.ps1`
- `scripts/runtime/Write-RequirementDoc.ps1`
- `scripts/runtime/Write-XlPlan.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`
- `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
- `scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1`
- `scripts/verify/vibe-current-routing-contract-scan.ps1`

Likely tests:

- `tests/runtime_neutral/test_simplified_skill_routing_contract.py`
- `tests/runtime_neutral/test_terminology_field_simplification.py`
- `tests/runtime_neutral/test_routing_terminology_hard_cleanup.py`
- `tests/runtime_neutral/test_current_routing_contract_scan.py`
- `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
- `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
- New guard test for current routing vocabulary final cleanup.

## Test Design

### Guard Tests

Add a runtime-neutral guard that asserts current behavior files do not expose
old dispatch names as current fields or current helper APIs.

The guard should check active surfaces such as:

```text
config/runtime-input-packet-policy.json
scripts/runtime/VibeRuntime.Common.ps1
scripts/runtime/Write-XlPlan.ps1
scripts/runtime/Write-RequirementDoc.ps1
```

The guard should reject current-field assignments such as:

```text
specialist_dispatch =
specialist_dispatch_contract =
host_specialist_dispatch_contract =
approved_specialist_dispatch_count =
```

The guard should not fail on clearly retired docs or explicitly legacy tests.

### Behavior Tests

Current behavior tests must prove:

- `skill_routing.selected` remains the selection authority.
- `selected_skill_execution` is still populated from selected skills.
- `skill_usage.used` / `skill_usage.unused` remains the only use-proof surface.
- No root `specialist_dispatch` is emitted by current runtime packets.
- Blocked, degraded, direct-routed, and executed skill execution paths still
  report current fields.

### Gate Tests

Update scan tests so active policy/helper residue is visible and driven toward
zero. The final scan output should distinguish:

- current behavior violations
- current policy/helper vocabulary violations
- historical/retired references

## Verification Plan

Minimum focused verification:

```powershell
python -m pytest `
  tests/runtime_neutral/test_simplified_skill_routing_contract.py `
  tests/runtime_neutral/test_terminology_field_simplification.py `
  tests/runtime_neutral/test_routing_terminology_hard_cleanup.py `
  tests/runtime_neutral/test_current_routing_contract_scan.py `
  tests/runtime_neutral/test_l_xl_native_execution_topology.py `
  tests/runtime_neutral/test_runtime_delivery_acceptance.py -q
```

Required gates:

```powershell
.\scripts\verify\vibe-routing-terminology-hard-cleanup-scan.ps1
.\scripts\verify\vibe-current-routing-contract-scan.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-governed-runtime-contract-gate.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1
.\scripts\verify\vibe-version-packaging-gate.ps1
.\scripts\verify\vibe-version-consistency-gate.ps1
```

If promotion or host handoff files are changed, also run:

```powershell
.\scripts\verify\vibe-skill-promotion-execution-gate.ps1
```

Finish with:

```powershell
git diff --check
git status --short --branch
```

## Acceptance Criteria

The cleanup is complete only when:

- Current policy fields no longer require current users to reason through
  `specialist_dispatch`.
- Current helper names no longer expose dispatch as the active projection.
- Current receipts and handoffs use selected skill execution vocabulary when
  they mean selected skill execution.
- `skill_candidates -> skill_routing.selected -> skill_usage.used / unused`
  remains intact.
- `selected_skill_execution -> skill_execution_units ->
  execution_skill_outcomes` remains intact.
- Current tests and gates pass.
- Historical references remain either retired, explicitly legacy, or out of the
  current behavior scan.

## Risk Controls

- Do not do a global search-replace.
- Rename one surface at a time and run focused tests after each step.
- Prefer deleting current old fields over adding dual-write compatibility.
- If a compatibility read must remain, isolate it and make the boundary
  explicit.
- Stop if any runtime packet starts writing old root routing fields again.
- Stop if `skill_usage` evidence semantics weaken.

## Specialist Recommendations Policy

`specialist_recommendations` should be marked as a temporary planning bridge in
this slice. It should not be presented as a new current state and should not be
used as material-use evidence.

Removal is allowed only when focused tests prove no current behavior depends on
the field. The default implementation path is therefore:

1. Clarify the field as bridge-only when it must remain.
2. Prefer `skill_routing.selected` in current behavior.
3. Remove the field only in a later safe deletion slice if it is no longer read.
