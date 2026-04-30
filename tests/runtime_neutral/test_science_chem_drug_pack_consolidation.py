from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEPT_SKILLS = [
    "chembl-database",
    "medchem",
    "rdkit",
]

DELETED_SKILLS = [
    "drugbank-database",
    "pubchem-database",
    "brenda-database",
    "hmdb-database",
    "zinc-database",
    "deepchem",
    "diffdock",
    "pytdc",
    "datamol",
    "molfeat",
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


class ScienceChemDrugPackConsolidationTests(unittest.TestCase):
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

    def assert_not_science_chem_drug(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("science-chem-drug", selected(result)[0], ranked_summary(result))

    def test_manifest_shrinks_to_three_route_owners(self) -> None:
        pack = pack_by_id("science-chem-drug")
        self.assertEqual(KEPT_SKILLS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_deleted_skills_removed_from_manifest_and_disk(self) -> None:
        pack = pack_by_id("science-chem-drug")
        candidates = set(pack.get("skill_candidates") or [])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        for skill in DELETED_SKILLS:
            self.assertNotIn(skill, candidates)
            self.assertFalse((REPO_ROOT / "bundled" / "skills" / skill).exists(), skill)

    def test_defaults_match_kept_route_owners(self) -> None:
        pack = pack_by_id("science-chem-drug")
        self.assertEqual(
            {
                "planning": "medchem",
                "coding": "rdkit",
                "research": "chembl-database",
            },
            pack.get("defaults_by_task"),
        )

    def test_rdkit_fingerprint_routes_to_rdkit(self) -> None:
        self.assert_selected(
            "用RDKit解析SMILES并计算Morgan fingerprint",
            "science-chem-drug",
            "rdkit",
        )

    def test_chembl_activity_routes_to_chembl(self) -> None:
        self.assert_selected(
            "在 ChEMBL 查询 EGFR 靶点的 IC50 / Ki / Kd 活性数据，并导出 assay 表格",
            "science-chem-drug",
            "chembl-database",
            grade="M",
        )

    def test_medchem_sar_routes_to_medchem(self) -> None:
        self.assert_selected(
            "做药物化学 SAR 分析、PAINS 过滤、Lipinski 规则和先导化合物优化建议",
            "science-chem-drug",
            "medchem",
            task_type="planning",
        )

    def test_deleted_cold_specialists_do_not_route_to_chem_drug(self) -> None:
        prompts = [
            "查询 DrugBank 中华法林和阿司匹林的药物相互作用、靶点和药理信息",
            "查询 PubChem CID、PUG-REST 和化合物编号",
            "从 ZINC 下载可购买小分子库用于 virtual screening",
            "在 BRENDA 查询某个 EC number 的 Km、kcat、Vmax 和酶动力学参数",
            "在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification",
            "用 DiffDock 做 docking pose prediction，输入 PDB 和 ligand",
            "用 DeepChem 训练 MoleculeNet 毒性预测模型和 GNN",
            "用 Therapeutics Data Commons / PyTDC 加载 benchmark 数据集并做 scaffold split",
            "用 MolFeat 生成 ChemBERTa embedding 用于分子机器学习",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assert_not_science_chem_drug(prompt, grade="M")

    def test_datamol_compat_prompt_routes_to_rdkit(self) -> None:
        self.assert_selected(
            "用 datamol 批量标准化 SMILES 并生成分子指纹",
            "science-chem-drug",
            "rdkit",
            task_type="coding",
            grade="M",
        )

    def test_bulk_rnaseq_does_not_route_to_chem_drug(self) -> None:
        self.assert_not_science_chem_drug(
            "分析 bulk RNA-seq 差异表达，做 GO KEGG 富集和 volcano plot",
        )

    def test_pubmed_bibtex_does_not_route_to_chem_drug(self) -> None:
        self.assert_selected(
            "在 PubMed 检索文献并导出 BibTeX",
            "science-literature-citations",
            "pubmed-database",
        )

    def test_clinical_trials_does_not_route_to_chem_drug(self) -> None:
        self.assert_selected(
            "在 ClinicalTrials.gov 按 NCT 编号查询临床试验入排标准和终点",
            "science-clinical-regulatory",
            "clinicaltrials-database",
        )


if __name__ == "__main__":
    unittest.main()
