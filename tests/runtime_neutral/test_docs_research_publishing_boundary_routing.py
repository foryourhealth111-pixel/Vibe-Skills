from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


def route(
    prompt: str,
    task_type: str = "research",
    grade: str = "L",
    requested_skill: str | None = None,
    installed_skill: str | None = None,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as temp_dir:
        agent_root = Path(temp_dir) / "home" / ".agents"
        if installed_skill is not None:
            skill_dir = agent_root / "skills" / installed_skill
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {prompt}\ndescription: {installed_skill} handles this local workflow.\n---\n# {installed_skill}\n",
                encoding="utf-8",
                newline="\n",
            )
        return route_prompt(
            prompt=prompt,
            grade=grade,
            task_type=task_type,
            requested_skill=requested_skill,
            target_root=str(agent_root),
            host_id="codex",
            repo_root=REPO_ROOT,
        )


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("candidate_focus")
    if not isinstance(selected_row, dict):
        return "", ""
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def selected_pack_or_none(result: dict[str, object]) -> str | None:
    selected_row = result.get("candidate_focus")
    if not isinstance(selected_row, dict):
        return None
    return str(selected_row.get("pack_id") or "") or None


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


class DocsResearchPublishingBoundaryRoutingTests(unittest.TestCase):
    def assert_selected(self, prompt: str, expected_pack: str, expected_skill: str, **kwargs: object) -> None:
        result = route(prompt, installed_skill=expected_skill, **kwargs)
        self.assertEqual(("local-skill-index", expected_skill), selected(result), (expected_pack, ranked_summary(result)))

    def test_existing_pdf_extraction_routes_to_pdf(self) -> None:
        self.assert_selected("读取 PDF 并提取正文", "docs-media", "pdf", grade="XL", task_type="coding")

    def test_pdf_to_markdown_routes_to_markitdown(self) -> None:
        self.assert_selected(
            "把 PDF 转成 Markdown",
            "docs-markitdown-conversion",
            "markitdown",
            grade="L",
            task_type="coding",
        )

    def test_latex_manuscript_pdf_build_routes_to_latex_pipeline(self) -> None:
        self.assert_selected(
            "用 LaTeX 写论文并构建 PDF",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            grade="XL",
            task_type="coding",
        )

    def test_scientific_report_routes_to_science_reporting(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF",
            "science-reporting",
            "scientific-reporting",
            grade="L",
            task_type="planning",
        )

    def test_slidev_pdf_export_routes_to_slides_as_code(self) -> None:
        self.assert_selected(
            "用 Slidev 做组会汇报并导出 PDF",
            "science-communication-slides",
            "slides-as-code",
            grade="L",
            task_type="coding",
        )

    def test_result_figures_route_to_scientific_visualization(self) -> None:
        self.assert_selected(
            "绘制机器学习模型评估结果图和投稿图",
            "science-figures-visualization",
            "scientific-visualization",
            grade="L",
            task_type="coding",
        )

    def test_figma_implementation_planning_routes_to_design_implementation(self) -> None:
        self.assert_selected(
            "把这个 Figma 设计稿还原为可运行代码",
            "design-implementation",
            "figma-implement-design",
            grade="L",
            task_type="planning",
        )

    def test_figma_implementation_coding_routes_to_design_implementation(self) -> None:
        self.assert_selected(
            "把这个 Figma 设计稿还原为可运行代码",
            "design-implementation",
            "figma-implement-design",
            grade="L",
            task_type="coding",
        )

    def test_quasi_experiment_design_stays_in_research_design(self) -> None:
        self.assert_selected(
            "帮我设计准实验方法，比较 DiD 和 ITS",
            "research-design",
            "designing-experiments",
            grade="L",
            task_type="planning",
        )

    def test_generic_xlsx_docx_parallel_prompt_is_not_docs_media_without_explicit_file_operation(self) -> None:
        result = route("xlsx and docx parallel processing", grade="XL", task_type="coding")
        self.assertNotEqual("docs-media", selected_pack_or_none(result), ranked_summary(result))

    def test_explicit_requested_xlsx_still_routes_to_docs_media_in_xl(self) -> None:
        self.assert_selected(
            "process xlsx workbook and preserve formulas",
            "docs-media",
            "xlsx",
            grade="XL",
            task_type="coding",
            requested_skill="xlsx",
        )

    def test_chinese_xlsx_to_docx_pdf_output_stays_in_docs_media(self) -> None:
        self.assert_selected(
            "请处理表格xlsx并生成docx和pdf文档",
            "docs-media",
            "xlsx",
            grade="M",
            task_type="coding",
        )
