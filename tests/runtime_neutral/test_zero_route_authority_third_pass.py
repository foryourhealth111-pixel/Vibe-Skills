from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


TARGET_DIRECT_OWNERS = {
    "docs-markitdown-conversion": "markitdown",
    "ip-uspto-patents": "uspto-database",
    "science-astropy": "astropy",
    "science-pymatgen": "pymatgen",
    "science-simpy-simulation": "simpy",
    "science-fluidsim-cfd": "fluidsim",
    "science-matchms-spectra": "matchms",
    "science-matlab-octave": "matlab",
    "science-neuropixels": "neuropixels-analysis",
    "science-pymc-bayesian": "pymc",
    "science-pymoo-optimization": "pymoo",
    "science-rowan-chemistry": "rowan",
    "ml-stable-baselines3": "stable-baselines3",
    "science-timesfm-forecasting": "timesfm-forecasting",
}


PROMPT_CASES = [
    ("用 MarkItDown 将 PDF 和 DOCX 转换成 Markdown", "docs-markitdown-conversion", "markitdown", "coding"),
    ("查询 USPTO patent 专利全文和权利要求", "ip-uspto-patents", "uspto-database", "research"),
    ("用 Astropy 读取 FITS 天文数据并处理 WCS 坐标", "science-astropy", "astropy", "coding"),
    ("用 pymatgen 解析 CIF 晶体结构并计算材料特征", "science-pymatgen", "pymatgen", "coding"),
    ("用 SimPy 做离散事件仿真排队系统和 resource process", "science-simpy-simulation", "simpy", "coding"),
    ("用 FluidSim 做 Navier-Stokes CFD 流体仿真并分析 turbulence spectra", "science-fluidsim-cfd", "fluidsim", "coding"),
    ("用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity", "science-matchms-spectra", "matchms", "coding"),
    ("写 MATLAB/Octave 脚本做矩阵计算和 Simulink 数据处理", "science-matlab-octave", "matlab", "coding"),
    ("分析 Neuropixels spike sorting 和 SpikeGLX 电生理数据", "science-neuropixels", "neuropixels-analysis", "research"),
    ("用 PyMC 建立 Bayesian hierarchical model 并运行 NUTS MCMC", "science-pymc-bayesian", "pymc", "coding"),
    ("用 pymoo 做 NSGA-II 多目标优化和 Pareto front 分析", "science-pymoo-optimization", "pymoo", "coding"),
    ("用 Rowan 云端量子化学平台做 pKa prediction 和 conformer search", "science-rowan-chemistry", "rowan", "research"),
    ("用 Stable-Baselines3 训练 PPO 强化学习智能体", "ml-stable-baselines3", "stable-baselines3", "coding"),
    ("用 TimesFM 做 zero-shot time series forecasting 并输出 prediction intervals", "science-timesfm-forecasting", "timesfm-forecasting", "coding"),
]


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
                str(row.get("candidate_selection_reason") or row.get("legacy_role") or ""),
            )
        )
    return rows


def load_manifest() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = load_manifest()
    return next(pack for pack in manifest["packs"] if pack["id"] == pack_id)


class ZeroRouteAuthorityThirdPassTests(unittest.TestCase):
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

    def test_manifest_makes_all_third_pass_packs_direct_owners(self) -> None:
        for pack_id, skill_id in TARGET_DIRECT_OWNERS.items():
            with self.subTest(pack_id=pack_id):
                pack = load_pack(pack_id)
                self.assertEqual([skill_id], pack["skill_candidates"])
                self.assertNotIn("route_authority_candidates", pack)
                self.assertNotIn("stage_assistant_candidates", pack)
                self.assertEqual(skill_id, pack["defaults_by_task"]["planning"])
                self.assertEqual(skill_id, pack["defaults_by_task"]["coding"])
                self.assertEqual(skill_id, pack["defaults_by_task"]["research"])

    def test_manifest_has_no_empty_candidate_or_legacy_field_packs(self) -> None:
        manifest = load_manifest()
        for pack in manifest["packs"]:
            self.assertTrue(pack.get("skill_candidates"), pack["id"])
            self.assertNotIn("route_authority_candidates", pack)
            self.assertNotIn("stage_assistant_candidates", pack)

    def test_third_pass_prompts_route_to_direct_owners(self) -> None:
        for prompt, expected_pack, expected_skill, task_type in PROMPT_CASES:
            with self.subTest(prompt=prompt):
                self.assert_selected(prompt, expected_pack, expected_skill, task_type=task_type)

    def test_third_pass_false_positive_boundaries(self) -> None:
        false_positive_cases = [
            ("用 NumPy 编写 Python matrix multiplication，不使用 MATLAB 或 Octave", ("science-matlab-octave", "matlab")),
            ("用 scikit-learn 训练随机森林分类模型，不是 reinforcement learning", ("ml-stable-baselines3", "stable-baselines3")),
            ("用 scikit-learn 做普通 tabular regression，不是 time series forecasting", ("science-timesfm-forecasting", "timesfm-forecasting")),
            ("检索 PubMed 文献并画论文 figures，不处理 mass spectra", ("science-matchms-spectra", "matchms")),
            ("用 scipy Rotation 做 quaternion transformation，不调用 Rowan 云端化学平台", ("science-rowan-chemistry", "rowan")),
        ]
        for prompt, forbidden in false_positive_cases:
            with self.subTest(prompt=prompt):
                result = route(prompt)
                self.assertNotEqual(forbidden, selected(result), ranked_summary(result))

    def test_no_third_pass_skill_directory_was_deleted(self) -> None:
        for skill_id in TARGET_DIRECT_OWNERS.values():
            with self.subTest(skill_id=skill_id):
                self.assertTrue((REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
