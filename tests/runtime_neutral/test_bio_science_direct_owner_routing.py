from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


def route(prompt: str, task_type: str = "research", grade: str = "M", installed_skill: str | None = None) -> dict[str, object]:
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
            target_root=str(agent_root),
            host_id="codex",
            repo_root=REPO_ROOT,
        )


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("candidate_focus")
    if not isinstance(selected_row, dict):
        return "", ""
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


class BioScienceDirectOwnerRoutingTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade, installed_skill=expected_skill)
        self.assertEqual(("local-skill-index", expected_skill), selected(result), ranked_summary(result))

    def assert_not_selected(
        self,
        prompt: str,
        blocked_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual(("bio-science", blocked_skill), selected(result), ranked_summary(result))

    def test_anndata_routes_to_scanpy_for_h5ad_container_work(self) -> None:
        self.assert_selected("用 AnnData 读写 h5ad，管理 obs/var 元数据和 backed mode 稀疏矩阵", "scanpy")

    def test_scvi_tools_routes_to_scanpy_for_single_cell_latent_models(self) -> None:
        self.assert_selected("用 scVI 和 scANVI 做 single-cell batch correction、latent model 和 cell type annotation", "scanpy")

    def test_deeptools_no_longer_routes_as_direct_owner_for_ngs_tracks(self) -> None:
        self.assert_not_selected("用 deepTools 把 BAM 转 bigWig，并围绕 TSS 画 ChIP-seq heatmap profile", "deeptools")

    def test_bio_database_evidence_routes_for_cross_database_queries(self) -> None:
        self.assert_selected("用 BioServices 同时查询 UniProt、KEGG、Reactome 并做 ID mapping", "bio-database-evidence")

    def test_bio_database_evidence_routes_for_variant_pathway_and_target_sources(self) -> None:
        self.assert_selected(
            "查询 ClinVar、COSMIC、GWAS Catalog、KEGG、Reactome 和 Open Targets 的生物数据库证据",
            "bio-database-evidence",
        )

    def test_bio_database_evidence_routes_for_structure_ppi_and_census_sources(self) -> None:
        self.assert_selected(
            "查询 AlphaFold Database、RCSB PDB、STRING API 和 CZ CELLxGENE Census 的 evidence metadata",
            "bio-database-evidence",
        )


if __name__ == "__main__":
    unittest.main()
