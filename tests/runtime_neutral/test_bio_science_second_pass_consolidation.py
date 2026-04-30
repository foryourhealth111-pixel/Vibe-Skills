from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


BIO_SCIENCE_DIRECT_OWNERS = [
    "biopython",
    "scanpy",
    "pydeseq2",
    "bio-database-evidence",
]

PRUNED_DIRECT_SKILLS = [
    "anndata",
    "scvi-tools",
    "pysam",
    "deeptools",
    "esm",
    "cobrapy",
    "geniml",
    "arboreto",
    "flowio",
]

MERGED_DATABASE_SKILLS = [
    "alphafold-database",
    "bioservices",
    "cellxgene-census",
    "clinvar-database",
    "cosmic-database",
    "ensembl-database",
    "gene-database",
    "gget",
    "gwas-database",
    "kegg-database",
    "opentargets-database",
    "pdb-database",
    "reactome-database",
    "string-database",
]

REMOVED_BIO_SCIENCE_SKILLS = MERGED_DATABASE_SKILLS + PRUNED_DIRECT_SKILLS


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def pack_by_id(pack_id: str) -> dict[str, object]:
    manifest = load_json("config/pack-manifest.json")
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


def route(prompt: str, task_type: str = "research", grade: str = "M") -> dict[str, object]:
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


class BioScienceSecondPassConsolidationTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def assert_not_selected(
        self,
        prompt: str,
        blocked_pack: str,
        blocked_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual((blocked_pack, blocked_skill), selected(result), ranked_summary(result))

    def test_bio_science_manifest_has_four_direct_owners(self) -> None:
        pack = pack_by_id("bio-science")

        self.assertEqual(BIO_SCIENCE_DIRECT_OWNERS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertEqual(
            {
                "planning": "biopython",
                "coding": "biopython",
                "research": "scanpy",
            },
            pack.get("defaults_by_task"),
        )

    def test_removed_bio_science_skills_are_absent_from_live_surfaces(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")
        skills_lock = load_json("config/skills-lock.json")

        keyword_skills = keyword_index.get("skills") or {}
        routing_skills = routing_rules.get("skills") or {}
        lock_skills = skills_lock.get("skills") or []
        lock_names = {
            str(item.get("name"))
            for item in lock_skills
            if isinstance(item, dict) and item.get("name")
        }

        self.assertIn("bio-database-evidence", keyword_skills)
        self.assertIn("bio-database-evidence", routing_skills)
        self.assertTrue((REPO_ROOT / "bundled" / "skills" / "bio-database-evidence").exists())

        for skill_id in REMOVED_BIO_SCIENCE_SKILLS:
            self.assertNotIn(skill_id, keyword_skills)
            self.assertNotIn(skill_id, routing_skills)
            self.assertNotIn(skill_id, lock_names)
            self.assertFalse((REPO_ROOT / "bundled" / "skills" / skill_id).exists())

    def test_bio_database_evidence_owns_biological_database_lookup(self) -> None:
        self.assert_selected(
            "查询 ClinVar COSMIC Ensembl GWAS KEGG Reactome Open Targets PDB STRING 的生物数据库证据",
            "bio-science",
            "bio-database-evidence",
        )

    def test_bio_database_evidence_owns_quick_gene_lookup(self) -> None:
        self.assert_selected(
            "快速查询 TP53 gene symbol、Ensembl ID、NCBI Gene metadata 和 RefSeq 注释",
            "bio-science",
            "bio-database-evidence",
        )

    def test_bio_database_evidence_owns_structure_and_ppi_evidence(self) -> None:
        self.assert_selected(
            "查询 AlphaFold predicted structure、RCSB PDB 坐标和 STRING protein interaction network",
            "bio-science",
            "bio-database-evidence",
        )

    def test_scanpy_still_owns_single_cell_analysis(self) -> None:
        self.assert_selected(
            "做 single-cell RNA-seq 聚类、UMAP、marker genes 和细胞注释",
            "bio-science",
            "scanpy",
        )

    def test_pydeseq2_still_owns_bulk_differential_expression(self) -> None:
        self.assert_selected(
            "bulk RNA-seq count matrix 做 DESeq2 差异表达、Wald test、FDR 和 volcano plot",
            "bio-science",
            "pydeseq2",
        )

    def test_scanpy_absorbs_anndata_container_work(self) -> None:
        self.assert_selected(
            "用 AnnData 读写 h5ad，管理 obs/var 元数据和 backed mode 稀疏矩阵",
            "bio-science",
            "scanpy",
        )

    def test_scanpy_absorbs_scvi_latent_model_work(self) -> None:
        self.assert_selected(
            "用 scVI 和 scANVI 做 single-cell batch correction、latent model 和 cell type annotation",
            "bio-science",
            "scanpy",
        )

    def test_pruned_cold_direct_skills_are_not_selected(self) -> None:
        blocked_cases = [
            ("读取 BAM VCF 做 pileup、coverage 和 region extraction", "pysam"),
            ("用 deepTools bamCoverage computeMatrix plotHeatmap 生成 ChIP-seq profile", "deeptools"),
            ("用 ESM protein language model 做 protein embedding 和 inverse folding", "esm"),
            ("用 COBRApy 做 FBA flux balance analysis 和 SBML metabolic model", "cobrapy"),
            ("对 BED genomic intervals 做 Region2Vec embedding 和 regulatory region similarity", "geniml"),
            ("用 pySCENIC 和 arboreto 推断 gene regulatory network", "arboreto"),
            ("读取 FCS flow cytometry 文件，提取 channel matrix", "flowio"),
        ]
        for prompt, skill_id in blocked_cases:
            with self.subTest(skill_id=skill_id):
                self.assert_not_selected(prompt, "bio-science", skill_id)

    def test_rdkit_stays_in_chem_drug(self) -> None:
        self.assert_selected(
            "用 RDKit 处理 SMILES 和 Morgan fingerprint",
            "science-chem-drug",
            "rdkit",
        )

    def test_pubmed_bibtex_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "检索 PubMed 文献并导出 BibTeX 引用",
            "science-literature-citations",
            "pubmed-database",
        )

    def test_latex_build_stays_in_submission_pipeline(self) -> None:
        self.assert_selected(
            "用 LaTeX 构建论文 PDF 和 submission zip",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            task_type="coding",
        )

    def test_result_figures_stay_in_scientific_visualization(self) -> None:
        self.assert_selected(
            "绘制论文结果图、统计图和多面板 figure",
            "science-figures-visualization",
            "scientific-visualization",
        )


if __name__ == "__main__":
    unittest.main()
