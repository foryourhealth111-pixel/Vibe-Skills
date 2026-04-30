from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
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


class FiguresReportingStageAssistantRemovalTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def test_figures_pack_has_only_direct_problem_owners(self) -> None:
        pack = load_pack("science-figures-visualization")
        expected = ["scientific-visualization", "scientific-schematics"]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_reporting_pack_has_only_direct_problem_owners(self) -> None:
        pack = load_pack("science-reporting")
        expected = ["scientific-reporting", "scientific-writing"]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_plotting_library_words_still_route_to_scientific_visualization(self) -> None:
        prompts = [
            "用 matplotlib 绘制 publication-ready result figure，600dpi TIFF，带误差棒和显著性标注",
            "用 seaborn 画模型评估结果图和投稿图，要求色盲友好配色",
            "用 plotly 做 interactive result figure，并导出 HTML figure 给科研报告使用",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assert_selected(
                    prompt,
                    "science-figures-visualization",
                    "scientific-visualization",
                    task_type="coding",
                )

    def test_figures_candidate_metadata_has_no_plotting_stage_assistants(self) -> None:
        result = route(
            "帮我做科研绘图，产出期刊级 figure，多面板、颜色无障碍、矢量导出",
            task_type="research",
            grade="L",
        )
        row = pack_row(result, "science-figures-visualization")
        ranking = row.get("candidate_ranking")
        assert isinstance(ranking, list), row
        ranking_skills = {str(item.get("skill") or "") for item in ranking if isinstance(item, dict)}
        self.assertEqual({"scientific-visualization", "scientific-schematics"}, ranking_skills)
        self.assertEqual([], row.get("stage_assistant_candidates"))

    def test_schematics_route_to_scientific_schematics(self) -> None:
        self.assert_selected(
            "用 Mermaid 写一个实验流程图 flowchart，并给出可复制 markdown",
            "science-figures-visualization",
            "scientific-schematics",
            task_type="coding",
            grade="M",
        )

    def test_reporting_routes_remain_stable(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF，附录写清复现步骤",
            "science-reporting",
            "scientific-reporting",
            task_type="planning",
            grade="L",
        )

    def test_reporting_candidate_metadata_has_no_figure_or_mermaid_stage_assistants(self) -> None:
        result = route(
            "请把我们现有实验结果整理成 research report，带 executive summary、appendix、Quarto/PDF 导出",
            task_type="research",
            grade="L",
        )
        row = pack_row(result, "science-reporting")
        ranking = row.get("candidate_ranking")
        assert isinstance(ranking, list), row
        ranking_skills = {str(item.get("skill") or "") for item in ranking if isinstance(item, dict)}
        self.assertEqual({"scientific-reporting", "scientific-writing"}, ranking_skills)
        self.assertEqual([], row.get("stage_assistant_candidates"))

    def test_manuscript_prose_still_selects_scientific_writing(self) -> None:
        result = route("请按 IMRAD 结构写科研论文正文", task_type="research", grade="L")
        self.assertEqual("scientific-writing", selected(result)[1], ranked_summary(result))


if __name__ == "__main__":
    unittest.main()
