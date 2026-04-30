# Zero Route Authority Third Pass

Date: 2026-04-30

## Scope

This pass completes the remaining single-skill zero-route-authority cleanup.

| Metric | Before | After |
| --- | ---: | ---: |
| zero-route-authority packs | 14 | 0 |
| non-empty `stage_assistant_candidates` | 0 | 0 |
| physically deleted skill directories | 0 | 0 |

Out of scope:

- six-stage Vibe runtime changes
- specialist consultation policy changes
- dense-pack false-positive audits
- route selection claims about actual material skill use

## Direct Owners

| Pack | Direct route owner | Boundary |
| --- | --- | --- |
| `docs-markitdown-conversion` | `markitdown` | MarkItDown document-to-Markdown conversion. |
| `ip-uspto-patents` | `uspto-database` | USPTO patent search, claims, text, and metadata. |
| `science-astropy` | `astropy` | Astronomy data, FITS, WCS, units, and Astropy workflows. |
| `science-pymatgen` | `pymatgen` | Materials structures, CIF, crystal structures, and pymatgen workflows. |
| `science-simpy-simulation` | `simpy` | Discrete-event simulation, queues, resources, and SimPy process models. |
| `science-fluidsim-cfd` | `fluidsim` | Computational fluid dynamics, Navier-Stokes, turbulence, and FluidSim workflows. |
| `science-matchms-spectra` | `matchms` | Mass spectra processing and spectral similarity with matchms. |
| `science-matlab-octave` | `matlab` | MATLAB/Octave scripts, Simulink, and matrix workflows. |
| `science-neuropixels` | `neuropixels-analysis` | Neuropixels electrophysiology, spike sorting, SpikeGLX, and Open Ephys workflows. |
| `science-pymc-bayesian` | `pymc` | Bayesian models, MCMC/NUTS, posterior analysis, and PyMC workflows. |
| `science-pymoo-optimization` | `pymoo` | Multi-objective and constrained optimization with pymoo. |
| `science-rowan-chemistry` | `rowan` | Rowan cloud quantum-chemistry workflows: pKa, conformer search, geometry optimization, docking, and cofolding. |
| `ml-stable-baselines3` | `stable-baselines3` | Stable-Baselines3 reinforcement-learning agents and PPO/SAC/DQN workflows. |
| `science-timesfm-forecasting` | `timesfm-forecasting` | TimesFM and foundation-model time-series forecasting. |

## Deletion Decision

No skill directories were physically deleted in this pass.

`fluidsim` was retained because the directory contains a full CFD skill and references for simulation setup, solvers, parameters, output analysis, and advanced features.

`rowan` was retained because the directory contains a full Rowan cloud quantum-chemistry skill with references for API usage, molecule handling, workflow types, RDKit/native workflows, and result interpretation.

## Route Protection

Focused tests protect:

- all 14 retained packs having direct route owners
- all 14 retained packs having empty `stage_assistant_candidates`
- prompt-level routing for each retained owner
- false-positive boundaries for MATLAB, Stable-Baselines3, TimesFM, matchms, and Rowan
- no remaining zero-route-authority packs

## Remaining Work

No zero-route-authority packs remain after this pass.

Remaining route architecture work is outside this pass:

- runtime/presentation compatibility terms such as `primary_skill`, `accept_primary`, `stage_assistant_candidates`, and `consultation_bucket`
- dense-pack false-positive audits for packs such as `bio-science`, `docs-media`, `data-ml`, `science-chem-drug`, and `scholarly-publishing-workflow`

## Verification

```powershell
python -m pytest tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py tests/runtime_neutral/test_zero_route_authority_pack_consolidation.py -q
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
```

Record the final pass/fail results in the completion report.
