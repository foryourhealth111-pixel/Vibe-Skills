from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


MEDICAL_IMAGING_SKILLS = [
    "pydicom",
    "imaging-data-commons",
    "histolab",
    "omero-integration",
    "pathml",
]


def route(prompt: str, task_type: str = "research", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


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


def skill_keywords(skill_id: str) -> list[str]:
    path = REPO_ROOT / "config" / "skill-keyword-index.json"
    index = json.loads(path.read_text(encoding="utf-8-sig"))
    skill = index.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    keywords = skill.get("keywords")
    assert isinstance(keywords, list), skill
    return [str(keyword).lower() for keyword in keywords]


def routing_rule(skill_id: str) -> dict[str, object]:
    path = REPO_ROOT / "config" / "skill-routing-rules.json"
    rules = json.loads(path.read_text(encoding="utf-8-sig"))
    skill = rules.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    return skill


def positive_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("positive_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def negative_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("negative_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def skill_body(skill_id: str) -> str:
    path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
    text = path.read_text(encoding="utf-8-sig")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lower()
    return text.lower()


class ScienceMedicalImagingPackConsolidationTests(unittest.TestCase):
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
        blocked_pack: str | None = None,
        blocked_skill: str | None = None,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        chosen_pack, chosen_skill = selected(result)
        if blocked_pack is not None:
            self.assertNotEqual(blocked_pack, chosen_pack, ranked_summary(result))
        if blocked_skill is not None:
            self.assertNotEqual(blocked_skill, chosen_skill, ranked_summary(result))

    def test_manifest_keeps_five_direct_owners_and_no_stage_assistants(self) -> None:
        pack = pack_by_id("science-medical-imaging")
        self.assertEqual(MEDICAL_IMAGING_SKILLS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        defaults = pack.get("defaults_by_task")
        self.assertIsInstance(defaults, dict)
        for task_name in ["planning", "coding", "research"]:
            self.assertIn(defaults.get(task_name), MEDICAL_IMAGING_SKILLS, defaults)

    def test_medical_imaging_positive_routes_hit_direct_owners(self) -> None:
        self.assert_selected(
            "用 pydicom 读取 CT DICOM tags，匿名化 PatientName，并导出 pixel array",
            "science-medical-imaging",
            "pydicom",
            task_type="coding",
        )
        self.assert_selected(
            "从 NCI Imaging Data Commons 查询 TCIA cancer imaging cohort 并下载 DICOMWeb 样例",
            "science-medical-imaging",
            "imaging-data-commons",
        )
        self.assert_selected(
            "用 histolab 对 whole slide image 做 tissue detection 和 H&E tile extraction",
            "science-medical-imaging",
            "histolab",
            task_type="coding",
        )
        self.assert_selected(
            "用 OMERO server Python API 读取 microscopy image server 的 ROI annotations",
            "science-medical-imaging",
            "omero-integration",
            task_type="coding",
        )
        self.assert_selected(
            "用 PathML 构建 computational pathology WSI pipeline，包含 nucleus segmentation 和 spatial graph",
            "science-medical-imaging",
            "pathml",
            task_type="planning",
        )

    def test_generic_datacommons_does_not_select_imaging_data_commons(self) -> None:
        self.assert_not_selected(
            "用 Data Commons 查询 population indicators、statistical variables 和 DCID，不涉及 Imaging Data Commons 或 DICOMWeb",
            blocked_pack="science-medical-imaging",
            blocked_skill="imaging-data-commons",
        )

    def test_literature_clinical_and_publishing_do_not_select_medical_imaging(self) -> None:
        self.assert_not_selected(
            "查询 PubMed 文献并整理 PMID citation evidence table",
            blocked_pack="science-medical-imaging",
        )
        self.assert_not_selected(
            "从 ClinicalTrials.gov 查询 NCT01234567 的终点和入排标准",
            blocked_pack="science-medical-imaging",
        )
        self.assert_not_selected(
            "写 LaTeX 论文并用 latexmk 构建 submission PDF",
            blocked_pack="science-medical-imaging",
            task_type="coding",
            grade="XL",
        )
        self.assert_not_selected(
            "写一篇科研报告，包含 methods results discussion 并导出 PDF",
            blocked_pack="science-medical-imaging",
            task_type="planning",
            grade="L",
        )

    def test_generic_image_processing_and_bioinformatics_do_not_select_medical_imaging(self) -> None:
        self.assert_not_selected(
            "对普通 PNG 图片做 OCR、截图裁剪和图像增强，不涉及 DICOM、WSI、OMERO 或 PathML",
            blocked_pack="science-medical-imaging",
            task_type="coding",
        )
        self.assert_not_selected(
            "分析 scRNA-seq h5ad，做 marker genes、KEGG enrichment 和 UMAP 可视化",
            blocked_pack="science-medical-imaging",
        )
        self.assert_not_selected(
            "用 RDKit 解析 SMILES 并做 molecule docking",
            blocked_pack="science-medical-imaging",
            task_type="coding",
        )

    def test_histolab_and_pathml_split_is_stable(self) -> None:
        self.assert_selected(
            "用 histolab 做 WSI tile extraction、tissue detection 和 H&E tile dataset preparation",
            "science-medical-imaging",
            "histolab",
            task_type="coding",
        )
        self.assert_not_selected(
            "用 histolab 做 WSI tile extraction、tissue detection 和 H&E tile dataset preparation",
            blocked_skill="pathml",
            task_type="coding",
        )
        self.assert_selected(
            "用 PathML 构建 digital pathology workflow，包含 nucleus segmentation、multiplex pathology 和 tissue graph",
            "science-medical-imaging",
            "pathml",
            task_type="planning",
        )
        self.assert_not_selected(
            "用 PathML 构建 digital pathology workflow，包含 nucleus segmentation、multiplex pathology 和 tissue graph",
            blocked_skill="histolab",
            task_type="planning",
        )

    def test_keyword_index_uses_specific_medical_imaging_terms(self) -> None:
        required = {
            "pydicom": ["dicom anonymization", "dicom pixel data", "medical scan"],
            "imaging-data-commons": ["nci imaging data commons", "tcia", "dicomweb", "cancer imaging cohort"],
            "histolab": ["wsi tile extraction", "tissue detection", "h&e tile"],
            "omero-integration": ["omero server", "roi annotation", "microscopy image server"],
            "pathml": ["computational pathology", "nucleus segmentation", "spatial pathology", "multiplex pathology"],
        }
        for skill_id, terms in required.items():
            with self.subTest(skill_id=skill_id):
                keywords = skill_keywords(skill_id)
                for term in terms:
                    self.assertIn(term, keywords)

    def test_routing_rules_encode_medical_imaging_owner_boundaries(self) -> None:
        expected_negative = {
            "pydicom": [
                "pubmed",
                "clinicaltrials",
                "latex",
                "scientific report",
                "generic image processing",
                "ocr",
                "screenshot",
                "scRNA-seq",
                "rdkit",
                "data commons",
            ],
            "imaging-data-commons": [
                "generic data commons",
                "population indicators",
                "statistical variables",
                "dcid",
                "pubmed",
                "clinicaltrials",
                "latex",
                "scientific report",
                "generic public dataset",
            ],
            "histolab": [
                "dicom",
                "dicomweb",
                "omero",
                "pathml workflow",
                "nucleus segmentation",
                "pubmed",
                "clinicaltrials",
                "generic image processing",
                "ocr",
            ],
            "omero-integration": [
                "pubmed",
                "clinicaltrials",
                "dicom",
                "tcia",
                "histolab",
                "pathml",
                "generic microscopy literature",
                "scRNA-seq",
                "rna-seq",
            ],
            "pathml": [
                "dicom tag",
                "dicom anonymization",
                "imaging data commons",
                "tcia",
                "omero server",
                "histolab tile extraction",
                "pubmed",
                "clinicaltrials",
                "generic image processing",
                "generic machine learning",
            ],
        }
        for skill_id, required_terms in expected_negative.items():
            with self.subTest(skill_id=skill_id):
                negatives = negative_keywords(skill_id)
                for term in required_terms:
                    self.assertIn(term.lower(), negatives)

    def test_kept_skill_docs_state_routing_boundaries(self) -> None:
        expected_phrases = {
            "pydicom": ["routing boundary", "dicom files, tags, pixel data, anonymization"],
            "imaging-data-commons": ["routing boundary", "not generic data commons"],
            "histolab": ["routing boundary", "basic wsi tile extraction"],
            "omero-integration": ["routing boundary", "omero server"],
            "pathml": ["routing boundary", "full computational pathology"],
        }
        for skill_id, phrases in expected_phrases.items():
            with self.subTest(skill_id=skill_id):
                body = skill_body(skill_id)
                for phrase in phrases:
                    self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main()
