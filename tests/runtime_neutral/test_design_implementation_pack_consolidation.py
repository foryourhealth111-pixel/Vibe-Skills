from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


DESIGN_IMPLEMENTATION_SKILLS = ["figma-implement-design"]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def pack_by_id(pack_id: str) -> dict[str, object]:
    manifest = load_json("config/pack-manifest.json")
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


def route(prompt: str, task_type: str = "planning", grade: str = "L") -> dict[str, object]:
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


class DesignImplementationPackConsolidationTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "planning",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def test_design_implementation_manifest_has_single_owner(self) -> None:
        pack = pack_by_id("design-implementation")

        self.assertEqual(DESIGN_IMPLEMENTATION_SKILLS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("figma", pack.get("skill_candidates") or [])
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertEqual("figma-implement-design", (pack.get("defaults_by_task") or {}).get("planning"))
        self.assertEqual("figma-implement-design", (pack.get("defaults_by_task") or {}).get("coding"))

    def test_figma_tool_skill_is_not_exposed_as_separate_live_skill(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")
        skills_lock = load_json("config/skills-lock.json")

        self.assertNotIn("figma", (keyword_index.get("skills") or {}))
        self.assertNotIn("figma", (routing_rules.get("skills") or {}))
        self.assertNotIn("figma", (skills_lock.get("skills") or {}))
        self.assertFalse((REPO_ROOT / "bundled" / "skills" / "figma").exists())

    def test_figma_implementation_still_routes_to_design_owner(self) -> None:
        self.assert_selected(
            "把这个 Figma 设计稿还原为可运行代码",
            "design-implementation",
            "figma-implement-design",
            task_type="coding",
        )

    def test_figma_mcp_setup_with_implementation_context_routes_to_design_owner(self) -> None:
        self.assert_selected(
            "配置 Figma MCP 后把当前 node id 的设计稿实现成前端组件",
            "design-implementation",
            "figma-implement-design",
            task_type="planning",
        )


if __name__ == "__main__":
    unittest.main()
