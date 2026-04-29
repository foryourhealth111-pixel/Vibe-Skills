from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


RESEARCH_DESIGN_SKILLS = [
    "designing-experiments",
    "experiment-failure-analysis",
    "hypogenic",
    "hypothesis-generation",
    "literature-matrix",
    "performing-causal-analysis",
    "performing-regression-analysis",
    "research-grants",
    "scientific-brainstorming",
]

MOVED_OUT_SKILLS = [
    "architecture-patterns",
    "comprehensive-research-agent",
    "hypothesis-testing",
    "playwright",
    "property-based-testing",
    "research-lookup",
    "scientific-data-preprocessing",
    "skill-creator",
    "skill-lookup",
    "ux-researcher-designer",
    "verification-quality-assurance",
    "report-generator",
    "structured-content-storage",
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


class ResearchDesignPackConsolidationTests(unittest.TestCase):
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

    def assert_not_research_design(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("research-design", selected(result)[0], ranked_summary(result))

    def test_research_design_manifest_is_research_methods_only(self) -> None:
        pack = pack_by_id("research-design")
        self.assertEqual(RESEARCH_DESIGN_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(RESEARCH_DESIGN_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))
        for moved_skill in MOVED_OUT_SKILLS:
            self.assertNotIn(moved_skill, pack.get("skill_candidates") or [])

    def test_quasi_experiment_design_routes_to_designing_experiments(self) -> None:
        self.assert_selected(
            "帮我设计准实验方法，比较 DiD 和 ITS",
            "research-design",
            "designing-experiments",
            task_type="planning",
        )

    def test_experiment_failure_analysis_routes_to_failure_analysis(self) -> None:
        self.assert_selected(
            "分析实验失败原因，判断是否继续优化还是放弃该方案",
            "research-design",
            "experiment-failure-analysis",
            task_type="review",
        )

    def test_hypogenic_routes_to_hypogenic(self) -> None:
        self.assert_selected(
            "用 HypoGeniC 从数据和文献中生成并测试科研假设",
            "research-design",
            "hypogenic",
            task_type="research",
        )

    def test_scientific_hypothesis_generation_routes_to_hypothesis_generation(self) -> None:
        self.assert_selected(
            "根据实验观察生成可检验的科研假设和预测",
            "research-design",
            "hypothesis-generation",
            task_type="planning",
        )

    def test_literature_matrix_routes_to_literature_matrix(self) -> None:
        self.assert_selected(
            "构建论文组合矩阵，寻找 A+B 的研究创新点",
            "research-design",
            "literature-matrix",
            task_type="planning",
        )

    def test_causal_method_routes_to_causal_analysis(self) -> None:
        self.assert_selected(
            "用 DID 和 synthetic control 做因果分析方案",
            "research-design",
            "performing-causal-analysis",
            task_type="research",
        )

    def test_regression_method_routes_to_regression_analysis(self) -> None:
        self.assert_selected(
            "做回归分析并解释系数、置信区间和诊断结果",
            "research-design",
            "performing-regression-analysis",
            task_type="research",
        )

    def test_research_grant_routes_to_research_grants(self) -> None:
        self.assert_selected(
            "写 NSF 科研基金申请书的 significance 和 innovation",
            "research-design",
            "research-grants",
            task_type="planning",
        )

    def test_scientific_brainstorming_routes_to_scientific_brainstorming(self) -> None:
        self.assert_selected(
            "围绕这个生物机制做科研头脑风暴，提出可能机制和实验方向",
            "research-design",
            "scientific-brainstorming",
            task_type="planning",
        )

    def test_pubmed_literature_lookup_stays_outside_research_design(self) -> None:
        self.assert_selected(
            "检索 PubMed 文献并导出 BibTeX",
            "science-literature-citations",
            "pubmed-database",
            task_type="research",
        )

    def test_scientific_report_stays_outside_research_design(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF",
            "science-reporting",
            "scientific-reporting",
            task_type="planning",
        )

    def test_figma_implementation_stays_outside_research_design(self) -> None:
        self.assert_selected(
            "把这个 Figma 设计稿还原为可运行代码",
            "design-implementation",
            "figma-implement-design",
            task_type="coding",
        )

    def test_playwright_browser_automation_does_not_route_to_research_design(self) -> None:
        result = route("用 Playwright 打开网页并截图", task_type="coding", grade="M")
        self.assertIn(selected(result)[0], {"web-scraping", "screen-capture"}, ranked_summary(result))
        self.assertNotEqual("research-design", selected(result)[0], ranked_summary(result))

    def test_property_based_testing_does_not_route_to_research_design(self) -> None:
        self.assert_not_research_design(
            "为 Python 函数写 property-based testing",
            task_type="coding",
            grade="M",
        )

    def test_backend_architecture_does_not_route_to_research_design(self) -> None:
        self.assert_not_research_design(
            "为后端系统设计 Clean Architecture 架构",
            task_type="planning",
            grade="M",
        )

    def test_skill_creation_does_not_route_to_research_design(self) -> None:
        self.assert_not_research_design(
            "创建一个新的 Codex skill",
            task_type="planning",
            grade="M",
        )

    def test_ux_research_does_not_route_to_research_design(self) -> None:
        self.assert_not_research_design(
            "做用户访谈、persona 和用户旅程图",
            task_type="research",
            grade="M",
        )

    def test_data_preprocessing_guard_does_not_route_to_research_design(self) -> None:
        self.assert_not_research_design(
            "对科研数据做缺失值处理和标准化，避免数据泄漏",
            task_type="planning",
            grade="M",
        )


if __name__ == "__main__":
    unittest.main()
