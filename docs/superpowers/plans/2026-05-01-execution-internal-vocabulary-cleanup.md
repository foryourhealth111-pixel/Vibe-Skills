# Execution Internal Vocabulary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining execution-internal `specialist_dispatch` vocabulary from current execution artifacts, current tests, and routing terminology gates while preserving the six governed stages and the current `skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused` model.

**Architecture:** Add failing contract tests for current execution vocabulary first, then add current execution fields as short-lived aliases, migrate consumers and tests to the current names, switch current lane/output identifiers to `skill_execution`, and finally remove the old execution names and tighten the scan to fail on any remaining execution-internal `specialist_dispatch` references. The cleanup is vocabulary-only: skill selection, pack routing, stage order, blocked/degraded safety behavior, and usage-proof semantics must remain unchanged.

**Tech Stack:** PowerShell runtime scripts, Python `unittest` / `pytest` runtime-neutral tests, Python verification-core delivery acceptance module, JSON scan config, existing Vibe verification gates.

---

## Fixed Boundaries

- Keep these six governed stages unchanged: `skeleton_check`, `deep_interview`, `requirement_doc`, `xl_plan`, `plan_execute`, `phase_cleanup`.
- Keep the current model unchanged: `skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused`.
- Do not delete skills, packs, or routing rules in this plan.
- Do not restore old root packet fields: `legacy_skill_routing`, root `specialist_dispatch`, root `specialist_recommendations`, or `stage_assistant_hints`.
- Do not preserve old root routing compatibility in current behavior.
- Treat transitional aliases as branch-local migration scaffolding only. They must be removed before the final scan gate.

---

## File Structure

- Create: `tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py`
  - Static and focused contract tests for the execution vocabulary migration.
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
  - Add current execution fields, migrate plan shadow classification/count names, migrate lane-kind checks, update proof manifest and plan execute receipt fields, then remove old execution names.
- Modify: `scripts/runtime/VibeExecution.Common.ps1`
  - Emit `kind = 'skill_execution'` and `lane_kind = 'skill_execution'` for current skill execution results and lanes.
- Modify: `scripts/runtime/Invoke-DelegatedLaneUnit.ps1`
  - Accept and emit `lane_kind = 'skill_execution'` for delegated skill execution lanes.
- Modify: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
  - Prefer current execution fields from `specialist_accounting`; remove current fallback to root packet `specialist_dispatch`.
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
  - Read `skill_execution_unit_count`, `selected_skill_execution`, `blocked_skill_execution_units`, `degraded_skill_execution_units`, and `execution_skill_outcomes`.
- Modify: `tests/runtime_neutral/test_plan_execute_receipts.py`
  - Use `lane_kind = 'skill_execution'` and assert current proof/receipt field names.
- Modify: `tests/runtime_neutral/test_runtime_contract_schema.py`
  - Keep current root packet absence checks and migrate any current execution assertions to current field names.
- Modify: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`
  - Use `selected_skill_execution` fixtures and current execution-accounting fields.
- Modify: `tests/runtime_neutral/test_skill_promotion_destructive_gate.py`
  - Assert blocked and selected execution through current execution-accounting names.
- Modify: `tests/runtime_neutral/test_skill_promotion_metrics.py`
  - Read `execution_skill_outcomes` instead of `specialist_dispatch_outcomes`.
- Modify: `config/routing-terminology-hard-cleanup.json`
  - Replace the execution-internal allowlist with a scan list whose accepted reference count is zero.
- Modify: `scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1`
  - Fail when any scanned execution-internal current file still contains `specialist_dispatch`.
- Modify: `scripts/verify/vibe-current-routing-contract-scan.ps1`
  - Keep surfacing the hard-cleanup execution-internal count and treat a hard-cleanup failure as a current routing-contract failure.
- Modify: `tests/runtime_neutral/test_routing_terminology_hard_cleanup.py`
  - Assert the hard-cleanup scan reports zero execution-internal references.
- Modify: `tests/runtime_neutral/test_current_routing_contract_scan.py`
  - Assert the current routing contract scan includes and enforces the zero execution-internal count.
- Modify only if a focused gate proves it still reads the removed plan-shadow field:
  - `scripts/verify/vibe-governed-runtime-contract-gate.ps1`

Do not modify pack route manifests, bundled skill directories, or the six-stage runtime sequence in this plan.

---

### Task 1: Add Current Execution Vocabulary Guard Tests

**Files:**
- Create: `tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py`

- [ ] **Step 1: Create the failing execution vocabulary test file**

Create `tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py`:

```python
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INVOKE_PLAN_EXECUTE = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
VIBE_EXECUTION_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
DELEGATED_LANE_UNIT = REPO_ROOT / "scripts" / "runtime" / "Invoke-DelegatedLaneUnit.ps1"
DELIVERY_ACCEPTANCE = (
    REPO_ROOT
    / "packages"
    / "verification-core"
    / "src"
    / "vgo_verify"
    / "runtime_delivery_acceptance_runtime.py"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ExecutionInternalVocabularyCleanupTests(unittest.TestCase):
    def test_plan_execute_declares_current_execution_accounting_fields(self) -> None:
        text = read(INVOKE_PLAN_EXECUTE)
        for field in [
            "skill_execution_unit_count",
            "selected_skill_execution_count",
            "selected_skill_execution",
            "frozen_selected_skill_execution_count",
            "frozen_selected_skill_execution",
            "auto_selected_skill_execution_count",
            "auto_selected_skill_execution",
            "blocked_skill_execution_unit_count",
            "blocked_skill_execution_units",
            "degraded_skill_execution_unit_count",
            "degraded_skill_execution_units",
            "execution_skill_outcome_count",
            "execution_skill_outcomes",
            "skill_execution_resolution_path",
        ]:
            self.assertIn(field, text)

    def test_current_runtime_files_do_not_emit_specialist_dispatch_lane_kind(self) -> None:
        for path in [INVOKE_PLAN_EXECUTE, VIBE_EXECUTION_COMMON, DELEGATED_LANE_UNIT]:
            text = read(path)
            self.assertNotIn("lane_kind = 'specialist_dispatch'", text, path)
            self.assertNotIn("'specialist_dispatch' {", text, path)
            self.assertNotIn("-eq 'specialist_dispatch'", text, path)
            self.assertNotIn("kind = 'specialist_dispatch'", text, path)

    def test_current_plan_execute_outputs_do_not_write_old_execution_field_names(self) -> None:
        text = read(INVOKE_PLAN_EXECUTE)
        forbidden_assignment_patterns = [
            r"^\s*specialist_dispatch_unit_count\s*=",
            r"^\s*specialist_dispatch_outcome_count\s*=",
            r"^\s*specialist_dispatch_outcomes\s*=",
            r"^\s*specialist_dispatch_resolution_path\s*=",
            r"^\s*approved_dispatch_count\s*=",
            r"^\s*approved_dispatch\s*=",
            r"^\s*frozen_approved_dispatch_count\s*=",
            r"^\s*frozen_approved_dispatch\s*=",
            r"^\s*auto_approved_dispatch_count\s*=",
            r"^\s*auto_approved_dispatch\s*=",
            r"^\s*blocked_specialist_unit_count\s*=",
            r"^\s*blocked_specialist_units\s*=",
            r"^\s*degraded_specialist_unit_count\s*=",
            r"^\s*degraded_specialist_units\s*=",
        ]
        for pattern in forbidden_assignment_patterns:
            self.assertIsNone(re.search(pattern, text, flags=re.MULTILINE), pattern)

    def test_delivery_acceptance_reads_current_execution_accounting_first(self) -> None:
        text = read(DELIVERY_ACCEPTANCE)
        self.assertIn('specialist_accounting.get("selected_skill_execution")', text)
        self.assertIn('specialist_accounting.get("selected_skill_execution_count")', text)
        self.assertIn('specialist_accounting.get("direct_routed_skill_execution_units")', text)
        self.assertIn('specialist_accounting.get("blocked_skill_execution_units")', text)
        self.assertIn('specialist_accounting.get("degraded_skill_execution_units")', text)
        self.assertNotIn('runtime_input_packet.get("specialist_dispatch")', text)
        self.assertNotIn('legacy_skill_routing.get("specialist_dispatch")', text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail on the current code**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py -q
```

Expected: FAIL, with missing current fields such as `selected_skill_execution` and still-present old lane/output strings such as `lane_kind = 'specialist_dispatch'`.

- [ ] **Step 3: Commit the failing guard test**

```powershell
git add tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py
git commit -m "test: guard execution internal vocabulary cleanup"
```

---

### Task 2: Add Current Execution Accounting Fields In Plan Execute Outputs

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`

- [ ] **Step 1: Add local current-name variables before execution manifest construction**

In `scripts/runtime/Invoke-PlanExecute.ps1`, just before `$executionManifest = [pscustomobject]@{`, add:

```powershell
$selectedSkillExecution = @($approvedDispatch)
$selectedSkillExecutionCount = @($selectedSkillExecution).Count
$frozenSelectedSkillExecution = @($frozenApprovedDispatch)
$frozenSelectedSkillExecutionCount = @($frozenSelectedSkillExecution).Count
$autoSelectedSkillExecution = @($autoApprovedDispatch)
$autoSelectedSkillExecutionCount = @($autoSelectedSkillExecution).Count
$blockedSkillExecutionUnits = @($blockedSpecialistUnits)
$blockedSkillExecutionUnitCount = @($blockedSkillExecutionUnits).Count
$degradedSkillExecutionUnits = @($degradedSpecialistUnits)
$degradedSkillExecutionUnitCount = @($degradedSkillExecutionUnits).Count
$skillExecutionResolutionPath = if ($specialistDispatchResolution.auto_absorb_gate.receipt_path) {
    [string]$specialistDispatchResolution.auto_absorb_gate.receipt_path
} else {
    $null
}
```

- [ ] **Step 2: Add current aliases to `dispatch_resolution`**

Replace the existing `dispatch_resolution = [pscustomobject]@{ ... }` block inside `execution_topology` with:

```powershell
dispatch_resolution = [pscustomobject]@{
    source = 'plan_execute_selected_skill_execution'
    frozen_selected_skill_execution_count = [int]$frozenSelectedSkillExecutionCount
    selected_skill_execution_count = [int]$selectedSkillExecutionCount
    auto_selected_skill_execution_count = [int]$autoSelectedSkillExecutionCount
    same_round_auto_absorb_applied = [bool]($autoSelectedSkillExecutionCount -gt 0)
    skill_execution_resolution_path = $skillExecutionResolutionPath
}
```

- [ ] **Step 3: Add current aliases to `specialist_accounting` while keeping old names temporarily**

Inside `specialist_accounting = [pscustomobject]@{`, add these fields beside the existing old fields:

```powershell
selected_skill_execution_count = [int]$selectedSkillExecutionCount
selected_skill_execution = @($selectedSkillExecution)
frozen_selected_skill_execution_count = [int]$frozenSelectedSkillExecutionCount
frozen_selected_skill_execution = @($frozenSelectedSkillExecution)
auto_selected_skill_execution_count = [int]$autoSelectedSkillExecutionCount
auto_selected_skill_execution = @($autoSelectedSkillExecution)
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
blocked_skill_execution_units = @($blockedSkillExecutionUnits)
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
degraded_skill_execution_units = @($degradedSkillExecutionUnits)
skill_execution_resolution_path = $skillExecutionResolutionPath
```

Keep the old fields only until Task 7 removes them:

```powershell
frozen_approved_dispatch_count = @($frozenApprovedDispatch).Count
frozen_approved_dispatch = @($frozenApprovedDispatch)
approved_dispatch_count = @($approvedDispatch).Count
approved_dispatch = @($approvedDispatch)
auto_approved_dispatch_count = @($autoApprovedDispatch).Count
auto_approved_dispatch = @($autoApprovedDispatch)
blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
blocked_specialist_units = @($blockedSpecialistUnits)
degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
degraded_specialist_units = @($degradedSpecialistUnits)
```

- [ ] **Step 4: Update topology tests to assert the current aliases exist and match existing behavior**

In `tests/runtime_neutral/test_l_xl_native_execution_topology.py`, update the existing execution accounting assertions around `skill_execution_unit_count` to include:

```python
self.assertIn("selected_skill_execution_count", specialist_accounting)
self.assertIn("selected_skill_execution", specialist_accounting)
self.assertIn("blocked_skill_execution_unit_count", specialist_accounting)
self.assertIn("blocked_skill_execution_units", specialist_accounting)
self.assertIn("degraded_skill_execution_unit_count", specialist_accounting)
self.assertIn("degraded_skill_execution_units", specialist_accounting)
self.assertIn("skill_execution_resolution_path", specialist_accounting)
self.assertEqual(
    int(specialist_accounting["selected_skill_execution_count"]),
    len(list(specialist_accounting["selected_skill_execution"])),
)
self.assertEqual(
    int(specialist_accounting["blocked_skill_execution_unit_count"]),
    len(list(specialist_accounting["blocked_skill_execution_units"])),
)
self.assertEqual(
    int(specialist_accounting["degraded_skill_execution_unit_count"]),
    len(list(specialist_accounting["degraded_skill_execution_units"])),
)
```

- [ ] **Step 5: Run focused alias tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py::ExecutionInternalVocabularyCleanupTests::test_plan_execute_declares_current_execution_accounting_fields tests/runtime_neutral/test_l_xl_native_execution_topology.py -q
```

Expected: the first guard test passes for field presence; topology tests pass with current aliases.

- [ ] **Step 6: Commit the current accounting aliases**

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_l_xl_native_execution_topology.py
git commit -m "feat: add current skill execution accounting fields"
```

---

### Task 3: Add Current Fields To Proof Manifest And Plan Execute Receipt

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `tests/runtime_neutral/test_plan_execute_receipts.py`

- [ ] **Step 1: Add current execution fields to `$proofManifest`**

In `$proofManifest = [pscustomobject]@{`, add current fields and keep old fields until Task 7:

```powershell
skill_execution_unit_count = [int]$specialistDispatchUnitCount
selected_skill_execution_count = [int]$selectedSkillExecutionCount
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
execution_skill_outcome_count = $totalSpecialistDispatchOutcomeCount
skill_execution_resolution_path = $skillExecutionResolutionPath
```

- [ ] **Step 2: Update proof summary Markdown lines to current execution names**

Replace old execution summary lines in `$proofLines`:

```powershell
('- specialist_dispatch_unit_count: `{0}`' -f [int]$specialistDispatchUnitCount),
('- blocked_specialist_unit_count: `{0}`' -f @($blockedSpecialistUnits).Count),
('- degraded_specialist_unit_count: `{0}`' -f @($degradedSpecialistUnits).Count),
```

with:

```powershell
('- skill_execution_unit_count: `{0}`' -f [int]$specialistDispatchUnitCount),
('- selected_skill_execution_count: `{0}`' -f [int]$selectedSkillExecutionCount),
('- blocked_skill_execution_unit_count: `{0}`' -f [int]$blockedSkillExecutionUnitCount),
('- degraded_skill_execution_unit_count: `{0}`' -f [int]$degradedSkillExecutionUnitCount),
```

- [ ] **Step 3: Add current execution fields to `$receipt`**

In `$receipt = [pscustomobject]@{`, add:

```powershell
skill_execution_unit_count = [int]$specialistDispatchUnitCount
selected_skill_execution_count = [int]$selectedSkillExecutionCount
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
execution_skill_outcome_count = $totalSpecialistDispatchOutcomeCount
skill_execution_resolution_path = $skillExecutionResolutionPath
```

- [ ] **Step 4: Update receipt tests to assert current proof and receipt fields**

In `tests/runtime_neutral/test_plan_execute_receipts.py`, add assertions to the tests that load `phase-execute.json` and the governed proof manifest:

```python
for field in [
    "skill_execution_unit_count",
    "selected_skill_execution_count",
    "blocked_skill_execution_unit_count",
    "degraded_skill_execution_unit_count",
    "execution_skill_outcome_count",
    "skill_execution_resolution_path",
]:
    self.assertIn(field, receipt)
    self.assertIn(field, proof_manifest)

self.assertEqual(receipt["skill_execution_unit_count"], proof_manifest["skill_execution_unit_count"])
self.assertEqual(receipt["selected_skill_execution_count"], proof_manifest["selected_skill_execution_count"])
self.assertEqual(receipt["execution_skill_outcome_count"], proof_manifest["execution_skill_outcome_count"])
```

- [ ] **Step 5: Run focused receipt tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_plan_execute_receipts.py tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py::ExecutionInternalVocabularyCleanupTests::test_plan_execute_declares_current_execution_accounting_fields -q
```

Expected: receipt tests pass and the current execution field presence guard passes.

- [ ] **Step 6: Commit proof and receipt aliases**

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_plan_execute_receipts.py
git commit -m "feat: expose current execution fields in receipts"
```

---

### Task 4: Migrate Current Lane Kind From `specialist_dispatch` To `skill_execution`

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `scripts/runtime/VibeExecution.Common.ps1`
- Modify: `scripts/runtime/Invoke-DelegatedLaneUnit.ps1`
- Modify: `tests/runtime_neutral/test_plan_execute_receipts.py`

- [ ] **Step 1: Update lane entries emitted by `VibeExecution.Common.ps1`**

In `scripts/runtime/VibeExecution.Common.ps1`, change the lane entry returned for selected skill execution from:

```powershell
lane_kind = 'specialist_dispatch'
```

to:

```powershell
lane_kind = 'skill_execution'
```

In the same file, change current skill execution result objects from:

```powershell
kind = 'specialist_dispatch'
```

to:

```powershell
kind = 'skill_execution'
```

- [ ] **Step 2: Update direct execution switch in `Invoke-PlanExecute.ps1`**

Replace the direct lane switch case:

```powershell
'specialist_dispatch' {
```

with:

```powershell
'skill_execution' {
```

- [ ] **Step 3: Update `ConvertTo-VibeExecutedUnitReceipt` lane-kind checks**

Replace every direct lane-kind comparison:

```powershell
[string]$Outcome.lane_entry.lane_kind -eq 'specialist_dispatch'
```

with:

```powershell
[string]$Outcome.lane_entry.lane_kind -eq 'skill_execution'
```

Replace the degraded-success check:

```powershell
[string]$Receipt.lane_kind -eq 'specialist_dispatch'
```

with:

```powershell
[string]$Receipt.lane_kind -eq 'skill_execution'
```

- [ ] **Step 4: Update delegated lane execution**

In `scripts/runtime/Invoke-DelegatedLaneUnit.ps1`, replace:

```powershell
$laneKind -eq 'specialist_dispatch'
```

with:

```powershell
$laneKind -eq 'skill_execution'
```

Replace the switch case:

```powershell
'specialist_dispatch' {
```

with:

```powershell
'skill_execution' {
```

Update the notes heading:

```powershell
"# Native Specialist Dispatch Receipt",
```

to:

```powershell
"# Native Skill Execution Receipt",
```

- [ ] **Step 5: Update plan execute receipt fixtures**

In `tests/runtime_neutral/test_plan_execute_receipts.py`, replace current lane fixtures:

```python
"lane_kind": "specialist_dispatch",
```

with:

```python
"lane_kind": "skill_execution",
```

When a test name contains `specialist_dispatch`, rename only the test identifier to current wording. For example:

```python
def test_retired_host_subprocess_mode_routes_specialist_dispatch_in_current_session(self) -> None:
```

becomes:

```python
def test_retired_host_subprocess_mode_routes_skill_execution_in_current_session(self) -> None:
```

- [ ] **Step 6: Run lane-focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_plan_execute_receipts.py tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py::ExecutionInternalVocabularyCleanupTests::test_current_runtime_files_do_not_emit_specialist_dispatch_lane_kind -q
```

Expected: all lane-focused tests pass and no current runtime file emits the old `specialist_dispatch` lane kind.

- [ ] **Step 7: Commit lane-kind migration**

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 scripts/runtime/VibeExecution.Common.ps1 scripts/runtime/Invoke-DelegatedLaneUnit.ps1 tests/runtime_neutral/test_plan_execute_receipts.py
git commit -m "refactor: rename current skill execution lane kind"
```

---

### Task 5: Migrate Plan Shadow Classification And Count Names

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
- Modify only if needed: `scripts/verify/vibe-governed-runtime-contract-gate.ps1`

- [ ] **Step 1: Rename plan-shadow classification**

In `New-VibePlanShadow` or the equivalent plan-shadow construction block in `scripts/runtime/Invoke-PlanExecute.ps1`, replace:

```powershell
$classification = 'specialist_dispatch_unit'
$reason = if ($sectionName -eq 'Specialist Skill Dispatch Plan') { 'bounded_native_specialist_dispatch_declared' } else { 'skill_routing_usage_declared' }
```

with:

```powershell
$classification = 'skill_execution_unit'
$reason = if ($sectionName -eq 'Specialist Skill Dispatch Plan') { 'bounded_native_skill_execution_declared' } else { 'skill_routing_usage_declared' }
```

- [ ] **Step 2: Rename the plan-shadow current count**

In the plan-shadow payload, replace:

```powershell
specialist_dispatch_unit_count = @($units | Where-Object { $_.classification -eq 'specialist_dispatch_unit' }).Count
```

with:

```powershell
skill_execution_unit_count = @($units | Where-Object { $_.classification -eq 'skill_execution_unit' }).Count
```

- [ ] **Step 3: Update execution manifest plan-shadow projection**

Replace:

```powershell
specialist_dispatch_unit_count = [int]$planShadow.payload.specialist_dispatch_unit_count
```

with:

```powershell
skill_execution_unit_count = [int]$planShadow.payload.skill_execution_unit_count
```

- [ ] **Step 4: Update governed runtime contract gate only when it reads the old field**

If `scripts/verify/vibe-governed-runtime-contract-gate.ps1` still reads `executionManifest.plan_shadow.specialist_dispatch_unit_count`, replace that check with:

```powershell
Add-Assertion -Results ([ref]$results) -Condition (($null -ne $executionManifest.plan_shadow) -and (([int]$executionManifest.plan_shadow.skill_execution_unit_count -ge 1) -or $noSpecialistResolved)) -Message 'runtime smoke plan shadow counts skill execution units or no-specialist resolution'
```

- [ ] **Step 5: Update topology tests**

In `tests/runtime_neutral/test_l_xl_native_execution_topology.py`, replace plan-shadow reads of:

```python
plan_shadow["specialist_dispatch_unit_count"]
```

with:

```python
plan_shadow["skill_execution_unit_count"]
```

- [ ] **Step 6: Run plan-shadow focused gates**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py -q
.\scripts\verify\vibe-governed-runtime-contract-gate.ps1
```

Expected: topology tests pass. The governed runtime contract gate passes if it is runnable in the current shell; if it is not runnable because it needs a launched session fixture, record the exact missing prerequisite in the task notes before continuing.

- [ ] **Step 7: Commit plan-shadow migration**

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_l_xl_native_execution_topology.py scripts/verify/vibe-governed-runtime-contract-gate.ps1
git commit -m "refactor: rename plan shadow skill execution counts"
```

---

### Task 6: Migrate Delivery Acceptance To Current Execution Fields

**Files:**
- Modify: `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
- Modify: `tests/runtime_neutral/test_runtime_delivery_acceptance.py`

- [ ] **Step 1: Remove current root packet `specialist_dispatch` fallback**

In `runtime_delivery_acceptance_runtime.py`, delete:

```python
legacy_skill_routing = runtime_input_packet.get("legacy_skill_routing") or {}
specialist_dispatch = (
    runtime_input_packet.get("specialist_dispatch")
    or legacy_skill_routing.get("specialist_dispatch")
    or {}
)
```

Keep:

```python
skill_routing = runtime_input_packet.get("skill_routing") or {}
specialist_accounting = execution_manifest.get("specialist_accounting") or {}
```

- [ ] **Step 2: Read selected execution from current accounting**

Replace:

```python
if "approved_dispatch" in specialist_accounting:
    approved_dispatch = specialist_accounting.get("approved_dispatch") or []
else:
    approved_dispatch = specialist_dispatch.get("approved_dispatch") or []
approved_dispatch_skill_ids = _normalize_skill_id_list(approved_dispatch)
```

with:

```python
selected_skill_execution = specialist_accounting.get("selected_skill_execution") or []
selected_skill_execution_count = int(specialist_accounting.get("selected_skill_execution_count") or 0)
selected_skill_execution_skill_ids = _normalize_skill_id_list(selected_skill_execution)
if selected_skill_execution_count and selected_skill_execution_count != len(selected_skill_execution_skill_ids):
    selected_skill_execution_count = len(selected_skill_execution_skill_ids)
```

Then replace downstream references to `approved_dispatch_skill_ids` with `selected_skill_execution_skill_ids` where the value means selected execution, not a historical decision field.

- [ ] **Step 3: Read direct routed units from current accounting first**

Replace:

```python
direct_routed_units_key_present = "direct_routed_specialist_units" in specialist_accounting
raw_direct_routed_specialist_units = specialist_accounting.get("direct_routed_specialist_units") or []
```

with:

```python
direct_routed_units_key_present = "direct_routed_skill_execution_units" in specialist_accounting
raw_direct_routed_specialist_units = specialist_accounting.get("direct_routed_skill_execution_units") or []
```

The local Python variable may remain `raw_direct_routed_specialist_units` for this task if renaming it would make the diff risky; it must not read old JSON fields after this step.

- [ ] **Step 4: Include blocked and degraded current fields in execution context**

Where the delivery report builds `execution_context`, include:

```python
"selected_skill_execution_skill_ids": selected_skill_execution_skill_ids,
"selected_skill_execution_count": selected_skill_execution_count,
"blocked_skill_execution_unit_count": int(specialist_accounting.get("blocked_skill_execution_unit_count") or 0),
"degraded_skill_execution_unit_count": int(specialist_accounting.get("degraded_skill_execution_unit_count") or 0),
```

Keep `approved_dispatch_skill_ids` in the report only if an existing public report contract test requires it; in that case set it from `selected_skill_execution_skill_ids` and add this comment directly above the assignment:

```python
# Backward report label only; current runtime source is selected_skill_execution.
```

- [ ] **Step 5: Migrate delivery acceptance fixtures**

In `tests/runtime_neutral/test_runtime_delivery_acceptance.py`, update the fixture helper signature from:

```python
approved_dispatch: list[dict[str, object]] | None = None,
```

to:

```python
selected_skill_execution: list[dict[str, object]] | None = None,
```

Inside the helper, replace the accounting payload:

```python
approved_dispatch_payload = list(approved_dispatch or [])
if approved_dispatch is not None or specialist_accounting is not None:
    accounting = {
        "approved_dispatch": approved_dispatch_payload,
        "approved_dispatch_count": len(approved_dispatch_payload),
        "direct_routed_specialist_units": direct_routed_units,
        "effective_execution_status": "live_native_executed" if approved_dispatch_payload else "none",
    }
```

with:

```python
selected_skill_execution_payload = list(selected_skill_execution or [])
if selected_skill_execution is not None or specialist_accounting is not None:
    accounting = {
        "selected_skill_execution": selected_skill_execution_payload,
        "selected_skill_execution_count": len(selected_skill_execution_payload),
        "direct_routed_skill_execution_units": direct_routed_units,
        "blocked_skill_execution_unit_count": 0,
        "blocked_skill_execution_units": [],
        "degraded_skill_execution_unit_count": 0,
        "degraded_skill_execution_units": [],
        "effective_execution_status": "live_native_executed" if selected_skill_execution_payload else "none",
    }
```

- [ ] **Step 6: Update delivery acceptance test names and assertions**

Rename current-behavior tests that use `approved_dispatch` as execution accounting. Example:

```python
def test_approved_dispatch_without_skill_usage_does_not_count_as_used(self) -> None:
```

becomes:

```python
def test_selected_skill_execution_without_skill_usage_does_not_count_as_used(self) -> None:
```

Update calls:

```python
approved_dispatch=approved_dispatch,
```

to:

```python
selected_skill_execution=selected_skill_execution,
```

Update assertions:

```python
self.assertEqual([], report["execution_context"]["approved_dispatch_skill_ids"])
```

to:

```python
self.assertEqual([], report["execution_context"]["selected_skill_execution_skill_ids"])
```

- [ ] **Step 7: Run delivery acceptance tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_delivery_acceptance.py tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py::ExecutionInternalVocabularyCleanupTests::test_delivery_acceptance_reads_current_execution_accounting_first -q
```

Expected: delivery acceptance tests pass and the guard proves current fields are preferred with no root `specialist_dispatch` fallback.

- [ ] **Step 8: Commit delivery acceptance migration**

```powershell
git add packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py tests/runtime_neutral/test_runtime_delivery_acceptance.py
git commit -m "refactor: read current skill execution fields in delivery acceptance"
```

---

### Task 7: Migrate Current Behavior Tests Away From Old Execution Names

**Files:**
- Modify: `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
- Modify: `tests/runtime_neutral/test_runtime_contract_schema.py`
- Modify: `tests/runtime_neutral/test_skill_promotion_destructive_gate.py`
- Modify: `tests/runtime_neutral/test_skill_promotion_metrics.py`
- Modify: `tests/runtime_neutral/test_plan_execute_receipts.py`

- [ ] **Step 1: Replace topology test reads**

In `tests/runtime_neutral/test_l_xl_native_execution_topology.py`, replace current behavior reads:

```python
specialist_accounting["approved_dispatch"]
specialist_accounting["approved_dispatch_count"]
specialist_accounting["frozen_approved_dispatch_count"]
specialist_accounting["degraded_specialist_unit_count"]
specialist_accounting["specialist_dispatch_outcomes"]
```

with:

```python
specialist_accounting["selected_skill_execution"]
specialist_accounting["selected_skill_execution_count"]
specialist_accounting["frozen_selected_skill_execution_count"]
specialist_accounting["degraded_skill_execution_unit_count"]
specialist_accounting["execution_skill_outcomes"]
```

- [ ] **Step 2: Replace destructive gate test reads**

In `tests/runtime_neutral/test_skill_promotion_destructive_gate.py`, replace:

```python
specialist_accounting["blocked_specialist_unit_count"]
specialist_accounting["approved_dispatch_count"]
specialist_accounting["blocked_specialist_units"]
```

with:

```python
specialist_accounting["blocked_skill_execution_unit_count"]
specialist_accounting["selected_skill_execution_count"]
specialist_accounting["blocked_skill_execution_units"]
```

- [ ] **Step 3: Replace metrics test expression extraction**

In `tests/runtime_neutral/test_skill_promotion_metrics.py`, replace:

```python
outcomes_expr = extract_expression(r"^\s*specialist_dispatch_outcomes = (.+)$")
```

with:

```python
outcomes_expr = extract_expression(r"^\s*execution_skill_outcomes = (.+)$")
```

Replace the PowerShell local variable in that test:

```python
"$specialist_dispatch_outcomes = {outcomes_expr}; "
"result_paths = @($specialist_dispatch_outcomes | ForEach-Object { [string]$_.result_path }); "
```

with:

```python
"$execution_skill_outcomes = {outcomes_expr}; "
"result_paths = @($execution_skill_outcomes | ForEach-Object { [string]$_.result_path }); "
```

- [ ] **Step 4: Replace current receipt test names and assertions**

In `tests/runtime_neutral/test_plan_execute_receipts.py`, replace current assertions that read:

```python
"specialist_dispatch_unit_count"
"specialist_dispatch_outcome_count"
"specialist_dispatch_resolution_path"
```

with:

```python
"skill_execution_unit_count"
"execution_skill_outcome_count"
"skill_execution_resolution_path"
```

- [ ] **Step 5: Keep root packet absence tests unchanged**

In `tests/runtime_neutral/test_runtime_contract_schema.py`, keep checks like:

```python
self.assertNotIn("specialist_dispatch", payload)
self.assertNotIn("specialist_dispatch", runtime_input)
```

Only migrate execution-accounting reads. Do not remove root absence assertions.

- [ ] **Step 6: Run migrated behavior tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_l_xl_native_execution_topology.py tests/runtime_neutral/test_runtime_contract_schema.py tests/runtime_neutral/test_skill_promotion_destructive_gate.py tests/runtime_neutral/test_skill_promotion_metrics.py tests/runtime_neutral/test_plan_execute_receipts.py -q
```

Expected: current behavior tests pass using current execution field names.

- [ ] **Step 7: Commit current test migration**

```powershell
git add tests/runtime_neutral/test_l_xl_native_execution_topology.py tests/runtime_neutral/test_runtime_contract_schema.py tests/runtime_neutral/test_skill_promotion_destructive_gate.py tests/runtime_neutral/test_skill_promotion_metrics.py tests/runtime_neutral/test_plan_execute_receipts.py
git commit -m "test: use current skill execution field names"
```

---

### Task 8: Stop Writing Old Execution Field Names

**Files:**
- Modify: `scripts/runtime/Invoke-PlanExecute.ps1`
- Modify: `tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py`

- [ ] **Step 1: Remove old execution fields from `specialist_accounting`**

In `scripts/runtime/Invoke-PlanExecute.ps1`, delete these fields from `specialist_accounting`:

```powershell
dispatch_unit_count = [int]$specialistDispatchUnitCount
frozen_approved_dispatch_count = @($frozenApprovedDispatch).Count
frozen_approved_dispatch = @($frozenApprovedDispatch)
approved_dispatch_count = @($approvedDispatch).Count
approved_dispatch = @($approvedDispatch)
auto_approved_dispatch_count = @($autoApprovedDispatch).Count
auto_approved_dispatch = @($autoApprovedDispatch)
parallelizable_dispatch_count = @($approvedDispatch | Where-Object { [bool]$_.parallelizable_in_root_xl }).Count
blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
blocked_specialist_units = @($blockedSpecialistUnits)
degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
degraded_specialist_units = @($degradedSpecialistUnits)
specialist_dispatch_outcomes = @($skillExecutionOutcomes)
```

Keep or add current replacements:

```powershell
skill_execution_unit_count = [int]$specialistDispatchUnitCount
selected_skill_execution_count = [int]$selectedSkillExecutionCount
selected_skill_execution = @($selectedSkillExecution)
frozen_selected_skill_execution_count = [int]$frozenSelectedSkillExecutionCount
frozen_selected_skill_execution = @($frozenSelectedSkillExecution)
auto_selected_skill_execution_count = [int]$autoSelectedSkillExecutionCount
auto_selected_skill_execution = @($autoSelectedSkillExecution)
parallelizable_skill_execution_count = @($selectedSkillExecution | Where-Object { [bool]$_.parallelizable_in_root_xl }).Count
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
blocked_skill_execution_units = @($blockedSkillExecutionUnits)
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
degraded_skill_execution_units = @($degradedSkillExecutionUnits)
execution_skill_outcome_count = $totalSpecialistDispatchOutcomeCount
execution_skill_outcomes = @($skillExecutionOutcomes)
skill_execution_resolution_path = $skillExecutionResolutionPath
```

- [ ] **Step 2: Remove old execution fields from proof manifest**

Delete these fields from `$proofManifest`:

```powershell
specialist_dispatch_unit_count = [int]$specialistDispatchUnitCount
blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
specialist_dispatch_resolution_path = if ($specialistDispatchResolution.auto_absorb_gate.receipt_path) { [string]$specialistDispatchResolution.auto_absorb_gate.receipt_path } else { $null }
```

Keep:

```powershell
skill_execution_unit_count = [int]$specialistDispatchUnitCount
selected_skill_execution_count = [int]$selectedSkillExecutionCount
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
execution_skill_outcome_count = $totalSpecialistDispatchOutcomeCount
skill_execution_resolution_path = $skillExecutionResolutionPath
```

- [ ] **Step 3: Remove old execution fields from plan execute receipt**

Delete these fields from `$receipt`:

```powershell
specialist_dispatch_unit_count = [int]$specialistDispatchUnitCount
blocked_specialist_unit_count = @($blockedSpecialistUnits).Count
degraded_specialist_unit_count = @($degradedSpecialistUnits).Count
specialist_dispatch_outcome_count = $totalSpecialistDispatchOutcomeCount
specialist_dispatch_resolution_path = if ($specialistDispatchResolution.auto_absorb_gate.receipt_path) { [string]$specialistDispatchResolution.auto_absorb_gate.receipt_path } else { $null }
```

Keep:

```powershell
skill_execution_unit_count = [int]$specialistDispatchUnitCount
selected_skill_execution_count = [int]$selectedSkillExecutionCount
blocked_skill_execution_unit_count = [int]$blockedSkillExecutionUnitCount
degraded_skill_execution_unit_count = [int]$degradedSkillExecutionUnitCount
execution_skill_outcome_count = $totalSpecialistDispatchOutcomeCount
skill_execution_resolution_path = $skillExecutionResolutionPath
```

- [ ] **Step 4: Remove old proof summary wording**

Ensure `$proofLines` contains current names only:

```powershell
('- skill_execution_unit_count: `{0}`' -f [int]$specialistDispatchUnitCount),
('- selected_skill_execution_count: `{0}`' -f [int]$selectedSkillExecutionCount),
('- blocked_skill_execution_unit_count: `{0}`' -f [int]$blockedSkillExecutionUnitCount),
('- degraded_skill_execution_unit_count: `{0}`' -f [int]$degradedSkillExecutionUnitCount),
```

- [ ] **Step 5: Run no-old-output guard**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py::ExecutionInternalVocabularyCleanupTests::test_current_plan_execute_outputs_do_not_write_old_execution_field_names -q
```

Expected: PASS.

- [ ] **Step 6: Commit old output field removal**

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py
git commit -m "refactor: stop writing old execution field names"
```

---

### Task 9: Tighten Routing Terminology Scans To Zero Execution-Internal References

**Files:**
- Modify: `config/routing-terminology-hard-cleanup.json`
- Modify: `scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1`
- Modify: `scripts/verify/vibe-current-routing-contract-scan.ps1`
- Modify: `tests/runtime_neutral/test_routing_terminology_hard_cleanup.py`
- Modify: `tests/runtime_neutral/test_current_routing_contract_scan.py`

- [ ] **Step 1: Replace allowlist config with zero-target scan config**

In `config/routing-terminology-hard-cleanup.json`, replace:

```json
"execution_internal_allowlist": [
  {
    "path": "scripts/runtime/Invoke-PlanExecute.ps1",
    "reason": "execution manifest and lane accounting internals derived from skill_routing.selected"
  },
  {
    "path": "scripts/runtime/VibeExecution.Common.ps1",
    "reason": "execution lane internals derived from selected skill execution units"
  },
  {
    "path": "scripts/runtime/Invoke-DelegatedLaneUnit.ps1",
    "reason": "delegated execution lane internals"
  },
  {
    "path": "tests/runtime_neutral/test_plan_execute_receipts.py",
    "reason": "execution-internal receipt tests"
  }
],
```

with:

```json
"execution_internal_scan_files": [
  "scripts/runtime/Invoke-PlanExecute.ps1",
  "scripts/runtime/VibeExecution.Common.ps1",
  "scripts/runtime/Invoke-DelegatedLaneUnit.ps1",
  "tests/runtime_neutral/test_plan_execute_receipts.py"
],
"execution_internal_allowed_specialist_dispatch_reference_count": 0,
```

- [ ] **Step 2: Update hard cleanup scan to fail on execution-internal references**

In `scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1`, replace the current execution count block:

```powershell
$executionInternalCount = 0
foreach ($entry in @($config.execution_internal_allowlist)) {
    $relative = [string]$entry.path
    $fullPath = Join-Path $RepoRoot $relative
    foreach ($lineText in @(Get-TextFileLines -Path $fullPath)) {
        if ([string]$lineText -and $lineText.IndexOf('specialist_dispatch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $executionInternalCount += 1
        }
    }
}
```

with:

```powershell
$executionInternalCount = 0
foreach ($relative in @($config.execution_internal_scan_files)) {
    $fullPath = Join-Path $RepoRoot ([string]$relative)
    $lines = @(Get-TextFileLines -Path $fullPath)
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $lineText = [string]$lines[$index]
        if ([string]$lineText -and $lineText.IndexOf('specialist_dispatch', [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $executionInternalCount += 1
            $findings.Add((New-Finding -Category 'execution_internal_specialist_dispatch_reference' -Path ([string]$relative) -Line ($index + 1) -Pattern 'specialist_dispatch' -Text $lineText)) | Out-Null
        }
    }
}
```

Keep this summary field:

```powershell
execution_internal_specialist_dispatch_reference_count = [int]$executionInternalCount
```

Because the execution references are now findings, the existing final failure block:

```powershell
if (@($summary.findings).Count -gt 0) {
    exit 1
}
```

will fail the gate when the count is nonzero.

- [ ] **Step 3: Update hard cleanup scan test**

In `tests/runtime_neutral/test_routing_terminology_hard_cleanup.py`, update `test_hard_cleanup_scan_reports_json`:

```python
self.assertIn("execution_internal_specialist_dispatch_reference_count", payload)
self.assertEqual(0, payload["execution_internal_specialist_dispatch_reference_count"])
self.assertEqual([], payload["findings"])
```

- [ ] **Step 4: Update current routing contract scan test**

In `tests/runtime_neutral/test_current_routing_contract_scan.py`, assert the hard-cleanup zero count:

```python
self.assertIn("hard_cleanup_execution_internal_specialist_dispatch_reference_count", payload)
self.assertEqual(0, payload["hard_cleanup_execution_internal_specialist_dispatch_reference_count"])
self.assertEqual([], payload["findings"])
```

- [ ] **Step 5: Run scan tests and scans**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_routing_terminology_hard_cleanup.py tests/runtime_neutral/test_current_routing_contract_scan.py -q
.\scripts\verify\vibe-routing-terminology-hard-cleanup-scan.ps1
.\scripts\verify\vibe-current-routing-contract-scan.ps1
```

Expected:

```text
Execution-internal specialist_dispatch allowlist references: 0
Gate Result: PASS
```

and:

```text
Hard cleanup execution-internal specialist_dispatch references: 0
Gate Result: PASS
```

- [ ] **Step 6: Commit scan tightening**

```powershell
git add config/routing-terminology-hard-cleanup.json scripts/verify/vibe-routing-terminology-hard-cleanup-scan.ps1 scripts/verify/vibe-current-routing-contract-scan.ps1 tests/runtime_neutral/test_routing_terminology_hard_cleanup.py tests/runtime_neutral/test_current_routing_contract_scan.py
git commit -m "test: enforce zero execution internal dispatch references"
```

---

### Task 10: Focused Regression

**Files:**
- No planned source edits.

- [ ] **Step 1: Run focused regression tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py tests/runtime_neutral/test_routing_terminology_hard_cleanup.py tests/runtime_neutral/test_current_routing_contract_scan.py tests/runtime_neutral/test_l_xl_native_execution_topology.py tests/runtime_neutral/test_plan_execute_receipts.py tests/runtime_neutral/test_runtime_contract_schema.py tests/runtime_neutral/test_runtime_delivery_acceptance.py tests/runtime_neutral/test_skill_promotion_destructive_gate.py tests/runtime_neutral/test_skill_promotion_metrics.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Search for residual old execution names in current execution files**

Run:

```powershell
rg -n "specialist_dispatch|approved_dispatch_count|approved_dispatch\\s*=|blocked_specialist_unit|degraded_specialist_unit|specialist_dispatch_outcome|specialist_dispatch_resolution" scripts/runtime/Invoke-PlanExecute.ps1 scripts/runtime/VibeExecution.Common.ps1 scripts/runtime/Invoke-DelegatedLaneUnit.ps1 tests/runtime_neutral/test_plan_execute_receipts.py
```

Expected: no matches.

- [ ] **Step 3: Commit only if focused regression required minor fixes**

If Step 1 or Step 2 required fixes, commit them:

```powershell
git add scripts/runtime/Invoke-PlanExecute.ps1 scripts/runtime/VibeExecution.Common.ps1 scripts/runtime/Invoke-DelegatedLaneUnit.ps1 packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py tests/runtime_neutral/test_execution_internal_vocabulary_cleanup.py tests/runtime_neutral/test_l_xl_native_execution_topology.py tests/runtime_neutral/test_plan_execute_receipts.py tests/runtime_neutral/test_runtime_contract_schema.py tests/runtime_neutral/test_runtime_delivery_acceptance.py tests/runtime_neutral/test_skill_promotion_destructive_gate.py tests/runtime_neutral/test_skill_promotion_metrics.py
git commit -m "fix: stabilize current skill execution vocabulary cleanup"
```

If no files changed, do not create an empty commit.

---

### Task 11: Broad Gates And Final Evidence

**Files:**
- No planned source edits.

- [ ] **Step 1: Run terminology and routing gates**

Run:

```powershell
.\scripts\verify\vibe-routing-terminology-hard-cleanup-scan.ps1
.\scripts\verify\vibe-current-routing-contract-scan.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected:

```text
Gate Result: PASS
Total assertions: 1014
Failed: 0
```

The exact total assertion count may increase only if this cleanup adds new route smoke assertions. A lower count requires investigation before completion.

- [ ] **Step 2: Run packaging/config/version gates**

Run:

```powershell
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1
.\scripts\verify\vibe-version-packaging-gate.ps1
.\scripts\verify\vibe-version-consistency-gate.ps1
```

Expected: every gate exits `0` and reports PASS or equivalent success output.

- [ ] **Step 3: Run diff hygiene checks**

Run:

```powershell
git diff --check
git status --short --branch
git log --oneline -n 12
```

Expected:

```text
git diff --check
```

prints no whitespace errors.

`git status --short --branch` shows only intentional branch ahead status and no uncommitted files.

- [ ] **Step 4: Final completion report**

Report these exact evidence points:

```text
Focused pytest: PASS
vibe-routing-terminology-hard-cleanup-scan.ps1: PASS, execution-internal specialist_dispatch references = 0
vibe-current-routing-contract-scan.ps1: PASS, hard cleanup execution-internal references = 0
vibe-pack-routing-smoke.ps1: PASS
offline/config/version gates: PASS
six governed stages: unchanged
routing model: unchanged
skills/packs deleted: none
```

If any gate could not be run, report the exact command, exit status, and blocker. Do not claim completion until the blocker is either fixed or explicitly accepted.
