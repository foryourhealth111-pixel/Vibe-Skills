# Science Chem Drug Pack Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate `science-chem-drug` into an 11-skill direct route-authority pack with no assistant/consult routing semantics and protected boundaries for chem databases, RDKit, medicinal chemistry, docking, molecular ML, and therapeutic benchmarks.

**Architecture:** Add focused route tests first, then shrink `skill_candidates` directly because the router selects from pack candidates. Keep `route_authority_candidates` as a compatibility mirror of the selectable 11 skills and make `stage_assistant_candidates` explicitly empty. Tighten keyword and routing rules so `datamol` routes to `rdkit`, `molfeat` routes by problem context to `deepchem` or `rdkit`, and non-chem prompts stay out of this pack.

**Tech Stack:** Python `unittest`/pytest route tests, PowerShell route probes, JSON config files, lock/parity verification scripts, Markdown governance docs.

---

## File Map

- Create: `tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py`
- Modify: `config/pack-manifest.json`
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Modify: `bundled/skills/vibe/config/pack-manifest.json`
- Modify: `bundled/skills/vibe/config/skill-keyword-index.json`
- Modify: `bundled/skills/vibe/config/skill-routing-rules.json`
- Modify: `scripts/verify/probe-scientific-packs.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Create: `docs/governance/science-chem-drug-pack-consolidation-2026-04-29.md`
- Modify: `config/skills-lock.json` after running `.\scripts\verify\vibe-generate-skills-lock.ps1`

No bundled skill directory should be physically deleted in this plan.

## Task 1: Add Focused Failing Tests

**Files:**
- Create: `tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py`

- [ ] **Step 1: Create the route and manifest test file**

Use `apply_patch` to add this exact file:

```python
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
    "drugbank-database",
    "pubchem-database",
    "brenda-database",
    "hmdb-database",
    "zinc-database",
    "deepchem",
    "medchem",
    "rdkit",
    "diffdock",
    "pytdc",
]

MOVED_OUT_SKILLS = [
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

    def test_manifest_shrinks_to_eleven_route_owners(self) -> None:
        pack = pack_by_id("science-chem-drug")
        self.assertEqual(KEPT_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(KEPT_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))

    def test_manifest_removes_helper_overlap_skills(self) -> None:
        pack = pack_by_id("science-chem-drug")
        candidates = set(pack.get("skill_candidates") or [])
        for skill in MOVED_OUT_SKILLS:
            self.assertNotIn(skill, candidates)

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

    def test_drugbank_interaction_routes_to_drugbank(self) -> None:
        self.assert_selected(
            "查询 DrugBank 中华法林和阿司匹林的药物相互作用、靶点和药理信息",
            "science-chem-drug",
            "drugbank-database",
            grade="M",
        )

    def test_pubchem_identifier_routes_to_pubchem(self) -> None:
        self.assert_selected(
            "查询 PubChem CID、SMILES、InChI 和化合物物性",
            "science-chem-drug",
            "pubchem-database",
            grade="M",
        )

    def test_zinc_screening_library_routes_to_zinc(self) -> None:
        self.assert_selected(
            "从 ZINC 下载可购买小分子库用于 virtual screening",
            "science-chem-drug",
            "zinc-database",
            grade="M",
        )

    def test_brenda_enzyme_kinetics_routes_to_brenda(self) -> None:
        self.assert_selected(
            "在 BRENDA 查询某个 EC number 的 Km、kcat、Vmax 和酶动力学参数",
            "science-chem-drug",
            "brenda-database",
            grade="M",
        )

    def test_hmdb_metabolite_identification_routes_to_hmdb(self) -> None:
        self.assert_selected(
            "在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification",
            "science-chem-drug",
            "hmdb-database",
            grade="M",
        )

    def test_medchem_sar_routes_to_medchem(self) -> None:
        self.assert_selected(
            "做药物化学 SAR 分析、PAINS 过滤、Lipinski 规则和先导化合物优化建议",
            "science-chem-drug",
            "medchem",
            task_type="planning",
        )

    def test_diffdock_pose_routes_to_diffdock(self) -> None:
        self.assert_selected(
            "用 DiffDock 做 protein-ligand docking pose prediction，输入 PDB 和 SMILES",
            "science-chem-drug",
            "diffdock",
            task_type="coding",
        )

    def test_deepchem_admet_model_routes_to_deepchem(self) -> None:
        self.assert_selected(
            "用 DeepChem 训练分子属性预测模型，做 scaffold split、ADMET 毒性预测和 GNN",
            "science-chem-drug",
            "deepchem",
            task_type="coding",
        )

    def test_pytdc_benchmark_routes_to_pytdc(self) -> None:
        self.assert_selected(
            "用 Therapeutics Data Commons / PyTDC 加载 ADMET benchmark 数据集并做 scaffold split",
            "science-chem-drug",
            "pytdc",
        )

    def test_datamol_prompt_routes_to_rdkit(self) -> None:
        self.assert_selected(
            "用 datamol 批量标准化 SMILES 并生成分子指纹",
            "science-chem-drug",
            "rdkit",
            task_type="coding",
            grade="M",
        )

    def test_molfeat_embedding_prompt_routes_to_deepchem(self) -> None:
        self.assert_selected(
            "用 MolFeat 生成 ChemBERTa 分子 embedding 和 ECFP 特征用于分子机器学习",
            "science-chem-drug",
            "deepchem",
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
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
```

Expected: fails because `science-chem-drug` still has 13 candidates, lacks `route_authority_candidates`, lacks explicit empty `stage_assistant_candidates`, and routes at least some new probes incorrectly.

- [ ] **Step 3: Commit the failing tests**

Run:

```powershell
git add tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py
git commit -m "test: cover science chem drug routing boundaries"
```

## Task 2: Shrink The Pack Manifest

**Files:**
- Modify: `config/pack-manifest.json`
- Modify: `bundled/skills/vibe/config/pack-manifest.json`

- [ ] **Step 1: Update the top-level pack manifest**

In `config/pack-manifest.json`, replace the `science-chem-drug` object with this target content while preserving neighboring packs:

```json
{
  "id": "science-chem-drug",
  "priority": 91,
  "grade_allow": [
    "M",
    "L",
    "XL"
  ],
  "task_allow": [
    "planning",
    "coding",
    "research"
  ],
  "trigger_keywords": [
    "chembl",
    "drugbank",
    "pubchem",
    "brenda",
    "hmdb",
    "zinc",
    "rdkit",
    "smiles",
    "inchi",
    "admet",
    "ic50",
    "ki",
    "kd",
    "docking",
    "binding pose",
    "virtual screening",
    "ligand",
    "molecule",
    "cheminformatics",
    "therapeutics data commons",
    "药化",
    "化合物",
    "小分子",
    "分子对接",
    "结合构象",
    "虚拟筛选",
    "药物相互作用",
    "酶动力学",
    "代谢物鉴定"
  ],
  "skill_candidates": [
    "chembl-database",
    "drugbank-database",
    "pubchem-database",
    "brenda-database",
    "hmdb-database",
    "zinc-database",
    "deepchem",
    "medchem",
    "rdkit",
    "diffdock",
    "pytdc"
  ],
  "route_authority_candidates": [
    "chembl-database",
    "drugbank-database",
    "pubchem-database",
    "brenda-database",
    "hmdb-database",
    "zinc-database",
    "deepchem",
    "medchem",
    "rdkit",
    "diffdock",
    "pytdc"
  ],
  "stage_assistant_candidates": [],
  "defaults_by_task": {
    "planning": "medchem",
    "coding": "rdkit",
    "research": "chembl-database"
  }
}
```

- [ ] **Step 2: Copy the manifest to the bundled Vibe config**

Run:

```powershell
Copy-Item -LiteralPath config\pack-manifest.json -Destination bundled\skills\vibe\config\pack-manifest.json -Force
```

Expected: `git diff -- config/pack-manifest.json bundled/skills/vibe/config/pack-manifest.json` shows the same `science-chem-drug` changes in both files.

- [ ] **Step 3: Run the focused test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
```

Expected: manifest tests pass; route tests may still fail because keyword/routing rules are not yet tightened.

- [ ] **Step 4: Commit manifest changes**

Run:

```powershell
git add config/pack-manifest.json bundled/skills/vibe/config/pack-manifest.json
git commit -m "fix: shrink science chem drug route candidates"
```

## Task 3: Tighten Keyword And Routing Rules

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Modify: `bundled/skills/vibe/config/skill-keyword-index.json`
- Modify: `bundled/skills/vibe/config/skill-routing-rules.json`

- [ ] **Step 1: Update keyword-index entries**

In `config/skill-keyword-index.json`, set the relevant entries to these keyword arrays:

```json
"chembl-database": {
  "keywords": ["chembl", "bioactivity", "assay", "ic50", "ki", "kd", "target activity", "chembl target", "活性数据", "靶点活性", "药物靶点活性"]
},
"drugbank-database": {
  "keywords": ["drugbank", "drug interaction", "drug-drug interaction", "drug target", "pharmacology", "atc", "药物相互作用", "药物靶点", "药理信息"]
},
"pubchem-database": {
  "keywords": ["pubchem", "cid", "pug-rest", "compound property", "smiles", "inchi", "molecular formula", "化合物物性", "化合物编号", "化学结构"]
},
"brenda-database": {
  "keywords": ["brenda", "ec number", "enzyme kinetics", "km", "kcat", "vmax", "substrate specificity", "酶动力学", "酶参数", "酶底物"]
},
"hmdb-database": {
  "keywords": ["hmdb", "metabolite", "metabolomics", "ms/ms", "nmr", "metabolite identification", "biomarker", "代谢物", "代谢组", "代谢物鉴定"]
},
"zinc-database": {
  "keywords": ["zinc", "zinc id", "purchasable compounds", "virtual screening library", "compound library", "vendor compound", "可购买小分子", "化合物库", "虚拟筛选库"]
},
"datamol": {
  "keywords": ["datamol"]
},
"deepchem": {
  "keywords": ["deepchem", "molecular ml", "molecular machine learning", "admet prediction", "toxicity prediction", "moleculenet", "graph neural network", "gnn", "chemberta", "molfeat", "molecular embedding", "药物发现", "分子机器学习", "分子属性预测"]
},
"medchem": {
  "keywords": ["medchem", "medicinal chemistry", "sar", "lead optimization", "hit to lead", "pains", "lipinski", "drug-likeness", "药物化学", "构效关系", "先导优化"]
},
"rdkit": {
  "keywords": ["rdkit", "datamol", "smiles", "sdf", "fingerprint", "morgan fingerprint", "descriptor", "substructure", "similarity", "standardize smiles", "logp", "tpsa", "分子指纹", "分子描述符", "分子标准化"]
},
"diffdock": {
  "keywords": ["diffdock", "docking", "protein ligand", "binding pose", "pose prediction", "pdb smiles", "molecular docking", "分子对接", "结合构象", "蛋白配体"]
},
"molfeat": {
  "keywords": ["molfeat"]
},
"pytdc": {
  "keywords": ["pytdc", "tdc", "therapeutics data commons", "admet benchmark", "drug discovery benchmark", "scaffold split", "get_split", "药物发现数据集", "基准数据集"]
}
```

- [ ] **Step 2: Update routing-rule entries**

In `config/skill-routing-rules.json`, set the relevant entries to these route rules:

```json
"chembl-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["chembl", "bioactivity", "assay", "target activity", "ic50", "ki", "kd", "活性数据", "靶点活性"],
  "negative_keywords": ["pubmed", "pmid", "pubchem", "drugbank", "clinicaltrials", "nct", "bulk RNA-seq", "rna-seq", "gene expression", "GO enrichment", "KEGG enrichment", "dicom"],
  "equivalent_group": "chem-db",
  "canonical_for_task": ["research"]
},
"drugbank-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["drugbank", "drug interaction", "drug-drug interaction", "drug target", "pharmacology", "atc", "药物相互作用", "药理信息"],
  "negative_keywords": ["chembl", "pubchem", "brenda", "hmdb", "pubmed", "clinicaltrials", "nct", "bulk RNA-seq", "dicom"],
  "equivalent_group": "chem-db",
  "canonical_for_task": []
},
"pubchem-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["pubchem", "cid", "pug-rest", "compound property", "molecular formula", "smiles", "inchi", "化合物物性", "化合物编号"],
  "negative_keywords": ["pubmed", "pmid", "chembl", "drugbank", "brenda", "hmdb", "zinc", "clinicaltrials", "nct", "bulk RNA-seq", "gene expression"],
  "equivalent_group": "chem-db",
  "canonical_for_task": ["research"]
},
"brenda-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["brenda", "ec number", "enzyme kinetics", "kinetics", "km", "kcat", "vmax", "substrate specificity", "酶动力学", "酶参数"],
  "negative_keywords": ["docking", "pose", "diffdock", "pubchem", "drugbank", "clinical trial", "dicom", "pubmed"],
  "equivalent_group": "chem-db",
  "canonical_for_task": ["research"]
},
"hmdb-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["hmdb", "metabolite", "metabolomics", "ms/ms", "nmr", "metabolite identification", "biomarker", "代谢物", "代谢组", "代谢物鉴定"],
  "negative_keywords": ["patent", "uspto", "drugbank", "clinical trial", "nct", "pubmed", "bulk RNA-seq", "dicom"],
  "equivalent_group": "chem-db",
  "canonical_for_task": []
},
"zinc-database": {
  "task_allow": ["research", "coding"],
  "positive_keywords": ["zinc", "zinc id", "purchasable compounds", "virtual screening library", "compound library", "vendor compound", "可购买小分子", "筛选库", "化合物库"],
  "negative_keywords": ["pubmed", "pmid", "chembl", "drugbank", "clinical trial", "dicom", "bulk RNA-seq"],
  "equivalent_group": "chem-db",
  "canonical_for_task": []
},
"datamol": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["datamol"],
  "negative_keywords": ["rdkit", "smiles", "fingerprint", "descriptor", "clinical trial", "dicom", "pubmed"],
  "equivalent_group": "chem-toolkit",
  "canonical_for_task": []
},
"deepchem": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["deepchem", "molecular ml", "molecular machine learning", "admet prediction", "toxicity prediction", "moleculenet", "graphconv", "graph neural network", "gnn", "chemberta", "molfeat", "molecular embedding", "分子机器学习", "分子属性预测"],
  "negative_keywords": ["excel", "pptx", "pubmed", "clinical trial", "drugbank interaction", "cid lookup", "brenda", "hmdb", "zinc library"],
  "equivalent_group": "chem-toolkit",
  "canonical_for_task": ["coding"]
},
"medchem": {
  "task_allow": ["planning", "research"],
  "positive_keywords": ["medchem", "medicinal chemistry", "sar", "lead optimization", "hit to lead", "pains", "lipinski", "drug-likeness", "药物化学", "构效关系", "先导优化"],
  "negative_keywords": ["dicom", "clinicaltrials", "pubmed", "brenda", "hmdb", "zinc id", "pdb"],
  "equivalent_group": "chem-strategy",
  "canonical_for_task": ["planning"]
},
"rdkit": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["rdkit", "datamol", "smiles", "sdf", "fingerprint", "morgan fingerprint", "descriptor", "substructure", "similarity", "standardize smiles", "molecule standardization", "logp", "tpsa", "分子指纹", "分子描述符", "分子标准化"],
  "negative_keywords": ["pubmed", "pmid", "chembl", "drugbank", "pubchem cid", "brenda", "hmdb", "zinc", "clinical trial", "nct", "bulk RNA-seq", "gene expression", "dicom"],
  "equivalent_group": "chem-toolkit",
  "canonical_for_task": ["coding"]
},
"diffdock": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["diffdock", "docking", "protein ligand", "binding pose", "pose prediction", "pdb smiles", "molecular docking", "分子对接", "结合构象", "蛋白配体"],
  "negative_keywords": ["pubmed", "citation", "zinc library", "compound library", "clinical trial", "drug interaction", "admet benchmark"],
  "equivalent_group": "chem-docking",
  "canonical_for_task": ["coding"]
},
"molfeat": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["molfeat"],
  "negative_keywords": ["deepchem", "chemberta", "embedding", "fingerprint", "ecfp", "rdkit", "clinical", "dicom", "pubmed"],
  "equivalent_group": "chem-toolkit",
  "canonical_for_task": []
},
"pytdc": {
  "task_allow": ["coding", "research"],
  "positive_keywords": ["pytdc", "tdc", "therapeutics data commons", "admet benchmark", "drug discovery benchmark", "get_split", "scaffold split", "药物发现数据集", "基准数据集"],
  "negative_keywords": ["pubmed", "pmid", "deepchem training", "gnn", "drugbank interaction", "pubchem cid", "brenda", "hmdb"],
  "equivalent_group": "chem-datasets",
  "canonical_for_task": []
}
```

- [ ] **Step 3: Copy updated routing configs to bundled Vibe config**

Run:

```powershell
Copy-Item -LiteralPath config\skill-keyword-index.json -Destination bundled\skills\vibe\config\skill-keyword-index.json -Force
Copy-Item -LiteralPath config\skill-routing-rules.json -Destination bundled\skills\vibe\config\skill-routing-rules.json -Force
```

- [ ] **Step 4: Run the focused test and inspect failures**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
```

Expected: all tests pass or remaining failures identify exact keyword weights to adjust in the same config files. Keep the selected route contract from Task 1 unchanged.

- [ ] **Step 5: Commit keyword and routing changes**

Run:

```powershell
git add config/skill-keyword-index.json config/skill-routing-rules.json bundled/skills/vibe/config/skill-keyword-index.json bundled/skills/vibe/config/skill-routing-rules.json
git commit -m "fix: tighten science chem drug routing rules"
```

## Task 4: Extend Scientific And Index Route Probes

**Files:**
- Modify: `scripts/verify/probe-scientific-packs.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`

- [ ] **Step 1: Expand the `science-chem-drug` block in `probe-scientific-packs.ps1`**

Replace the three-case chem block with this block:

```powershell
    # science-chem-drug
    [pscustomobject]@{
        name = "chem_rdkit_fingerprint"
        group = "science-chem-drug"
        prompt = "/vibe 用 RDKit 解析 SMILES，计算 Morgan fingerprint，并做相似度检索"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "rdkit"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_chembl_ic50"
        group = "science-chem-drug"
        prompt = "/vibe 在 ChEMBL 查询某靶点的 IC50 / Ki / Kd 活性数据，并输出结构化表格"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "chembl-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_drugbank_interaction"
        group = "science-chem-drug"
        prompt = "/vibe 查询 DrugBank 药物相互作用、药物靶点和药理信息"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "drugbank-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_pubchem_cid"
        group = "science-chem-drug"
        prompt = "/vibe 查询 PubChem CID、SMILES、InChI 和化合物物性"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "pubchem-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_zinc_library"
        group = "science-chem-drug"
        prompt = "/vibe 从 ZINC 下载可购买小分子库用于 virtual screening"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "zinc-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_brenda_kinetics"
        group = "science-chem-drug"
        prompt = "/vibe 在 BRENDA 查询 EC number 的 Km、kcat 和酶动力学参数"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "brenda-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_hmdb_msms"
        group = "science-chem-drug"
        prompt = "/vibe 在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification"
        grade = "M"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "hmdb-database"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_medchem_sar"
        group = "science-chem-drug"
        prompt = "/vibe 做药物化学 SAR 分析、PAINS 过滤和先导化合物优化建议"
        grade = "M"
        task_type = "planning"
        expected_pack = "science-chem-drug"
        expected_skill = "medchem"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_diffdock_pose"
        group = "science-chem-drug"
        prompt = "/vibe 用 DiffDock 做 docking pose prediction：给定 PDB + SMILES 输出结合构象"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "diffdock"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_deepchem_admet_model"
        group = "science-chem-drug"
        prompt = "/vibe 用 DeepChem 训练分子属性预测模型，做 scaffold split、ADMET 毒性预测和 GNN"
        grade = "L"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "deepchem"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_pytdc_admet_benchmark"
        group = "science-chem-drug"
        prompt = "/vibe 用 Therapeutics Data Commons / PyTDC 加载 ADMET benchmark 数据集并做 scaffold split"
        grade = "L"
        task_type = "research"
        expected_pack = "science-chem-drug"
        expected_skill = "pytdc"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_datamol_standardize_routes_rdkit"
        group = "science-chem-drug"
        prompt = "/vibe 用 datamol 批量标准化 SMILES 并生成分子指纹"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "rdkit"
        requested_skill = $null
    },
    [pscustomobject]@{
        name = "chem_molfeat_embedding_routes_deepchem"
        group = "science-chem-drug"
        prompt = "/vibe 用 MolFeat 生成 ChemBERTa 分子 embedding 和 ECFP 特征用于分子机器学习"
        grade = "M"
        task_type = "coding"
        expected_pack = "science-chem-drug"
        expected_skill = "deepchem"
        requested_skill = $null
    },
```

- [ ] **Step 2: Add focused route cases to `vibe-skill-index-routing-audit.ps1`**

Insert these cases immediately after the existing `rdkit smiles not bio` case:

```powershell
    [pscustomobject]@{ Name = "drugbank interaction"; Prompt = "查询 DrugBank 药物相互作用、药物靶点和药理信息"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "drugbank-database" },
    [pscustomobject]@{ Name = "pubchem cid lookup"; Prompt = "查询 PubChem CID、SMILES、InChI 和化合物物性"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "pubchem-database" },
    [pscustomobject]@{ Name = "brenda enzyme kinetics"; Prompt = "在 BRENDA 查询 EC number 的 Km、kcat 和酶动力学参数"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "brenda-database" },
    [pscustomobject]@{ Name = "hmdb metabolite identification"; Prompt = "在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "hmdb-database" },
    [pscustomobject]@{ Name = "deepchem molecular ml"; Prompt = "用 DeepChem 训练分子属性预测模型，做 scaffold split、ADMET 毒性预测和 GNN"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "deepchem" },
    [pscustomobject]@{ Name = "pytdc benchmark dataset"; Prompt = "用 Therapeutics Data Commons / PyTDC 加载 ADMET benchmark 数据集"; Grade = "L"; TaskType = "research"; ExpectedPack = "science-chem-drug"; ExpectedSkill = "pytdc" },
```

- [ ] **Step 3: Run the focused and probe tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected: focused pytest passes; probe scripts report all checked cases passing.

- [ ] **Step 4: Commit probe changes**

Run:

```powershell
git add scripts/verify/probe-scientific-packs.ps1 scripts/verify/vibe-skill-index-routing-audit.ps1
git commit -m "test: expand science chem drug route probes"
```

## Task 5: Add Governance Note

**Files:**
- Create: `docs/governance/science-chem-drug-pack-consolidation-2026-04-29.md`

- [ ] **Step 1: Create the governance note**

Use `apply_patch` to add this exact file:

````markdown
# Science Chem Drug Pack Consolidation

Date: 2026-04-29

## Summary

`science-chem-drug` was consolidated into a direct chem/drug specialist routing pack.

This cleanup keeps the six-stage Vibe runtime unchanged and preserves the binary usage model:

```text
skill_routing.selected -> skill_usage.used / unused
```

No `primary/secondary`, `consult`, `advisory`, or stage-assistant execution semantics were added.

## Before And After

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 13 | 11 |
| `route_authority_candidates` | 0 | 11 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

## Kept Route Authorities

| Skill | Boundary |
| --- | --- |
| `rdkit` | SMILES/SDF parsing, descriptors, Morgan fingerprints, similarity, substructure, reactions, molecular drawing, and datamol-style molecule standardization prompts |
| `medchem` | Drug-likeness, PAINS, Lipinski, structural alerts, SAR, hit-to-lead and lead optimization |
| `diffdock` | Protein-ligand docking pose prediction from PDB plus SMILES |
| `deepchem` | Molecular property prediction, ADMET/toxicity model building, MoleculeNet, GNN, ChemBERTa/MolFeat-style embedding workflows |
| `pytdc` | Therapeutics Data Commons datasets, ADMET benchmarks, scaffold splits, therapeutic ML benchmark access |
| `chembl-database` | Target-ligand bioactivity, IC50/Ki/Kd, assay retrieval, SAR activity tables |
| `drugbank-database` | Approved drug metadata, drug-drug interactions, pharmacology, targets, pathways |
| `pubchem-database` | PubChem CID, SMILES/InChI, formula, compound properties |
| `zinc-database` | ZINC IDs, purchasable compound libraries, virtual-screening source libraries |
| `brenda-database` | BRENDA EC numbers, Km/kcat/Vmax, enzyme kinetics, substrate specificity |
| `hmdb-database` | HMDB IDs, metabolites, MS/MS and NMR reference spectra, metabolomics lookup |

`route_authority_candidates` mirrors `skill_candidates` for compatibility and documentation. The actual simplification is enforced by shrinking `skill_candidates`.

## Moved Out Of Ordinary Routing

| Skill | Reason |
| --- | --- |
| `datamol` | Useful RDKit wrapper, but it does not own a distinct user route; ordinary datamol standardization prompts route to `rdkit` |
| `molfeat` | Useful featurization library, but broad user routes should choose `deepchem` for molecular ML embeddings or `rdkit` for pure fingerprints/descriptors |

Moved-out skills remain on disk. They were not physically deleted because useful references and examples need migration review before deletion.

## Protected Route Boundaries

| Prompt | Expected route |
| --- | --- |
| `用RDKit解析SMILES并计算Morgan fingerprint` | `science-chem-drug / rdkit` |
| `在 ChEMBL 查询某靶点的 IC50 / Ki / Kd 活性数据` | `science-chem-drug / chembl-database` |
| `查询 DrugBank 药物相互作用、药物靶点和药理信息` | `science-chem-drug / drugbank-database` |
| `查询 PubChem CID、SMILES、InChI 和化合物物性` | `science-chem-drug / pubchem-database` |
| `从 ZINC 下载可购买小分子库用于 virtual screening` | `science-chem-drug / zinc-database` |
| `在 BRENDA 查询 EC number 的 Km、kcat 和酶动力学参数` | `science-chem-drug / brenda-database` |
| `在 HMDB 里按 MS/MS 谱和代谢物名称做 metabolite identification` | `science-chem-drug / hmdb-database` |
| `做药物化学 SAR 分析、PAINS 过滤和先导化合物优化建议` | `science-chem-drug / medchem` |
| `用 DiffDock 做 docking pose prediction：给定 PDB + SMILES 输出结合构象` | `science-chem-drug / diffdock` |
| `用 DeepChem 训练分子属性预测模型，做 scaffold split、ADMET 毒性预测和 GNN` | `science-chem-drug / deepchem` |
| `用 Therapeutics Data Commons / PyTDC 加载 ADMET benchmark 数据集` | `science-chem-drug / pytdc` |
| `用 datamol 批量标准化 SMILES 并生成分子指纹` | `science-chem-drug / rdkit` |
| `用 MolFeat 生成 ChemBERTa 分子 embedding 和 ECFP 特征用于分子机器学习` | `science-chem-drug / deepchem` |
| `bulk RNA-seq 差异表达 / GO KEGG 富集` | not `science-chem-drug` |
| `PubMed 检索 / BibTeX / 文献综述` | not `science-chem-drug` |
| `ClinicalTrials.gov / NCT / FDA label` | not `science-chem-drug` |

## Verification

Focused:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
```

Broader probes and gates:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
````

- [ ] **Step 2: Commit the governance note**

Run:

```powershell
git add docs/governance/science-chem-drug-pack-consolidation-2026-04-29.md
git commit -m "docs: record science chem drug boundary"
```

## Task 6: Refresh Lock And Run Full Verification

**Files:**
- Modify: `config/skills-lock.json`

- [ ] **Step 1: Refresh the skills lock**

Run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
```

Expected: `config/skills-lock.json` updates if the lock encodes config routing state. If the command produces no diff, continue without committing this file.

- [ ] **Step 2: Run focused and broad verification**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_science_chem_drug_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

Expected:

```text
focused pytest: passed
probe-scientific-packs: passed
vibe-skill-index-routing-audit: passed
vibe-pack-regression-matrix: passed
vibe-pack-routing-smoke: passed
vibe-offline-skills-gate: passed
vibe-config-parity-gate: passed
git diff --check: no output
```

- [ ] **Step 3: Commit lock refresh if needed**

Run:

```powershell
git status --short
```

If `config/skills-lock.json` is modified, run:

```powershell
git add config/skills-lock.json
git commit -m "chore: refresh skills lock after chem drug routing cleanup"
```

If `config/skills-lock.json` is not modified, make no commit in this step.

- [ ] **Step 4: Final status check**

Run:

```powershell
git status --short --branch
git log --oneline -6
```

Expected: worktree is clean and recent commits include the test, manifest, routing, probe, governance, and lock-refresh commits.

## Self-Review Checklist

- The plan implements every spec requirement from `docs/superpowers/specs/2026-04-29-science-chem-drug-pack-consolidation-design.md`.
- The route model remains binary: selected skill is used, unselected skills are unused.
- `stage_assistant_candidates` is explicitly `[]`.
- `datamol` and `molfeat` are removed from ordinary `science-chem-drug` candidates and remain on disk.
- The plan modifies both top-level config and bundled Vibe config copies.
- The plan adds focused pytest coverage, scientific-pack probes, skill-index audit cases, governance notes, lock refresh, parity gate, and `git diff --check`.
