# Runtime Output Compatibility Naming Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove legacy routing role field names from new active Python and PowerShell route outputs while preserving old artifact compatibility and six-stage runtime behavior.

**Architecture:** Keep legacy field readers as fallback-only compatibility, but stop writing `stage_assistant_candidates`, `route_authority_eligible`, and `legacy_role` into current public route results. Use internal underscore-prefixed fields during selection when needed, then project public route rows before returning JSON.

**Tech Stack:** Python runtime-core router, PowerShell router and runtime scripts, pytest, PowerShell verification gates.

---

## File Structure

- Create: `tests/runtime_neutral/test_runtime_route_output_shape.py`
  - Runtime-neutral guard for Python `route_prompt` and PowerShell `resolve-pack-route.ps1` output shape.
- Modify: `tests/unit/test_router_contract_selection_guards.py`
  - Update unit expectations from old public fields to internal/private selection fields and public ranking shape.
- Modify: `tests/runtime_neutral/test_router_bridge.py`
  - Update route-output assertions to require absence of old output fields.
- Modify: `tests/runtime_neutral/test_custom_admission_bridge.py`
  - Keep advisory custom-skill behavior while removing `route_authority_eligible` assertions from public output.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`
  - Keep legacy pack-field fallback readers, but return public ranking rows without old field names.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
  - Use internal route eligibility for selection math, then strip internal and legacy fields from public `ranked` output.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_presentation.py`
  - Stop looking for `stage_assistant_candidates` in active route output.
- Modify: `packages/runtime-core/src/vgo_runtime/custom_admission.py`
  - Keep internal route eligibility, but remove old field names from public admitted-candidate summaries.
- Modify: `scripts/router/modules/41-candidate-selection.ps1`
  - Mirror Python selection cleanup with internal underscore fields.
- Modify: `scripts/router/resolve-pack-route.ps1`
  - Use internal route eligibility for scoring and selection, then output public ranked rows only.
- Modify: `scripts/router/modules/46-confirm-ui.ps1`
  - Stop looking for `stage_assistant_candidates` in active route output.
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
  - Ensure new route results cannot create fresh `stage_assistant_hints` from removed active fields.
- Modify: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
  - Preserve usage evidence boundary and assert new packets do not depend on active stage-assistant route output.

Out of scope:

- No skill deletion.
- No pack pruning.
- No removal of `legacy_skill_routing`.
- No repo-wide rewrite of historical plan documents.
- No deletion of old artifact reader fallback.

---

### Task 1: Add Failing Active Route Output Shape Guard

**Files:**
- Create: `tests/runtime_neutral/test_runtime_route_output_shape.py`
- Test: `tests/runtime_neutral/test_runtime_route_output_shape.py`

- [ ] **Step 1: Create the failing route output shape test**

Create `tests/runtime_neutral/test_runtime_route_output_shape.py` with this content:

```python
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


LEGACY_PACK_ROW_FIELDS = {"stage_assistant_candidates", "route_authority_eligible"}
LEGACY_CANDIDATE_ROW_FIELDS = {"legacy_role", "route_authority_eligible"}


ROUTE_CASES = [
    (
        "帮我做科研绘图，产出期刊级 figure，多面板、颜色无障碍、矢量导出",
        "L",
        "research",
        "science-figures-visualization",
        "scientific-visualization",
    ),
    (
        "请用 LaTeX 构建论文 PDF，检查 bibtex 引用、模板和 submission checklist",
        "L",
        "coding",
        "scholarly-publishing-workflow",
        "latex-submission-pipeline",
    ),
    (
        "机器学习 data preprocessing pipeline：清洗数据、feature encoding、standardize data、validate input data",
        "L",
        "coding",
        "data-ml",
        "preprocessing-data-with-automated-pipelines",
    ),
    (
        "request code review before merge：请整理提交评审材料，准备 code review request",
        "L",
        "review",
        "code-quality",
        "requesting-code-review",
    ),
]


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def assert_public_route_output_shape(testcase: unittest.TestCase, result: dict[str, Any]) -> None:
    testcase.assertIn("ranked", result)
    testcase.assertIsInstance(result["ranked"], list)
    for pack_row in result["ranked"]:
        testcase.assertIsInstance(pack_row, dict)
        for field in LEGACY_PACK_ROW_FIELDS:
            testcase.assertNotIn(field, pack_row, pack_row.get("pack_id"))
        custom_admission = pack_row.get("custom_admission")
        if isinstance(custom_admission, dict):
            testcase.assertNotIn("route_authority_eligible", custom_admission, pack_row.get("pack_id"))
        ranking = pack_row.get("candidate_ranking") or []
        testcase.assertIsInstance(ranking, list)
        for candidate_row in ranking:
            testcase.assertIsInstance(candidate_row, dict)
            for field in LEGACY_CANDIDATE_ROW_FIELDS:
                testcase.assertNotIn(field, candidate_row, candidate_row.get("skill"))


class RuntimeRouteOutputShapeTests(unittest.TestCase):
    def test_python_route_output_has_no_legacy_role_fields(self) -> None:
        for prompt, grade, task_type, expected_pack, expected_skill in ROUTE_CASES:
            with self.subTest(expected_pack=expected_pack, expected_skill=expected_skill):
                result = route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)

                self.assertEqual(expected_pack, result["selected"]["pack_id"])
                self.assertEqual(expected_skill, result["selected"]["skill"])
                assert_public_route_output_shape(self, result)

    def test_powershell_route_output_has_no_legacy_role_fields(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        script_path = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
        for prompt, grade, task_type, expected_pack, expected_skill in ROUTE_CASES:
            with self.subTest(expected_pack=expected_pack, expected_skill=expected_skill):
                completed = subprocess.run(
                    [
                        shell,
                        "-NoLogo",
                        "-NoProfile",
                        "-File",
                        str(script_path),
                        "-Prompt",
                        prompt,
                        "-Grade",
                        grade,
                        "-TaskType",
                        task_type,
                    ],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=True,
                    env={"VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
                )
                result = json.loads(completed.stdout)

                self.assertEqual(expected_pack, result["selected"]["pack_id"])
                self.assertEqual(expected_skill, result["selected"]["skill"])
                assert_public_route_output_shape(self, result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_route_output_shape.py -q
```

Expected: FAIL. The failure must mention at least one of:

```text
stage_assistant_candidates
route_authority_eligible
legacy_role
```

- [ ] **Step 3: Commit the failing guard**

Run:

```powershell
git add tests/runtime_neutral/test_runtime_route_output_shape.py
git commit -m "test: guard active route output naming"
```

Expected: commit succeeds with only the new test file.

---

### Task 2: Clean Python Candidate Selection Public Rows

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`
- Modify: `tests/unit/test_router_contract_selection_guards.py`
- Test: `tests/unit/test_router_contract_selection_guards.py`

- [ ] **Step 1: Add internal-field helpers to Python selection**

In `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`, add this block after `get_pack_default_candidate`:

```python
INTERNAL_CANDIDATE_USABLE = "_candidate_usable"
INTERNAL_LEGACY_ROLE = "_legacy_role"
INTERNAL_SELECTION_USABLE = "_selection_usable"
INTERNAL_LEGACY_STAGE_ASSISTANTS = "_legacy_stage_assistant_candidates"


def public_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    public = dict(row)
    for key in (
        INTERNAL_CANDIDATE_USABLE,
        INTERNAL_LEGACY_ROLE,
        "route_authority_eligible",
        "legacy_role",
    ):
        public.pop(key, None)
    return public


def public_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [public_candidate_row(row) for row in rows]


def candidate_is_usable(row: dict[str, Any]) -> bool:
    if INTERNAL_CANDIDATE_USABLE in row:
        return bool(row[INTERNAL_CANDIDATE_USABLE])
    return bool(row.get("route_authority_eligible", True))


def candidate_legacy_role(row: dict[str, Any]) -> str:
    if INTERNAL_LEGACY_ROLE in row:
        return str(row[INTERNAL_LEGACY_ROLE])
    return str(row.get("legacy_role") or "skill_candidate")
```

- [ ] **Step 2: Replace public legacy candidate fields with internal fields**

In `select_pack_candidate`, replace each candidate ranking row field:

```python
"route_authority_eligible": use_eligible,
"legacy_role": legacy_role,
```

with:

```python
INTERNAL_CANDIDATE_USABLE: use_eligible,
INTERNAL_LEGACY_ROLE: legacy_role,
```

In requested-skill ranking rows, replace:

```python
"route_authority_eligible": True,
"legacy_role": "explicit_request",
```

with:

```python
INTERNAL_CANDIDATE_USABLE: True,
INTERNAL_LEGACY_ROLE: "explicit_request",
```

- [ ] **Step 3: Replace selection-level public legacy fields with internal fields**

In every return dict from `select_pack_candidate`, replace:

```python
"route_authority_eligible": True,
```

with:

```python
INTERNAL_SELECTION_USABLE: True,
```

Replace:

```python
"route_authority_eligible": False,
```

with:

```python
INTERNAL_SELECTION_USABLE: False,
```

Replace every public `stage_assistant_candidates` entry:

```python
"stage_assistant_candidates": [],
```

with:

```python
INTERNAL_LEGACY_STAGE_ASSISTANTS: [],
```

Replace non-empty stage-assistant return entries with:

```python
INTERNAL_LEGACY_STAGE_ASSISTANTS: public_candidate_rows(
    [row for row in stage_assistant_ranked if row.get("skill") != requested_candidate][:4]
),
```

or the same expression using `fallback` / `top.get("skill")` for the corresponding branch.

- [ ] **Step 4: Use internal helpers for ranking and public ranking output**

Replace:

```python
usable_ranked = [row for row in ranked_all if bool(row["route_authority_eligible"])]
stage_assistant_ranked = [
    row
    for row in ranked_all
    if row.get("legacy_role") == "stage_assistant"
]
```

with:

```python
usable_ranked = [row for row in ranked_all if candidate_is_usable(row)]
stage_assistant_ranked = [
    row
    for row in ranked_all
    if candidate_legacy_role(row) == "stage_assistant"
]
```

Replace every returned `"ranking": usable_ranked[:6]` with:

```python
"ranking": public_candidate_rows(usable_ranked[:6])
```

Replace requested-skill returned ranking lists with `public_candidate_rows([...])`.

- [ ] **Step 5: Update unit tests for private selection state and public ranking shape**

In `tests/unit/test_router_contract_selection_guards.py`, update the first two tests:

```python
assert selection["_selection_usable"] is False
```

and:

```python
assert selection["_selection_usable"] is True
```

In `test_active_skill_candidates_do_not_need_legacy_role_fields`, replace:

```python
assert selection["ranking"][0]["legacy_role"] == "skill_candidate"
assert selection["stage_assistant_candidates"] == []
assert "routing_role" not in selection["ranking"][0]
```

with:

```python
assert "legacy_role" not in selection["ranking"][0]
assert "route_authority_eligible" not in selection["ranking"][0]
assert selection["_legacy_stage_assistant_candidates"] == []
assert "routing_role" not in selection["ranking"][0]
```

- [ ] **Step 6: Run selection unit tests**

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 7: Commit Python selection cleanup**

Run:

```powershell
git add packages/runtime-core/src/vgo_runtime/router_contract_selection.py tests/unit/test_router_contract_selection_guards.py
git commit -m "fix: hide legacy candidate selection fields"
```

Expected: commit succeeds with the Python selection helper and unit test update.

---

### Task 3: Clean Python Route Result Output And Confirm UI Lookup

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_presentation.py`
- Modify: `packages/runtime-core/src/vgo_runtime/custom_admission.py`
- Modify: `tests/runtime_neutral/test_router_bridge.py`
- Modify: `tests/runtime_neutral/test_custom_admission_bridge.py`
- Test: `tests/runtime_neutral/test_runtime_route_output_shape.py`
- Test: `tests/runtime_neutral/test_router_bridge.py`
- Test: `tests/runtime_neutral/test_custom_admission_bridge.py`

- [ ] **Step 1: Import internal constants and add public pack-row projection**

In `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`, update the import from `router_contract_selection` to include:

```python
INTERNAL_LEGACY_STAGE_ASSISTANTS,
INTERNAL_SELECTION_USABLE,
public_candidate_rows,
```

Add these helpers near `_get_preferred_host_selection`:

```python
INTERNAL_ROUTE_USABLE = "_route_usable"


def _public_custom_metadata(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    public = dict(value)
    public.pop("route_authority_eligible", None)
    return public


def _public_pack_row(row: dict[str, object]) -> dict[str, object]:
    public = dict(row)
    public.pop(INTERNAL_ROUTE_USABLE, None)
    public.pop("route_authority_eligible", None)
    public.pop("stage_assistant_candidates", None)
    public["candidate_ranking"] = public_candidate_rows(list(public.get("candidate_ranking") or []))
    public["custom_admission"] = _public_custom_metadata(public.get("custom_admission"))
    return public


def _public_admitted_candidates(rows: Any) -> list[dict[str, object]]:
    public_rows: list[dict[str, object]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        public_row = dict(row)
        public_row.pop("route_authority_eligible", None)
        public_rows.append(public_row)
    return public_rows
```

- [ ] **Step 2: Stop using stage-assistant rows in Python preferred-host selection**

In `_get_preferred_host_selection`, delete this loop:

```python
for row in pack_row.get("stage_assistant_candidates", []) or []:
    if isinstance(row, dict):
        add_candidate(row, 0.0, "", str(row.get("skill") or "").strip() == selected_skill)
```

Do not replace it. The selected skill is already represented by `selected_candidate` and `candidate_ranking`.

- [ ] **Step 3: Use internal route usability in Python route result assembly**

In `route_prompt`, replace:

```python
route_authority_eligible = bool(selection.get("route_authority_eligible", selection.get("selected") is not None))
```

with:

```python
route_usable = bool(selection.get(INTERNAL_SELECTION_USABLE, selection.get("selected") is not None))
```

Then update the following logic to use `route_usable` instead of `route_authority_eligible`:

```python
if isinstance(custom_metadata, dict):
    route_usable = route_usable and bool(custom_metadata.get("route_authority_eligible", False))
if weak_fallback:
    route_usable = False
```

In the `pack_results.append(...)` dict, remove:

```python
"stage_assistant_candidates": selection.get("stage_assistant_candidates", []),
"route_authority_eligible": route_authority_eligible,
```

and add:

```python
INTERNAL_ROUTE_USABLE: route_usable,
```

Keep:

```python
"candidate_ranking": selection["ranking"],
```

because Task 2 already makes those rows public.

- [ ] **Step 4: Use public ranked rows in Python route result**

Replace:

```python
authority_ranked = [row for row in ranked if bool(row.get("route_authority_eligible", True))]
```

with:

```python
authority_ranked = [row for row in ranked if bool(row.get(INTERNAL_ROUTE_USABLE, True))]
```

Replace:

```python
preferred_selection = _get_preferred_host_selection(top) if top and not bool(top.get("route_authority_eligible", True)) else None
```

with:

```python
preferred_selection = _get_preferred_host_selection(top) if top and not bool(top.get(INTERNAL_ROUTE_USABLE, True)) else None
```

Replace:

```python
"ranked": ranked[:3],
```

with:

```python
"ranked": [_public_pack_row(row) for row in ranked[:3]],
```

In the `custom_admission` result block, replace:

```python
"admitted_candidates": custom_admission.get("admitted_candidates"),
```

with:

```python
"admitted_candidates": _public_admitted_candidates(custom_admission.get("admitted_candidates")),
```

- [ ] **Step 5: Remove route-authority field from public custom admission summaries**

In `packages/runtime-core/src/vgo_runtime/custom_admission.py`, leave the internal `admitted` dict unchanged, because routing still needs it. In `custom_summary`, remove this entry:

```python
"route_authority_eligible": admitted["route_authority_eligible"],
```

The public `admitted_candidates` summary should still include:

```python
"skill_id"
"manifest_kind"
"pack_id"
"trigger_mode"
"dispatch_phase"
"binding_profile"
"lane_policy"
"parallelizable_in_root_xl"
"native_usage_required"
"must_preserve_workflow"
"skill_md_path"
"description"
```

- [ ] **Step 6: Remove stage-assistant lookup from Python confirm UI**

In `packages/runtime-core/src/vgo_runtime/router_contract_presentation.py`, delete this block inside `_order_confirm_ranking`:

```python
if selected_row is None:
    for pack_row in route_result.get("ranked", []):
        if str(pack_row.get("pack_id") or "").strip() != selected_pack:
            continue
        for candidate in pack_row.get("stage_assistant_candidates", []) or []:
            if str(candidate.get("skill") or "").strip() == selected_skill:
                selected_row = candidate
                break
        if selected_row is not None:
            break
```

Do not replace it. The fallback below that creates:

```python
{"skill": selected_skill, "score": route_result["selected"].get("selection_score")}
```

is now the correct fallback.

- [ ] **Step 7: Update Python route bridge tests**

In `tests/runtime_neutral/test_router_bridge.py`, replace assertions like:

```python
self.assertEqual("skill_candidate", ranking_by_skill["scientific-visualization"]["legacy_role"])
self.assertEqual([], figure_row["stage_assistant_candidates"])
```

with:

```python
self.assertNotIn("legacy_role", ranking_by_skill["scientific-visualization"])
self.assertNotIn("route_authority_eligible", ranking_by_skill["scientific-visualization"])
self.assertNotIn("stage_assistant_candidates", figure_row)
self.assertNotIn("route_authority_eligible", figure_row)
```

Apply the same pattern to:

```text
scientific-schematics
webthinker-deep-research
flashrag-evidence
preprocessing-data-with-automated-pipelines
```

- [ ] **Step 8: Update custom admission bridge tests**

In `tests/runtime_neutral/test_custom_admission_bridge.py`, replace:

```python
self.assertFalse(bool(custom_ranked["route_authority_eligible"]))
```

with:

```python
self.assertNotIn("route_authority_eligible", custom_ranked)
self.assertNotEqual("genomics-qc-flow", result["selected"]["skill"])
```

Also add this assertion after checking `admitted_candidates`:

```python
for admitted in result["custom_admission"]["admitted_candidates"]:
    self.assertNotIn("route_authority_eligible", admitted)
```

- [ ] **Step 9: Run Python route output tests**

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_runtime_route_output_shape.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_custom_admission_bridge.py -q
```

Expected: Python route-output assertions pass, but the PowerShell half of `test_runtime_route_output_shape.py` may still fail until Task 4.

- [ ] **Step 10: Commit Python route output cleanup**

If only the PowerShell shape subtest is still failing, commit the Python work:

```powershell
git add packages/runtime-core/src/vgo_runtime/router_contract_selection.py packages/runtime-core/src/vgo_runtime/router_contract_runtime.py packages/runtime-core/src/vgo_runtime/router_contract_presentation.py packages/runtime-core/src/vgo_runtime/custom_admission.py tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_custom_admission_bridge.py
git commit -m "fix: hide legacy python route output fields"
```

Expected: commit succeeds. If any Python route tests fail, fix them before committing.

---

### Task 4: Clean PowerShell Route Output

**Files:**
- Modify: `scripts/router/modules/41-candidate-selection.ps1`
- Modify: `scripts/router/resolve-pack-route.ps1`
- Modify: `scripts/router/modules/46-confirm-ui.ps1`
- Test: `tests/runtime_neutral/test_runtime_route_output_shape.py`
- Test: `tests/runtime_neutral/test_custom_admission_bridge.py`

- [ ] **Step 1: Switch PowerShell candidate selection to internal fields**

In `scripts/router/modules/41-candidate-selection.ps1`, replace public selection object properties:

```powershell
route_authority_eligible = $true
route_authority_eligible = $false
stage_assistant_candidates = @()
legacy_role = $legacyRole
```

with internal properties:

```powershell
_selection_usable = $true
_selection_usable = $false
_legacy_stage_assistant_candidates = @()
_legacy_role = $legacyRole
```

For candidate ranking rows, replace:

```powershell
route_authority_eligible = [bool]$useEligible
legacy_role = $legacyRole
```

with:

```powershell
_candidate_usable = [bool]$useEligible
_legacy_role = $legacyRole
```

- [ ] **Step 2: Update PowerShell ranking filters**

In the same file, replace:

```powershell
$usableRanked = @($ranked | Where-Object { $_.route_authority_eligible })
$stageAssistantRanked = @($ranked | Where-Object { [string]$_.legacy_role -eq 'stage_assistant' })
```

with:

```powershell
$usableRanked = @($ranked | Where-Object { $_.PSObject.Properties.Name -contains '_candidate_usable' -and [bool]$_._candidate_usable })
$stageAssistantRanked = @($ranked | Where-Object { $_.PSObject.Properties.Name -contains '_legacy_role' -and [string]$_._legacy_role -eq 'stage_assistant' })
```

Before returning any public `ranking`, pipe it through a new helper:

```powershell
function ConvertTo-PublicCandidateRanking {
    param([AllowNull()] [object[]]$Rows = @())

    $publicRows = @()
    foreach ($row in @($Rows)) {
        $public = [ordered]@{}
        foreach ($property in @($row.PSObject.Properties)) {
            if ($property.Name -in @('_candidate_usable', '_legacy_role', 'route_authority_eligible', 'legacy_role')) {
                continue
            }
            $public[$property.Name] = $property.Value
        }
        $publicRows += [pscustomobject]$public
    }
    return @($publicRows)
}
```

Use it in every returned object:

```powershell
ranking = @(ConvertTo-PublicCandidateRanking -Rows @($usableRanked | Select-Object -First 6))
```

For internal legacy assistants, use:

```powershell
_legacy_stage_assistant_candidates = @(ConvertTo-PublicCandidateRanking -Rows @($stageAssistantRanked | Select-Object -First 4))
```

- [ ] **Step 3: Use internal route usability in `resolve-pack-route.ps1`**

In `scripts/router/resolve-pack-route.ps1`, replace:

```powershell
$routeAuthorityEligible = if ($selection.PSObject.Properties.Name -contains 'route_authority_eligible') { [bool]$selection.route_authority_eligible } else { -not [string]::IsNullOrWhiteSpace([string]$selection.selected) }
```

with:

```powershell
$routeUsable = if ($selection.PSObject.Properties.Name -contains '_selection_usable') { [bool]$selection._selection_usable } else { -not [string]::IsNullOrWhiteSpace([string]$selection.selected) }
```

Then replace later assignments to `$routeAuthorityEligible` with `$routeUsable`.

In each pack result row, remove:

```powershell
stage_assistant_candidates = @($selection.stage_assistant_candidates)
route_authority_eligible = [bool]$routeAuthorityEligible
```

and add:

```powershell
_route_usable = [bool]$routeUsable
```

- [ ] **Step 4: Add public route row projection in `resolve-pack-route.ps1`**

Add this function before the final `$result = [pscustomobject]@{ ... }` block:

```powershell
function ConvertTo-PublicRoutePackRow {
    param([Parameter(Mandatory)] [object]$PackRow)

    $public = [ordered]@{}
    foreach ($property in @($PackRow.PSObject.Properties)) {
        if ($property.Name -in @('_route_usable', 'route_authority_eligible', 'stage_assistant_candidates')) {
            continue
        }
        if ($property.Name -eq 'candidate_ranking') {
            $public[$property.Name] = @(ConvertTo-PublicCandidateRanking -Rows @($property.Value))
            continue
        }
        if ($property.Name -eq 'custom_admission' -and $null -ne $property.Value) {
            $metadata = [ordered]@{}
            foreach ($metadataProperty in @($property.Value.PSObject.Properties)) {
                if ($metadataProperty.Name -eq 'route_authority_eligible') {
                    continue
                }
                $metadata[$metadataProperty.Name] = $metadataProperty.Value
            }
            $public[$property.Name] = [pscustomobject]$metadata
            continue
        }
        $public[$property.Name] = $property.Value
    }
    return [pscustomobject]$public
}
```

Replace:

```powershell
$authorityRanked = @($ranked | Where-Object { $_.route_authority_eligible })
```

with:

```powershell
$authorityRanked = @($ranked | Where-Object { $_.PSObject.Properties.Name -contains '_route_usable' -and [bool]$_._route_usable })
```

Replace:

```powershell
$effectivePreferredSelection = if ($effectiveTop -and -not [bool]$effectiveTop.route_authority_eligible) { Get-PreferredHostSelection -PackRow $effectiveTop } else { $null }
```

with:

```powershell
$effectivePreferredSelection = if ($effectiveTop -and -not [bool]$effectiveTop._route_usable) { Get-PreferredHostSelection -PackRow $effectiveTop } else { $null }
```

Replace final ranked output:

```powershell
ranked = @($ranked | Select-Object -First 3)
```

with:

```powershell
ranked = @($ranked | Select-Object -First 3 | ForEach-Object { ConvertTo-PublicRoutePackRow -PackRow $_ })
```

- [ ] **Step 5: Remove stage-assistant lookup from PowerShell preferred selection and confirm UI**

In `scripts/router/resolve-pack-route.ps1`, remove this loop from `Get-PreferredHostSelection`:

```powershell
foreach ($candidate in @($PackRow.stage_assistant_candidates)) {
    Add-PreferredHostSelectionCandidate `
        -PreferredMap $preferred `
        -CandidateRow $candidate `
        -FallbackScore 0.0 `
        -FallbackSkill '' `
        -IsSelectedCandidate ([string]$candidate.skill -eq [string]$PackRow.selected_candidate) `
        -OrdinalRef ([ref]$ordinal)
}
```

In `scripts/router/modules/46-confirm-ui.ps1`, remove this block:

```powershell
if (-not $selectedRow -and $packRow -and $packRow.stage_assistant_candidates) {
    $selectedRow = @($packRow.stage_assistant_candidates | Where-Object { [string]$_.skill -eq $selectedSkill } | Select-Object -First 1)
}
```

- [ ] **Step 6: Run PowerShell output shape tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_route_output_shape.py tests/runtime_neutral/test_custom_admission_bridge.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit PowerShell route output cleanup**

Run:

```powershell
git add scripts/router/modules/41-candidate-selection.ps1 scripts/router/resolve-pack-route.ps1 scripts/router/modules/46-confirm-ui.ps1 tests/runtime_neutral/test_runtime_route_output_shape.py tests/runtime_neutral/test_custom_admission_bridge.py
git commit -m "fix: hide legacy powershell route output fields"
```

Expected: commit succeeds.

---

### Task 5: Stabilize Runtime Packet Compatibility Boundaries

**Files:**
- Modify: `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- Modify: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- Modify: `tests/runtime_neutral/test_simplified_skill_routing_contract.py`
- Test: `tests/runtime_neutral/test_binary_skill_usage_contract.py`
- Test: `tests/runtime_neutral/test_simplified_skill_routing_contract.py`
- Test: `tests/runtime_neutral/test_governed_runtime_bridge.py`

- [ ] **Step 1: Stop deriving new hints from removed active route output**

In `scripts/runtime/Freeze-RuntimeInputPacket.ps1`, replace the body of `Get-VibeStageAssistantHints` after `$dispatchContractForHint` is created with this explicit empty active-output behavior:

```powershell
    # Current route output no longer writes stage_assistant_candidates. Old runtime
    # packets remain readable through VibeRuntime.Common.ps1 compatibility helpers.
    return @()
```

Keep the function signature. Do not remove calls to `Get-VibeStageAssistantHints`; they should now receive an empty list for new packets.

- [ ] **Step 2: Tighten binary usage packet assertions**

In `tests/runtime_neutral/test_binary_skill_usage_contract.py`, after:

```python
self.assertNotIn("stage_assistant_hints", packet)
```

add:

```python
self.assertEqual([], packet["legacy_skill_routing"]["stage_assistant_hints"])
```

Do not weaken the existing `skill_usage.used` / `skill_usage.unused` assertions. Route-output shape is covered by `tests/runtime_neutral/test_runtime_route_output_shape.py`; this packet test only proves new freeze packets no longer create fresh legacy stage-assistant hints.

- [ ] **Step 3: Preserve old packet reader compatibility**

In `tests/runtime_neutral/test_simplified_skill_routing_contract.py`, add this test to prove old packet hints remain readable:

```python
    def test_stage_assistant_hint_reader_still_reads_old_legacy_container(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "legacy_skill_routing = [pscustomobject]@{ "
            "stage_assistant_hints = @([pscustomobject]@{ skill_id = 'legacy-helper'; reason = 'old packet' }) "
            "} "
            "}; "
            "$hints = Get-VibeRuntimeStageAssistantHints -RuntimeInputPacket $packet; "
            "[pscustomobject]@{ hint_ids = @($hints | ForEach-Object { $_.skill_id }) } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual(["legacy-helper"], as_list(payload["hint_ids"]))
```

- [ ] **Step 4: Run runtime packet tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_governed_runtime_bridge.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit runtime packet compatibility cleanup**

Run:

```powershell
git add scripts/runtime/Freeze-RuntimeInputPacket.ps1 tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_simplified_skill_routing_contract.py
git commit -m "fix: keep stage assistant hints legacy-only"
```

Expected: commit succeeds.

---

### Task 6: Run Focused Regression Suite And Repair Drift

**Files:**
- Modify only files already touched by Tasks 1-5 if tests expose required updates.
- Test: focused route/runtime tests.

- [ ] **Step 1: Run focused regression suite**

Run:

```powershell
python -m pytest tests/unit/test_runtime_stage_machine.py tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_runtime_route_output_shape.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_custom_admission_bridge.py tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_figures_reporting_stage_assistant_removal.py tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Search for forbidden active output assertions**

Run:

```powershell
rg -n 'row\["stage_assistant_candidates"\]|row\.get\("stage_assistant_candidates"\)|\["route_authority_eligible"\]|"legacy_role"' tests/runtime_neutral tests/unit/test_router_contract_selection_guards.py
```

Expected allowed matches only in:

```text
tests/unit/test_router_contract_selection_guards.py old fixture input dictionaries
tests/runtime_neutral/test_simplified_skill_routing_contract.py old runtime packet compatibility fixture
tests/runtime_neutral/test_runtime_route_output_shape.py forbidden-field guard constants/assertions
```

If the search finds an active output expectation in another test, update that test to assert absence of the field.

- [ ] **Step 3: Run route output shape test after any repair**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_route_output_shape.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit any drift repairs**

If Step 1 or Step 2 required additional source or test changes, run:

```powershell
git add packages scripts tests
git commit -m "fix: stabilize runtime output naming cleanup"
```

Expected: commit succeeds only if files changed. If no files changed, skip this commit.

---

### Task 7: Full Verification And Final Status

**Files:**
- Verify only.

- [ ] **Step 1: Run core pytest coverage**

Run:

```powershell
python -m pytest tests/unit/test_runtime_stage_machine.py tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_runtime_route_output_shape.py tests/runtime_neutral/test_simplified_skill_routing_contract.py tests/runtime_neutral/test_binary_skill_usage_contract.py tests/runtime_neutral/test_terminology_field_simplification.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_custom_admission_bridge.py tests/runtime_neutral/test_governed_runtime_bridge.py tests/runtime_neutral/test_figures_reporting_stage_assistant_removal.py tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run pack routing smoke**

Run:

```powershell
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected:

```text
Pack routing smoke checks passed.
```

- [ ] **Step 3: Run offline skills gate**

Run:

```powershell
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected:

```text
[PASS] offline skill closure gate passed.
```

- [ ] **Step 4: Run config parity gate**

Run:

```powershell
pwsh -NoLogo -NoProfile -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
```

Expected:

```text
Gate Result: PASS
Total diff paths: 0
```

If artifacts are written under `outputs/verify`, check `git status --short` and do not commit generated artifacts unless they are already tracked and intentionally changed.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 6: Confirm active manifest fields are still clean**

Run:

```powershell
@'
import json
from pathlib import Path
manifest = json.loads(Path('config/pack-manifest.json').read_text(encoding='utf-8-sig'))
bad = [
    pack['id']
    for pack in manifest['packs']
    if 'route_authority_candidates' in pack or 'stage_assistant_candidates' in pack
]
print({'pack_count': len(manifest['packs']), 'bad_pack_count': len(bad), 'bad_packs': bad})
raise SystemExit(1 if bad else 0)
'@ | python -
```

Expected:

```text
{'pack_count': 41, 'bad_pack_count': 0, 'bad_packs': []}
```

- [ ] **Step 7: Confirm public route output shape directly**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_runtime_route_output_shape.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Report final status**

Run:

```powershell
git status --short --branch
git log --oneline -n 8
```

Expected:

- Worktree is clean except intentionally ignored/generated files.
- Final report lists commits created during this implementation.
- Final report states whether:
  - active manifest old fields are absent,
  - public Python route output old fields are absent,
  - public PowerShell route output old fields are absent,
  - old packet compatibility remains,
  - six-stage tests pass,
  - routing smoke passes,
  - offline skills gate passes,
  - config parity passes.
