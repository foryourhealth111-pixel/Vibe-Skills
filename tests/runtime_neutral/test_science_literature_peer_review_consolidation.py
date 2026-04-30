from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


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


class ScienceLiteraturePeerReviewConsolidationTests(unittest.TestCase):
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

    def test_literature_pack_manifest_is_literature_only(self) -> None:
        pack = pack_by_id("science-literature-citations")
        self.assertEqual(
            [
                "pubmed-database",
                "openalex-database",
                "pyzotero",
                "citation-management",
                "literature-review",
            ],
            pack.get("skill_candidates"),
        )
        self.assertEqual(pack.get("skill_candidates"), pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))

    def test_peer_review_pack_has_explicit_route_authorities(self) -> None:
        pack = pack_by_id("science-peer-review")
        self.assertEqual(
            ["peer-review", "scientific-critical-thinking", "scholar-evaluation"],
            pack.get("skill_candidates"),
        )
        self.assertEqual(pack.get("skill_candidates"), pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))

    def test_open_notebook_skill_directory_is_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / ("open" + "-notebook")).exists())

    def test_low_value_literature_tool_directories_are_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "biorxiv-database").exists())
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "bgpt-paper-search").exists())

    def test_retained_literature_skills_do_not_require_helper_experts(self) -> None:
        for skill_id in ("literature-review", "citation-management"):
            text = (REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8-sig")
            self.assertNotIn("scientific-schematics", text)
            self.assertNotIn("MANDATORY", text)

    def test_pubmed_bibtex_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "在 PubMed 检索文献并导出 BibTeX",
            "science-literature-citations",
            "pubmed-database",
        )

    def test_pyzotero_api_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "用 pyzotero 连接 Zotero library，批量整理条目并导出 BibTeX",
            "science-literature-citations",
            "pyzotero",
            task_type="coding",
            grade="M",
        )

    def test_citation_formatting_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography",
            "science-literature-citations",
            "citation-management",
            task_type="planning",
            grade="M",
        )

    def test_systematic_review_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "做系统综述和 meta-analysis，输出 PRISMA 流程和纳排标准",
            "science-literature-citations",
            "literature-review",
        )

    def test_full_text_evidence_table_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "做 full-text 文献检索，提取样本量、effect size、方法学细节，生成系统综述证据表",
            "science-literature-citations",
            "literature-review",
        )

    def test_biorxiv_preprint_search_is_absorbed_by_literature_review(self) -> None:
        self.assert_selected(
            "把 bioRxiv 预印本纳入文献综述，检索最近两年的 life sciences preprints",
            "science-literature-citations",
            "literature-review",
        )

    def test_formal_peer_review_routes_to_peer_review_pack(self) -> None:
        self.assert_selected(
            "请对这篇论文做 peer review，指出方法学缺陷和可复现性风险",
            "science-peer-review",
            "peer-review",
            task_type="review",
        )

    def test_scholareval_routes_to_scholar_evaluation(self) -> None:
        self.assert_selected(
            "用 ScholarEval rubric 评估这篇论文的问题 formulation、methodology、analysis 和 writing",
            "science-peer-review",
            "scholar-evaluation",
            task_type="review",
        )

    def test_evidence_strength_routes_to_scientific_critical_thinking(self) -> None:
        self.assert_selected(
            "批判性分析这篇论文的证据强度、偏倚和混杂因素",
            "science-peer-review",
            "scientific-critical-thinking",
            task_type="review",
        )

    def test_publishing_rebuttal_stays_with_publishing_workflow(self) -> None:
        self.assert_selected(
            "写论文投稿 cover letter 和 response to reviewers rebuttal matrix",
            "scholarly-publishing-workflow",
            "submission-checklist",
            task_type="planning",
        )

    def test_latex_paper_build_stays_with_latex_pipeline(self) -> None:
        self.assert_selected(
            "用 LaTeX 写论文并构建 PDF",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            task_type="coding",
            grade="XL",
        )
