from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


TARGET_DIRECT_OWNERS = {
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
    "ml-torch-geometric": "torch-geometric",
}


POSITIVE_ROUTE_CASES = [
    (
        "用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization",
        "science-simpy-simulation",
        "simpy",
        "coding",
    ),
    (
        "用 FluidSim 做 Navier-Stokes CFD turbulence spectra 分析",
        "science-fluidsim-cfd",
        "fluidsim",
        "coding",
    ),
    (
        "用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity",
        "science-matchms-spectra",
        "matchms",
        "coding",
    ),
    (
        "写 MATLAB/Octave .m script 并连接 Simulink 模型",
        "science-matlab-octave",
        "matlab",
        "coding",
    ),
    (
        "分析 Neuropixels SpikeGLX 数据，运行 Kilosort spike sorting 并整理 probe channel map",
        "science-neuropixels",
        "neuropixels-analysis",
        "research",
    ),
    (
        "用 PyMC 建立 Bayesian hierarchical model，运行 NUTS MCMC 和 posterior predictive checks",
        "science-pymc-bayesian",
        "pymc",
        "coding",
    ),
    (
        "用 pymoo 做 NSGA-II multi-objective optimization，输出 Pareto front",
        "science-pymoo-optimization",
        "pymoo",
        "coding",
    ),
    (
        "用 Rowan rowan-python 调用 labs.rowansci.com API 管理计算任务",
        "science-rowan-chemistry",
        "rowan",
        "coding",
    ),
    (
        "用 Stable-Baselines3 SB3 训练 PPO reinforcement learning agent",
        "ml-stable-baselines3",
        "stable-baselines3",
        "coding",
    ),
    (
        "用 TimesFM 做 zero-shot forecasting，设置 forecast horizon 和 prediction intervals",
        "science-timesfm-forecasting",
        "timesfm-forecasting",
        "coding",
    ),
    (
        "用 PyTorch Geometric torch_geometric 写 PyG GNN node classification pipeline",
        "ml-torch-geometric",
        "torch-geometric",
        "coding",
    ),
]


BLOCKED_ROUTE_CASES = [
    (
        "设计一个普通 agent-based simulation 和 Monte Carlo simulation，不使用 SimPy 或离散事件资源队列",
        "science-simpy-simulation",
        "simpy",
        "planning",
    ),
    (
        "用 Python scipy 解 PDE 和 physics simulation，不使用 FluidSim 或 CFD",
        "science-fluidsim-cfd",
        "fluidsim",
        "coding",
    ),
    (
        "检索 PubMed 代谢组学文献并整理 metabolomics pathway evidence，不处理 mass spectra",
        "science-matchms-spectra",
        "matchms",
        "research",
    ),
    (
        "用 NumPy 做 Python matrix multiplication，在 Jupyter 里做 scientific visualization，不使用 MATLAB 或 Octave",
        "science-matlab-octave",
        "matlab",
        "coding",
    ),
    (
        "分析 clinical EEG 和 fMRI neuroscience 文献，不涉及 Neuropixels、SpikeGLX 或 Kilosort",
        "science-neuropixels",
        "neuropixels-analysis",
        "research",
    ),
    (
        "用 scikit-learn 做普通 regression 和 causal analysis，不使用 PyMC、MCMC 或 probabilistic programming",
        "science-pymc-bayesian",
        "pymc",
        "research",
    ),
    (
        "做实验设计和普通 optimization plan，不使用 pymoo、NSGA-II 或 Pareto front",
        "science-pymoo-optimization",
        "pymoo",
        "planning",
    ),
    (
        "用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan",
        "science-rowan-chemistry",
        "rowan",
        "research",
    ),
    (
        "用 scikit-learn 训练 supervised classification 模型，不是 reinforcement learning 或 SB3",
        "ml-stable-baselines3",
        "stable-baselines3",
        "coding",
    ),
    (
        "做普通 business forecast、ARIMA baseline 和 tabular regression，不使用 TimesFM 或 foundation forecasting",
        "science-timesfm-forecasting",
        "timesfm-forecasting",
        "research",
    ),
    (
        "训练普通 PyTorch neural network，并画 network graph visualization，不涉及 PyG 或 graph neural network",
        "ml-torch-geometric",
        "torch-geometric",
        "coding",
    ),
]


REQUIRED_KEYWORDS = {
    "simpy": ["simpy", "simpy discrete event simulation", "simpy queue simulation", "simpy resource process"],
    "fluidsim": ["fluidsim", "fluidsim cfd", "fluidsim navier-stokes", "fluidsim turbulence"],
    "matchms": ["matchms", "ms/ms", "mass spectra", "spectral similarity", "metabolomics spectrum processing"],
    "matlab": ["matlab", "octave", ".m script", "m-file", "simulink", "matlab script"],
    "neuropixels-analysis": ["neuropixels", "spikeglx", "kilosort", "spike sorting", "open ephys"],
    "pymc": ["pymc", "bayesian hierarchical model", "nuts mcmc", "posterior predictive", "probabilistic programming"],
    "pymoo": ["pymoo", "nsga-ii", "multi-objective optimization", "pareto front", "pymoo constraint optimization"],
    "rowan": ["rowan", "rowan chemistry", "rowan-python", "labs.rowansci.com", "rowan api"],
    "stable-baselines3": ["stable-baselines3", "stable baselines3", "sb3", "ppo", "reinforcement learning"],
    "timesfm-forecasting": ["timesfm", "zero-shot forecasting", "foundation model forecasting", "forecast horizon", "prediction intervals"],
    "torch-geometric": ["torch-geometric", "torch_geometric", "pytorch geometric", "pyg", "graph neural network"],
}


FORBIDDEN_POSITIVE_KEYWORDS = {
    "simpy": ["event simulation", "process simulation", "agent-based model", "monte carlo simulation"],
    "fluidsim": ["fluid simulation", "python simulation", "physics simulation", "pde solver"],
    "matlab": ["matrix calculation", "numpy matrix", "scientific visualization", "data analysis", "numerical computing"],
    "pymoo": ["optimization", "experiment design"],
    "rowan": [
        "pka prediction",
        "conformer search",
        "geometry optimization",
        "quantum chemistry",
        "docking",
        "boltz",
        "chai-1",
        "molecular machine learning",
    ],
    "timesfm-forecasting": ["time series forecasting", "business forecast", "tabular regression"],
}


REQUIRED_NEGATIVE_KEYWORDS = {
    "simpy": ["sympy", "agent-based model", "monte carlo simulation", "generic simulation", "physics simulation"],
    "fluidsim": ["css", "fluid layout", "responsive design", "generic pde", "finite element", "python simulation"],
    "matchms": ["pubmed", "literature review", "generic chemistry", "non-spectral metabolomics", "not mass spectra"],
    "matlab": ["not matlab", "not octave", "numpy", "python matrix", "jupyter", "scientific visualization", "data analysis"],
    "neuropixels-analysis": ["clinical eeg", "fmri", "generic neuroscience", "single-cell rna", "flow cytometry"],
    "pymc": ["scikit-learn", "sklearn", "generic regression", "causal analysis", "pymoo", "nsga"],
    "pymoo": ["pymc", "bayesian", "generic optimization", "experiment design", "gradient descent", "causal analysis"],
    "rowan": ["rdkit", "pubchem", "chembl", "docking", "pka", "conformer search", "quantum chemistry", "not rowan"],
    "stable-baselines3": ["scikit-learn", "sklearn", "random forest", "supervised learning", "not reinforcement learning"],
    "timesfm-forecasting": ["scikit-learn", "ordinary regression", "tabular regression", "business forecast", "arima", "not time series"],
    "torch-geometric": ["cnn", "resnet", "generic neural network", "network graph visualization", "molecule-only", "image classification"],
}


DOC_BOUNDARY_PHRASES = {
    "simpy": ["routing boundary", "simpy", "discrete-event"],
    "fluidsim": ["routing boundary", "fluidsim", "cfd"],
    "matchms": ["routing boundary", "mass spectra", "spectral"],
    "matlab": ["routing boundary", "matlab", "octave"],
    "neuropixels-analysis": ["routing boundary", "neuropixels", "spike sorting"],
    "pymc": ["routing boundary", "pymc", "probabilistic programming"],
    "pymoo": ["routing boundary", "pymoo", "multi-objective"],
    "rowan": ["routing boundary", "explicit rowan", "rowan-python"],
    "stable-baselines3": ["routing boundary", "stable-baselines3", "reinforcement learning"],
    "timesfm-forecasting": ["routing boundary", "timesfm", "foundation forecasting"],
    "torch-geometric": ["routing boundary", "pytorch geometric", "graph neural network"],
}


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
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


def load_keyword_index() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "skill-keyword-index.json").read_text(encoding="utf-8-sig"))


def skill_keywords(skill_id: str) -> list[str]:
    index = load_keyword_index()
    skill = index.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    keywords = skill.get("keywords")
    assert isinstance(keywords, list), skill
    return [str(keyword).lower() for keyword in keywords]


def load_routing_rules() -> dict[str, object]:
    return json.loads((REPO_ROOT / "config" / "skill-routing-rules.json").read_text(encoding="utf-8-sig"))


def routing_rule(skill_id: str) -> dict[str, object]:
    rules = load_routing_rules()
    skill = rules.get("skills", {}).get(skill_id)
    assert isinstance(skill, dict), skill_id
    return skill


def positive_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("positive_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def negative_keywords(skill_id: str) -> list[str]:
    keywords = routing_rule(skill_id).get("negative_keywords")
    assert isinstance(keywords, list), skill_id
    return [str(keyword).lower() for keyword in keywords]


def skill_body(skill_id: str) -> str:
    path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
    text = path.read_text(encoding="utf-8-sig")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lower()
    return text.lower()


class LongtailScienceMlPackCleanupTests(unittest.TestCase):
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

    def assert_not_selected(
        self,
        prompt: str,
        blocked_pack: str | None = None,
        blocked_skill: str | None = None,
        *,
        task_type: str = "coding",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        chosen_pack, chosen_skill = selected(result)
        if blocked_pack is not None:
            self.assertNotEqual(blocked_pack, chosen_pack, ranked_summary(result))
        if blocked_skill is not None:
            self.assertNotEqual(blocked_skill, chosen_skill, ranked_summary(result))

    def test_manifest_keeps_target_direct_owners_and_zero_stage_assistants(self) -> None:
        for pack_id, skill_id in TARGET_DIRECT_OWNERS.items():
            with self.subTest(pack_id=pack_id):
                pack = load_pack(pack_id)
                self.assertEqual([skill_id], pack.get("skill_candidates"))
                self.assertNotIn("route_authority_candidates", pack)
                self.assertNotIn("stage_assistant_candidates", pack)
                defaults = pack.get("defaults_by_task")
                self.assertIsInstance(defaults, dict)
                self.assertEqual(skill_id, defaults.get("planning"))
                self.assertEqual(skill_id, defaults.get("coding"))
                self.assertEqual(skill_id, defaults.get("research"))

    def test_explicit_target_prompts_route_to_direct_owners(self) -> None:
        for prompt, expected_pack, expected_skill, task_type in POSITIVE_ROUTE_CASES:
            with self.subTest(expected_skill=expected_skill):
                self.assert_selected(prompt, expected_pack, expected_skill, task_type=task_type)

    def test_generic_neighbor_prompts_do_not_route_to_longtail_owners(self) -> None:
        for prompt, blocked_pack, blocked_skill, task_type in BLOCKED_ROUTE_CASES:
            with self.subTest(blocked_skill=blocked_skill):
                self.assert_not_selected(prompt, blocked_pack, blocked_skill, task_type=task_type)

    def test_keyword_index_uses_precise_target_terms(self) -> None:
        for skill_id, required_terms in REQUIRED_KEYWORDS.items():
            with self.subTest(skill_id=skill_id):
                keywords = skill_keywords(skill_id)
                for term in required_terms:
                    self.assertIn(term.lower(), keywords)

    def test_keyword_index_removes_broad_ordinary_route_terms(self) -> None:
        for skill_id, forbidden_terms in FORBIDDEN_POSITIVE_KEYWORDS.items():
            with self.subTest(skill_id=skill_id):
                keywords = skill_keywords(skill_id)
                positives = positive_keywords(skill_id)
                for term in forbidden_terms:
                    self.assertNotIn(term.lower(), keywords)
                    self.assertNotIn(term.lower(), positives)

    def test_routing_rules_encode_negative_boundaries(self) -> None:
        for skill_id, required_terms in REQUIRED_NEGATIVE_KEYWORDS.items():
            with self.subTest(skill_id=skill_id):
                negatives = negative_keywords(skill_id)
                for term in required_terms:
                    self.assertIn(term.lower(), negatives)

    def test_skill_docs_state_routing_boundaries(self) -> None:
        for skill_id, phrases in DOC_BOUNDARY_PHRASES.items():
            with self.subTest(skill_id=skill_id):
                body = skill_body(skill_id)
                for phrase in phrases:
                    self.assertIn(phrase, body)

    def test_simplified_route_model_does_not_reintroduce_assistant_states(self) -> None:
        manifest = load_manifest()
        for pack in manifest.get("packs", []):
            assert isinstance(pack, dict), pack
            self.assertNotIn("advisory_candidates", pack)
            self.assertNotIn("consultation_candidates", pack)
            self.assertNotIn("primary_skill", pack)
            self.assertNotIn("secondary_skills", pack)


if __name__ == "__main__":
    unittest.main()
