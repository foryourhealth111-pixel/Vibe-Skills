# Stage-Bound Specialist Dispatch Governance

## Execution Summary
Implement the smallest coherent extension that turns specialist skills into governed, phase-bound execution contracts under `vibe`. Reuse the current canonical router and root/child hierarchy, add deterministic specialist binding metadata, place specialist units into `L` serial steps and `XL` bounded specialist lanes, and prove the result with artifact-backed tests.

## Frozen Inputs
- Requirement doc: /home/lqf/table/table5/runtime-sandboxes/verify-main-77694e8/docs/requirements/2026-03-28-stage-bound-specialist-dispatch-governance.md
- Source task: improve specialist-skill use inside `vibe` without conflict or authority drift
- Runtime owner invariant: explicit governed entry remains `vibe`

## Internal Grade Decision
- Grade: XL
- The task spans config, runtime topology, docs, and test surfaces with disjoint write scopes and benefits from staged parallel investigation.

## Wave Plan
- Wave 1: freeze specialist binding policy, requirement truth, plan truth, and stable governance wording
- Wave 2: implement runtime packet and specialist topology changes for stage-bound dispatch
- Wave 3: upgrade manifests and delegated-lane receipts so specialist phase binding is observable
- Wave 4: add runtime-neutral tests for `L` serial specialist steps, `XL` bounded specialist lanes, and hierarchy safety
- Wave 5: run targeted verification, collect proof artifacts, and close with cleanup

## Ownership Boundaries
- Specialist binding policy and runtime freeze: `config/runtime-input-packet-policy.json`, `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- Requirement and plan surfacing: `scripts/runtime/Write-RequirementDoc.ps1`, `scripts/runtime/Write-XlPlan.ps1`
- Specialist topology and delegated execution: `scripts/runtime/VibeExecution.Common.ps1`, `scripts/runtime/Invoke-DelegatedLaneUnit.ps1`, `scripts/runtime/Invoke-PlanExecute.ps1`
- Stable governance docs: `protocols/runtime.md`, `protocols/team.md`, `docs/root-child-vibe-hierarchy-governance.md`, `docs/governance/specialist-dispatch-governance.md`
- Verification: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`, `tests/runtime_neutral/test_root_child_hierarchy_bridge.py`

## Specialist Skill Dispatch Plan
- Freeze each specialist recommendation as a bounded execution contract with `binding_profile`, `dispatch_phase`, `lane_policy`, `parallelizable_in_root_xl`, `write_scope`, and `review_mode`.
- Treat `pre_execution` specialists as planning or setup support, `in_execution` specialists as bounded implementation support, `post_execution` specialists as deliverable support, and `verification` specialists as review-only support.
- In `L`, execute specialist units as explicit serial native steps.
- In `XL`, allow only root-approved specialist units with disjoint write scopes to enter bounded parallel windows.
- Keep child-local new specialists advisory-first; only same-round root absorb may upgrade them.

## Verification Commands
- `git diff --check`
- `python3 -m pytest tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_root_child_hierarchy_bridge.py tests/runtime_neutral/test_l_xl_native_execution_topology.py -q`
- `pwsh -NoProfile -File scripts/verify/vibe-root-child-hierarchy-gate.ps1`
- `pwsh -NoProfile -File scripts/verify/vibe-child-specialist-escalation-gate.ps1`
- targeted manual replay of composite tasks with fake codex adapter for bounded native specialist execution proof

## Rollback Plan
- Revert only the specialist-dispatch governance change set if hierarchy invariants or runtime-neutral tests fail.
- If bounded parallel specialist lanes are unstable, preserve the binding metadata and serial fallback while disabling only the parallel specialist path.

## Phase Cleanup Contract
- Remove temporary test artifacts and `.pytest_cache` after verification.
- Audit node processes and clear only managed stale residue if present.
- Leave the branch with intended source/docs/tests changes only.
