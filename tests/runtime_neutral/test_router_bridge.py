# ruff: noqa: RUF001

from __future__ import annotations

import json
import subprocess
import shutil
import sys
import unittest
from pathlib import Path

# Import UI constants for testing
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "runtime-core" / "src"))
from vgo_runtime.router_contract_presentation import (
    CONFIRM_UI_BATCH_PROMPT,
    DEEP_DISCOVERY_FIRST_QUESTION,
    build_confirm_ui,
)
from vgo_runtime.router_contract_runtime import route_prompt
from vgo_runtime.router_contract_support import RepoContext


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "router" / "invoke-pack-route.py"
ROUTE_FIXTURE = REPO_ROOT / "tests" / "replay" / "route" / "recovery-wave-curated-prompts.json"
PLATFORM_FIXTURE = REPO_ROOT / "tests" / "replay" / "platform" / "linux-without-pwsh.json"


def run_bridge(
    prompt: str,
    grade: str,
    task_type: str,
    requested_skill: str | None = None,
    entry_intent_id: str | None = None,
) -> dict:
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
    if entry_intent_id:
        command.extend(["--entry-intent-id", entry_intent_id])
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


def run_powershell_route(prompt: str, grade: str, task_type: str, requested_skill: str | None = None) -> dict:
    powershell = shutil.which("pwsh")
    if not powershell:
        raise unittest.SkipTest("PowerShell 7 (pwsh) not found in PATH")

    command = [
        powershell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"),
        "-Prompt",
        prompt,
        "-Grade",
        grade,
        "-TaskType",
        task_type,
    ]
    if requested_skill:
        command.extend(["-RequestedSkill", requested_skill])

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


class RouterBridgeTests(unittest.TestCase):
    def test_build_confirm_ui_keeps_selected_skill_visible_when_ranking_is_truncated(self) -> None:
        repo = RepoContext(
            repo_root=REPO_ROOT,
            config_root=REPO_ROOT / "config",
            bundled_skills_root=REPO_ROOT / "bundled" / "skills",
        )
        route_result = {
            "route_mode": "confirm_required",
            "selected": {
                "pack_id": "synthetic-pack",
                "skill": "selected-skill",
                "selection_score": 0.42,
            },
            "ranked": [
                {
                    "pack_id": "synthetic-pack",
                    "candidate_ranking": [
                        {"skill": "skill-a", "score": 0.91},
                        {"skill": "skill-b", "score": 0.81},
                        {"skill": "skill-c", "score": 0.71},
                        {"skill": "skill-d", "score": 0.61},
                        {"skill": "skill-e", "score": 0.51},
                        {"skill": "selected-skill", "score": 0.42},
                    ],
                    "stage_assistant_candidates": [],
                }
            ],
        }

        confirm_ui = build_confirm_ui(repo, route_result, None)

        self.assertIsNotNone(confirm_ui)
        self.assertEqual("selected-skill", confirm_ui["options"][0]["skill"])
        self.assertTrue(confirm_ui["options"][0]["is_primary"])
        self.assertIn("selected-skill", confirm_ui["route_decision_contract"]["allowed_skill_ids"])

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
                if "blocked_pack" in expected:
                    self.assertNotEqual(expected["blocked_pack"], result["selected"]["pack_id"])
                    ranked_pack_ids = {
                        str(row.get("pack_id") or "")
                        for row in result["ranked"]
                        if isinstance(row, dict)
                    }
                    self.assertNotIn(expected["blocked_pack"], ranked_pack_ids)
                if "blocked_skill_prefix" in expected:
                    blocked_prefix = expected["blocked_skill_prefix"]
                    ranked_skills = {str(result["selected"].get("skill") or "")}
                    for row in result["ranked"]:
                        if not isinstance(row, dict):
                            continue
                        for field in ("candidate_ranking", "stage_assistant_candidates"):
                            for item in row.get(field) or []:
                                if isinstance(item, dict):
                                    ranked_skills.add(str(item.get("skill") or ""))
                    self.assertFalse(
                        [skill for skill in sorted(ranked_skills) if skill.startswith(blocked_prefix)],
                        ranked_skills,
                    )

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

    def test_host_selection_confirm_ui_does_not_reopen_generic_clarifiers(self) -> None:
        result = run_bridge(
            "create implementation plan and task breakdown",
            "L",
            "planning",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("host_selection_required", result["route_reason"])
        self.assertIn("confirm_ui", result)
        self.assertEqual([], result["confirm_ui"]["clarification_questions"])
        self.assertNotIn(CONFIRM_UI_BATCH_PROMPT, result["confirm_ui"]["rendered_text"])
        self.assertNotIn(DEEP_DISCOVERY_FIRST_QUESTION, result["confirm_ui"]["rendered_text"])
        self.assertFalse(result["deep_discovery_advice"]["should_apply_hook"])

    def test_powershell_host_selection_confirm_ui_does_not_reopen_generic_clarifiers(self) -> None:
        result = run_powershell_route(
            "create implementation plan and task breakdown",
            "L",
            "planning",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("host_selection_required", result["route_reason"])
        self.assertIn("confirm_ui", result)
        self.assertEqual([], result["confirm_ui"]["clarification_questions"])
        self.assertNotIn(CONFIRM_UI_BATCH_PROMPT, result["confirm_ui"]["rendered_text"])
        self.assertNotIn(DEEP_DISCOVERY_FIRST_QUESTION, result["confirm_ui"]["rendered_text"])

    def test_ml_critical_discussion_routes_to_data_leakage_guard(self) -> None:
        result = run_bridge(
            "请你作为机器学习专家和我进行三轮批判式讨论：这个分类方案有没有数据泄漏、基线是否充分、是否该先用简单模型",
            "L",
            "research",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("ml-data-leakage-guard", result["selected"]["skill"])

    def test_ml_threshold_question_does_not_false_positive_to_vibe(self) -> None:
        result = run_bridge(
            "Please help me choose a confidence threshold and fallback threshold for a scikit-learn binary classifier using ROC and precision-recall tradeoffs.",
            "L",
            "research",
        )

        self.assertNotEqual("vibe", result["selected"]["skill"])
        self.assertEqual("data-ml", result["selected"]["pack_id"])

    def test_requested_mixed_case_active_skill_routes_authoritatively_in_runtime_neutral_lane(self) -> None:
        result = run_bridge(
            "请用机器学习专家视角审视这个分类方案",
            "L",
            "research",
            requested_skill="Scikit-Learn",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("data-ml", result["selected"]["pack_id"])
        self.assertEqual("scikit-learn", result["selected"]["skill"])

    def test_wrapper_entry_intent_does_not_override_runtime_neutral_router_selection(self) -> None:
        prompt = (
            "Please use scikit-learn to prototype a tabular classification baseline, "
            "run feature selection, and compare cross-validation metrics."
        )
        baseline = route_prompt(
            prompt=prompt,
            grade="L",
            task_type="coding",
            repo_root=REPO_ROOT,
        )
        wrapped = route_prompt(
            prompt=prompt,
            grade="L",
            task_type="coding",
            entry_intent_id="vibe-what-do-i-want",
            repo_root=REPO_ROOT,
        )

        self.assertEqual(baseline["route_mode"], wrapped["route_mode"])
        self.assertEqual(baseline["selected"]["pack_id"], wrapped["selected"]["pack_id"])
        self.assertEqual(baseline["selected"]["skill"], wrapped["selected"]["skill"])
        self.assertEqual("vibe-what-do-i-want", wrapped["alias"]["entry_intent_id"])
        self.assertIsNone(wrapped["alias"]["requested_input"])

    def test_vibe_keeps_route_authority_while_plan_helpers_move_to_stage_assistants(self) -> None:
        result = run_bridge(
            "请持续更新 task_plan.md 和 progress.md，按阶段推进这个复杂任务",
            "L",
            "planning",
            requested_skill="vibe",
        )

        self.assertEqual("vibe", result["alias"]["requested_canonical"])
        self.assertNotEqual("orchestration-core", result["selected"]["pack_id"])
        self.assertIn("brainstorm_planning", result["intent_contract"]["capabilities"])
        self.assertEqual(["vibe"], result["deep_discovery_advice"]["recommended_skills"])

    def test_scientific_figure_route_uses_only_direct_figure_candidates(self) -> None:
        result = run_bridge(
            "帮我做科研绘图，产出期刊级 figure，多面板、颜色无障碍、矢量导出",
            "L",
            "research",
        )

        self.assertEqual("science-figures-visualization", result["selected"]["pack_id"])
        self.assertEqual("scientific-visualization", result["selected"]["skill"])

        figure_row = next(row for row in result["ranked"] if row["pack_id"] == "science-figures-visualization")
        ranking_by_skill = {row["skill"]: row for row in figure_row["candidate_ranking"]}
        self.assertEqual(
            {"scientific-visualization", "scientific-schematics"},
            set(ranking_by_skill),
        )
        self.assertEqual("route_authority", ranking_by_skill["scientific-visualization"]["legacy_role"])
        self.assertEqual("route_authority", ranking_by_skill["scientific-schematics"]["legacy_role"])
        self.assertEqual([], figure_row["stage_assistant_candidates"])

    def test_full_text_evidence_table_prefers_bgpt_structured_paper_search(self) -> None:
        result = run_bridge(
            "请帮我做 full-text 文献检索，提取样本量、effect size、方法学细节，做系统综述证据表",
            "L",
            "research",
        )

        self.assertIn(result["route_mode"], {"pack_overlay", "confirm_required"})
        self.assertEqual("science-literature-citations", result["selected"]["pack_id"])
        self.assertEqual("bgpt-paper-search", result["selected"]["skill"])

    def test_deep_research_pack_has_no_legacy_stage_assistants(self) -> None:
        result = run_bridge(
            "我要做 deep research，多跳浏览网页并保留 trace.jsonl 和 sources.json 证据链",
            "L",
            "research",
        )

        self.assertEqual("ruc-nlpir-augmentation", result["selected"]["pack_id"])
        self.assertEqual("webthinker-deep-research", result["selected"]["skill"])

        deep_research_row = next(row for row in result["ranked"] if row["pack_id"] == "ruc-nlpir-augmentation")
        ranking_by_skill = {row["skill"]: row for row in deep_research_row["candidate_ranking"]}
        self.assertEqual({"flashrag-evidence", "webthinker-deep-research"}, set(ranking_by_skill))
        self.assertEqual("route_authority", ranking_by_skill["webthinker-deep-research"]["legacy_role"])
        self.assertEqual("route_authority", ranking_by_skill["flashrag-evidence"]["legacy_role"])
        self.assertEqual([], deep_research_row["stage_assistant_candidates"])

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

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertEqual("code-quality", result["selected"]["pack_id"])
        self.assertEqual("systematic-debugging", result["selected"]["skill"])
        self.assertEqual("vibe", result["alias"]["requested_canonical"])
        self.assertNotEqual("orchestration-core", result["selected"]["pack_id"])
        self.assertIn("confirm_ui", result)
        self.assertTrue(result["confirm_ui"]["enabled"])

    def test_vibe_do_it_wrapper_keywords_fold_back_to_canonical_vibe_before_prelaunch_routing(self) -> None:
        result = run_bridge(
            "execute plan phase-cleanup facial-recognition few-shot dataset download training baseline enhancements experiments latex-paper",
            "L",
            "research",
            requested_skill="vibe-do-it",
        )

        self.assertEqual("pack_overlay", result["route_mode"])
        self.assertNotEqual("orchestration-core", result["selected"]["pack_id"])
        self.assertEqual("vibe", result["alias"]["requested_canonical"])


if __name__ == "__main__":
    unittest.main()
