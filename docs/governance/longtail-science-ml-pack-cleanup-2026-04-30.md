# Longtail Science ML Pack Cleanup

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

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
- Chinese negation scope now recognizes `不调用`, so prompts such as `不调用 Rowan` block Rowan route capture.
- Every target pack remains free of `stage_assistant_candidates`.
- No target bundled skill directory was physically deleted in this pass.

## Verification

| Command | Result |
| --- | --- |
| `python -m pytest tests\runtime_neutral\test_longtail_science_ml_pack_cleanup.py -q` | `8 passed in 5.74s`. |
| `python -m pytest tests\runtime_neutral\test_zero_route_authority_third_pass.py tests\runtime_neutral\test_zero_route_authority_second_pass.py -q` | `14 passed in 8.02s`. |
| `.\scripts\verify\probe-scientific-packs.ps1` | exit 0; wrote `outputs\verify\route-probe-scientific\summary.json`. |
| `.\scripts\verify\vibe-skill-index-routing-audit.ps1` | `Total assertions: 521; Passed: 521; Failed: 0`; `Skill-index routing audit passed.` |
| `.\scripts\verify\vibe-pack-regression-matrix.ps1` | `Total assertions: 479; Passed: 479; Failed: 0`; `Pack regression matrix checks passed.` |
| `.\scripts\verify\vibe-pack-routing-smoke.ps1` | `Total assertions: 958; Passed: 958; Failed: 0`; `Pack routing smoke checks passed.` |
| `.\scripts\verify\vibe-offline-skills-gate.ps1` | `[PASS] offline skill closure gate passed`; `present_skills=296`; `lock_skills=296`. |
| `git diff --check` | exit 0; no whitespace errors. |

`longtail-science-ml` probe group summary:

```json
{
  "group": "longtail-science-ml",
  "case_count": 16,
  "pack_match_ratio": 1.0,
  "skill_match_ratio": 1.0,
  "skill_match_text": "100%",
  "confirm_required_ratio": 0.0,
  "avg_confidence": 0.8127
}
```

## Evidence Boundary

This pass proves routing, config, bundled skill documentation, regression tests, and governance documentation only.

It does not prove real task material skill use. Material use still requires actual routed task artifacts such as produced code, model outputs, figures, reports, execution logs, or built deliverables.
