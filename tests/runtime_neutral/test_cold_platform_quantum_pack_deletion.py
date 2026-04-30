from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


DELETED_PACKS = {"cloud-modalcom", "science-quantum"}
DELETED_SKILLS = {"modal", "modal-labs", "qiskit", "cirq", "pennylane", "qutip"}


def load_json(relative_path: str) -> Any:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def route(prompt: str, task_type: str = "coding", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_pack_ids(result: dict[str, object]) -> set[str]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    return {
        str(row.get("pack_id") or "")
        for row in ranked
        if isinstance(row, dict)
    }


def ranked_candidate_skills(result: dict[str, object]) -> set[str]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    skills: set[str] = set()
    for row in ranked:
        if not isinstance(row, dict):
            continue
        skills.add(str(row.get("skill") or ""))
        skills.add(str(row.get("selected_candidate") or ""))
        candidate_ranking = row.get("candidate_ranking")
        if isinstance(candidate_ranking, list):
            skills.update(
                str(item.get("skill") or "")
                for item in candidate_ranking
                if isinstance(item, dict)
            )
        stage_candidates = row.get("stage_assistant_candidates")
        if isinstance(stage_candidates, list):
            skills.update(
                str(item.get("skill") or "")
                for item in stage_candidates
                if isinstance(item, dict)
            )
    return {skill for skill in skills if skill}


class ColdPlatformQuantumPackDeletionTests(unittest.TestCase):
    def test_pack_manifest_has_no_deleted_packs_or_skills(self) -> None:
        manifest = load_json("config/pack-manifest.json")
        packs = manifest["packs"]
        pack_ids = {str(pack["id"]) for pack in packs}
        self.assertFalse(pack_ids & DELETED_PACKS, sorted(pack_ids & DELETED_PACKS))

        for pack in packs:
            for field in ("skill_candidates", "route_authority_candidates", "stage_assistant_candidates"):
                values = {str(value) for value in (pack.get(field) or [])}
                self.assertFalse(values & DELETED_SKILLS, (pack["id"], field, sorted(values & DELETED_SKILLS)))

    def test_bundled_skill_directories_are_deleted(self) -> None:
        remaining = {
            skill
            for skill in DELETED_SKILLS
            if (REPO_ROOT / "bundled" / "skills" / skill).exists()
        }
        self.assertEqual(set(), remaining)

    def test_live_routing_configs_have_no_deleted_skill_keys(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")

        self.assertFalse(set(keyword_index["skills"]) & DELETED_SKILLS)
        self.assertFalse(set(routing_rules["skills"]) & DELETED_SKILLS)

    def test_skills_lock_has_no_deleted_skills(self) -> None:
        lock = load_json("config/skills-lock.json")
        locked = {str(row.get("name") or "") for row in lock["skills"]}
        self.assertFalse(locked & DELETED_SKILLS, sorted(locked & DELETED_SKILLS))

    def test_removed_modal_prompts_do_not_select_or_rank_deleted_surfaces(self) -> None:
        prompts = [
            ("Run a Python batch job on a cloud GPU without specifying Modal.", "coding", "M"),
            ("Deploy a serverless GPU function, but use any cloud container platform except Modal.", "coding", "M"),
            ("把 Python 任务部署到云端 GPU，不指定 Modal，用普通容器也可以", "coding", "M"),
            ("用 Modal.com 部署 serverless GPU Python function 和 batch job", "coding", "M"),
            ("Build a React modal dialog with overlay and focus trap.", "coding", "M"),
        ]
        for prompt, task_type, grade in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type, grade=grade)
                pack_id, skill = selected(result)
                self.assertNotIn(pack_id, DELETED_PACKS, result)
                self.assertNotIn(skill, DELETED_SKILLS, result)
                self.assertFalse(ranked_pack_ids(result) & DELETED_PACKS, result)
                self.assertFalse(ranked_candidate_skills(result) & DELETED_SKILLS, result)

    def test_removed_quantum_prompts_do_not_select_or_rank_deleted_surfaces(self) -> None:
        prompts = [
            ("Quantum chemistry pKa and DFT analysis, not a quantum circuit.", "research", "M"),
            ("调研 quantum chemistry 论文和 pKa 预测，不写量子电路", "research", "M"),
            ("Use Qiskit to create a Bell-state quantum circuit.", "coding", "M"),
            ("Use Cirq to build quantum gate moments for a simulator.", "coding", "M"),
            ("Use PennyLane for a quantum machine learning variational circuit.", "coding", "M"),
            ("Use QuTiP to simulate an open quantum system master equation.", "research", "M"),
        ]
        for prompt, task_type, grade in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type, grade=grade)
                pack_id, skill = selected(result)
                self.assertNotIn(pack_id, DELETED_PACKS, result)
                self.assertNotIn(skill, DELETED_SKILLS, result)
                self.assertFalse(ranked_pack_ids(result) & DELETED_PACKS, result)
                self.assertFalse(ranked_candidate_skills(result) & DELETED_SKILLS, result)

    def test_rowan_quantum_chemistry_boundary_still_has_its_owner(self) -> None:
        result = route("用 Rowan 云端量子化学平台做 pKa prediction 和 conformer search", task_type="research")
        self.assertEqual(("science-rowan-chemistry", "rowan"), selected(result), result)

    def test_remaining_packs_keep_simple_route_shape(self) -> None:
        manifest = load_json("config/pack-manifest.json")
        zero_route_authority = [
            pack["id"]
            for pack in manifest["packs"]
            if pack.get("skill_candidates") and not pack.get("route_authority_candidates")
        ]
        stage_assistant_packs = {
            pack["id"]: pack.get("stage_assistant_candidates")
            for pack in manifest["packs"]
            if pack.get("stage_assistant_candidates") or []
        }
        self.assertEqual([], zero_route_authority)
        self.assertEqual({}, stage_assistant_packs)


if __name__ == "__main__":
    unittest.main()
