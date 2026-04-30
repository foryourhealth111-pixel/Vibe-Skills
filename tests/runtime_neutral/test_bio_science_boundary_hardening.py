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


class BioScienceBoundaryHardeningTests(unittest.TestCase):
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

    def test_geniml_owns_bed_genomic_interval_embeddings(self) -> None:
        self.assert_selected(
            "对 BED genomic intervals 做 embeddings 和 similarity search。",
            "bio-science",
            "geniml",
        )

    def test_negated_genomic_ml_does_not_route_to_geniml(self) -> None:
        self.assert_not_selected(
            "用 random forest 对普通临床表格做 machine learning，不是 genomic ML。",
            "bio-science",
            "geniml",
        )

    def test_chinese_bu_shi_negation_keeps_flowio_from_stealing_scanpy(self) -> None:
        self.assert_selected(
            "做 single-cell RNA-seq clustering 和 UMAP，不是 flow cytometry，也不是 FCS 文件解析。",
            "bio-science",
            "scanpy",
        )

    def test_biopython_owns_sequence_conversion(self) -> None:
        self.assert_selected(
            "用 Biopython SeqIO 把 FASTA 转 GenBank，并通过 Entrez 拉取序列记录",
            "bio-science",
            "biopython",
        )

    def test_anndata_owns_container_editing(self) -> None:
        self.assert_selected(
            "编辑 AnnData h5ad 文件的 obs/var 元数据、layers 和 backed mode",
            "bio-science",
            "anndata",
        )

    def test_scvi_tools_owns_latent_single_cell_models(self) -> None:
        self.assert_selected(
            "用 scVI 训练 single-cell latent model 做 batch correction 和 scANVI 注释",
            "bio-science",
            "scvi-tools",
        )

    def test_cellxgene_owns_census_queries(self) -> None:
        self.assert_selected(
            "查询 CELLxGENE Census 里 human lung epithelial cells 的 tissue disease metadata",
            "bio-science",
            "cellxgene-census",
        )

    def test_pydeseq2_owns_bulk_rnaseq_de(self) -> None:
        self.assert_selected(
            "用 PyDESeq2 对 bulk RNA-seq count matrix 做 Wald test、FDR 和 volcano plot",
            "bio-science",
            "pydeseq2",
        )

    def test_pysam_owns_alignment_variant_files(self) -> None:
        self.assert_selected(
            "用 pysam 读取 BAM/CRAM/VCF 做 pileup、coverage 和 region extraction",
            "bio-science",
            "pysam",
        )

    def test_deeptools_owns_genomics_signal_tracks(self) -> None:
        self.assert_selected(
            "用 deepTools bamCoverage 把 BAM 转 bigWig，并用 computeMatrix plotHeatmap 围绕 TSS 作图",
            "bio-science",
            "deeptools",
        )

    def test_bioservices_owns_explicit_multi_service_aggregation(self) -> None:
        self.assert_selected(
            "用 BioServices 同时查询 UniProt、KEGG、Reactome 并做跨数据库 ID mapping",
            "bio-science",
            "bioservices",
        )

    def test_gget_owns_quick_lookup(self) -> None:
        self.assert_selected(
            "用 gget 做 quick BLAST、gene symbol 和 transcript lookup",
            "bio-science",
            "gget",
        )

    def test_cobrapy_owns_flux_balance_analysis(self) -> None:
        self.assert_selected(
            "用 COBRApy 构建 metabolic model 并做 FBA flux balance analysis",
            "bio-science",
            "cobrapy",
        )

    def test_esm_owns_protein_embeddings(self) -> None:
        self.assert_selected(
            "用 ESM protein language model 生成蛋白 embedding，不做 Biopython 序列解析",
            "bio-science",
            "esm",
        )

    def test_flowio_owns_real_fcs_flow_cytometry(self) -> None:
        self.assert_selected(
            "读取 FCS flow cytometry 文件，提取 channel matrix 和 compensation",
            "bio-science",
            "flowio",
        )

    def test_scanpy_loses_to_anndata_for_container_only_work(self) -> None:
        self.assert_selected(
            "只需要整理 h5ad AnnData 的 obs、var、layers、raw 和 backed mode，不做聚类分析",
            "bio-science",
            "anndata",
        )

    def test_scanpy_loses_to_cellxgene_for_census_query(self) -> None:
        self.assert_selected(
            "从 CELLxGENE Census 下载细胞图谱，然后在后续可能用 scanpy 分析",
            "bio-science",
            "cellxgene-census",
        )

    def test_biopython_loses_to_pysam_for_bam_vcf_files(self) -> None:
        self.assert_selected(
            "解析 BAM/VCF 文件，计算 coverage 和 pileup，不做序列格式转换",
            "bio-science",
            "pysam",
        )

    def test_bioservices_loses_to_kegg_for_explicit_kegg_rest(self) -> None:
        self.assert_selected(
            "用 KEGG REST 做 pathway mapping、ID conversion 和 metabolic pathway 查询，不使用 BioServices",
            "bio-science",
            "kegg-database",
        )

    def test_bioservices_loses_to_reactome_for_explicit_reactome(self) -> None:
        self.assert_selected(
            "用 Reactome API 做 pathway enrichment 和 gene-pathway mapping，不使用 BioServices",
            "bio-science",
            "reactome-database",
        )

    def test_gget_loses_to_opentargets_for_target_evidence(self) -> None:
        self.assert_selected(
            "用 Open Targets 做 target-disease association、tractability 和 known drugs evidence，不使用 gget",
            "bio-science",
            "opentargets-database",
        )

    def test_rdkit_smiles_stays_in_chem_drug_pack(self) -> None:
        self.assert_selected(
            "用 RDKit 处理 SMILES、Morgan fingerprints 和分子描述符",
            "science-chem-drug",
            "rdkit",
        )

    def test_pubmed_bibtex_stays_in_literature_pack(self) -> None:
        self.assert_selected(
            "做 PubMed 文献综述，导出 BibTeX 和引用格式",
            "science-literature-citations",
            "citation-management",
        )

    def test_clinicaltrials_stays_in_clinical_regulatory_pack(self) -> None:
        self.assert_selected(
            "查询 ClinicalTrials.gov NCT 试验入排标准和 endpoint",
            "science-clinical-regulatory",
            "clinicaltrials-database",
        )

    def test_dicom_tags_stay_in_medical_imaging_pack(self) -> None:
        self.assert_selected(
            "用 pydicom 读取 DICOM metadata 和影像 tag",
            "science-medical-imaging",
            "pydicom",
        )

    def test_generic_scikit_learn_stays_in_data_ml_pack(self) -> None:
        self.assert_selected(
            "用 scikit-learn random forest 对普通 tabular data 做监督学习和交叉验证",
            "data-ml",
            "scikit-learn",
        )

    def test_result_figures_stay_in_scientific_visualization_pack(self) -> None:
        self.assert_selected(
            "把机器学习模型评估结果做成投稿级结果图，600dpi，多面板，色盲友好",
            "science-figures-visualization",
            "scientific-visualization",
        )

    def test_latex_pdf_stays_in_submission_pipeline(self) -> None:
        self.assert_selected(
            "用 LaTeX 写成论文 PDF，latexmk 编译，生成可投稿 PDF",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
        )


if __name__ == "__main__":
    unittest.main()
