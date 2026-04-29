from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


KEEP_SKILLS = [
    "openai-docs",
    "prompt-lookup",
    "embedding-strategies",
    "similarity-search-patterns",
    "evaluating-llms-harness",
]

MOVED_OUT_SKILLS = [
    "documentation-lookup",
    "openai-knowledge",
    "evaluating-code-models",
    "nowait-reasoning-optimizer",
    "transformer-lens-interpretability",
    "transformers",
]


def route(prompt: str, task_type: str = "research", grade: str = "M") -> dict[str, object]:
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


class AiLlmPackConsolidationTests(unittest.TestCase):
    def load_pack(self) -> dict[str, object]:
        manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
        pack = next(item for item in manifest["packs"] if item["id"] == "ai-llm")
        assert isinstance(pack, dict)
        return pack

    def assert_selected(self, prompt: str, expected_skill: str, **kwargs: object) -> None:
        result = route(prompt, **kwargs)
        self.assertEqual(("ai-llm", expected_skill), selected(result), ranked_summary(result))

    def test_manifest_keeps_only_core_ai_llm_route_authorities(self) -> None:
        pack = self.load_pack()
        self.assertEqual(KEEP_SKILLS, pack["skill_candidates"])
        self.assertEqual(KEEP_SKILLS, pack["route_authority_candidates"])
        self.assertEqual([], pack.get("stage_assistant_candidates", []))
        self.assertEqual(
            {
                "planning": "embedding-strategies",
                "review": "evaluating-llms-harness",
                "coding": "openai-docs",
                "research": "openai-docs",
            },
            pack["defaults_by_task"],
        )
        for skill in MOVED_OUT_SKILLS:
            self.assertNotIn(skill, pack["skill_candidates"])

    def test_core_ai_llm_skills_own_their_prompts(self) -> None:
        cases = [
            ("查询OpenAI官方文档中的Responses API用法", "openai-docs", "research"),
            ("帮我检索提示词模板并优化prompt", "prompt-lookup", "research"),
            ("设计向量嵌入策略用于语义检索", "embedding-strategies", "planning"),
            ("设计vector database nearest neighbor similarity search方案", "similarity-search-patterns", "planning"),
            ("用MMLU和GSM8K做大模型评测", "evaluating-llms-harness", "research"),
        ]
        for prompt, expected_skill, task_type in cases:
            with self.subTest(prompt=prompt):
                self.assert_selected(prompt, expected_skill, task_type=task_type)

    def test_moved_out_and_cold_skills_do_not_route_to_ai_llm(self) -> None:
        prompts = [
            ("查询React 19官方文档并给出useEffect示例", "coding"),
            ("用HumanEval和MBPP评测代码生成模型", "research"),
            ("优化DeepSeek-R1推理，减少thinking tokens和反思token", "coding"),
            ("用TransformerLens做activation patching和circuit analysis", "research"),
            ("用Hugging Face Transformers微调BERT文本分类模型", "coding"),
        ]
        for prompt, task_type in prompts:
            with self.subTest(prompt=prompt):
                result = route(prompt, task_type=task_type)
                self.assertNotEqual("ai-llm", selected(result)[0], ranked_summary(result))


if __name__ == "__main__":
    unittest.main()
