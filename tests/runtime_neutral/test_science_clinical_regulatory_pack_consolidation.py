from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEPT_SKILLS = [
    "clinicaltrials-database",
    "fda-database",
    "clinpgx-database",
    "clinical-reports",
    "treatment-plans",
    "iso-13485-certification",
    "clinical-decision-support",
]


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


class ScienceClinicalRegulatoryPackConsolidationTests(unittest.TestCase):
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

    def assert_not_clinical_regulatory(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("science-clinical-regulatory", selected(result)[0], ranked_summary(result))

    def test_manifest_keeps_seven_direct_route_owners(self) -> None:
        pack = pack_by_id("science-clinical-regulatory")
        self.assertEqual(KEPT_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(KEPT_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))
        self.assertEqual(
            {
                "planning": "clinical-decision-support",
                "coding": "clinicaltrials-database",
                "review": "clinical-reports",
                "research": "clinicaltrials-database",
            },
            pack.get("defaults_by_task"),
        )

    def test_clinicaltrials_routes_to_clinicaltrials_database(self) -> None:
        self.assert_selected(
            "在 ClinicalTrials.gov 按 NCT 编号 NCT01234567 查询试验入排标准、终点和 trial phase",
            "science-clinical-regulatory",
            "clinicaltrials-database",
        )

    def test_fda_label_routes_to_fda_database(self) -> None:
        self.assert_selected(
            "根据 FDA drug label 提取适应症、禁忌、不良反应、recall 和用法用量",
            "science-clinical-regulatory",
            "fda-database",
        )

    def test_clinpgx_routes_to_clinpgx_database(self) -> None:
        self.assert_selected(
            "查询 CPIC 药物基因组指南，解释 CYP2C19 和 clopidogrel 的 gene-drug 用药建议",
            "science-clinical-regulatory",
            "clinpgx-database",
        )

    def test_clinical_report_routes_to_clinical_reports(self) -> None:
        self.assert_selected(
            "撰写 CARE guidelines 病例报告，包含临床时间线、诊断、治疗、知情同意和去标识化检查",
            "science-clinical-regulatory",
            "clinical-reports",
            task_type="planning",
        )

    def test_clinical_report_review_routes_to_clinical_reports(self) -> None:
        self.assert_selected(
            "审查 clinical report 的 HIPAA 合规性、去标识化、完整性和医学术语规范",
            "science-clinical-regulatory",
            "clinical-reports",
            task_type="review",
        )

    def test_treatment_plan_routes_to_treatment_plans(self) -> None:
        self.assert_selected(
            "为糖尿病患者生成一页式 treatment plan，包含 SMART 目标、用药方案和随访计划",
            "science-clinical-regulatory",
            "treatment-plans",
            task_type="planning",
        )

    def test_iso_13485_routes_to_iso_certification(self) -> None:
        self.assert_selected(
            "准备 ISO 13485 医疗器械 QMS 认证差距分析、质量手册和 CAPA 程序文件",
            "science-clinical-regulatory",
            "iso-13485-certification",
            task_type="planning",
        )

    def test_clinical_decision_support_routes_to_cds(self) -> None:
        self.assert_selected(
            "生成 clinical decision support 文档，包含 GRADE 证据、治疗算法、队列生存分析和 biomarker 分层",
            "science-clinical-regulatory",
            "clinical-decision-support",
            task_type="planning",
            grade="L",
        )

    def test_dicom_imaging_stays_outside_clinical_regulatory(self) -> None:
        self.assert_selected(
            "读取DICOM并提取tags",
            "science-medical-imaging",
            "pydicom",
            task_type="research",
        )

    def test_pubmed_literature_stays_outside_clinical_regulatory(self) -> None:
        self.assert_selected(
            "检索PubMed文献并导出BibTeX",
            "science-literature-citations",
            "pubmed-database",
            task_type="research",
        )

    def test_rdkit_smiles_stays_outside_clinical_regulatory(self) -> None:
        self.assert_selected(
            "用RDKit解析SMILES并计算Morgan fingerprint",
            "science-chem-drug",
            "rdkit",
            task_type="coding",
        )

    def test_scientific_report_stays_outside_clinical_regulatory(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF",
            "science-reporting",
            "scientific-reporting",
            task_type="planning",
            grade="L",
        )

    def test_generic_code_quality_review_stays_outside_clinical_regulatory(self) -> None:
        self.assert_not_clinical_regulatory(
            "审查代码质量、测试覆盖率和安全风险",
            task_type="review",
            grade="M",
        )


if __name__ == "__main__":
    unittest.main()
