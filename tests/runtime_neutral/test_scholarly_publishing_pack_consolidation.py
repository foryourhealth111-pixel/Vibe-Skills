from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


SCHOLARLY_PUBLISHING_SKILLS = [
    "scholarly-publishing",
    "submission-checklist",
    "manuscript-as-code",
    "latex-submission-pipeline",
    "scientific-writing",
    "venue-templates",
    "latex-posters",
    "paper-2-web",
]

MOVED_OUT_SKILLS = [
    "slides-as-code",
    "scientific-visualization",
    "scientific-schematics",
    "citation-management",
    "scientific-slides",
]

FORBIDDEN_INLINE_HELPER_REFERENCES = sorted(
    set(SCHOLARLY_PUBLISHING_SKILLS + MOVED_OUT_SKILLS)
    | {
        "research-lookup",
        "literature-review",
        "peer-review",
        "research-grants",
    }
)


def route(prompt: str, task_type: str = "research", grade: str = "L") -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        repo_root=REPO_ROOT,
    )


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
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


def pack_by_id(pack_id: str) -> dict[str, object]:
    manifest_path = REPO_ROOT / "config" / "pack-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


def skill_body(skill_id: str) -> str:
    skill_path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8-sig")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lower()
    return text.lower()


class ScholarlyPublishingPackConsolidationTests(unittest.TestCase):
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

    def assert_not_scholarly_publishing(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("scholarly-publishing-workflow", selected(result)[0], ranked_summary(result))

    def test_manifest_is_publishing_workflow_only(self) -> None:
        pack = pack_by_id("scholarly-publishing-workflow")
        self.assertEqual(SCHOLARLY_PUBLISHING_SKILLS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertEqual(
            {
                "planning": "scholarly-publishing",
                "coding": "latex-submission-pipeline",
                "research": "scientific-writing",
            },
            pack.get("defaults_by_task"),
        )
        for moved_skill in MOVED_OUT_SKILLS:
            self.assertNotIn(moved_skill, pack.get("skill_candidates") or [])

    def test_kept_skill_docs_do_not_inline_cross_call_other_skills(self) -> None:
        forbidden_headings = [
            "visual enhancement with scientific schematics",
            "integration with other skills",
            "integration with other scientific skills",
        ]
        for skill_id in SCHOLARLY_PUBLISHING_SKILLS:
            with self.subTest(skill_id=skill_id):
                body = skill_body(skill_id)
                forbidden_refs = [
                    ref
                    for ref in FORBIDDEN_INLINE_HELPER_REFERENCES
                    if ref != skill_id and ref in body
                ]
                self.assertEqual([], forbidden_refs)
                for heading in forbidden_headings:
                    self.assertNotIn(heading, body)

    def test_publishing_workflow_routes_to_scholarly_publishing(self) -> None:
        self.assert_selected(
            "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready",
            "scholarly-publishing-workflow",
            "scholarly-publishing",
            task_type="planning",
        )

    def test_rebuttal_matrix_routes_to_submission_checklist(self) -> None:
        self.assert_selected(
            "写 cover letter 和 response to reviewers rebuttal matrix",
            "scholarly-publishing-workflow",
            "submission-checklist",
            task_type="planning",
        )

    def test_manuscript_as_code_routes_to_manuscript_as_code(self) -> None:
        self.assert_selected(
            "把论文仓库改成 manuscript-as-code，可复现构建 PDF",
            "scholarly-publishing-workflow",
            "manuscript-as-code",
            task_type="planning",
        )

    def test_latex_pipeline_routes_to_latex_submission_pipeline(self) -> None:
        self.assert_selected(
            "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            task_type="coding",
            grade="XL",
        )

    def test_scientific_writing_routes_to_scientific_writing(self) -> None:
        self.assert_selected(
            "请按 IMRAD 结构写科研论文正文",
            "scholarly-publishing-workflow",
            "scientific-writing",
            task_type="research",
        )

    def test_venue_template_routes_to_venue_templates(self) -> None:
        self.assert_selected(
            "查 NeurIPS 模板和匿名投稿格式要求",
            "scholarly-publishing-workflow",
            "venue-templates",
            task_type="planning",
        )

    def test_latex_poster_routes_to_latex_posters(self) -> None:
        self.assert_selected(
            "用 beamerposter 做会议学术海报",
            "scholarly-publishing-workflow",
            "latex-posters",
            task_type="coding",
        )

    def test_paper2web_routes_to_paper_2_web(self) -> None:
        self.assert_selected(
            "把论文转换成 paper2web 项目主页和视频摘要",
            "scholarly-publishing-workflow",
            "paper-2-web",
            task_type="planning",
        )

    def test_result_figures_stay_in_science_figures(self) -> None:
        self.assert_selected(
            "绘制机器学习模型评估结果图和投稿图",
            "science-figures-visualization",
            "scientific-visualization",
            task_type="coding",
        )

    def test_schematics_stay_in_science_figures(self) -> None:
        self.assert_selected(
            "画一个机制示意图和流程图",
            "science-figures-visualization",
            "scientific-schematics",
            task_type="planning",
        )

    def test_slidev_stays_in_science_communication_slides(self) -> None:
        self.assert_selected(
            "用 Slidev 做组会汇报并导出 PDF",
            "science-communication-slides",
            "slides-as-code",
            task_type="coding",
        )

    def test_scientific_slide_deck_stays_in_science_communication_slides(self) -> None:
        self.assert_selected(
            "顶级PPT制作：组会汇报 slide deck",
            "science-communication-slides",
            "scientific-slides",
            task_type="planning",
        )

    def test_citation_management_stays_in_literature_citations(self) -> None:
        self.assert_selected(
            "整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography",
            "science-literature-citations",
            "citation-management",
            task_type="planning",
        )

    def test_existing_pdf_extraction_stays_in_docs_media(self) -> None:
        self.assert_selected(
            "读取 PDF 并提取正文",
            "docs-media",
            "pdf",
            task_type="coding",
            grade="XL",
        )

    def test_scientific_report_stays_in_science_reporting(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF",
            "science-reporting",
            "scientific-reporting",
            task_type="planning",
        )

    def test_generic_figure_or_slide_prompts_do_not_route_to_publishing(self) -> None:
        self.assert_not_scholarly_publishing(
            "做一套科研图表和组会幻灯片",
            task_type="planning",
        )


if __name__ == "__main__":
    unittest.main()
