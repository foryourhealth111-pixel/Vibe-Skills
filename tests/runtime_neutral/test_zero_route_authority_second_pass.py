from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


REMOVED_SECOND_PASS_PACKS = {"cloud-modalcom", "science-quantum"}
REMOVED_SECOND_PASS_SKILLS = {"modal", "modal-labs", "qiskit", "cirq", "pennylane", "qutip"}


def route(prompt: str, task_type: str = "coding", grade: str = "M") -> dict[str, object]:
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


def load_manifest() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = load_manifest()
    return next(pack for pack in manifest["packs"] if pack["id"] == pack_id)


class ZeroRouteAuthoritySecondPassTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "coding",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def test_removed_second_pass_packs_are_absent(self) -> None:
        manifest = load_manifest()
        pack_ids = {pack["id"] for pack in manifest["packs"]}
        self.assertFalse(pack_ids & REMOVED_SECOND_PASS_PACKS)
        for pack in manifest["packs"]:
            values = set(pack.get("skill_candidates") or [])
            self.assertFalse(values & REMOVED_SECOND_PASS_SKILLS, (pack["id"], "skill_candidates"))
            self.assertNotIn("route_authority_candidates", pack)
            self.assertNotIn("stage_assistant_candidates", pack)

    def test_ml_torch_geometric_has_one_canonical_owner(self) -> None:
        pack = load_pack("ml-torch-geometric")
        self.assertEqual(["torch-geometric"], pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["planning"])
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["coding"])
        self.assertEqual("torch-geometric", pack["defaults_by_task"]["research"])

    def test_ml_torch_geometric_routes_alias_keywords_to_canonical_skill(self) -> None:
        self.assert_selected("用 PyTorch Geometric 构建 GCN 图神经网络", "ml-torch-geometric", "torch-geometric")
        self.assert_selected("用 torch_geometric 写 GAT 节点分类模型", "ml-torch-geometric", "torch-geometric")
        self.assert_selected("训练 PyG graph classification pipeline", "ml-torch-geometric", "torch-geometric")

    def test_ml_torch_geometric_does_not_capture_generic_pytorch(self) -> None:
        result = route("用 PyTorch 训练 CNN 图像分类模型，不涉及 graph neural network 或 PyG", task_type="coding")
        self.assertNotEqual(("ml-torch-geometric", "torch-geometric"), selected(result), ranked_summary(result))

    def test_selected_packs_do_not_reintroduce_stage_assistants(self) -> None:
        pack = load_pack("ml-torch-geometric")
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)


if __name__ == "__main__":
    unittest.main()
