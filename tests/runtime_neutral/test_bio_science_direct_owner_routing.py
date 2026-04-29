from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


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


class BioScienceDirectOwnerRoutingTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual(("bio-science", expected_skill), selected(result), ranked_summary(result))

    def test_anndata_routes_as_direct_owner_for_h5ad_container_work(self) -> None:
        self.assert_selected("用 AnnData 读写 h5ad，管理 obs/var 元数据和 backed mode 稀疏矩阵", "anndata")

    def test_scvi_tools_routes_as_direct_owner_for_single_cell_latent_models(self) -> None:
        self.assert_selected("用 scVI 和 scANVI 做 single-cell batch correction、latent model 和 cell type annotation", "scvi-tools")

    def test_deeptools_routes_as_direct_owner_for_ngs_tracks(self) -> None:
        self.assert_selected("用 deepTools 把 BAM 转 bigWig，并围绕 TSS 画 ChIP-seq heatmap profile", "deeptools")

    def test_bioservices_routes_as_direct_owner_for_cross_database_queries(self) -> None:
        self.assert_selected("用 BioServices 同时查询 UniProt、KEGG、Reactome 并做 ID mapping", "bioservices")

    def test_alphafold_routes_as_direct_owner_for_predicted_structures(self) -> None:
        self.assert_selected("从 AlphaFold Database 按 UniProt ID 下载 mmCIF，并检查 pLDDT 和 PAE", "alphafold-database")

    def test_clinvar_routes_as_direct_owner_for_variant_significance(self) -> None:
        self.assert_selected("查询 ClinVar 中 BRCA1 variant 的 clinical significance、VUS 和 review stars", "clinvar-database")

    def test_cosmic_routes_as_direct_owner_for_cancer_mutations(self) -> None:
        self.assert_selected("查询 COSMIC cancer mutation、Cancer Gene Census 和 mutational signatures", "cosmic-database")

    def test_ensembl_routes_as_direct_owner_for_vep_and_orthologs(self) -> None:
        self.assert_selected("用 Ensembl REST 查询 gene、orthologs、VEP variant effect 和坐标转换", "ensembl-database")

    def test_gene_database_routes_as_direct_owner_for_ncbi_gene(self) -> None:
        self.assert_selected("用 NCBI Gene 查询 TP53 symbol、RefSeq、GO annotation 和基因位置", "gene-database")

    def test_gwas_routes_as_direct_owner_for_trait_associations(self) -> None:
        self.assert_selected("查询 GWAS Catalog 中 rs ID、trait association、p-value 和 summary statistics", "gwas-database")

    def test_kegg_routes_as_direct_owner_for_pathway_id_mapping(self) -> None:
        self.assert_selected("用 KEGG REST 做 pathway mapping、ID conversion 和 metabolic pathway 查询", "kegg-database")

    def test_opentargets_routes_as_direct_owner_for_target_disease_evidence(self) -> None:
        self.assert_selected("用 Open Targets 查询 target-disease association、tractability、safety 和 known drugs", "opentargets-database")

    def test_pdb_routes_as_direct_owner_for_experimental_structures(self) -> None:
        self.assert_selected("在 RCSB PDB 按 sequence similarity 搜索结构并下载 PDB/mmCIF 坐标", "pdb-database")

    def test_reactome_routes_as_direct_owner_for_pathway_enrichment(self) -> None:
        self.assert_selected("用 Reactome 做 pathway enrichment、gene-pathway mapping 和 disease pathway 分析", "reactome-database")

    def test_string_routes_as_direct_owner_for_ppi_networks(self) -> None:
        self.assert_selected("用 STRING API 查询 protein-protein interaction network、GO enrichment 和 hub proteins", "string-database")

    def test_cellxgene_routes_as_direct_owner_for_census_queries(self) -> None:
        self.assert_selected("查询 CZ CELLxGENE Census 的 human lung epithelial cells expression data 和 metadata", "cellxgene-census")


if __name__ == "__main__":
    unittest.main()
