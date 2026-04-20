# ruff: noqa: RUF001

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Import UI constants for testing
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "runtime-core" / "src"))
from vgo_runtime.router_contract_presentation import (
    CONFIRM_UI_BATCH_PROMPT,
    DEEP_DISCOVERY_FIRST_QUESTION,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "router" / "invoke-pack-route.py"
ROUTE_FIXTURE = REPO_ROOT / "tests" / "replay" / "route" / "recovery-wave-curated-prompts.json"
PLATFORM_FIXTURE = REPO_ROOT / "tests" / "replay" / "platform" / "linux-without-pwsh.json"


def run_bridge(prompt: str, grade: str, task_type: str, requested_skill: str | None = None) -> dict:
    command = [
        sys.executable,
        str(BRIDGE_SCRIPT),
        "--prompt",
        prompt,
        "--grade",
        grade,
        "--task-type",
        task_type,
        "--force-runtime-neutral",
    ]
    if requested_skill:
        command.extend(["--requested-skill", requested_skill])
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


class RouterBridgeTests(unittest.TestCase):
    def test_linux_without_pwsh_fixture_points_to_bridge_contract(self) -> None:
        platform = json.loads(PLATFORM_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual("linux_without_pwsh", platform["lane"])
        self.assertEqual("scripts/router/invoke-pack-route.py", platform["entry_script"])
        self.assertTrue(platform["constraints"]["force_runtime_neutral"])
        self.assertFalse(platform["constraints"]["requires_powershell_host"])

    def test_runtime_neutral_bridge_satisfies_curated_route_cases(self) -> None:
        fixture = json.loads(ROUTE_FIXTURE.read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                result = run_bridge(case["prompt"], case["grade"], case["task_type"])
                expected = case["expected"]

                self.assertIn("route_mode", result)
                self.assertIn("route_reason", result)
                self.assertIn("selected", result)
                self.assertIn("ranked", result)
                self.assertIn("runtime_neutral_bridge", result)
                self.assertEqual("python", result["runtime_neutral_bridge"]["engine"])

                if "route_mode" in expected:
                    self.assertEqual(expected["route_mode"], result["route_mode"])
                if "allowed_route_modes" in expected:
                    self.assertIn(result["route_mode"], expected["allowed_route_modes"])
                if "selected_pack" in expected:
                    self.assertEqual(expected["selected_pack"], result["selected"]["pack_id"])
                if "selected_skill" in expected:
                    self.assertEqual(expected["selected_skill"], result["selected"]["skill"])

    def test_confirm_required_returns_batched_clarification_bundle(self) -> None:
        result = run_bridge(
            "Help me clarify scope, choose repo path, define constraints, and then implement the feature with verification and deliverables.",
            "L",
            "planning",
        )
        self.assertEqual("confirm_required", result["route_mode"])
        self.assertGreaterEqual(len(result["deep_discovery_advice"]["interview_questions"]), 6)
        self.assertIn("confirm_ui", result)
        self.assertTrue(result["confirm_ui"]["enabled"])
        self.assertGreaterEqual(len(result["confirm_ui"]["options"]), 1)
        self.assertGreaterEqual(len(result["confirm_ui"]["clarification_questions"]), 6)
        self.assertIn(CONFIRM_UI_BATCH_PROMPT, result["confirm_ui"]["rendered_text"])
        self.assertIn(DEEP_DISCOVERY_FIRST_QUESTION, result["confirm_ui"]["rendered_text"])

    def test_ml_critical_discussion_routes_to_lqf_ml_expert(self) -> None:
        result = run_bridge(
            "请你作为机器学习专家和我进行三轮批判式讨论：这个分类方案有没有数据泄漏、基线是否充分、是否该先用简单模型",
            "L",
            "research",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("LQF_Machine_Learning_Expert_Guide", result["selected"]["skill"])

    def test_requested_mixed_case_skill_routes_authoritatively_in_runtime_neutral_lane(self) -> None:
        result = run_bridge(
            "请用机器学习专家视角审视这个分类方案",
            "L",
            "research",
            requested_skill="LQF_Machine_Learning_Expert_Guide",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("LQF_Machine_Learning_Expert_Guide", result["selected"]["skill"])

    def test_vibe_keeps_route_authority_while_plan_helpers_move_to_stage_assistants(self) -> None:
        result = run_bridge(
            "请持续更新 task_plan.md 和 progress.md，按阶段推进这个复杂任务",
            "L",
            "planning",
            requested_skill="vibe",
        )

        self.assertEqual("orchestration-core", result["selected"]["pack_id"])
        self.assertEqual("vibe", result["selected"]["skill"])

        orchestration_row = next(row for row in result["ranked"] if row["pack_id"] == "orchestration-core")
        self.assertEqual("vibe", orchestration_row["selected_candidate"])
        self.assertEqual(["vibe"], [row["skill"] for row in orchestration_row["candidate_ranking"]])
        self.assertIn("planning-with-files", [row["skill"] for row in orchestration_row["stage_assistant_candidates"]])

    def test_scientific_figure_route_keeps_plotting_libraries_out_of_main_candidate_pool(self) -> None:
        result = run_bridge(
            "帮我做科研绘图，产出期刊级 figure，多面板、颜色无障碍、矢量导出",
            "L",
            "research",
        )

        self.assertEqual("science-figures-visualization", result["selected"]["pack_id"])
        self.assertEqual("scientific-visualization", result["selected"]["skill"])

        figure_row = next(row for row in result["ranked"] if row["pack_id"] == "science-figures-visualization")
        self.assertEqual(
            ["scientific-visualization", "scientific-schematics"],
            [row["skill"] for row in figure_row["candidate_ranking"]],
        )
        self.assertTrue(
            {"matplotlib", "seaborn", "plotly"}.issubset(
                {row["skill"] for row in figure_row["stage_assistant_candidates"]}
            )
        )

    def test_full_text_evidence_table_prefers_bgpt_structured_paper_search(self) -> None:
        result = run_bridge(
            "请帮我做 full-text 文献检索，提取样本量、effect size、方法学细节，做系统综述证据表",
            "L",
            "research",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("science-literature-citations", result["selected"]["pack_id"])
        self.assertEqual("bgpt-paper-search", result["selected"]["skill"])

    def test_deep_research_pack_keeps_deepagent_helpers_out_of_main_candidate_pool(self) -> None:
        result = run_bridge(
            "我要做 deep research，多跳浏览网页并保留 trace.jsonl 和 sources.json 证据链",
            "L",
            "research",
        )

        self.assertEqual("ruc-nlpir-augmentation", result["selected"]["pack_id"])
        self.assertEqual("webthinker-deep-research", result["selected"]["skill"])

        deep_research_row = next(row for row in result["ranked"] if row["pack_id"] == "ruc-nlpir-augmentation")
        self.assertEqual(
            ["webthinker-deep-research", "flashrag-evidence"],
            [row["skill"] for row in deep_research_row["candidate_ranking"]],
        )

    def test_data_leakage_audit_can_route_to_ml_data_leakage_guard(self) -> None:
        result = run_bridge(
            "请检查这个特征工程流程有没有数据泄漏，尤其是 fit before split 和 prediction time 问题",
            "L",
            "review",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("ml-data-leakage-guard", result["selected"]["skill"])

    def test_baseline_leakage_research_stays_with_dedicated_guard(self) -> None:
        result = run_bridge(
            "请检查我的 baseline model 有没有 data leakage，尤其是 fit before split、train test split 和 prediction time 问题",
            "L",
            "research",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("ml-data-leakage-guard", result["selected"]["skill"])

    def test_test_report_packaging_routes_to_generating_test_reports(self) -> None:
        result = run_bridge(
            "请根据 pytest 和 coverage 输出生成测试报告，整理失败摘要、覆盖率和质量门禁结论",
            "L",
            "review",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("code-quality", result["selected"]["pack_id"])
        self.assertEqual("generating-test-reports", result["selected"]["skill"])

    def test_regression_analysis_routes_to_regression_owner(self) -> None:
        result = run_bridge(
            "请对这个实验数据做回归分析：线性回归或 GLM 建模、残差诊断、系数解释和拟合优度比较",
            "L",
            "research",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("research-design", result["selected"]["pack_id"])
        self.assertEqual("performing-regression-analysis", result["selected"]["skill"])

    def test_preprocessing_pipeline_surfaces_stage_assistant_without_taking_main_route(self) -> None:
        result = run_bridge(
            "请用 scikit-learn 设计数据预处理流水线：清洗、编码、标准化、ETL pipeline，但先不要做数据泄漏审计",
            "L",
            "research",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        data_ml_row = next(row for row in result["ranked"] if row["pack_id"] == "data-ml")
        self.assertEqual("scikit-learn", data_ml_row["selected_candidate"])
        self.assertNotIn(
            "preprocessing-data-with-automated-pipelines",
            [row["skill"] for row in data_ml_row["candidate_ranking"]],
        )
        self.assertIn(
            "preprocessing-data-with-automated-pipelines",
            [row["skill"] for row in data_ml_row["stage_assistant_candidates"]],
        )

    def test_research_report_authoring_stays_on_scientific_reporting(self) -> None:
        result = run_bridge(
            "请把我们现有实验结果整理成 research report，带 executive summary、appendix、Quarto/PDF 导出",
            "L",
            "research",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("science-reporting", result["selected"]["pack_id"])
        self.assertEqual("scientific-reporting", result["selected"]["skill"])

    def test_requested_vibe_can_preserve_runtime_authority_while_router_selects_specialist(self) -> None:
        result = run_bridge(
            "I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
            "XL",
            "debug",
            requested_skill="vibe",
        )

        self.assertEqual("confirm_required", result["route_mode"])
        self.assertEqual("code-quality", result["selected"]["pack_id"])
        self.assertEqual("systematic-debugging", result["selected"]["skill"])
        self.assertEqual("vibe", result["alias"]["requested_canonical"])
        self.assertEqual("vibe", result["ranked"][1]["selected_candidate"])
        self.assertIn("confirm_ui", result)
        self.assertTrue(result["confirm_ui"]["enabled"])


if __name__ == "__main__":
    unittest.main()