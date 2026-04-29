# Final Stage Assistant Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the last active stage-assistant routing semantics from `code-quality` and `data-ml`, leaving only direct candidate selection and used/unused skill status.

**Architecture:** Add runtime-neutral route regression tests first, then update audit expectations, manifest role lists, keyword/routing metadata, skill text, governance notes, and lock files. `requesting-code-review` becomes a direct route owner for review-request preparation. `preprocessing-data-with-automated-pipelines` is retained as a direct route owner because it has assets, references, scripts, and a distinct preprocessing-pipeline task boundary.

**Tech Stack:** Python `unittest`, `vgo_runtime.router_contract_runtime.route_prompt`, JSON config files, bundled `SKILL.md` files, PowerShell verification gates.

---

## File Structure

- Create: `tests/runtime_neutral/test_final_stage_assistant_removal.py`
  - Owns the new behavior contract: no non-empty `stage_assistant_candidates`, direct routing for review-request preparation, direct routing for preprocessing pipelines, and no stage-assistant wording in retained target skill docs.
- Modify: `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`
  - Updates the code-quality problem map target from "stage assistant" to direct route authority.
- Modify: `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`
  - Updates the audit tests to match the new direct route-owner contract.
- Modify: `packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py`
  - Updates the data-ml problem map target from "stage assistant" to direct route authority.
- Modify: `tests/runtime_neutral/test_ml_skills_pruning_audit.py`
  - Updates data-ml audit tests to expect preprocessing as a retained direct owner.
- Modify: `tests/runtime_neutral/test_router_bridge.py`
  - Replaces the legacy preprocessing stage-role assertion with a direct route-authority assertion.
- Modify: `config/pack-manifest.json`
  - Adds `requesting-code-review` and `preprocessing-data-with-automated-pipelines` to direct route authority lists and clears both stage assistant lists.
- Modify: `config/skill-keyword-index.json`
  - Adds or sharpens keywords for review-request preparation and preprocessing-pipeline ownership.
- Modify: `config/skill-routing-rules.json`
  - Adds positive and negative routing terms that separate review request vs actual review vs review feedback, and preprocessing vs full ML workflow vs leakage audit.
- Modify: `bundled/skills/requesting-code-review/SKILL.md`
  - Removes historical stage-assistant wording and states the direct task boundary.
- Modify: `bundled/skills/preprocessing-data-with-automated-pipelines/SKILL.md`
  - Removes historical stage-assistant wording and states the direct task boundary.
- Create: `docs/governance/final-stage-assistant-removal-2026-04-29.md`
  - Records before/after counts, retained route owners, probes, and deletion deferral for preprocessing assets.
- Modify: `config/skills-lock.json`
  - Refresh after config and skill text changes.

---

### Task 1: Add Failing Runtime-Neutral Regression Tests

**Files:**
- Create: `tests/runtime_neutral/test_final_stage_assistant_removal.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/runtime_neutral/test_final_stage_assistant_removal.py` with this complete content:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


def load_manifest() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = load_manifest()
    return next(pack for pack in manifest["packs"] if pack["id"] == pack_id)


def route(prompt: str, task_type: str = "research", grade: str = "L") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def pack_row(result: dict[str, object], pack_id: str) -> dict[str, object]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    row = next((item for item in ranked if isinstance(item, dict) and item.get("pack_id") == pack_id), None)
    assert isinstance(row, dict), result
    return row


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
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


class FinalStageAssistantRemovalTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> dict[str, object]:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))
        return result

    def test_manifest_has_no_non_empty_stage_assistant_lists(self) -> None:
        manifest = load_manifest()
        non_empty = {
            pack["id"]: pack.get("stage_assistant_candidates")
            for pack in manifest["packs"]
            if pack.get("stage_assistant_candidates")
        }
        self.assertEqual({}, non_empty)

    def test_code_quality_manifest_makes_requesting_review_direct_owner(self) -> None:
        pack = load_pack("code-quality")
        expected = [
            "code-reviewer",
            "deslop",
            "generating-test-reports",
            "receiving-code-review",
            "requesting-code-review",
            "security-reviewer",
            "systematic-debugging",
            "tdd-guide",
            "verification-before-completion",
            "windows-hook-debugging",
        ]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertEqual(expected, pack["route_authority_candidates"])
        self.assertEqual([], pack["stage_assistant_candidates"])

    def test_review_request_preparation_routes_to_requesting_code_review(self) -> None:
        result = self.assert_selected(
            "request code review before merge：请整理提交评审材料，准备 code review request",
            "code-quality",
            "requesting-code-review",
            task_type="review",
        )
        row = pack_row(result, "code-quality")
        ranking_by_skill = {item["skill"]: item for item in row["candidate_ranking"]}
        self.assertEqual("route_authority", ranking_by_skill["requesting-code-review"]["legacy_role"])
        self.assertEqual([], row["stage_assistant_candidates"])

    def test_actual_code_review_stays_with_code_reviewer(self) -> None:
        self.assert_selected(
            "请做 code review，审查这次代码改动 code change 有没有 bug risk 和回归风险",
            "code-quality",
            "code-reviewer",
            task_type="review",
        )

    def test_received_review_feedback_routes_to_receiving_code_review(self) -> None:
        self.assert_selected(
            "我收到了 CodeRabbit review comments 和评审意见，请逐条判断并处理",
            "code-quality",
            "receiving-code-review",
            task_type="review",
        )

    def test_data_ml_manifest_makes_preprocessing_direct_owner(self) -> None:
        pack = load_pack("data-ml")
        expected = [
            "aeon",
            "evaluating-machine-learning-models",
            "exploratory-data-analysis",
            "ml-data-leakage-guard",
            "ml-pipeline-workflow",
            "preprocessing-data-with-automated-pipelines",
            "scikit-learn",
            "shap",
        ]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertEqual(expected, pack["route_authority_candidates"])
        self.assertEqual([], pack["stage_assistant_candidates"])

    def test_preprocessing_pipeline_routes_directly_and_has_no_stage_metadata(self) -> None:
        result = self.assert_selected(
            "机器学习 data preprocessing pipeline：清洗数据、feature encoding、standardize data、validate input data，输出可复用预处理流水线",
            "data-ml",
            "preprocessing-data-with-automated-pipelines",
            task_type="coding",
        )
        row = pack_row(result, "data-ml")
        ranking_by_skill = {item["skill"]: item for item in row["candidate_ranking"]}
        self.assertEqual(
            "route_authority",
            ranking_by_skill["preprocessing-data-with-automated-pipelines"]["legacy_role"],
        )
        self.assertEqual([], row["stage_assistant_candidates"])

    def test_broad_ml_workflow_does_not_route_to_preprocessing(self) -> None:
        result = self.assert_selected(
            "我需要一个完整机器学习建模流程，包括训练、评估、模型比较和结果汇报",
            "data-ml",
            "ml-pipeline-workflow",
            task_type="planning",
        )
        self.assertNotEqual("preprocessing-data-with-automated-pipelines", selected(result)[1])

    def test_data_leakage_stays_with_guard(self) -> None:
        self.assert_selected(
            "请检查训练集和测试集是否发生数据泄漏，尤其是 fit before split 和 prediction time 问题",
            "data-ml",
            "ml-data-leakage-guard",
            task_type="review",
        )

    def test_retained_target_skill_docs_do_not_describe_stage_assistant_roles(self) -> None:
        forbidden = [
            "stage assistant",
            "stage-assistant",
            "阶段助手",
            "辅助专家",
            "次技能",
        ]
        for skill_id in [
            "requesting-code-review",
            "preprocessing-data-with-automated-pipelines",
        ]:
            path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(skill_id=skill_id):
                for phrase in forbidden:
                    self.assertNotIn(phrase.lower(), text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and confirm they fail on current behavior**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py -q
```

Expected now: FAIL. The failures should include non-empty stage assistant lists for `code-quality` and `data-ml`, `requesting-code-review` not being direct route authority, and old stage-assistant wording in the two target `SKILL.md` files.

- [ ] **Step 3: Commit the failing test**

Run:

```powershell
git add tests/runtime_neutral/test_final_stage_assistant_removal.py
git commit -m "test: cover final stage assistant removal"
```

---

### Task 2: Update Code-Quality Audit Contract

**Files:**
- Modify: `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`
- Modify: `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`

- [ ] **Step 1: Update code-quality target constants**

In `packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py`, replace the existing `TARGET_ROUTE_AUTHORITIES` and `TARGET_STAGE_ASSISTANTS` blocks with:

```python
TARGET_ROUTE_AUTHORITIES = [
    "code-reviewer",
    "deslop",
    "generating-test-reports",
    "receiving-code-review",
    "requesting-code-review",
    "security-reviewer",
    "systematic-debugging",
    "tdd-guide",
    "verification-before-completion",
    "windows-hook-debugging",
]

TARGET_STAGE_ASSISTANTS: list[str] = []
```

- [ ] **Step 2: Update the `requesting-code-review` decision**

In the same file, replace the `CODE_QUALITY_DECISIONS["requesting-code-review"]` dictionary with:

```python
    "requesting-code-review": {
        "problem_ids": ["review_request_preparation"],
        "primary_problem_id": "review_request_preparation",
        "target_role": "keep-route-authority",
        "target_owner": "",
        "overlap_with": "code-reviewer; receiving-code-review",
        "routing_change": "keep as direct route authority for preparing review requests",
        "delete_allowed_now": False,
        "risk_level": "low",
        "rationale": "准备发起 code review、整理 review 请求材料是明确任务，不再作为阶段助手表达。",
    },
```

- [ ] **Step 3: Update code-quality audit tests**

In `tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py`, change the assertion in `test_problem_map_assigns_target_roles` from:

```python
self.assertEqual("stage-assistant", rows["requesting-code-review"].target_role)
```

to:

```python
self.assertEqual("keep-route-authority", rows["requesting-code-review"].target_role)
self.assertEqual("review_request_preparation", rows["requesting-code-review"].primary_problem_id)
```

In `test_problem_map_keeps_removed_decisions_visible_after_consolidation`, replace the manifest fixture route/stage entries with:

```python
                        "route_authority_candidates": target_candidates,
                        "stage_assistant_candidates": [],
```

Add this assertion after `artifact = audit_code_quality_problem_map(self.root)` in `test_artifact_writer_outputs_json_csv_and_markdown`:

```python
self.assertEqual(0, artifact.to_dict()["summary"]["target_stage_assistant_count"])
```

- [ ] **Step 4: Run the code-quality audit tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the code-quality audit update**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py
git commit -m "test: update code quality direct review request contract"
```

---

### Task 3: Update Data-ML Audit Contract

**Files:**
- Modify: `packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py`
- Modify: `tests/runtime_neutral/test_ml_skills_pruning_audit.py`

- [ ] **Step 1: Update the preprocessing decision**

In `packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py`, replace the `DATA_ML_PROBLEM_DECISIONS["preprocessing-data-with-automated-pipelines"]` dictionary with:

```python
    "preprocessing-data-with-automated-pipelines": {
        "problem_ids": ["ml_preprocessing_features"],
        "primary_problem_id": "ml_preprocessing_features",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "engineering-features-for-machine-learning; scikit-learn; ml-pipeline-workflow",
        "routing_change": "keep in data-ml as direct preprocessing-pipeline route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "清洗、编码、缩放、转换和验证可形成独立的可复用预处理流水线任务。",
    },
```

- [ ] **Step 2: Update stale preprocessing wording in overlapping decisions**

In the same file, replace this `engineering-features-for-machine-learning` rationale:

```python
"特征工程和预处理是同一阶段问题，应集中到一个阶段助手。"
```

with:

```python
"特征工程和预处理是同一类输入准备问题，应集中到直接预处理流水线 owner。"
```

- [ ] **Step 3: Update data-ml audit tests**

In `tests/runtime_neutral/test_ml_skills_pruning_audit.py`, add these assertions to `test_data_ml_problem_map_marks_targets_for_consolidation` after the `shap` assertions:

```python
self.assertEqual("keep", rows["preprocessing-data-with-automated-pipelines"].target_role)
self.assertEqual(
    "ml_preprocessing_features",
    rows["preprocessing-data-with-automated-pipelines"].primary_problem_id,
)
```

Add this assertion after `artifact = audit_data_ml_problem_map(self.root)` in `test_problem_artifact_writer_outputs_json_csv_and_markdown`:

```python
self.assertEqual(0, artifact.to_dict()["summary"]["target_stage_assistant_count"])
```

- [ ] **Step 4: Run the data-ml audit tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_ml_skills_pruning_audit.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the data-ml audit update**

Run:

```powershell
git add packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py tests/runtime_neutral/test_ml_skills_pruning_audit.py
git commit -m "test: update data ml preprocessing direct owner contract"
```

---

### Task 4: Update Pack Manifest And Routing Metadata

**Files:**
- Modify: `config/pack-manifest.json`
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Modify: `tests/runtime_neutral/test_router_bridge.py`

- [ ] **Step 1: Update `code-quality` role lists in `config/pack-manifest.json`**

In the `code-quality` pack, set:

```json
"route_authority_candidates": [
  "code-reviewer",
  "deslop",
  "generating-test-reports",
  "receiving-code-review",
  "requesting-code-review",
  "security-reviewer",
  "systematic-debugging",
  "tdd-guide",
  "verification-before-completion",
  "windows-hook-debugging"
],
"stage_assistant_candidates": []
```

Add these strings to `code-quality.trigger_keywords` if they are not already present:

```json
[
  "request review",
  "code review request",
  "before merge",
  "code change",
  "review code change",
  "代码改动",
  "代码变更",
  "发起代码审查",
  "请求代码审查",
  "提交评审"
]
```

- [ ] **Step 2: Update `data-ml` role lists in `config/pack-manifest.json`**

In the `data-ml` pack, set:

```json
"route_authority_candidates": [
  "aeon",
  "evaluating-machine-learning-models",
  "exploratory-data-analysis",
  "ml-data-leakage-guard",
  "ml-pipeline-workflow",
  "preprocessing-data-with-automated-pipelines",
  "scikit-learn",
  "shap"
],
"stage_assistant_candidates": []
```

Add these strings to `data-ml.trigger_keywords` if they are not already present:

```json
[
  "data preprocessing",
  "preprocessing pipeline",
  "data cleaning pipeline",
  "feature encoding",
  "standardize data",
  "validate input data",
  "数据预处理",
  "数据清洗",
  "预处理流水线",
  "特征编码",
  "数据验证"
]
```

- [ ] **Step 3: Update `config/skill-keyword-index.json`**

Set the `requesting-code-review` entry to:

```json
"requesting-code-review": {
  "keywords": [
    "request review",
    "request code review",
    "code review request",
    "prepare review request",
    "before merge",
    "pre-merge review",
    "提交评审",
    "发起代码审查",
    "请求代码审查",
    "准备代码审查",
    "整理 review 请求材料",
    "整理review请求材料"
  ]
}
```

Set the `preprocessing-data-with-automated-pipelines.keywords` list to:

```json
[
  "preprocess data",
  "data preprocessing",
  "preprocessing pipeline",
  "data cleaning pipeline",
  "etl pipeline",
  "data transformation",
  "feature encoding",
  "feature preprocessing",
  "standardize data",
  "normalize data",
  "validate input data",
  "reusable preprocessing pipeline",
  "数据预处理",
  "清洗数据",
  "数据清洗",
  "预处理流水线",
  "特征编码",
  "ETL流水线",
  "数据转换",
  "数据验证",
  "可复用预处理流水线"
]
```

- [ ] **Step 4: Update `requesting-code-review` and review-boundary rules**

In `config/skill-routing-rules.json`, set `requesting-code-review` to:

```json
"requesting-code-review": {
  "task_allow": [
    "review"
  ],
  "positive_keywords": [
    "request review",
    "request code review",
    "code review request",
    "prepare review request",
    "before merge",
    "pre-merge review",
    "提交评审",
    "发起代码审查",
    "请求代码审查",
    "准备代码审查",
    "整理 review 请求材料",
    "整理review请求材料"
  ],
  "negative_keywords": [
    "implement feature",
    "fresh code review",
    "review this change",
    "actual code review",
    "security audit",
    "review feedback",
    "review comments",
    "评审反馈",
    "评审意见",
    "逐条判断",
    "审查这次代码改动"
  ],
  "equivalent_group": null,
  "canonical_for_task": []
}
```

Add these strings to `code-reviewer.positive_keywords`:

```json
[
  "review code change",
  "code change",
  "代码改动",
  "代码变更",
  "审查这次代码改动"
]
```

Add these strings to `code-reviewer.negative_keywords`:

```json
[
  "request code review",
  "code review request",
  "prepare review request",
  "提交评审",
  "发起代码审查",
  "请求代码审查",
  "整理 review 请求材料"
]
```

Add these strings to `receiving-code-review.positive_keywords`:

```json
[
  "received review feedback",
  "received review comments",
  "收到 review comments",
  "收到 CodeRabbit",
  "收到了 CodeRabbit",
  "收到了 code review 意见"
]
```

- [ ] **Step 5: Update preprocessing and ML-boundary rules**

In `config/skill-routing-rules.json`, set `preprocessing-data-with-automated-pipelines` to:

```json
"preprocessing-data-with-automated-pipelines": {
  "task_allow": [
    "coding",
    "research",
    "review"
  ],
  "positive_keywords": [
    "preprocess data",
    "data preprocessing",
    "preprocessing pipeline",
    "data cleaning pipeline",
    "etl pipeline",
    "data transformation",
    "feature encoding",
    "feature preprocessing",
    "standardize data",
    "normalize data",
    "validate input data",
    "reusable preprocessing pipeline",
    "数据预处理",
    "清洗数据",
    "数据清洗",
    "预处理流水线",
    "特征编码",
    "ETL流水线",
    "数据转换",
    "数据验证",
    "可复用预处理流水线"
  ],
  "negative_keywords": [
    "data leakage",
    "fit before split",
    "prediction time",
    "批判式讨论",
    "challenge my assumptions",
    "train model",
    "model evaluation",
    "full machine learning workflow",
    "完整机器学习建模流程",
    "训练、评估",
    "publication figure",
    "research report"
  ],
  "equivalent_group": "ml-preprocessing",
  "canonical_for_task": []
}
```

Add these strings to `ml-pipeline-workflow.positive_keywords`:

```json
[
  "完整机器学习建模流程",
  "模型比较",
  "结果汇报"
]
```

- [ ] **Step 6: Update the legacy router bridge test**

In `tests/runtime_neutral/test_router_bridge.py`, replace `test_preprocessing_pipeline_keeps_legacy_stage_role_while_unifying_candidates` with:

```python
    def test_preprocessing_pipeline_routes_as_direct_data_ml_owner(self) -> None:
        result = run_bridge(
            "机器学习 data preprocessing pipeline：清洗数据、feature encoding、standardize data、validate input data，输出可复用预处理流水线",
            "L",
            "coding",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("preprocessing-data-with-automated-pipelines", result["selected"]["skill"])

        data_ml_row = next(row for row in result["ranked"] if row["pack_id"] == "data-ml")
        ranking_by_skill = {row["skill"]: row for row in data_ml_row["candidate_ranking"]}
        self.assertEqual(
            "route_authority",
            ranking_by_skill["preprocessing-data-with-automated-pipelines"]["legacy_role"],
        )
        self.assertEqual([], data_ml_row["stage_assistant_candidates"])
```

- [ ] **Step 7: Run the new route tests and targeted router bridge test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py tests/runtime_neutral/test_router_bridge.py::RouterBridgeTests::test_preprocessing_pipeline_routes_as_direct_data_ml_owner -q
```

Expected: PASS.

- [ ] **Step 8: Commit routing config and bridge test updates**

Run:

```powershell
git add config/pack-manifest.json config/skill-keyword-index.json config/skill-routing-rules.json tests/runtime_neutral/test_router_bridge.py
git commit -m "fix: remove final stage assistant route roles"
```

---

### Task 5: Update Target Skill Text

**Files:**
- Modify: `bundled/skills/requesting-code-review/SKILL.md`
- Modify: `bundled/skills/preprocessing-data-with-automated-pipelines/SKILL.md`

- [ ] **Step 1: Replace `requesting-code-review` frontmatter and boundary text**

In `bundled/skills/requesting-code-review/SKILL.md`, replace the frontmatter with:

```markdown
---
name: requesting-code-review
description: Prepare and request a code review after implementation or before merge by assembling scope, requirements, git range, and reviewer instructions.
---
```

Replace the `## Routing Boundary` section with:

```markdown
## Routing Boundary

Use this skill when the user needs to prepare or request a code review.

This skill owns the request package: implementation summary, requirements reference, base/head git range, reviewer prompt, and response handling checklist.

Use `code-reviewer` for the actual review findings.

Use `receiving-code-review` when review feedback already exists and must be evaluated or applied.
```

- [ ] **Step 2: Remove stale stage wording from `requesting-code-review`**

In the same file, remove the sentence:

```markdown
This is a stage assistant. It helps a workflow decide when to request review, while `code-reviewer` remains the primary owner for actually reviewing code.
```

Also replace the first body sentence:

```markdown
Dispatch superpowers:code-reviewer subagent to catch issues before they cascade.
```

with:

```markdown
Prepare a complete review request so the reviewer can evaluate the exact change against the intended requirements.
```

- [ ] **Step 3: Replace preprocessing frontmatter and positioning**

In `bundled/skills/preprocessing-data-with-automated-pipelines/SKILL.md`, replace the frontmatter with:

```markdown
---
name: preprocessing-data-with-automated-pipelines
description: |
  Design and implement repeatable preprocessing pipelines for cleaning, encoding, transforming, and validating ML input data.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(cmd:*)
version: 1.0.0
author: Jeremy Longshore <jeremy@intentsolutions.io>
license: MIT
---
```

Replace the `## Positioning` section with:

```markdown
## Positioning

Use this skill as the direct owner for ML input-preparation pipelines.

It covers preprocessing-heavy tasks where the requested deliverable is a repeatable pipeline for cleaning, encoding, transforming, and validating input data.
```

- [ ] **Step 4: Remove stale stage wording from preprocessing**

In the same file, remove these sentences:

```markdown
In governed ML routing, treat this skill as a stage assistant.
It is for preprocessing-heavy execution after the pack owner is chosen.
```

Replace the last `Typical Outputs` bullet:

```markdown
- Handoff notes for leakage review, training, or evaluation
```

with:

```markdown
- Notes that identify where leakage review, training, or evaluation should be run next
```

- [ ] **Step 5: Run the doc wording assertion**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py::FinalStageAssistantRemovalTests::test_retained_target_skill_docs_do_not_describe_stage_assistant_roles -q
```

Expected: PASS.

- [ ] **Step 6: Commit skill text updates**

Run:

```powershell
git add bundled/skills/requesting-code-review/SKILL.md bundled/skills/preprocessing-data-with-automated-pipelines/SKILL.md
git commit -m "docs: clarify direct review and preprocessing skill boundaries"
```

---

### Task 6: Add Governance Note

**Files:**
- Create: `docs/governance/final-stage-assistant-removal-2026-04-29.md`

- [ ] **Step 1: Create the governance note**

Create `docs/governance/final-stage-assistant-removal-2026-04-29.md` with:

```markdown
# Final Stage Assistant Removal

Date: 2026-04-29

## Scope

This cleanup removes the last active `stage_assistant_candidates` semantics from pack routing.

The public six-stage Vibe runtime is unchanged. The skill usage model is simplified to:

```text
candidate skill -> selected skill -> used / unused
```

## Before And After

| pack | before route authority | before stage assistants | after route authority | after stage assistants |
| --- | ---: | ---: | ---: | ---: |
| `code-quality` | 9 | 1 | 10 | 0 |
| `data-ml` | 7 | 1 | 8 | 0 |

## Direct Owners Added

| skill | direct task boundary | not for |
| --- | --- | --- |
| `requesting-code-review` | Prepare and request a code review after implementation or before merge. | Actual review findings; review feedback repair. |
| `preprocessing-data-with-automated-pipelines` | Build repeatable ML data preprocessing pipelines for cleaning, encoding, transforming, and validating input data. | Full ML workflow planning; general model training; leakage auditing. |

## Boundary Probes

| prompt class | expected owner |
| --- | --- |
| review request preparation | `code-quality/requesting-code-review` |
| actual code review | `code-quality/code-reviewer` |
| received review feedback | `code-quality/receiving-code-review` |
| preprocessing pipeline | `data-ml/preprocessing-data-with-automated-pipelines` |
| broad ML workflow | `data-ml/ml-pipeline-workflow` |
| data leakage audit | `data-ml/ml-data-leakage-guard` |

## Deletion Decision

`preprocessing-data-with-automated-pipelines` is not physically deleted in this cleanup. The directory contains assets, references, and scripts, and the retained direct task boundary is distinct.

## Verification

Required focused tests:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py -q
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_ml_skills_pruning_audit.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py::RouterBridgeTests::test_preprocessing_pipeline_routes_as_direct_data_ml_owner -q
```

Required gates:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
```
```

- [ ] **Step 2: Commit the governance note**

Run:

```powershell
git add docs/governance/final-stage-assistant-removal-2026-04-29.md
git commit -m "docs: record final stage assistant removal"
```

---

### Task 7: Refresh Lock And Run Verification Gates

**Files:**
- Modify: `config/skills-lock.json`

- [ ] **Step 1: Refresh skills lock**

Run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
```

Expected: `config/skills-lock.json` is updated if skill/config hashes changed.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py -q
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_ml_skills_pruning_audit.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py::RouterBridgeTests::test_preprocessing_pipeline_routes_as_direct_data_ml_owner -q
```

Expected: all commands PASS.

- [ ] **Step 3: Run routing and config gates**

Run:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
```

Expected: all commands PASS.

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected changed files are limited to the files listed in this plan.

- [ ] **Step 5: Commit lock refresh and verification closure**

Run:

```powershell
git add config/skills-lock.json
git commit -m "chore: refresh skills lock after stage assistant removal"
```

- [ ] **Step 6: Capture final status**

Run:

```powershell
git status --short --branch
git log -5 --oneline
```

Expected: clean working tree, branch ahead count increased by the implementation commits.

