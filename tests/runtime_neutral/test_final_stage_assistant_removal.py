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

    def test_manifest_has_no_legacy_candidate_fields(self) -> None:
        manifest = load_manifest()
        for pack in manifest["packs"]:
            self.assertNotIn("route_authority_candidates", pack)
            self.assertNotIn("stage_assistant_candidates", pack)

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
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_review_request_preparation_routes_to_requesting_code_review(self) -> None:
        result = self.assert_selected(
            "request code review before merge：请整理提交评审材料，准备 code review request",
            "code-quality",
            "requesting-code-review",
            task_type="review",
        )
        row = pack_row(result, "code-quality")
        ranking_by_skill = {item["skill"]: item for item in row["candidate_ranking"]}
        self.assertEqual("skill_candidate", ranking_by_skill["requesting-code-review"]["legacy_role"])
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
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

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
            "skill_candidate",
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
