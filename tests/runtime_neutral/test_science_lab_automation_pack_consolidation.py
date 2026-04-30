from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


DELETED_PACK = "science-lab-automation"
DELETED_SKILLS = [
    "opentrons-integration",
    "pylabrobot",
    "protocolsio-integration",
    "benchling-integration",
    "labarchive-integration",
    "ginkgo-cloud-lab",
]

OUT_OF_SCOPE_SKILLS = [
    "latchbio-integration",
]


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def manifest_pack_ids() -> set[str]:
    manifest = load_json(REPO_ROOT / "config" / "pack-manifest.json")
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    return {str(pack.get("id")) for pack in packs if isinstance(pack, dict)}


def manifest_skill_ids() -> set[str]:
    manifest = load_json(REPO_ROOT / "config" / "pack-manifest.json")
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    skill_ids: set[str] = set()
    for pack in packs:
        assert isinstance(pack, dict), pack
        for field in ("skill_candidates", "route_authority_candidates", "stage_assistant_candidates"):
            values = pack.get(field) or []
            assert isinstance(values, list), pack
            skill_ids.update(str(value) for value in values)
        defaults = pack.get("defaults_by_task") or {}
        assert isinstance(defaults, dict), pack
        skill_ids.update(str(value) for value in defaults.values())
    return skill_ids


def skill_index_ids() -> set[str]:
    payload = load_json(REPO_ROOT / "config" / "skill-keyword-index.json")
    skills = payload.get("skills")
    assert isinstance(skills, dict), payload
    return {str(key) for key in skills.keys()}


def routing_rule_ids() -> set[str]:
    payload = load_json(REPO_ROOT / "config" / "skill-routing-rules.json")
    skills = payload.get("skills")
    assert isinstance(skills, dict), payload
    return {str(key) for key in skills.keys()}


def lock_skill_ids() -> set[str]:
    payload = load_json(REPO_ROOT / "config" / "skills-lock.json")
    skills = payload.get("skills")
    assert isinstance(skills, list), payload
    return {str(row.get("name")) for row in skills if isinstance(row, dict)}


class ScienceLabAutomationPackDeletionTests(unittest.TestCase):
    def assert_deleted_pack_not_selected(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        pack_id, skill_id = selected(result)
        self.assertNotEqual(DELETED_PACK, pack_id, ranked_summary(result))
        self.assertNotIn(skill_id, DELETED_SKILLS, ranked_summary(result))

    def test_pack_manifest_removes_deleted_pack(self) -> None:
        self.assertNotIn(DELETED_PACK, manifest_pack_ids())

    def test_deleted_skills_removed_from_manifest_surfaces(self) -> None:
        remaining_manifest_skills = manifest_skill_ids()
        for skill_id in DELETED_SKILLS:
            with self.subTest(skill_id=skill_id):
                self.assertNotIn(skill_id, remaining_manifest_skills)

    def test_deleted_skills_removed_from_keyword_index_and_routing_rules(self) -> None:
        keyword_ids = skill_index_ids()
        rule_ids = routing_rule_ids()
        for skill_id in DELETED_SKILLS:
            with self.subTest(skill_id=skill_id):
                self.assertNotIn(skill_id, keyword_ids)
                self.assertNotIn(skill_id, rule_ids)

    def test_deleted_skills_removed_from_skills_lock(self) -> None:
        lock_ids = lock_skill_ids()
        for skill_id in DELETED_SKILLS:
            with self.subTest(skill_id=skill_id):
                self.assertNotIn(skill_id, lock_ids)

    def test_deleted_skill_directories_are_absent(self) -> None:
        for skill_id in DELETED_SKILLS:
            with self.subTest(skill_id=skill_id):
                self.assertFalse((REPO_ROOT / "bundled" / "skills" / skill_id).exists())

    def test_out_of_scope_latchbio_is_not_deleted_by_this_pass(self) -> None:
        for skill_id in OUT_OF_SCOPE_SKILLS:
            with self.subTest(skill_id=skill_id):
                self.assertTrue((REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md").is_file())

    def test_deleted_product_prompts_do_not_route_to_deleted_pack(self) -> None:
        cases = [
            ("写一个 Opentrons OT-2 protocol：96孔板分液 + 混匀，输出可运行脚本", "coding", "M"),
            ("用 Opentrons Flex 和 thermocycler module 写一个 PCR setup protocol", "coding", "M"),
            ("用 PyLabRobot 控制 Hamilton 和 Tecan 液体处理机器人，统一调度 plate reader", "coding", "M"),
            ("在 protocols.io 查找 PCR protocol，并总结关键步骤与关键试剂", "research", "M"),
            ("用 protocols.io API 创建并发布一个实验 protocol，包含 workspace 和文件附件", "coding", "M"),
            ("查询 Benchling registry 里的 DNA sequence 和 inventory containers，并导出样品表", "coding", "M"),
            ("备份 LabArchives notebook，导出 entries、attachments 和 JSON metadata", "coding", "M"),
            ("在 Ginkgo Cloud Lab / cloud.ginkgo.bio 准备下单输入并估算 protocol pricing", "planning", "M"),
        ]
        for prompt, task_type, grade in cases:
            with self.subTest(prompt=prompt):
                self.assert_deleted_pack_not_selected(prompt, task_type=task_type, grade=grade)

    def test_existing_negative_boundaries_still_do_not_route_to_deleted_pack(self) -> None:
        cases = [
            ("用 LatchBio / Latch SDK 部署 Nextflow RNA-seq workflow，管理 LatchFile 和 LatchDir", "coding", "M"),
            ("帮我整理电子实验记录 ELN 模板，不指定 Benchling 或 LabArchives", "planning", "M"),
            ("把实验图片和 CSV 附件整理到实验记录里，不使用 LabArchives 或 Benchling", "planning", "M"),
            ("写一个普通 wet-lab protocol 的 Markdown 文档，不使用 protocols.io 或机器人", "planning", "M"),
        ]
        for prompt, task_type, grade in cases:
            with self.subTest(prompt=prompt):
                self.assert_deleted_pack_not_selected(prompt, task_type=task_type, grade=grade)

    def test_pubmed_methods_still_route_to_literature_owner(self) -> None:
        result = route("在 PubMed 检索 wet-lab methods papers 并导出 BibTeX", task_type="research", grade="M")
        self.assertEqual(("science-literature-citations", "pubmed-database"), selected(result), ranked_summary(result))


if __name__ == "__main__":
    unittest.main()
