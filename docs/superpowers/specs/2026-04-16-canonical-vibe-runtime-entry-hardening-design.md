# Canonical Vibe Runtime Entry Hardening Design

## Goal

Make explicit `$vibe` and `/vibe` entry resolve to the canonical `vibe` runtime instead of degrading to "read `SKILL.md` and simulate the workflow in prose".

This enhancement wave supports only:

- Codex
- Claude Code
- OpenCode

The design must keep `vibe` as the only runtime authority, keep the runtime core cohesive, keep host adapters thin, and make false canonical-run claims impossible.

## Non-Goals

- Do not redesign the six-stage governed runtime state machine.
- Do not expand support for Cursor, Windsurf, or OpenClaw in this wave.
- Do not create a second router or second planning authority.
- Do not make `SKILL.md` itself responsible for launching runtime logic.
- Do not regress existing discoverable wrapper names such as `Vibe`, `Vibe: What Do I Want?`, `Vibe: How Do We Do It?`, and `Vibe: Do It`.

## Problem Statement

The current codebase has a split-brain runtime entry model:

1. Some surfaces already say explicit `$vibe` should enter canonical `vibe` first and should block instead of silently falling back.
2. Other surfaces still materialize `vibe` as a host-visible wrapper that says "Use the `vibe` skill and follow its governed runtime contract for this request."
3. Core install and wrapper materialization logic still classifies Claude Code and OpenCode as skill-only activation hosts.

This means users can hit a host-visible `vibe` surface, the host opens `SKILL.md`, the model manually imitates the workflow, and the system still appears to the user as if canonical `vibe` ran.

That behavior violates the intended contract in two ways:

- runtime truth is no longer tied to runtime-generated artifacts
- a documentation surface is allowed to masquerade as runtime entry

## Real Evidence Collected

### 1. Latest upstream baseline

Remote `HEAD` resolved during this design pass:

- `db821ea56a14683b2d12aa6462adc66ef0ee0877`

### 2. Canonical runtime kernel is real and runnable

The canonical PowerShell runtime exists and executes the full six-stage state machine:

- `scripts/runtime/invoke-vibe-runtime.ps1`

This design pass executed the runtime for real with native specialist execution disabled to keep the proof deterministic:

- artifact root: `/tmp/vibe-runtime-artifacts-rKnskB`
- summary json: `/tmp/vibe-runtime-summary-ee4DCx.json`

Observed proof:

- mode: `interactive_governed`
- stage order:
  - `skeleton_check`
  - `deep_interview`
  - `requirement_doc`
  - `xl_plan`
  - `plan_execute`
  - `phase_cleanup`
- runtime packet present
- governance capsule present
- stage lineage present

Concrete artifact paths from this real run:

- `/tmp/vibe-runtime-artifacts-rKnskB/outputs/runtime/vibe-sessions/codex-canonical-vibe-baseline-proof/runtime-input-packet.json`
- `/tmp/vibe-runtime-artifacts-rKnskB/outputs/runtime/vibe-sessions/codex-canonical-vibe-baseline-proof/governance-capsule.json`
- `/tmp/vibe-runtime-artifacts-rKnskB/outputs/runtime/vibe-sessions/codex-canonical-vibe-baseline-proof/stage-lineage.json`

The runtime packet from that proof contains the required canonical truth fields:

- `canonical_router`
- `route_snapshot`
- `specialist_recommendations`
- `specialist_dispatch`
- `divergence_shadow`

### 3. Current host-visible `vibe` wrappers are still documentation-first

Observed host-visible wrapper behavior in the current code:

- `packages/installer-core/src/vgo_installer/discoverable_wrappers.py` writes wrapper bodies that say:
  - `Use the 'vibe' skill and follow its governed runtime contract for this request.`
- `config/opencode/commands/vibe.md` is documentation-only guidance
- `config/opencode/agents/vibe-plan.md` is documentation-only guidance

Real install inspection confirmed:

- Codex materializes `commands/vibe.md`
- Claude Code materializes `skills/vibe/SKILL.md`
- OpenCode materializes `commands/vibe.md`, `command/vibe.md`, and `agents/vibe-plan.md`

None of those host-visible files currently launch the runtime kernel.

### 4. Current host truth source is inconsistent

`config/adapter-registry.json` and `packages/contracts/src/vgo_contracts/runtime_surface_contract.py` disagree about host runtime semantics.

Current mismatch:

- `adapter-registry.json` says:
  - Codex: `governed`
  - Claude Code: `preview-guidance`
  - OpenCode: `preview-guidance`
- `runtime_surface_contract.py` hard-codes Claude Code and OpenCode into `SKILL_ONLY_ACTIVATION_HOSTS`

This guarantees that different layers can make different decisions about whether `vibe` is a runtime entry or a skill-document entry.

### 5. Existing installed-host specialist execution tests already show degraded entry behavior

Real test run during this design pass:

- `pytest -q tests/runtime_neutral/test_installed_host_runtime_simulation.py -k test_installed_hosts_support_high_fidelity_planning_debug_and_execution_tasks`

Observed failure pattern:

- `effective_execution_status = explicitly_degraded`
- this appeared for Codex, Claude Code, and OpenCode in the current baseline run

That failure is not itself the root cause of the `SKILL.md` fallback bug, but it proves the current multi-host execution story is not yet strong enough to be trusted as canonical truth without stricter gating.

## Design Principles

1. `vibe` remains the only runtime authority.
2. Runtime core owns governance. Host adapters only launch it.
3. `SKILL.md` may describe canonical `vibe`, but it may not serve as evidence that canonical `vibe` ran.
4. Any host that cannot actually launch canonical runtime must block loudly.
5. Truth claims must be artifact-backed.
6. Host support differences must be expressed as capability data, not hard-coded branching scattered across the codebase.

## Candidate Approaches

### Option 1. Only strengthen `SKILL.md`

Update `SKILL.md`, bootstrap text, and wrapper wording so they all say runtime execution is mandatory.

Pros:

- minimal code churn
- low implementation cost

Cons:

- does not remove the actual fallback path
- still allows host-visible wrappers to be treated as prose contracts
- does not produce runtime-launch evidence

Conclusion:

- reject

### Option 2. Patch each host independently

Implement separate runtime-entry logic in Codex, Claude Code, and OpenCode without introducing a shared host capability contract or proof gate.

Pros:

- can move fast for one host at a time
- may be easier to prototype

Cons:

- duplicates entry semantics across hosts
- increases long-term adapter drift
- makes it harder to verify canonical truth consistently

Conclusion:

- reject as the main architecture

### Option 3. Runtime-first entry contract with shared truth gate

Introduce a single canonical launch contract and thin per-host launch adapters. A host-visible `vibe` surface may only do one of two things:

- launch canonical runtime
- report blocked

Pros:

- highest cohesion
- lowest long-term coupling
- strongest regression boundary
- makes false canonical claims mechanically impossible

Conclusion:

- recommended

## Recommended Architecture

### 1. Create a single host capability source of truth

Replace `SKILL_ONLY_ACTIVATION_HOSTS` style semantics with host capability data resolved from `config/adapter-registry.json`.

Add a new `canonical_vibe` contract block per host. Proposed shape:

```json
"canonical_vibe": {
  "entry_mode": "direct_runtime | bridged_runtime | unsupported",
  "fallback_policy": "blocked",
  "proof_required": true,
  "allow_skill_doc_fallback": false,
  "launcher_kind": "native_command | managed_bridge",
  "supports_bounded_stop": true
}
```

Interpretation in this wave:

- Codex:
  - `entry_mode = direct_runtime`
  - `launcher_kind = native_command`
- Claude Code:
  - `entry_mode = bridged_runtime`
  - `launcher_kind = managed_bridge`
- OpenCode:
  - `entry_mode = bridged_runtime`
  - `launcher_kind = managed_bridge`

All logic that currently asks "is this host skill-only?" should instead ask "what is this host's canonical vibe entry mode?"

This removes split-brain routing truth from:

- contracts
- installer
- wrapper projection
- verification gates

### 2. Introduce a canonical runtime launcher

Add a dedicated runtime entry layer that is responsible only for canonical launch orchestration.

Responsibilities:

- resolve host capability
- resolve wrapper entry intent
- call the canonical runtime kernel
- collect launch receipts
- verify minimum truth artifacts before returning success

Non-responsibilities:

- it must not become a second router
- it must not freeze a second requirement surface
- it must not reimplement the six-stage state machine

This launcher should be the only layer allowed to say "canonical `vibe` was entered".

### 3. Introduce a host launch receipt

Add a new artifact written before canonical-run success can be claimed:

- `host-launch-receipt.json`

Required fields:

- `host_id`
- `entry_id`
- `launch_mode`
- `launcher_path`
- `requested_stage_stop`
- `requested_grade_floor`
- `runtime_entrypoint`
- `run_id`
- `created_at`
- `launch_status`

This gives host-level proof that the visible wrapper did not stop at prose activation.

### 4. Add a canonical truth gate

Add a new verification gate for canonical-entry truth.

Canonical `vibe` may only be claimed when all of the following exist and validate:

- `host-launch-receipt.json`
- `runtime-input-packet.json`
- `governance-capsule.json`
- `stage-lineage.json`

Minimum semantic checks:

1. runtime packet contains:
   - `canonical_router`
   - `route_snapshot`
   - `specialist_recommendations`
   - `specialist_dispatch`
   - `divergence_shadow`
2. governance capsule says:
   - `runtime_selected_skill = vibe`
3. stage lineage reflects a valid bounded stop:
   - full `vibe` / `vibe-do-it` must end at `phase_cleanup`
   - `vibe-how-do-we-do` must end at `xl_plan`
   - `vibe-what-do-i-want` must end at `requirement_doc`
4. host launch receipt agrees with runtime packet:
   - same `host_id`
   - same requested stop target
   - same runtime authority

If any of those checks fail:

- canonical claim is forbidden
- the host must report blocked or degraded truth
- the run may not describe itself as "entered canonical vibe"

### 5. Make `SKILL.md` explicitly non-canonical as an entry proof

Update `vibe/SKILL.md` so it explicitly states:

- reading this file is not evidence of canonical runtime entry
- host-visible wrappers must launch the runtime kernel or report blocked
- no wrapper may claim canonical `vibe` unless runtime truth artifacts exist

This change is important for user-facing correctness, but it is not the main fix. The real fix is the launcher plus truth gate.

### 6. Convert host-visible wrappers into launch trampolines

Current wrapper generator writes prose instructions. That must change.

New wrapper rule:

- a discoverable `vibe` wrapper is a launch trampoline, not a workflow document

Allowed wrapper behavior:

- resolve the canonical launcher
- pass wrapper metadata such as bounded stop target
- report blocked if launcher cannot run

Forbidden wrapper behavior:

- "Use the `vibe` skill..."
- "follow the governed runtime contract..."
- any behavior that lets the host stop after opening `SKILL.md`

## Per-Host Design

### Codex

Codex is the strongest lane in this wave and should be treated as `direct_runtime`.

Required changes:

- keep `$vibe` and `/vibe` bootstrap semantics
- route explicit entry to the canonical launcher
- refuse silent downgrade
- require host launch receipt plus runtime truth artifacts before any canonical claim

Codex bootstrap language is already directionally correct. The change is to make it executable and verifiable rather than documentary.

### Claude Code

Claude Code should be upgraded from prose-oriented preview guidance to `bridged_runtime`.

Required changes:

- keep the managed settings surface
- add a managed bridge descriptor for canonical `vibe`
- ensure host-visible `vibe` entry launches the canonical launcher
- if the bridge cannot be resolved, report blocked

Important constraint:

- Claude Code may still need host-managed plugin and provider surfaces, but that must not be allowed to silently demote runtime entry back to a `SKILL.md` read.

### OpenCode

OpenCode should also move to `bridged_runtime`.

Required changes:

- keep `commands/` and `agents/` discoverability if desired
- convert them from prose wrappers into launch trampolines
- keep real `opencode.json` host-managed if necessary
- ensure that `command.vibe`, `commands/vibe.md`, and `agents/vibe-plan.md` all resolve to the same launcher contract

Important constraint:

- multiple entry surfaces are acceptable
- multiple runtime authorities are not

## Failure and Degradation Policy

For Codex, Claude Code, and OpenCode in this wave:

- no silent fallback to document-only skill activation
- no "best effort canonical vibe" language
- no "entered vibe" claim without proof artifacts

Allowed outcomes:

- `canonical_entered`
- `blocked_before_launch`
- `blocked_after_launch_receipt`
- `degraded_truth_no_canonical_claim`

Disallowed outcome:

- `skill_doc_opened_but_claimed_canonical`

## Packaging and Cohesion Boundaries

High cohesion is preserved by keeping responsibilities narrow:

- runtime core:
  - state machine
  - freeze logic
  - requirement/plan/execute/cleanup
- launcher layer:
  - canonical entry
  - proof preconditions
  - host launch receipt
- adapter registry:
  - host capability truth
- wrapper materialization:
  - thin launch trampolines only
- verification:
  - canonical truth gate

Low coupling is preserved by avoiding:

- host-specific runtime forks
- duplicated truth logic in wrapper files
- ad hoc hard-coded host lists in multiple modules

## Testing Strategy

### Layer 1. Capability contract tests

Add tests that prove:

- Codex resolves to `direct_runtime`
- Claude Code resolves to `bridged_runtime`
- OpenCode resolves to `bridged_runtime`
- no supported host in this wave is classified through hard-coded `SKILL_ONLY_ACTIVATION_HOSTS`
- `allow_skill_doc_fallback = false` for all three hosts

### Layer 2. Wrapper materialization tests

Add tests that install each host into a temporary target root and verify:

- launcher metadata is present
- host-visible wrappers contain launch-trampoline content, not prose workflow guidance
- `vibe/SKILL.md` remains present as contract documentation
- wrapper stop-target metadata is preserved

### Layer 3. Real launch tests

For each of the three hosts, run the canonical launcher for real and assert:

- `host-launch-receipt.json` exists
- `runtime-input-packet.json` exists
- `governance-capsule.json` exists
- `stage-lineage.json` exists
- the final stage matches the wrapper's bounded stop target

Evidence to capture in test output:

- host id
- launcher path
- runtime entrypoint path
- receipt paths
- effective host adapter
- stage lineage

### Layer 4. False-claim rejection tests

Add negative tests that prove canonical claims are rejected when:

- launcher is missing
- only `SKILL.md` was opened
- launch receipt is missing
- runtime packet is missing required truth fields
- stage lineage does not match the bounded stop target

### Layer 5. Regression tests

Keep or extend existing tests for:

- runtime packet execution
- governed runtime bridge
- host install simulation
- discoverable wrapper visibility
- contract goldens

The enhancement is acceptable only if those tests still pass after the new entry contract lands.

## Acceptance Criteria

1. Explicit `$vibe` and `/vibe` on Codex, Claude Code, and OpenCode can no longer degrade into documentation-only activation while still claiming canonical runtime entry.
2. Canonical `vibe` claims require a host launch receipt plus runtime truth artifacts.
3. Wrapper files for the three target hosts act as launch trampolines, not prose workflow instructions.
4. The six-stage runtime kernel remains the only governed runtime authority.
5. Current discoverable wrapper names remain stable.
6. The implementation does not expand scope beyond Codex, Claude Code, and OpenCode in this wave.

## Rollout Order

### Wave 1. Truth model hardening

- add `canonical_vibe` capability contract
- remove hard-coded skill-only host truth
- add canonical truth gate

### Wave 2. Launcher introduction

- add canonical launcher
- add host launch receipt
- switch Codex to verified direct runtime entry

### Wave 3. Bridged host cutover

- switch Claude Code to bridged runtime
- switch OpenCode to bridged runtime
- replace prose wrappers with launch trampolines

### Wave 4. Deep verification

- run full host install and entry tests
- collect proof artifacts for all three hosts
- verify false-claim rejection paths

## Review Notes

This design intentionally avoids changing the runtime core state machine because the real problem is not the six-stage kernel. The real problem is that host entry surfaces are still allowed to stop at prose activation.

The architectural fix is therefore not "make `SKILL.md` stricter". The fix is:

- runtime-first launch semantics
- a single host capability truth source
- a canonical proof gate that prevents false entry claims
