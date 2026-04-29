from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEPT_SKILLS = [
    "scientific-slides",
    "slides-as-code",
    "pptx-posters",
    "infographics",
]

MOVED_OUT_SKILLS = [
    "markdown-mermaid-writing",
    "markitdown",
    "document-skills",
    "generate-image",
]

REMOVED_PACK_TRIGGERS = [
    "poster",
    "infographic",
    "mermaid",
    "diagram",
    "flowchart",
    "海报",
    "信息图",
    "流程图",
    "示意图",
]


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


class ScienceCommunicationSlidesPackConsolidationTests(unittest.TestCase):
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

    def assert_not_science_communication(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("science-communication-slides", selected(result)[0], ranked_summary(result))

    def test_manifest_shrinks_to_four_route_owners(self) -> None:
        pack = pack_by_id("science-communication-slides")
        self.assertEqual(KEPT_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(KEPT_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))

    def test_manifest_removes_moved_out_skills(self) -> None:
        pack = pack_by_id("science-communication-slides")
        candidates = set(pack.get("skill_candidates") or [])
        for skill in MOVED_OUT_SKILLS:
            self.assertNotIn(skill, candidates)

    def test_pack_triggers_are_slide_specific(self) -> None:
        pack = pack_by_id("science-communication-slides")
        triggers = set(pack.get("trigger_keywords") or [])
        for keyword in REMOVED_PACK_TRIGGERS:
            self.assertNotIn(keyword, triggers)
        for keyword in ["slides", "slide deck", "ppt", "pptx", "powerpoint", "slidev", "marp", "reveal.js", "幻灯片", "演示文稿", "组会汇报", "答辩"]:
            self.assertIn(keyword, triggers)

    def test_defaults_match_kept_slide_owners(self) -> None:
        pack = pack_by_id("science-communication-slides")
        self.assertEqual(
            {
                "planning": "scientific-slides",
                "coding": "slides-as-code",
                "research": "scientific-slides",
            },
            pack.get("defaults_by_task"),
        )

    def test_scientific_slide_deck_routes_to_scientific_slides(self) -> None:
        self.assert_selected(
            "顶级PPT制作：组会汇报 slide deck，需要讲述结构与视觉规范",
            "science-communication-slides",
            "scientific-slides",
            task_type="planning",
            grade="L",
        )

    def test_slidev_pdf_export_routes_to_slides_as_code(self) -> None:
        self.assert_selected(
            "用 Slidev 做组会汇报并导出 PDF",
            "science-communication-slides",
            "slides-as-code",
            task_type="coding",
            grade="L",
        )

    def test_marp_pdf_export_routes_to_slides_as_code(self) -> None:
        self.assert_selected(
            "用 Marp 做科研 presentation 并导出 PDF",
            "science-communication-slides",
            "slides-as-code",
            task_type="coding",
            grade="L",
        )

    def test_pptx_poster_routes_to_pptx_posters(self) -> None:
        self.assert_selected(
            "制作 PowerPoint PPTX 学术海报",
            "science-communication-slides",
            "pptx-posters",
            task_type="planning",
            grade="L",
        )

    def test_plain_conference_poster_routes_to_latex_posters(self) -> None:
        self.assert_selected(
            "制作学术海报 conference poster",
            "scholarly-publishing-workflow",
            "latex-posters",
            task_type="planning",
            grade="L",
        )

    def test_explicit_infographic_routes_to_infographics(self) -> None:
        self.assert_selected(
            "做一个研究结论信息图 infographic visual summary",
            "science-communication-slides",
            "infographics",
            task_type="planning",
            grade="L",
        )

    def test_mermaid_flowchart_leaves_slides_pack(self) -> None:
        self.assert_selected(
            "用 Mermaid 写一个实验流程图 flowchart，并给出可复制的 markdown",
            "science-figures-visualization",
            "scientific-schematics",
            task_type="coding",
            grade="M",
        )

    def test_mechanism_flowchart_routes_to_scientific_schematics(self) -> None:
        self.assert_selected(
            "画一个机制示意图和流程图",
            "science-figures-visualization",
            "scientific-schematics",
            task_type="planning",
            grade="L",
        )

    def test_result_figures_route_to_scientific_visualization(self) -> None:
        self.assert_selected(
            "绘制机器学习模型评估结果图和投稿图",
            "science-figures-visualization",
            "scientific-visualization",
            task_type="coding",
            grade="L",
        )

    def test_pdf_to_markdown_routes_to_markitdown_pack(self) -> None:
        self.assert_selected(
            "把 PDF 转成 Markdown，要求保留表格与标题结构",
            "docs-markitdown-conversion",
            "markitdown",
            task_type="coding",
            grade="M",
        )

    def test_general_image_generation_does_not_route_to_slides_pack(self) -> None:
        self.assert_not_science_communication(
            "生成一张产品概念图 image generation",
            task_type="planning",
            grade="M",
        )


if __name__ == "__main__":
    unittest.main()
