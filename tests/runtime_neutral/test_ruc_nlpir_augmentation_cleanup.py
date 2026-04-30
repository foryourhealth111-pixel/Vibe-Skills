from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEEP_SKILLS = ["flashrag-evidence", "webthinker-deep-research"]
DEEPAGENT_SKILLS = ["deepagent-toolchain-plan", "deepagent-memory-fold"]


def load_json(relative_path: str) -> dict[str, object]:
    path = REPO_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8-sig"))


def route(prompt: str, task_type: str = "research", grade: str = "L") -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        requested_skill=None,
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


def ruc_pack() -> dict[str, object]:
    manifest = load_json("config/pack-manifest.json")
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == "ruc-nlpir-augmentation":
            return pack
    raise AssertionError("ruc-nlpir-augmentation pack missing")


class RucNlpirAugmentationCleanupTests(unittest.TestCase):
    def test_manifest_keeps_only_explicit_tool_route_owners(self) -> None:
        pack = ruc_pack()
        self.assertEqual(KEEP_SKILLS, pack.get("skill_candidates"))
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertEqual({"research": "webthinker-deep-research"}, pack.get("defaults_by_task"))

        trigger_keywords = {str(item).lower() for item in pack.get("trigger_keywords") or []}
        for forbidden in ["deepagent", "toolchain", "skill chain", "memory folding", "工具链", "技能链", "记忆折叠"]:
            self.assertNotIn(forbidden, trigger_keywords)

    def test_deepagent_skill_ids_are_absent_from_live_config_surfaces(self) -> None:
        keyword_index = load_json("config/skill-keyword-index.json")
        routing_rules = load_json("config/skill-routing-rules.json")
        capability_catalog = load_json("config/capability-catalog.json")
        upstream_aliases = load_json("config/upstream-source-aliases.json")
        upstream_lock = load_json("config/upstream-lock.json")
        runtime = load_json("config/ruc-nlpir-runtime.json")
        overlays = load_json("config/ruc-nlpir-overlays.json")
        vco_overlays = load_json("config/vco-overlays.json")

        routing_skills = routing_rules.get("skills")
        self.assertIsInstance(routing_skills, dict)

        for skill in DEEPAGENT_SKILLS:
            self.assertNotIn(skill, keyword_index)
            self.assertNotIn(skill, routing_skills)
            pack = ruc_pack()
            self.assertNotIn(skill, pack.get("skill_candidates") or [])
            self.assertNotIn("route_authority_candidates", pack)
            self.assertNotIn("stage_assistant_candidates", pack)

        serialized_catalog = json.dumps(capability_catalog, ensure_ascii=False).lower()
        self.assertNotIn("deepagent", serialized_catalog)
        self.assertNotIn("deepagent-toolchain-plan", serialized_catalog)
        self.assertNotIn("deepagent-memory-fold", serialized_catalog)
        capability_ids = {str(item.get("id")) for item in capability_catalog.get("capabilities") or [] if isinstance(item, dict)}
        self.assertNotIn("toolchain_planning", capability_ids)
        self.assertNotIn("memory_folding", capability_ids)

        aliases = upstream_aliases.get("aliases")
        self.assertIsInstance(aliases, dict)
        self.assertNotIn("DeepAgent", aliases)
        self.assertNotIn("RUC-NLPIR/DeepAgent", aliases)
        self.assertNotIn("deepagent", {str(value) for value in aliases.values()})

        upstream_entries = upstream_lock.get("sources")
        if upstream_entries is None:
            upstream_entries = upstream_lock.get("upstreams")
        if upstream_entries is None:
            upstream_entries = upstream_lock.get("dependencies")
        self.assertIsInstance(upstream_entries, list)
        serialized_upstream = json.dumps(upstream_entries, ensure_ascii=False).lower()
        self.assertNotIn("deepagent", serialized_upstream)

        repos = runtime.get("repos")
        self.assertIsInstance(repos, dict)
        self.assertEqual({"FlashRAG", "WebThinker"}, set(repos))
        self.assertEqual(
            {
                "flashrag_evidence": "auto",
                "webthinker_deep_research": "lite",
            },
            runtime.get("engine_defaults"),
        )

        overlay_text = json.dumps(overlays, ensure_ascii=False).lower()
        self.assertNotIn("deepagent", overlay_text)
        provider_text = json.dumps(vco_overlays, ensure_ascii=False).lower()
        self.assertNotIn("deepagent", provider_text)

    def test_deepagent_skill_and_overlay_files_are_physically_deleted(self) -> None:
        for relative_path in [
            "bundled/skills/deepagent-toolchain-plan",
            "bundled/skills/deepagent-memory-fold",
            "references/overlays/ruc-nlpir/deepagent-toolchain-plan.md",
            "references/overlays/ruc-nlpir/deepagent-memory-fold.md",
        ]:
            self.assertFalse((REPO_ROOT / relative_path).exists(), relative_path)

    def test_preflight_no_longer_hardcodes_deepagent(self) -> None:
        preflight = (REPO_ROOT / "scripts" / "ruc-nlpir" / "preflight.ps1").read_text(encoding="utf-8")
        self.assertNotIn("DeepAgent", preflight)
        self.assertIn("$runtime.repos.PSObject.Properties.Name", preflight)

    def test_deleted_deepagent_prompts_do_not_select_deleted_skills_or_pack(self) -> None:
        prompts = [
            ("用 DeepAgent 规划工具链和技能链", "planning"),
            ("请整理长会话上下文，做 memory folding", "review"),
        ]
        for prompt, task_type in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type)
                pack_id, skill = selected(result)
                self.assertNotEqual("ruc-nlpir-augmentation", pack_id, ranked_summary(result))
                self.assertNotIn(skill, DEEPAGENT_SKILLS, ranked_summary(result))

    def test_kept_tools_still_route_on_explicit_tool_prompts(self) -> None:
        local_result = route(
            "请用 FlashRAG 做本地 repo/config 证据检索，给出 SKILL.md 文件和行号，说明路由规则在哪里定义",
            task_type="review",
        )
        self.assertEqual(("ruc-nlpir-augmentation", "flashrag-evidence"), selected(local_result), ranked_summary(local_result))

        web_result = route(
            "我要做 deep research，多跳浏览网页并保留 trace.jsonl 和 sources.json 证据链",
            task_type="research",
        )
        self.assertEqual(("ruc-nlpir-augmentation", "webthinker-deep-research"), selected(web_result), ranked_summary(web_result))


if __name__ == "__main__":
    unittest.main()
