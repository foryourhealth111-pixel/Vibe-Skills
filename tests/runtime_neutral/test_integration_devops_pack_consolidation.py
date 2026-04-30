from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEEP_SKILLS = [
    "gh-fix-ci",
    "mcp-integration",
    "sentry",
    "vercel-deploy",
    "netlify-deploy",
    "node-zombie-guardian",
]

MOVED_OUT_SKILLS = [
    "gh-address-comments",
    "performance-testing",
    "security-best-practices",
    "security-ownership-map",
    "security-threat-model",
    "smart-file-writer",
    "yeet",
]


def route(prompt: str, task_type: str = "debug", grade: str = "L") -> dict[str, object]:
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


class IntegrationDevopsPackConsolidationTests(unittest.TestCase):
    def load_pack(self) -> dict[str, object]:
        manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
        pack = next(item for item in manifest["packs"] if item["id"] == "integration-devops")
        assert isinstance(pack, dict)
        return pack

    def assert_selected(self, prompt: str, expected_skill: str, **kwargs: object) -> None:
        result = route(prompt, **kwargs)
        self.assertEqual(("integration-devops", expected_skill), selected(result), ranked_summary(result))

    def test_manifest_keeps_only_devops_route_authorities(self) -> None:
        pack = self.load_pack()
        self.assertEqual(KEEP_SKILLS, pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertNotIn("review", pack["task_allow"])
        self.assertEqual(
            {
                "debug": "gh-fix-ci",
                "planning": "mcp-integration",
                "coding": "vercel-deploy",
            },
            pack["defaults_by_task"],
        )
        for skill in MOVED_OUT_SKILLS:
            self.assertNotIn(skill, pack["skill_candidates"])

    def test_kept_route_authorities_still_own_their_devops_prompts(self) -> None:
        cases = [
            ("排查GitHub Actions CI失败并修复", "gh-fix-ci", "debug"),
            ("需要接入MCP server并配置.mcp.json", "mcp-integration", "planning"),
            ("查看Sentry线上报错并汇总根因", "sentry", "debug"),
            ("请把应用部署到Vercel并返回访问链接", "vercel-deploy", "coding"),
            ("请部署到Netlify并生成预览链接", "netlify-deploy", "coding"),
            ("审计并清理VCO托管的僵尸node进程", "node-zombie-guardian", "debug"),
        ]
        for prompt, expected_skill, task_type in cases:
            with self.subTest(prompt=prompt):
                self.assert_selected(prompt, expected_skill, task_type=task_type)

    def test_moved_out_skills_do_not_route_to_integration_devops(self) -> None:
        prompts = [
            ("回复PR评审意见并修改代码", "coding"),
            ("做一次安全最佳实践审查", "review"),
            ("为这个仓库做威胁建模", "planning"),
            ("分析安全所有权和bus factor", "review"),
            ("处理文件写入失败和Permission denied", "debug"),
            ("运行BenchmarkDotNet性能测试", "coding"),
            ("一键提交commit push并打开PR", "coding"),
        ]
        for prompt, task_type in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type)
                self.assertNotEqual("integration-devops", selected(result)[0], ranked_summary(result))


if __name__ == "__main__":
    unittest.main()
