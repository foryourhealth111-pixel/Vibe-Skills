from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEPT_SKILLS = [
    "opentrons-integration",
    "pylabrobot",
    "protocolsio-integration",
    "benchling-integration",
    "labarchive-integration",
    "ginkgo-cloud-lab",
]

MOVED_OUT_SKILLS = [
    "latchbio-integration",
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


class ScienceLabAutomationPackConsolidationTests(unittest.TestCase):
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

    def assert_not_science_lab_automation(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("science-lab-automation", selected(result)[0], ranked_summary(result))

    def test_manifest_shrinks_to_six_route_owners(self) -> None:
        pack = pack_by_id("science-lab-automation")
        self.assertEqual(KEPT_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(KEPT_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))

    def test_manifest_removes_latchbio_from_lab_automation(self) -> None:
        pack = pack_by_id("science-lab-automation")
        candidates = set(pack.get("skill_candidates") or [])
        for skill in MOVED_OUT_SKILLS:
            self.assertNotIn(skill, candidates)

    def test_defaults_match_kept_route_owners(self) -> None:
        pack = pack_by_id("science-lab-automation")
        self.assertEqual(
            {
                "planning": "protocolsio-integration",
                "coding": "opentrons-integration",
                "research": "protocolsio-integration",
            },
            pack.get("defaults_by_task"),
        )

    def test_opentrons_ot2_protocol_routes_to_opentrons(self) -> None:
        self.assert_selected(
            "写一个 Opentrons OT-2 protocol：96孔板分液 + 混匀，输出可运行脚本",
            "science-lab-automation",
            "opentrons-integration",
            task_type="coding",
            grade="M",
        )

    def test_opentrons_flex_module_routes_to_opentrons(self) -> None:
        self.assert_selected(
            "用 Opentrons Flex 和 thermocycler module 写一个 PCR setup protocol",
            "science-lab-automation",
            "opentrons-integration",
            task_type="coding",
            grade="M",
        )

    def test_pylabrobot_hamilton_tecan_routes_to_pylabrobot(self) -> None:
        self.assert_selected(
            "用 PyLabRobot 控制 Hamilton 和 Tecan 液体处理机器人，统一调度 plate reader",
            "science-lab-automation",
            "pylabrobot",
            task_type="coding",
            grade="M",
        )

    def test_pylabrobot_simulation_routes_to_pylabrobot(self) -> None:
        self.assert_selected(
            "用 pylabrobot resources 模拟 liquid handling workflow 和 deck layout",
            "science-lab-automation",
            "pylabrobot",
            task_type="coding",
            grade="M",
        )

    def test_protocolsio_pcr_routes_to_protocolsio(self) -> None:
        self.assert_selected(
            "在 protocols.io 查找 PCR protocol，并总结关键步骤与关键试剂",
            "science-lab-automation",
            "protocolsio-integration",
            grade="M",
        )

    def test_protocolsio_publish_routes_to_protocolsio(self) -> None:
        self.assert_selected(
            "用 protocols.io API 创建并发布一个实验 protocol，包含 workspace 和文件附件",
            "science-lab-automation",
            "protocolsio-integration",
            task_type="coding",
            grade="M",
        )

    def test_benchling_registry_inventory_routes_to_benchling(self) -> None:
        self.assert_selected(
            "查询 Benchling registry 里的 DNA sequence 和 inventory containers，并导出样品表",
            "science-lab-automation",
            "benchling-integration",
            task_type="coding",
            grade="M",
        )

    def test_benchling_eln_export_routes_to_benchling(self) -> None:
        self.assert_selected(
            "自动化 Benchling ELN entry 和 Data Warehouse export，把 workflow tasks 同步到表格",
            "science-lab-automation",
            "benchling-integration",
            task_type="coding",
            grade="M",
        )

    def test_labarchives_backup_routes_to_labarchive(self) -> None:
        self.assert_selected(
            "备份 LabArchives notebook，导出 entries、attachments 和 JSON metadata",
            "science-lab-automation",
            "labarchive-integration",
            task_type="coding",
            grade="M",
        )

    def test_labarchives_upload_routes_to_labarchive(self) -> None:
        self.assert_selected(
            "把自动化实验输出上传到 LabArchives entry，并附加 CSV 和图片附件",
            "science-lab-automation",
            "labarchive-integration",
            task_type="coding",
            grade="M",
        )

    def test_ginkgo_cloud_lab_order_routes_to_ginkgo(self) -> None:
        self.assert_selected(
            "在 Ginkgo Cloud Lab / cloud.ginkgo.bio 准备下单输入并估算 protocol pricing",
            "science-lab-automation",
            "ginkgo-cloud-lab",
            task_type="planning",
            grade="M",
        )

    def test_ginkgo_cell_free_expression_routes_to_ginkgo(self) -> None:
        self.assert_selected(
            "提交 Ginkgo Cloud Lab cell-free protein expression validation run",
            "science-lab-automation",
            "ginkgo-cloud-lab",
            task_type="planning",
            grade="M",
        )

    def test_latchbio_nextflow_does_not_route_to_lab_automation(self) -> None:
        self.assert_not_science_lab_automation(
            "用 LatchBio / Latch SDK 部署 Nextflow RNA-seq workflow，管理 LatchFile 和 LatchDir",
            task_type="coding",
            grade="M",
        )

    def test_generic_markdown_protocol_does_not_route_to_protocolsio(self) -> None:
        self.assert_not_science_lab_automation(
            "写一个普通 wet-lab protocol 的 Markdown 文档，不使用 protocols.io 或机器人",
            task_type="planning",
            grade="M",
        )

    def test_pubmed_methods_does_not_route_to_lab_automation(self) -> None:
        self.assert_selected(
            "在 PubMed 检索 wet-lab methods papers 并导出 BibTeX",
            "science-literature-citations",
            "pubmed-database",
            grade="M",
        )


if __name__ == "__main__":
    unittest.main()
