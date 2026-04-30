from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


AIOS_SKILLS = {
    "aios-analyst",
    "aios-architect",
    "aios-data-engineer",
    "aios-dev",
    "aios-devops",
    "aios-master",
    "aios-pm",
    "aios-po",
    "aios-qa",
    "aios-sm",
    "aios-squad-creator",
    "aios-ux-design-expert",
}


def load_json(relative_path: str) -> Any:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def route(prompt: str, task_type: str = "planning", grade: str = "L") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(walk_strings(item))
        return found
    if isinstance(value, dict):
        found = []
        for key, item in value.items():
            found.append(str(key))
            found.extend(walk_strings(item))
        return found
    return []


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
        ranking = row.get("candidate_ranking")
        if isinstance(ranking, list):
            skills.update(
                str(item.get("skill") or "")
                for item in ranking
                if isinstance(item, dict)
            )
    return skills


class AiosCoreHardRemovalTests(unittest.TestCase):
    def test_pack_manifest_has_no_aios_core_or_aios_skills(self) -> None:
        manifest = load_json("config/pack-manifest.json")
        packs = manifest["packs"]
        self.assertNotIn("aios-core", {pack["id"] for pack in packs})
        for pack in packs:
            values = set(pack.get("skill_candidates") or [])
            self.assertFalse(values & AIOS_SKILLS, (pack["id"], "skill_candidates", sorted(values & AIOS_SKILLS)))
            self.assertNotIn("route_authority_candidates", pack)
            self.assertNotIn("stage_assistant_candidates", pack)

    def test_bundled_aios_skill_directories_are_deleted(self) -> None:
        remaining = {
            path.name
            for path in (REPO_ROOT / "bundled" / "skills").glob("aios-*")
            if path.is_dir()
        }
        self.assertEqual(set(), remaining)

    def test_live_routing_configs_have_no_aios_skill_keys(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")
        capability_catalog = load_json("config/capability-catalog.json")
        self.assertFalse(set(keyword_index["skills"]) & AIOS_SKILLS)
        self.assertFalse(set(routing_rules["skills"]) & AIOS_SKILLS)
        capability_strings = set(walk_strings(capability_catalog))
        self.assertFalse(capability_strings & AIOS_SKILLS)

    def test_skills_lock_has_no_aios_skills(self) -> None:
        lock = load_json("config/skills-lock.json")
        locked = {str(row.get("name") or "") for row in lock["skills"]}
        self.assertFalse(locked & AIOS_SKILLS, sorted(locked & AIOS_SKILLS))

    def test_upstream_source_configs_have_no_aios_reimport_handles(self) -> None:
        source_aliases = load_json("config/upstream-source-aliases.json")
        upstream_lock = load_json("config/upstream-lock.json")
        upstream_strings = set(walk_strings(source_aliases) + walk_strings(upstream_lock))
        self.assertNotIn("aios-core", upstream_strings)
        self.assertNotIn("SynkraAI/aios-core", upstream_strings)
        self.assertFalse([value for value in upstream_strings if "SynkraAI/aios-core" in value])

    def test_product_planning_prompts_do_not_select_aios(self) -> None:
        prompts = [
            "create PRD and user story backlog with quality gate",
            "输出用户故事和产品需求文档",
            "product owner style backlog prioritization and acceptance criteria",
            "draft product roadmap and PRD scope for next release",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt)
                pack_id, skill = selected(result)
                self.assertNotEqual("aios-core", pack_id, result)
                self.assertNotIn(skill, AIOS_SKILLS, result)
                self.assertNotIn("aios-core", ranked_pack_ids(result), result)
                self.assertFalse(ranked_candidate_skills(result) & AIOS_SKILLS, result)

    def test_aios_words_do_not_resurrect_aios_routes(self) -> None:
        prompts = [
            "aios master orchestrator should plan this project",
            "use Synkra AIOS role team for product owner and scrum master planning",
            "敏捷智能体 产品负责人 质量门禁",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt)
                pack_id, skill = selected(result)
                self.assertNotEqual("aios-core", pack_id, result)
                self.assertNotIn(skill, AIOS_SKILLS, result)
                self.assertNotIn("aios-core", ranked_pack_ids(result), result)
                self.assertFalse(ranked_candidate_skills(result) & AIOS_SKILLS, result)


if __name__ == "__main__":
    unittest.main()
