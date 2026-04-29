# Zero Route Authority Second Pass

Date: 2026-04-29

## Scope

This pass cleans three zero-route-authority packs:

| Pack | Before | After |
| --- | --- | --- |
| `cloud-modalcom` | 1 skill candidate, 0 route owners | 1 direct route owner, 0 stage assistants |
| `ml-torch-geometric` | 2 skill candidates, 0 route owners | 1 canonical direct route owner, 0 stage assistants |
| `science-quantum` | 4 skill candidates, 0 route owners | 4 direct route owners, 0 stage assistants |

Out of scope:

- six-stage Vibe runtime changes
- specialist consultation policy changes
- dense-pack audits
- route selection claims about actual material skill use

## Direct Owners

| Pack | Direct route owners | Boundary |
| --- | --- | --- |
| `cloud-modalcom` | `modal-labs` | Modal / modal.com / Modal Labs cloud execution, Python GPU functions, batch jobs, serverless GPU, autoscaling containers, and Modal deployment. |
| `ml-torch-geometric` | `torch-geometric` | PyTorch Geometric / PyG graph neural networks, including GCN, GAT, graph classification, node classification, and link prediction. |
| `science-quantum` | `qiskit`, `cirq`, `pennylane`, `qutip` | Qiskit default quantum circuits, Cirq ecosystem work, PennyLane quantum ML, and QuTiP open quantum systems. |

## Removed Or Consolidated

| Skill | Decision | Reason |
| --- | --- | --- |
| `torch_geometric` | Removed after alias review | It was a thin compatibility alias that delegated to `torch-geometric` and had no unique scripts, references, examples, or assets. The underscore spelling is retained as a keyword/API spelling for the canonical `torch-geometric` skill. |

## Route Protection

Focused tests protect:

- Chinese Modal deployment prompts routing to `cloud-modalcom/modal-labs`.
- Modal-not-Vercel prompts avoiding `integration-devops/vercel-deploy`.
- Frontend modal dialog prompts avoiding `cloud-modalcom/modal-labs`.
- `torch_geometric` API spelling routing to canonical `torch-geometric`.
- Generic PyTorch image/CNN prompts avoiding PyG.
- Qiskit, Cirq, PennyLane, and QuTiP ecosystem prompts selecting the intended quantum owner.

## Remaining Zero-Route-Authority Packs

The following packs remain intentionally deferred:

```text
docs-markitdown-conversion
ip-uspto-patents
science-astropy
science-pymatgen
science-simpy-simulation
science-fluidsim-cfd
science-matchms-spectra
science-matlab-octave
science-neuropixels
science-pymc-bayesian
science-pymoo-optimization
science-rowan-chemistry
ml-stable-baselines3
science-timesfm-forecasting
```

## Verification

```powershell
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py -q
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
```

Record the final pass/fail results in the completion report.
