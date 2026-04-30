# Cold Platform And Quantum Pack Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `cloud-modalcom` and `science-quantum` from live routing and physically delete their Modal and quantum skill directories.

**Architecture:** This is a hard-removal migration across routing config, bundled skill directories, route probes, lock generation, and governance notes. The change removes cold vendor and quantum-computing surfaces instead of narrowing triggers again; all new route evidence is absence-based. The public Vibe six-stage runtime and the simplified `candidate skill -> selected skill -> used / unused` model stay unchanged.

**Tech Stack:** JSON routing configs, Python unittest/pytest runtime-neutral tests, PowerShell route probes and verification gates, generated `config/skills-lock.json`, Git-tracked bundled skill directories, Markdown governance docs.

---

## File Map

- Create `tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py`: focused RED/GREEN contract proving deleted packs, deleted skill dirs, deleted skill config keys, stale lock entries, and route resurrection are gone.
- Modify `config/pack-manifest.json`: delete the complete `cloud-modalcom` and `science-quantum` pack objects.
- Modify `config/skill-keyword-index.json`: delete skill keyword entries for `modal`, `modal-labs`, `qiskit`, `cirq`, `pennylane`, and `qutip`.
- Modify `config/skill-routing-rules.json`: delete routing rule entries for `modal-labs`, `qiskit`, `cirq`, `pennylane`, and `qutip`.
- Modify `config/skills-lock.json`: refresh after physical skill-directory deletion.
- Delete `bundled/skills/modal-labs`.
- Delete `bundled/skills/modal`.
- Delete `bundled/skills/qiskit`.
- Delete `bundled/skills/cirq`.
- Delete `bundled/skills/pennylane`.
- Delete `bundled/skills/qutip`.
- Modify `tests/runtime_neutral/test_zero_route_authority_second_pass.py`: remove old positive Modal and quantum assertions, keep the `ml-torch-geometric` second-pass coverage, and add absence assertions for the removed second-pass packs.
- Modify `scripts/verify/probe-scientific-packs.ps1`: replace `science-quantum` positive probe cases with blocked-pack probes.
- Modify `scripts/verify/vibe-pack-regression-matrix.ps1`: add Modal and quantum deletion regressions as blocked-pack and blocked-skill route cases.
- Modify `scripts/verify/vibe-skill-index-routing-audit.ps1`: add the same deletion regressions at the skill-index route-audit layer.
- Modify `scripts/verify/vibe-pack-routing-smoke.ps1`: assert deleted packs, deleted skill-index keys, deleted routing-rule keys, and deleted bundled directories are absent.
- Create `docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md`: record deletion rationale, routing behavior after deletion, verification results, and the evidence boundary.

## Task 1: Focused RED Test

**Files:**
- Create: `tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py`

- [ ] **Step 1: Add the focused hard-removal test**

Create `tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py`:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


DELETED_PACKS = {"cloud-modalcom", "science-quantum"}
DELETED_SKILLS = {"modal", "modal-labs", "qiskit", "cirq", "pennylane", "qutip"}


def load_json(relative_path: str) -> Any:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def route(prompt: str, task_type: str = "coding", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_pack_ids(result: dict[str, object]) -> set[str]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    return {
        str(row.get("pack_id") or "")
        for row in ranked
        if isinstance(row, dict)
    }


def ranked_candidate_skills(result: dict[str, object]) -> set[str]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    skills: set[str] = set()
    for row in ranked:
        if not isinstance(row, dict):
            continue
        skills.add(str(row.get("skill") or ""))
        skills.add(str(row.get("selected_candidate") or ""))
        candidate_ranking = row.get("candidate_ranking")
        if isinstance(candidate_ranking, list):
            skills.update(
                str(item.get("skill") or "")
                for item in candidate_ranking
                if isinstance(item, dict)
            )
        stage_candidates = row.get("stage_assistant_candidates")
        if isinstance(stage_candidates, list):
            skills.update(
                str(item.get("skill") or "")
                for item in stage_candidates
                if isinstance(item, dict)
            )
    return {skill for skill in skills if skill}


class ColdPlatformQuantumPackDeletionTests(unittest.TestCase):
    def test_pack_manifest_has_no_deleted_packs_or_skills(self) -> None:
        manifest = load_json("config/pack-manifest.json")
        packs = manifest["packs"]
        pack_ids = {str(pack["id"]) for pack in packs}
        self.assertFalse(pack_ids & DELETED_PACKS, sorted(pack_ids & DELETED_PACKS))

        for pack in packs:
            for field in ("skill_candidates", "route_authority_candidates", "stage_assistant_candidates"):
                values = {str(value) for value in (pack.get(field) or [])}
                self.assertFalse(values & DELETED_SKILLS, (pack["id"], field, sorted(values & DELETED_SKILLS)))

    def test_bundled_skill_directories_are_deleted(self) -> None:
        remaining = {
            skill
            for skill in DELETED_SKILLS
            if (REPO_ROOT / "bundled" / "skills" / skill).exists()
        }
        self.assertEqual(set(), remaining)

    def test_live_routing_configs_have_no_deleted_skill_keys(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")

        self.assertFalse(set(keyword_index["skills"]) & DELETED_SKILLS)
        self.assertFalse(set(routing_rules["skills"]) & DELETED_SKILLS)

    def test_skills_lock_has_no_deleted_skills(self) -> None:
        lock = load_json("config/skills-lock.json")
        locked = {str(row.get("name") or "") for row in lock["skills"]}
        self.assertFalse(locked & DELETED_SKILLS, sorted(locked & DELETED_SKILLS))

    def test_removed_modal_prompts_do_not_select_or_rank_deleted_surfaces(self) -> None:
        prompts = [
            ("Run a Python batch job on a cloud GPU without specifying Modal.", "coding", "M"),
            ("Deploy a serverless GPU function, but use any cloud container platform except Modal.", "coding", "M"),
            ("把 Python 任务部署到云端 GPU，不指定 Modal，用普通容器也可以", "coding", "M"),
            ("用 Modal.com 部署 serverless GPU Python function 和 batch job", "coding", "M"),
            ("Build a React modal dialog with overlay and focus trap.", "coding", "M"),
        ]
        for prompt, task_type, grade in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type, grade=grade)
                pack_id, skill = selected(result)
                self.assertNotIn(pack_id, DELETED_PACKS, result)
                self.assertNotIn(skill, DELETED_SKILLS, result)
                self.assertFalse(ranked_pack_ids(result) & DELETED_PACKS, result)
                self.assertFalse(ranked_candidate_skills(result) & DELETED_SKILLS, result)

    def test_removed_quantum_prompts_do_not_select_or_rank_deleted_surfaces(self) -> None:
        prompts = [
            ("Quantum chemistry pKa and DFT analysis, not a quantum circuit.", "research", "M"),
            ("调研 quantum chemistry 论文和 pKa 预测，不写量子电路", "research", "M"),
            ("Use Qiskit to create a Bell-state quantum circuit.", "coding", "M"),
            ("Use Cirq to build quantum gate moments for a simulator.", "coding", "M"),
            ("Use PennyLane for a quantum machine learning variational circuit.", "coding", "M"),
            ("Use QuTiP to simulate an open quantum system master equation.", "research", "M"),
        ]
        for prompt, task_type, grade in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type, grade=grade)
                pack_id, skill = selected(result)
                self.assertNotIn(pack_id, DELETED_PACKS, result)
                self.assertNotIn(skill, DELETED_SKILLS, result)
                self.assertFalse(ranked_pack_ids(result) & DELETED_PACKS, result)
                self.assertFalse(ranked_candidate_skills(result) & DELETED_SKILLS, result)

    def test_rowan_quantum_chemistry_boundary_still_has_its_owner(self) -> None:
        result = route("用 Rowan 云端量子化学平台做 pKa prediction 和 conformer search", task_type="research")
        self.assertEqual(("science-rowan-chemistry", "rowan"), selected(result), result)

    def test_remaining_packs_keep_simple_route_shape(self) -> None:
        manifest = load_json("config/pack-manifest.json")
        zero_route_authority = [
            pack["id"]
            for pack in manifest["packs"]
            if pack.get("skill_candidates") and not pack.get("route_authority_candidates")
        ]
        stage_assistant_packs = {
            pack["id"]: pack.get("stage_assistant_candidates")
            for pack in manifest["packs"]
            if pack.get("stage_assistant_candidates") or []
        }
        self.assertEqual([], zero_route_authority)
        self.assertEqual({}, stage_assistant_packs)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm it fails before deletion**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
```

Expected:

```text
FAIL. The failure should mention existing `cloud-modalcom` / `science-quantum` pack rows, existing bundled skill directories, current keyword/routing keys, or stale skills-lock entries.
```

- [ ] **Step 3: Commit only the RED test if execution is split by task**

Run this only if the execution mode is committing each task separately:

```powershell
git add tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py
git commit -m "test: cover cold platform quantum pack deletion"
```

Expected:

```text
Commit succeeds with only the focused RED test staged.
```

## Task 2: Remove Live Config Rows And Skill Directories

**Files:**
- Modify: `config/pack-manifest.json`
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Delete: `bundled/skills/modal-labs`
- Delete: `bundled/skills/modal`
- Delete: `bundled/skills/qiskit`
- Delete: `bundled/skills/cirq`
- Delete: `bundled/skills/pennylane`
- Delete: `bundled/skills/qutip`

- [ ] **Step 1: Remove pack manifest rows**

Edit `config/pack-manifest.json` and delete the full objects whose IDs are:

```text
cloud-modalcom
science-quantum
```

The deleted `science-quantum` object currently contains these exact skill candidates:

```json
[
  "qiskit",
  "cirq",
  "pennylane",
  "qutip"
]
```

The deleted `cloud-modalcom` object currently contains this exact skill candidate:

```json
[
  "modal-labs"
]
```

After the edit, run:

```powershell
python -m json.tool config/pack-manifest.json > $env:TEMP\pack-manifest.json.check
```

Expected:

```text
The command exits 0.
```

- [ ] **Step 2: Remove skill keyword index entries**

Edit `config/skill-keyword-index.json` and remove these skill keys from the top-level `skills` object:

```text
qiskit
cirq
pennylane
qutip
modal
modal-labs
```

Run:

```powershell
python -m json.tool config/skill-keyword-index.json > $env:TEMP\skill-keyword-index.json.check
```

Expected:

```text
The command exits 0.
```

- [ ] **Step 3: Remove skill routing rule entries**

Edit `config/skill-routing-rules.json` and remove these skill keys from the top-level `skills` object:

```text
qiskit
cirq
pennylane
qutip
modal-labs
```

Run:

```powershell
python -m json.tool config/skill-routing-rules.json > $env:TEMP\skill-routing-rules.json.check
```

Expected:

```text
The command exits 0.
```

- [ ] **Step 4: Physically delete the six skill directories with path verification**

Run:

```powershell
$repoRoot = Resolve-Path -LiteralPath .
$skillRoot = Resolve-Path -LiteralPath "bundled\skills"
$deleteDirs = @(
  "bundled\skills\modal-labs",
  "bundled\skills\modal",
  "bundled\skills\qiskit",
  "bundled\skills\cirq",
  "bundled\skills\pennylane",
  "bundled\skills\qutip"
)

foreach ($dir in $deleteDirs) {
  $resolved = Resolve-Path -LiteralPath $dir -ErrorAction Stop
  if (-not $resolved.Path.StartsWith($skillRoot.Path, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to delete outside bundled skills: $($resolved.Path)"
  }
  Remove-Item -LiteralPath $resolved.Path -Recurse -Force
}
```

Expected:

```text
The command exits 0 and removes only the six approved directories under `bundled\skills`.
```

- [ ] **Step 5: Run the focused test and note the expected stale-lock failure**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
```

Expected:

```text
The pack/config/directory assertions pass. If this still fails, the remaining failure should be `config/skills-lock.json` until Task 4 refreshes the lock.
```

## Task 3: Rewrite Existing Route Tests And Probes

**Files:**
- Modify: `tests/runtime_neutral/test_zero_route_authority_second_pass.py`
- Modify: `scripts/verify/probe-scientific-packs.ps1`
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Modify: `scripts/verify/vibe-pack-routing-smoke.ps1`

- [ ] **Step 1: Replace second-pass Modal and quantum positives with absence checks**

Edit `tests/runtime_neutral/test_zero_route_authority_second_pass.py` so the file keeps the `ml-torch-geometric` assertions and removes every positive assertion for `cloud-modalcom`, `modal-labs`, `science-quantum`, `qiskit`, `cirq`, `pennylane`, and `qutip`.

Use this complete replacement:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


REMOVED_SECOND_PASS_PACKS = {"cloud-modalcom", "science-quantum"}
REMOVED_SECOND_PASS_SKILLS = {"modal", "modal-labs", "qiskit", "cirq", "pennylane", "qutip"}


def route(prompt: str, task_type: str = "coding", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_summary(result: dict[str, object]) -> list[tuple[str, str, float, str]]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    rows: list[tuple[str, str, float, str]] = []
    for row in ranked[:8]:
        assert isinstance(row, dict), row
        rows.append(
            (
                str(row.get("pack_id") or ""),
                str(row.get("selected_candidate") or ""),
                float(row.get("score") or 0.0),
                str(row.get("candidate_selection_reason") or row.get("legacy_role") or ""),
            )
        )
    return rows


def load_manifest() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = load_manifest()
    return next(pack for pack in manifest["packs"] if pack["id"] == pack_id)


class ZeroRouteAuthoritySecondPassTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "coding",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def test_removed_second_pass_packs_are_absent(self) -> None:
        manifest = load_manifest()
        pack_ids = {pack["id"] for pack in manifest["packs"]}
        self.assertFalse(pack_ids & REMOVED_SECOND_PASS_PACKS)
        for pack in manifest["packs"]:
            for field in ("skill_candidates", "route_authority_candidates", "stage_assistant_candidates"):
                values = set(pack.get(field) or [])
                self.assertFalse(values & REMOVED_SECOND_PASS_SKILLS, (pack["id"], field))

    def test_ml_torch_geometric_has_one_canonical_owner(self) -> None:
        pack = load_pack("ml-torch-geometric")
        self.assertEqual(["torch-geometric"], pack["skill_candidates"])
        self.assertEqual(["torch-geometric"], pack["route_authority_candidates"])
        self.assertEqual([], pack.get("stage_assistant_candidates") or [])
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["planning"])
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["coding"])
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["research"])

    def test_ml_torch_geometric_routes_alias_keywords_to_canonical_skill(self) -> None:
        self.assert_selected("用 PyTorch Geometric 构建 GCN 图神经网络", "ml-torch-geometric", "torch-geometric")
        self.assert_selected("用 torch_geometric 写 GAT 节点分类模型", "ml-torch-geometric", "torch-geometric")
        self.assert_selected("训练 PyG graph classification pipeline", "ml-torch-geometric", "torch-geometric")

    def test_ml_torch_geometric_does_not_capture_generic_pytorch(self) -> None:
        result = route("用 PyTorch 训练 CNN 图像分类模型，不涉及 graph neural network 或 PyG", task_type="coding")
        self.assertNotEqual(("ml-torch-geometric", "torch-geometric"), selected(result), ranked_summary(result))

    def test_selected_packs_do_not_reintroduce_stage_assistants(self) -> None:
        self.assertEqual([], load_pack("ml-torch-geometric").get("stage_assistant_candidates") or [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Replace science-quantum probe cases with blocked cases**

In `scripts/verify/probe-scientific-packs.ps1`, replace the current `# science-quantum` block with:

```powershell
    # deleted science-quantum regressions
    [pscustomobject]@{
        name = "quantum_qiskit_deleted_pack_blocked"
        group = "deleted-science-quantum"
        prompt = "/vibe 用 Qiskit 创建 Bell state quantum circuit，并在模拟器上运行"
        grade = "M"
        task_type = "coding"
        expected_pack = $null
        expected_skill = $null
        blocked_pack = "science-quantum"
        blocked_skill = "qiskit"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "quantum_pennylane_deleted_pack_blocked"
        group = "deleted-science-quantum"
        prompt = "/vibe 用 PennyLane 做 quantum machine learning 的最小示例（QML）"
        grade = "M"
        task_type = "coding"
        expected_pack = $null
        expected_skill = $null
        blocked_pack = "science-quantum"
        blocked_skill = "pennylane"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "quantum_chemistry_no_deleted_quantum_pack"
        group = "deleted-science-quantum"
        prompt = "/vibe 调研 quantum chemistry 论文和 pKa 预测，不写量子电路"
        grade = "M"
        task_type = "research"
        expected_pack = $null
        expected_skill = $null
        blocked_pack = "science-quantum"
        blocked_skill = "qiskit"
        requested_skill = $null
    },
```

Run:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
```

Expected:

```text
The report is generated. The `deleted-science-quantum` rows show blocked pack or blocked skill checks as OK.
```

- [ ] **Step 3: Add deletion regressions to the pack regression matrix**

In `scripts/verify/vibe-pack-regression-matrix.ps1`, add these cases near the existing hard-removal and low-signal boundary cases:

```powershell
    [pscustomobject]@{ Name = "cloud modalcom removed generic gpu"; Prompt = "把 Python 任务部署到云端 GPU，不指定 Modal，用普通容器也可以"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "cloud modalcom removed explicit modal"; Prompt = "用 Modal.com 部署 serverless GPU Python function 和 batch job"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "science quantum removed qiskit"; Prompt = "用 Qiskit 创建 Bell state quantum circuit 并 transpile"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-quantum"; BlockedSkill = "qiskit"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
    [pscustomobject]@{ Name = "science quantum removed chemistry false positive"; Prompt = "调研 quantum chemistry 论文和 pKa 预测，不写量子电路"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-quantum"; BlockedSkill = "qiskit"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
```

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected:

```text
The four new cases pass their `BlockedPack` and `BlockedSkill` assertions.
```

- [ ] **Step 4: Add deletion regressions to the skill-index routing audit**

In `scripts/verify/vibe-skill-index-routing-audit.ps1`, add these cases near the other hard-removal and boundary cases:

```powershell
    [pscustomobject]@{ Name = "deleted modal generic gpu"; Prompt = "把 Python 任务部署到云端 GPU，不指定 Modal，用普通容器也可以"; Grade = "M"; TaskType = "coding"; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs" },
    [pscustomobject]@{ Name = "deleted modal explicit modal"; Prompt = "用 Modal.com 部署 serverless GPU Python function 和 batch job"; Grade = "M"; TaskType = "coding"; BlockedPack = "cloud-modalcom"; BlockedSkill = "modal-labs" },
    [pscustomobject]@{ Name = "deleted quantum qiskit"; Prompt = "用 Qiskit 创建 Bell state quantum circuit 并 transpile"; Grade = "M"; TaskType = "coding"; BlockedPack = "science-quantum"; BlockedSkill = "qiskit" },
    [pscustomobject]@{ Name = "deleted quantum chemistry"; Prompt = "调研 quantum chemistry 论文和 pKa 预测，不写量子电路"; Grade = "M"; TaskType = "research"; BlockedPack = "science-quantum"; BlockedSkill = "qiskit" },
```

Run:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected:

```text
The four new cases pass their blocked pack and blocked skill assertions.
```

- [ ] **Step 5: Add absence checks to pack routing smoke**

In `scripts/verify/vibe-pack-routing-smoke.ps1`, add this after `$requiredPackIds` and `$packIds` are initialized:

```powershell
$deletedPackIds = @(
    "cloud-modalcom",
    "science-quantum"
)

foreach ($id in $deletedPackIds) {
    $results += Assert-True -Condition ($packIds -notcontains $id) -Message "deleted pack '$id' is absent"
}
```

Add this after `$skillKeywordIndex` and `$routingRules` are loaded:

```powershell
$deletedSkillIds = @(
    "modal",
    "modal-labs",
    "qiskit",
    "cirq",
    "pennylane",
    "qutip"
)

foreach ($skill in $deletedSkillIds) {
    $results += Assert-True -Condition (-not ($skillKeywordIndex.skills.PSObject.Properties.Name -contains $skill)) -Message "deleted skill '$skill' absent from skill keyword index"
    $results += Assert-True -Condition (-not ($routingRules.skills.PSObject.Properties.Name -contains $skill)) -Message "deleted skill '$skill' absent from routing rules"
}
```

Add this after `$topLevelSkillNames` is built:

```powershell
foreach ($skill in $deletedSkillIds) {
    $results += Assert-True -Condition ($topLevelSkillNames -notcontains $skill) -Message "deleted skill directory '$skill' is absent"
}
```

Run:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected:

```text
The new deleted-pack, deleted-skill-key, and deleted-directory assertions pass.
```

## Task 4: Refresh Lock And Close Focused Tests

**Files:**
- Modify: `config/skills-lock.json`

- [ ] **Step 1: Regenerate skills lock**

Run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
```

Expected:

```text
The command exits 0 and rewrites `config/skills-lock.json` without `modal`, `modal-labs`, `qiskit`, `cirq`, `pennylane`, or `qutip` entries.
```

- [ ] **Step 2: Run the offline skills gate**

Run:

```powershell
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected:

```text
The command exits 0. Deleted skill directories are not reported as missing because lock/config surfaces no longer expect them.
```

- [ ] **Step 3: Run focused Python tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
```

Expected:

```text
Both pytest commands exit 0.
```

## Task 5: Full Verification

**Files:**
- Verify: `tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py`
- Verify: `tests/runtime_neutral/test_zero_route_authority_second_pass.py`
- Verify: `tests/runtime_neutral/test_zero_route_authority_third_pass.py`
- Verify: `scripts/verify/probe-scientific-packs.ps1`
- Verify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Verify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Verify: `scripts/verify/vibe-pack-routing-smoke.ps1`
- Verify: `scripts/verify/vibe-generate-skills-lock.ps1`
- Verify: `scripts/verify/vibe-offline-skills-gate.ps1`
- Verify: `scripts/verify/vibe-config-parity-gate.ps1`

- [ ] **Step 1: Run the complete verification sequence**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

Expected:

```text
Every command exits 0.
The probe script writes its report and summary paths.
`git diff --check` exits 0.
```

- [ ] **Step 2: Search for remaining live positive references**

Run:

```powershell
rg -n "cloud-modalcom|modal-labs|science-quantum|qiskit|cirq|pennylane|qutip|bundled/skills/modal|bundled\\skills\\modal" config tests scripts -S
```

Expected:

```text
Matches are limited to deletion tests, blocked-pack route regressions, blocked-skill route regressions, or historical non-live prompts used to prove absence. There are no live config entries, lock entries, positive route expectations, or bundled-skill paths that keep the deleted skills active.
```

- [ ] **Step 3: Inspect the diff**

Run:

```powershell
git status --short --branch
git diff --stat
git diff -- config/pack-manifest.json config/skill-keyword-index.json config/skill-routing-rules.json
git diff -- tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py tests/runtime_neutral/test_zero_route_authority_second_pass.py
git diff -- scripts/verify/probe-scientific-packs.ps1 scripts/verify/vibe-pack-regression-matrix.ps1 scripts/verify/vibe-skill-index-routing-audit.ps1 scripts/verify/vibe-pack-routing-smoke.ps1
```

Expected:

```text
The diff contains only the approved pack deletion, approved skill directory deletion, focused absence tests, rewritten probes, lock refresh, and governance note.
```

## Task 6: Governance Note And Commit

**Files:**
- Create: `docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md`
- Commit: all intended implementation files and deleted directories

- [ ] **Step 1: Create the governance note after verification**

Create `docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md` with this structure and the actual command outcomes from Task 5:

````markdown
# Cold Platform And Quantum Pack Deletion

Date: 2026-04-30

## Decision

`cloud-modalcom` and `science-quantum` were removed from live Vibe-Skills routing.

This was a hard removal pass, not a trigger-narrowing pass. The goal was to reduce cold, specialized, high-false-positive route surfaces while keeping the public six-stage Vibe runtime unchanged:

```text
skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
```

The simplified skill-use model remains:

```text
candidate skill -> selected skill -> used / unused
```

No advisory experts, consultation state, helper experts, primary/secondary skill hierarchy, or stage assistants were added.

## Deleted Packs

| Pack | Removed route owners | Reason |
| --- | --- | --- |
| `cloud-modalcom` | `modal-labs` | Cold vendor-specific Modal.com surface; broad GPU/batch keywords created false-positive risk for generic cloud execution prompts. |
| `science-quantum` | `qiskit`, `cirq`, `pennylane`, `qutip` | Cold quantum-computing surface with high boundary-maintenance cost and false-positive risk around quantum chemistry, pKa, DFT, and molecular simulation prompts. |

## Deleted Skill Directories

- `bundled/skills/modal-labs`
- `bundled/skills/modal`
- `bundled/skills/qiskit`
- `bundled/skills/cirq`
- `bundled/skills/pennylane`
- `bundled/skills/qutip`

## Routing Contract After Deletion

| Prompt class | New behavior |
| --- | --- |
| Explicit Modal deployment | Does not select `cloud-modalcom` or Modal skills. It may route to an existing general owner only when that owner clearly matches, otherwise confirmation/fallback is acceptable. |
| Generic cloud GPU or batch job | Does not select `cloud-modalcom`, `modal`, or `modal-labs`. |
| Frontend modal dialog | Remains unrelated to Modal.com routing. |
| Explicit Qiskit/Cirq/PennyLane/QuTiP prompt | Does not select `science-quantum` or the deleted quantum skills. |
| Quantum chemistry / pKa / DFT prompt | Does not select `science-quantum` or `qiskit`; Rowan-specific quantum chemistry still routes to `science-rowan-chemistry / rowan`. |

## Verification

Commands run:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

All commands above passed in this implementation run.

## Evidence Boundary

This change proves route/config/docs/tests cleanup only. It does not prove that any skill was materially used in a real task.

Material skill-use evidence still requires task artifacts such as `specialist-execution.json`, `phase-execute.json`, source code, generated outputs, metrics, figures, paper sources, or final PDFs from an actual governed run.
````

Replace the sentence `All commands above passed in this implementation run.` with a more specific pass-count line only if the commands print pass counts in the terminal. Do not invent pass counts.

- [ ] **Step 2: Stage the intended implementation files**

Run:

```powershell
git add config/pack-manifest.json `
  config/skill-keyword-index.json `
  config/skill-routing-rules.json `
  config/skills-lock.json `
  tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py `
  tests/runtime_neutral/test_zero_route_authority_second_pass.py `
  scripts/verify/probe-scientific-packs.ps1 `
  scripts/verify/vibe-pack-regression-matrix.ps1 `
  scripts/verify/vibe-skill-index-routing-audit.ps1 `
  scripts/verify/vibe-pack-routing-smoke.ps1 `
  docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md
git add -A -- bundled/skills/modal-labs bundled/skills/modal bundled/skills/qiskit bundled/skills/cirq bundled/skills/pennylane bundled/skills/qutip
```

Expected:

```text
Only the approved config, test, script, governance, lock, and deleted skill-directory paths are staged.
```

- [ ] **Step 3: Commit the implementation**

Run:

```powershell
git commit -m "fix: remove cold platform and quantum packs"
```

Expected:

```text
Commit succeeds.
```

- [ ] **Step 4: Final status check**

Run:

```powershell
git status --short --branch
git log -5 --oneline
```

Expected:

```text
Working tree is clean.
The implementation commit is visible above the plan and design commits.
```

## Self-Review Notes

- Spec coverage: The plan removes `cloud-modalcom` and `science-quantum`, deletes all six approved skill directories, removes deleted skill keys from routing configs and lock, rewrites Modal/quantum positive tests into absence tests, adds negative route regressions, and records governance.
- Scope control: The plan does not create a replacement Modal, cloud GPU, generic quantum, or quantum chemistry owner.
- Runtime boundary: The plan does not change `skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup`.
- Simplified routing: The plan does not add advisory experts, consultation state, helper experts, primary/secondary skills, or stage assistants.
- Evidence boundary: The plan explicitly separates route/config cleanup from actual material skill use in a governed task.
