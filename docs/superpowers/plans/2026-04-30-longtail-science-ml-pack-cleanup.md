# Longtail Science ML Pack Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Narrow and verify the longtail single-tool science/ML route owners while keeping the Vibe six-stage runtime and the simplified `candidate skill -> selected skill -> used / unused` model unchanged.

**Architecture:** Keep the target packs as ordinary direct owners, but make cold specialists require explicit tool names or unmistakable domain signals. Rowan and MATLAB stay installed but become explicit-tool routes only, so generic chemistry, matrix computing, visualization, and scientific Python work do not get captured by them. This implementation changes route tests, JSON route configuration, verification scripts, short bundled skill boundary notes, governance evidence, and the skills lock; it does not add advisory experts, helper experts, primary/secondary skill state, or stage assistants.

**Tech Stack:** Python `unittest`/`pytest`, PowerShell verification scripts, JSON route configuration, bundled Markdown skill docs, skills lock generation, Git.

---

## Scope

This plan implements:

```text
docs/superpowers/specs/2026-04-30-longtail-science-ml-pack-cleanup-design.md
```

Target packs and skills:

```text
science-simpy-simulation    -> simpy
science-fluidsim-cfd        -> fluidsim
science-matchms-spectra     -> matchms
science-matlab-octave       -> matlab
science-neuropixels         -> neuropixels-analysis
science-pymc-bayesian       -> pymc
science-pymoo-optimization  -> pymoo
science-rowan-chemistry     -> rowan
ml-stable-baselines3        -> stable-baselines3
science-timesfm-forecasting -> timesfm-forecasting
ml-torch-geometric          -> torch-geometric
```

Keep this invariant for every target pack:

```text
skill_candidates = [target skill]
route_authority_candidates = [target skill]
stage_assistant_candidates = []
```

Do not physically delete target `bundled/skills/*` directories in this pass. All target skill directories contain unique files and assets.

Do not claim real task material skill use from these changes. This work proves route/config/doc/test cleanup only.

## File Map

- Create `tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py`: focused Python route/config/doc regression tests for all 11 target packs.
- Modify `config/skill-keyword-index.json`: remove broad standalone Rowan/MATLAB triggers and narrow cold specialist keyword lists.
- Modify `config/skill-routing-rules.json`: add precise positive route phrases and strong negative route boundaries for all 11 target skills.
- Modify `scripts/verify/vibe-pack-regression-matrix.ps1`: add longtail positive and blocked route cases.
- Modify `scripts/verify/vibe-skill-index-routing-audit.ps1`: add longtail positive and blocked route cases at the skill-index audit level.
- Modify `scripts/verify/probe-scientific-packs.ps1`: add a `longtail-science-ml` probe group with retained direct-owner and blocked generic cases.
- Modify `bundled/skills/simpy/SKILL.md`: add a short route boundary note requiring SimPy/discrete-event context.
- Modify `bundled/skills/fluidsim/SKILL.md`: add a short route boundary note requiring FluidSim/CFD context.
- Modify `bundled/skills/matchms/SKILL.md`: add a short route boundary note separating spectral processing from generic literature/chemistry work.
- Modify `bundled/skills/matlab/SKILL.md`: add a short route boundary note requiring MATLAB/Octave/Simulink or `.m` context.
- Modify `bundled/skills/neuropixels-analysis/SKILL.md`: add a short route boundary note requiring Neuropixels/spike-sorting/electrophysiology acquisition context.
- Modify `bundled/skills/pymc/SKILL.md`: add a short route boundary note separating PyMC/probabilistic programming from generic regression.
- Modify `bundled/skills/pymoo/SKILL.md`: add a short route boundary note separating pymoo/multi-objective optimization from generic optimization or experiment design.
- Modify `bundled/skills/rowan/SKILL.md`: add a short route boundary note requiring explicit Rowan tool/platform context.
- Modify `bundled/skills/stable-baselines3/SKILL.md`: add a short route boundary note separating SB3/RL from ordinary supervised ML.
- Modify `bundled/skills/timesfm-forecasting/SKILL.md`: add a short route boundary note requiring TimesFM/foundation-forecasting context.
- Modify `bundled/skills/torch-geometric/SKILL.md`: add a short route boundary note separating PyG/GNN from generic neural networks and graph visualization.
- Create `docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md`: governance note with decisions and verification evidence.
- Modify `config/skills-lock.json`: refresh after bundled skill docs change.

## Task 1: Add Failing Longtail Route Tests

**Files:**
- Create: `tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py`

- [ ] **Step 1: Create the focused test file**

Create `tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py` with this exact content:

```python
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
                self.assertEqual([skill_id], pack.get("route_authority_candidates"))
                self.assertEqual([], pack.get("stage_assistant_candidates"))
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
```

- [ ] **Step 2: Run the focused test and confirm it fails before implementation**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py -q
```

Expected result before implementation:

```text
FAILED
```

The expected failing assertions are missing route boundaries, broad Rowan/MATLAB positive keywords, missing script coverage, or missing skill-doc boundary phrases.

- [ ] **Step 3: Commit the failing coverage**

Run:

```powershell
git add tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py
git diff --cached --check
git commit -m "test: add longtail science ml cleanup coverage"
```

Expected result:

```text
[main <sha>] test: add longtail science ml cleanup coverage
```

## Task 2: Narrow JSON Route Configuration

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Check only: `config/pack-manifest.json`
- Test: `tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py`

- [ ] **Step 1: Verify the manifest invariant before changing route keywords**

Run:

```powershell
$manifest = Get-Content -Raw -LiteralPath 'config\pack-manifest.json' | ConvertFrom-Json
$ids = @(
  'science-simpy-simulation',
  'science-fluidsim-cfd',
  'science-matchms-spectra',
  'science-matlab-octave',
  'science-neuropixels',
  'science-pymc-bayesian',
  'science-pymoo-optimization',
  'science-rowan-chemistry',
  'ml-stable-baselines3',
  'science-timesfm-forecasting',
  'ml-torch-geometric'
)
$manifest.packs |
  Where-Object { $ids -contains $_.id } |
  Select-Object id, skill_candidates, route_authority_candidates, stage_assistant_candidates, defaults_by_task |
  ConvertTo-Json -Depth 8
```

Expected result: each target pack shows one skill candidate, one route authority candidate, empty `stage_assistant_candidates`, and all task defaults set to the same target skill.

- [ ] **Step 2: Edit the target keyword-index entries**

In `config/skill-keyword-index.json`, set the `keywords` arrays for the target skills to these exact lower-noise lists:

```json
{
  "simpy": [
    "simpy",
    "simpy discrete event simulation",
    "simpy queue simulation",
    "simpy resource process",
    "simpy environment",
    "离散事件仿真 simpy",
    "simpy 排队仿真"
  ],
  "fluidsim": [
    "fluidsim",
    "fluidsim cfd",
    "fluidsim navier-stokes",
    "fluidsim turbulence",
    "fluidsim shallow water",
    "fluidsim pseudospectral",
    "fluid dynamics fluidsim",
    "流体仿真 fluidsim"
  ],
  "matchms": [
    "matchms",
    "mass spectra",
    "mass spectrum",
    "ms/ms",
    "msms",
    "spectral similarity",
    "metabolomics spectrum processing",
    "spectrum processing",
    "质谱谱图匹配"
  ],
  "matlab": [
    "matlab",
    "octave",
    ".m script",
    "m-file",
    "simulink",
    "matlab script",
    "matlab/octave",
    "matlab脚本"
  ],
  "neuropixels-analysis": [
    "neuropixels",
    "spikeglx",
    "kilosort",
    "spike sorting",
    "open ephys",
    "ibl electrophysiology",
    "neuropixels probe",
    "神经电生理 neuropixels"
  ],
  "pymc": [
    "pymc",
    "bayesian hierarchical model",
    "nuts mcmc",
    "posterior predictive",
    "probabilistic programming",
    "pymc model",
    "pymc sampling",
    "贝叶斯 pymc"
  ],
  "pymoo": [
    "pymoo",
    "nsga-ii",
    "nsga",
    "multi-objective optimization",
    "pareto front",
    "pymoo constraint optimization",
    "pymoo algorithm",
    "多目标优化 pymoo"
  ],
  "rowan": [
    "rowan",
    "rowan chemistry",
    "rowan-python",
    "labs.rowansci.com",
    "rowan api",
    "rowan workflow",
    "rowan cloud chemistry",
    "rowan 量子化学"
  ],
  "stable-baselines3": [
    "stable-baselines3",
    "stable baselines3",
    "sb3",
    "ppo",
    "sac",
    "dqn",
    "reinforcement learning",
    "rl agent",
    "强化学习 stable-baselines3"
  ],
  "timesfm-forecasting": [
    "timesfm",
    "timesfm forecasting",
    "zero-shot forecasting",
    "prediction intervals",
    "foundation model forecasting",
    "forecast horizon",
    "time series foundation model",
    "零样本预测 timesfm"
  ],
  "torch-geometric": [
    "torch-geometric",
    "torch_geometric",
    "pyg",
    "pytorch geometric",
    "graph neural network",
    "gnn",
    "gcn",
    "gat",
    "graph classification",
    "node classification",
    "link prediction",
    "图神经网络 pyg"
  ]
}
```

Do not add standalone `matrix calculation`, `pka prediction`, `conformer search`, `geometry optimization`, `quantum chemistry`, `docking`, `time series forecasting`, `business forecast`, or `optimization` as positive terms for the target skills.

- [ ] **Step 3: Edit the target routing-rule entries**

In `config/skill-routing-rules.json`, set the target skills' `positive_keywords` to match the keyword-index arrays from Step 2 and set these `negative_keywords`:

```json
{
  "simpy": [
    "sympy",
    "symbolic math",
    "matplotlib animation",
    "agent-based model",
    "monte carlo simulation",
    "generic simulation",
    "physics simulation"
  ],
  "fluidsim": [
    "css",
    "fluid layout",
    "responsive design",
    "fluid typography",
    "generic pde",
    "finite element",
    "python simulation",
    "液态布局"
  ],
  "matchms": [
    "pubmed",
    "literature review",
    "generic chemistry",
    "non-spectral metabolomics",
    "plotting",
    "matplotlib",
    "not mass spectra",
    "不处理 mass spectra"
  ],
  "matlab": [
    "not matlab",
    "not octave",
    "不使用 matlab",
    "不使用 MATLAB",
    "numpy",
    "python matrix",
    "jupyter",
    "scientific visualization",
    "data analysis",
    "numerical computing",
    "numpy array"
  ],
  "neuropixels-analysis": [
    "single-cell rna",
    "flow cytometry",
    "clinical eeg",
    "fmri",
    "generic neuroscience",
    "rna-seq",
    "calcium imaging without neuropixels"
  ],
  "pymc": [
    "pymatgen",
    "crystal structure",
    "materials project",
    "pymoo",
    "nsga",
    "scikit-learn",
    "sklearn",
    "generic regression",
    "causal analysis"
  ],
  "pymoo": [
    "pymc",
    "bayesian",
    "mcmc",
    "posterior",
    "generic optimization",
    "experiment design",
    "gradient descent",
    "causal analysis"
  ],
  "rowan": [
    "quaternion",
    "scipy rotation",
    "rotation matrix",
    "rowan tree",
    "not rowan",
    "不调用 rowan",
    "rdkit",
    "pubchem",
    "chembl",
    "docking",
    "pka",
    "conformer search",
    "quantum chemistry",
    "molecular machine learning"
  ],
  "stable-baselines3": [
    "scikit-learn",
    "sklearn",
    "random forest",
    "supervised learning",
    "ordinary supervised",
    "not reinforcement learning",
    "不是 reinforcement learning",
    "classification model"
  ],
  "timesfm-forecasting": [
    "scikit-learn",
    "ordinary regression",
    "tabular regression",
    "business forecast",
    "arima",
    "not time series",
    "不是 time series forecasting"
  ],
  "torch-geometric": [
    "cnn",
    "resnet",
    "image classification",
    "图像分类",
    "computer vision",
    "vision transformer",
    "generic neural network",
    "network graph visualization",
    "molecule-only"
  ]
}
```

- [ ] **Step 4: Validate JSON syntax**

Run:

```powershell
python -m json.tool config/skill-keyword-index.json > $null
python -m json.tool config/skill-routing-rules.json > $null
python -m json.tool config/pack-manifest.json > $null
```

Expected result:

```text
<no output and exit code 0>
```

- [ ] **Step 5: Run the focused Python test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py -q
```

Expected result after JSON-only changes: remaining failures may be limited to missing bundled skill-doc boundary phrases. Route positive/negative cases and keyword/rule assertions should pass before moving on.

- [ ] **Step 6: Commit the JSON route narrowing**

Run:

```powershell
git add config/skill-keyword-index.json config/skill-routing-rules.json
git diff --cached --check
git commit -m "fix: narrow longtail science ml route boundaries"
```

Expected result:

```text
[main <sha>] fix: narrow longtail science ml route boundaries
```

## Task 3: Expand PowerShell Route Evidence

**Files:**
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Modify: `scripts/verify/probe-scientific-packs.ps1`

- [ ] **Step 1: Add regression-matrix cases**

In `scripts/verify/vibe-pack-regression-matrix.ps1`, add these cases inside the `$cases = @(` array near the other science route cases:

```powershell
[pscustomobject]@{ Name = "longtail simpy explicit"; Prompt = "用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-simpy-simulation"; ExpectedSkill = "simpy"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail fluidsim explicit"; Prompt = "用 FluidSim 做 Navier-Stokes CFD turbulence spectra 分析"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-fluidsim-cfd"; ExpectedSkill = "fluidsim"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail matchms explicit"; Prompt = "用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-matchms-spectra"; ExpectedSkill = "matchms"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail matlab explicit"; Prompt = "写 MATLAB/Octave .m script 并连接 Simulink 模型"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-matlab-octave"; ExpectedSkill = "matlab"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail neuropixels explicit"; Prompt = "分析 Neuropixels SpikeGLX 数据，运行 Kilosort spike sorting 并整理 probe channel map"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "science-neuropixels"; ExpectedSkill = "neuropixels-analysis"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail pymc explicit"; Prompt = "用 PyMC 建立 Bayesian hierarchical model，运行 NUTS MCMC 和 posterior predictive checks"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-pymc-bayesian"; ExpectedSkill = "pymc"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail pymoo explicit"; Prompt = "用 pymoo 做 NSGA-II multi-objective optimization，输出 Pareto front"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-pymoo-optimization"; ExpectedSkill = "pymoo"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail rowan explicit"; Prompt = "用 Rowan rowan-python 调用 labs.rowansci.com API 管理计算任务"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-rowan-chemistry"; ExpectedSkill = "rowan"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail sb3 explicit"; Prompt = "用 Stable-Baselines3 SB3 训练 PPO reinforcement learning agent"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "ml-stable-baselines3"; ExpectedSkill = "stable-baselines3"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail timesfm explicit"; Prompt = "用 TimesFM 做 zero-shot forecasting，设置 forecast horizon 和 prediction intervals"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "science-timesfm-forecasting"; ExpectedSkill = "timesfm-forecasting"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail torch geometric explicit"; Prompt = "用 PyTorch Geometric torch_geometric 写 PyG GNN node classification pipeline"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "ml-torch-geometric"; ExpectedSkill = "torch-geometric"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail blocks generic simulation"; Prompt = "设计一个普通 agent-based simulation 和 Monte Carlo simulation，不使用 SimPy 或离散事件资源队列"; Grade = "M"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-simpy-simulation"; BlockedSkill = "simpy"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail blocks numpy matlab"; Prompt = "用 NumPy 做 Python matrix multiplication，在 Jupyter 里做 scientific visualization，不使用 MATLAB 或 Octave"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-matlab-octave"; BlockedSkill = "matlab"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail blocks generic chemistry rowan"; Prompt = "用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-rowan-chemistry"; BlockedSkill = "rowan"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail blocks sklearn sb3"; Prompt = "用 scikit-learn 训练 supervised classification 模型，不是 reinforcement learning 或 SB3"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "ml-stable-baselines3"; BlockedSkill = "stable-baselines3"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "longtail blocks generic forecast timesfm"; Prompt = "做普通 business forecast、ARIMA baseline 和 tabular regression，不使用 TimesFM 或 foundation forecasting"; Grade = "M"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = $null; BlockedPack = "science-timesfm-forecasting"; BlockedSkill = "timesfm-forecasting"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") }
```

- [ ] **Step 2: Add skill-index audit cases**

In `scripts/verify/vibe-skill-index-routing-audit.ps1`, add the same 16 cases from Task 3 Step 1 inside the `$cases = @(` array. Remove the `RequestedSkill` and `AllowedModes` properties from each object because this script does not use them.

The first added object should look exactly like this in this script:

```powershell
[pscustomobject]@{ Name = "longtail simpy explicit"; Prompt = "用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization"; Grade = "M"; TaskType = "coding"; ExpectedPack = "science-simpy-simulation"; ExpectedSkill = "simpy" },
```

The blocked Rowan object should look exactly like this in this script:

```powershell
[pscustomobject]@{ Name = "longtail blocks generic chemistry rowan"; Prompt = "用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan"; Grade = "M"; TaskType = "research"; BlockedPack = "science-rowan-chemistry"; BlockedSkill = "rowan" },
```

- [ ] **Step 3: Add scientific probe cases**

In `scripts/verify/probe-scientific-packs.ps1`, add these `longtail-science-ml` objects inside `$cases = @(`:

```powershell
[pscustomobject]@{ name = "longtail_simpy_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 SimPy 建一个离散事件仿真 queue resource process，并输出 resource utilization"; grade = "M"; task_type = "coding"; expected_pack = "science-simpy-simulation"; expected_skill = "simpy"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_fluidsim_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 FluidSim 做 Navier-Stokes CFD turbulence spectra 分析"; grade = "M"; task_type = "coding"; expected_pack = "science-fluidsim-cfd"; expected_skill = "fluidsim"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_matchms_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 matchms 处理 MS/MS mass spectra 并计算 spectral similarity"; grade = "M"; task_type = "coding"; expected_pack = "science-matchms-spectra"; expected_skill = "matchms"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_matlab_explicit"; group = "longtail-science-ml"; prompt = "/vibe 写 MATLAB/Octave .m script 并连接 Simulink 模型"; grade = "M"; task_type = "coding"; expected_pack = "science-matlab-octave"; expected_skill = "matlab"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_neuropixels_explicit"; group = "longtail-science-ml"; prompt = "/vibe 分析 Neuropixels SpikeGLX 数据，运行 Kilosort spike sorting 并整理 probe channel map"; grade = "M"; task_type = "research"; expected_pack = "science-neuropixels"; expected_skill = "neuropixels-analysis"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_pymc_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 PyMC 建立 Bayesian hierarchical model，运行 NUTS MCMC 和 posterior predictive checks"; grade = "M"; task_type = "coding"; expected_pack = "science-pymc-bayesian"; expected_skill = "pymc"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_pymoo_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 pymoo 做 NSGA-II multi-objective optimization，输出 Pareto front"; grade = "M"; task_type = "coding"; expected_pack = "science-pymoo-optimization"; expected_skill = "pymoo"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_rowan_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 Rowan rowan-python 调用 labs.rowansci.com API 管理计算任务"; grade = "M"; task_type = "coding"; expected_pack = "science-rowan-chemistry"; expected_skill = "rowan"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_sb3_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 Stable-Baselines3 SB3 训练 PPO reinforcement learning agent"; grade = "M"; task_type = "coding"; expected_pack = "ml-stable-baselines3"; expected_skill = "stable-baselines3"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_timesfm_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 TimesFM 做 zero-shot forecasting，设置 forecast horizon 和 prediction intervals"; grade = "M"; task_type = "coding"; expected_pack = "science-timesfm-forecasting"; expected_skill = "timesfm-forecasting"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_torch_geometric_explicit"; group = "longtail-science-ml"; prompt = "/vibe 用 PyTorch Geometric torch_geometric 写 PyG GNN node classification pipeline"; grade = "M"; task_type = "coding"; expected_pack = "ml-torch-geometric"; expected_skill = "torch-geometric"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_blocks_generic_simulation"; group = "longtail-science-ml"; prompt = "/vibe 设计一个普通 agent-based simulation 和 Monte Carlo simulation，不使用 SimPy 或离散事件资源队列"; grade = "M"; task_type = "planning"; blocked_pack = "science-simpy-simulation"; blocked_skill = "simpy"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_blocks_numpy_matlab"; group = "longtail-science-ml"; prompt = "/vibe 用 NumPy 做 Python matrix multiplication，在 Jupyter 里做 scientific visualization，不使用 MATLAB 或 Octave"; grade = "M"; task_type = "coding"; blocked_pack = "science-matlab-octave"; blocked_skill = "matlab"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_blocks_generic_chemistry_rowan"; group = "longtail-science-ml"; prompt = "/vibe 用 RDKit、PubChem、ChEMBL 做 generic chemistry、docking、pKa、conformer search 和 molecular ML，不调用 Rowan"; grade = "M"; task_type = "research"; blocked_pack = "science-rowan-chemistry"; blocked_skill = "rowan"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_blocks_sklearn_sb3"; group = "longtail-science-ml"; prompt = "/vibe 用 scikit-learn 训练 supervised classification 模型，不是 reinforcement learning 或 SB3"; grade = "M"; task_type = "coding"; blocked_pack = "ml-stable-baselines3"; blocked_skill = "stable-baselines3"; requested_skill = $null },
[pscustomobject]@{ name = "longtail_blocks_generic_forecast_timesfm"; group = "longtail-science-ml"; prompt = "/vibe 做普通 business forecast、ARIMA baseline 和 tabular regression，不使用 TimesFM 或 foundation forecasting"; grade = "M"; task_type = "research"; blocked_pack = "science-timesfm-forecasting"; blocked_skill = "timesfm-forecasting"; requested_skill = $null }
```

- [ ] **Step 4: Run the three route evidence scripts**

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\probe-scientific-packs.ps1
```

Expected result:

```text
Pack regression matrix checks passed.
Skill-index routing audit passed.
```

`probe-scientific-packs.ps1` should write `outputs\verify\route-probe-scientific\summary.json` and exit 0.

- [ ] **Step 5: Commit the PowerShell route evidence**

Run:

```powershell
git add scripts/verify/vibe-pack-regression-matrix.ps1 scripts/verify/vibe-skill-index-routing-audit.ps1 scripts/verify/probe-scientific-packs.ps1
git diff --cached --check
git commit -m "test: expand longtail science ml route regressions"
```

Expected result:

```text
[main <sha>] test: expand longtail science ml route regressions
```

## Task 4: Clarify Bundled Skill Boundaries

**Files:**
- Modify: `bundled/skills/simpy/SKILL.md`
- Modify: `bundled/skills/fluidsim/SKILL.md`
- Modify: `bundled/skills/matchms/SKILL.md`
- Modify: `bundled/skills/matlab/SKILL.md`
- Modify: `bundled/skills/neuropixels-analysis/SKILL.md`
- Modify: `bundled/skills/pymc/SKILL.md`
- Modify: `bundled/skills/pymoo/SKILL.md`
- Modify: `bundled/skills/rowan/SKILL.md`
- Modify: `bundled/skills/stable-baselines3/SKILL.md`
- Modify: `bundled/skills/timesfm-forecasting/SKILL.md`
- Modify: `bundled/skills/torch-geometric/SKILL.md`
- Modify: `config/skills-lock.json`
- Test: `tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py`

- [ ] **Step 1: Add one short `## Routing Boundary` section per target skill**

Add the matching section below the front matter and before workflow details in each target `SKILL.md`. Keep existing operational instructions intact.

`bundled/skills/simpy/SKILL.md`:

````markdown
## Routing Boundary

Use this skill only for SimPy or explicit discrete-event simulation work involving SimPy environments, resources, processes, queues, and event scheduling. Do not use it for generic simulation, Monte Carlo work, agent-based modeling, physics simulation, animation, or SymPy symbolic math unless the user explicitly asks for SimPy.
````

`bundled/skills/fluidsim/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for FluidSim or explicit CFD workflows such as Navier-Stokes, turbulence, shallow-water, stratified-flow, or pseudospectral fluid simulations. Do not use it for CSS fluid layouts, responsive design, generic Python simulation, generic PDE solving, or non-FluidSim numerical physics work.
```

`bundled/skills/matchms/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for matchms, mass spectra, MS/MS spectrum processing, spectral similarity, and metabolomics spectrum workflows. Do not use it for PubMed searches, generic chemistry, non-spectral metabolomics, plotting-only requests, or literature review tasks that do not process mass spectra.
```

`bundled/skills/matlab/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only when the user explicitly asks for MATLAB, Octave, Simulink, `.m` scripts, M-files, or MATLAB-specific tooling. Do not use it for generic NumPy, Python matrix work, Jupyter notebooks, scientific visualization, data analysis, or numerical computing unless MATLAB or Octave is explicit.
```

`bundled/skills/neuropixels-analysis/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for Neuropixels, SpikeGLX, Kilosort, Open Ephys, spike sorting, probe/channel maps, or electrophysiology recording workflows tied to these tools. Do not use it for generic neuroscience literature, clinical EEG, fMRI, flow cytometry, or single-cell RNA analysis.
```

`bundled/skills/pymc/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for PyMC, probabilistic programming, Bayesian hierarchical models, NUTS/MCMC sampling, posterior predictive checks, and PyMC model diagnostics. Do not use it for generic regression, scikit-learn modeling, causal analysis, pymoo optimization, or materials-science prompts.
```

`bundled/skills/pymoo/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for pymoo, NSGA-II/NSGA, Pareto-front analysis, multi-objective optimization, constrained optimization, and pymoo algorithm implementation. Do not use it for generic optimization planning, experiment design, gradient descent, Bayesian modeling, PyMC, or causal analysis.
```

`bundled/skills/rowan/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only when the user explicitly names Rowan, rowan-python, labs.rowansci.com, the Rowan API, or a Rowan-specific chemistry workflow. Do not use it for generic chemistry, RDKit, PubChem, ChEMBL, docking, pKa, conformer search, quantum chemistry, molecular machine learning, Boltz, or Chai-1 unless explicit Rowan context is present.
```

`bundled/skills/stable-baselines3/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for Stable-Baselines3, SB3, PPO/SAC/DQN, reinforcement learning agents, Gymnasium environments, policies, rollouts, and RL training workflows. Do not use it for ordinary scikit-learn, random forests, supervised classification, tabular regression, or generic machine-learning model training.
```

`bundled/skills/timesfm-forecasting/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for TimesFM, zero-shot forecasting, foundation forecasting, forecast horizons, prediction intervals, or TimesFM-specific time-series pipelines. Do not use it for generic business forecasting, ARIMA baselines, tabular regression, ordinary scikit-learn modeling, or exploratory time-series analysis without TimesFM/foundation-model signals.
```

`bundled/skills/torch-geometric/SKILL.md`:

```markdown
## Routing Boundary

Use this skill only for PyTorch Geometric, torch_geometric, PyG, graph neural networks, GCN/GAT, graph classification, node classification, link prediction, and heterogeneous graph learning. Do not use it for generic neural networks, CNN/image classification, graph visualization, or molecule-only tasks unless PyG or graph neural network modeling is explicit.
```

- [ ] **Step 2: Run the focused Python test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py -q
```

Expected result:

```text
8 passed
```

- [ ] **Step 3: Refresh and verify the skills lock**

Run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected result:

```text
Offline skills gate passed.
```

- [ ] **Step 4: Commit the skill doc boundaries and lock**

Run:

```powershell
git add bundled/skills/simpy/SKILL.md bundled/skills/fluidsim/SKILL.md bundled/skills/matchms/SKILL.md bundled/skills/matlab/SKILL.md bundled/skills/neuropixels-analysis/SKILL.md bundled/skills/pymc/SKILL.md bundled/skills/pymoo/SKILL.md bundled/skills/rowan/SKILL.md bundled/skills/stable-baselines3/SKILL.md bundled/skills/timesfm-forecasting/SKILL.md bundled/skills/torch-geometric/SKILL.md config/skills-lock.json
git diff --cached --check
git commit -m "fix: clarify longtail science ml skill boundaries"
```

Expected result:

```text
[main <sha>] fix: clarify longtail science ml skill boundaries
```

## Task 5: Record Governance Decision

**Files:**
- Create: `docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md`

- [ ] **Step 1: Create the governance note**

Create `docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md` with this structure and the command results observed during Tasks 1-4:

````markdown
# Longtail Science ML Pack Cleanup

Date: 2026-04-30

## Decision

This pass cleaned up longtail single-tool science and ML packs without changing the public Vibe six-stage runtime.

The route model remains:

```text
candidate skill -> selected skill -> used / unused
```

No advisory experts, consultation state, helper experts, primary/secondary skill hierarchy, or stage assistants were added.

## Target Packs

| Pack | Skill | Decision |
| --- | --- | --- |
| `science-simpy-simulation` | `simpy` | Kept as a direct owner; narrowed to SimPy/discrete-event context. |
| `science-fluidsim-cfd` | `fluidsim` | Kept as a direct owner; narrowed to FluidSim/CFD context. |
| `science-matchms-spectra` | `matchms` | Kept as a direct owner; hardened spectral-processing boundaries. |
| `science-matlab-octave` | `matlab` | Kept installed and direct-owned; narrowed to explicit MATLAB/Octave/Simulink/.m context. |
| `science-neuropixels` | `neuropixels-analysis` | Kept as a direct owner; narrowed to Neuropixels/spike-sorting/electrophysiology acquisition context. |
| `science-pymc-bayesian` | `pymc` | Kept as a direct owner; hardened probabilistic-programming boundaries. |
| `science-pymoo-optimization` | `pymoo` | Kept as a direct owner; narrowed to pymoo/multi-objective/Pareto context. |
| `science-rowan-chemistry` | `rowan` | Kept installed and direct-owned; narrowed to explicit Rowan/platform context. |
| `ml-stable-baselines3` | `stable-baselines3` | Kept as a direct owner; narrowed to SB3/reinforcement-learning context. |
| `science-timesfm-forecasting` | `timesfm-forecasting` | Kept as a direct owner; narrowed to TimesFM/foundation-forecasting context. |
| `ml-torch-geometric` | `torch-geometric` | Kept as a direct owner; hardened PyG/GNN boundaries. |

## Boundary Outcomes

- `rowan` no longer has standalone broad positive triggers for generic pKa, conformer search, geometry optimization, quantum chemistry, docking, Boltz, Chai-1, or molecular ML.
- `matlab` no longer has standalone broad positive triggers for matrix calculation, NumPy/Python matrix work, Jupyter, scientific visualization, data analysis, or generic numerical computing.
- Cold specialists now require explicit tool or narrow domain signals.
- Every target pack remains free of `stage_assistant_candidates`.
- No target bundled skill directory was physically deleted in this pass.

## Verification

Record the exact output summary for each command run in the final verification task.

| Command | Result |
| --- | --- |
| `python -m pytest tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py -q` | all tests passed |
| `python -m pytest tests/runtime_neutral/test_zero_route_authority_third_pass.py tests/runtime_neutral/test_zero_route_authority_second_pass.py -q` | all tests passed |
| `.\scripts\verify\probe-scientific-packs.ps1` | exit 0 |
| `.\scripts\verify\vibe-skill-index-routing-audit.ps1` | exit 0 |
| `.\scripts\verify\vibe-pack-regression-matrix.ps1` | exit 0 |
| `.\scripts\verify\vibe-pack-routing-smoke.ps1` | exit 0 |
| `.\scripts\verify\vibe-offline-skills-gate.ps1` | exit 0 |
| `git diff --check` | exit 0 |

## Evidence Boundary

This pass proves routing, config, bundled skill documentation, regression tests, and governance documentation only.

It does not prove real task material skill use. Material use still requires actual routed task artifacts such as produced code, model outputs, figures, reports, execution logs, or built deliverables.
````

- [ ] **Step 2: Commit the governance note**

Run:

```powershell
git add docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md
git diff --cached --check
git commit -m "docs: record longtail science ml cleanup"
```

Expected result:

```text
[main <sha>] docs: record longtail science ml cleanup
```

## Task 6: Final Verification And Evidence Update

**Files:**
- Modify: `docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md`

- [ ] **Step 1: Run the focused and related Python tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_longtail_science_ml_pack_cleanup.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_third_pass.py tests/runtime_neutral/test_zero_route_authority_second_pass.py -q
```

Expected result:

```text
passed
```

- [ ] **Step 2: Run route verification scripts**

Run:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

Expected result:

```text
VCO outputs and all scripts exit 0; git diff --check prints no whitespace errors.
```

- [ ] **Step 3: Summarize the scientific probe output**

Run:

```powershell
$summary = Get-Content -Raw -LiteralPath 'outputs\verify\route-probe-scientific\summary.json' | ConvertFrom-Json
$summary.group_summary | Where-Object { $_.group -eq 'longtail-science-ml' } | ConvertTo-Json -Depth 6
```

Expected result: the `longtail-science-ml` group exists and shows successful pack/skill checks for its expected and blocked cases.

- [ ] **Step 4: Update the governance note with observed verification evidence**

Update `docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md` so the `## Verification` table includes the exact pass counts or exit summaries from Steps 1-3. Keep the evidence-boundary statement unchanged.

- [ ] **Step 5: Commit the verification evidence**

Run:

```powershell
git add docs/governance/longtail-science-ml-pack-cleanup-2026-04-30.md
git diff --cached --check
git commit -m "docs: add longtail science ml verification evidence"
```

Expected result:

```text
[main <sha>] docs: add longtail science ml verification evidence
```

## Task 7: Final Status Report

**Files:**
- Check only: repository status and recent commits

- [ ] **Step 1: Inspect final repository state**

Run:

```powershell
git status --short --branch
git log --oneline -10
```

Expected result:

```text
## main...origin/main [ahead <n>]
```

The short status should contain no uncommitted files from this cleanup.

- [ ] **Step 2: Report the outcome in Chinese**

Final response content:

```text
已完成 longtail science/ML 单工具 pack 整治。

本次保持了六阶段不变，也保持了 candidate skill -> selected skill -> used / unused 的两态使用模型；没有加入辅助专家、咨询状态、主/次技能或 stage assistant。

提交包括：
- test: add longtail science ml cleanup coverage
- fix: narrow longtail science ml route boundaries
- test: expand longtail science ml route regressions
- fix: clarify longtail science ml skill boundaries
- docs: record longtail science ml cleanup
- docs: add longtail science ml verification evidence

验证已通过：列出实际运行过的 pytest 和 PowerShell gate。

注意：这证明的是路由、配置、文档边界和回归测试，不代表真实任务中这些 skills 已经被实质使用。
```
