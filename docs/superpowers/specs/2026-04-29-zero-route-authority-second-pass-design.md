# Zero Route Authority Second Pass Design

Date: 2026-04-29

## 1. Goal

This design defines the second cleanup pass for Vibe-Skills packs that still have
`skill_candidates` but no `route_authority_candidates`.

The goal is to keep the public six-stage Vibe runtime unchanged while making
these packs match the simplified skill-use model:

```text
candidate skill -> selected skill -> used / unused
```

This pass must not reintroduce helper experts, stage assistants,
primary/secondary skill states, advisory routing, consultation routing, or hidden
assistant ownership. A retained skill either directly owns a clear user problem
or it leaves the primary route surface.

## 2. Current Evidence

The working tree was clean before this design was written:

```text
main...origin/main [ahead 162]
```

The latest merged cleanup removed active `stage_assistant_candidates` from the
pack manifest. A fresh manifest scan showed:

```text
total packs: 44
missing skill directories: 0
route/stage candidates outside skill_candidates: 0
non-empty stage_assistant_candidates: 0
zero-route-authority packs: 17
```

The remaining zero-route-authority packs are:

```text
docs-markitdown-conversion
science-quantum
ip-uspto-patents
science-astropy
science-pymatgen
science-simpy-simulation
science-fluidsim-cfd
science-matchms-spectra
science-matlab-octave
cloud-modalcom
science-neuropixels
science-pymc-bayesian
science-pymoo-optimization
science-rowan-chemistry
ml-stable-baselines3
science-timesfm-forecasting
ml-torch-geometric
```

This pass covers only the highest-signal subset:

```text
cloud-modalcom
ml-torch-geometric
science-quantum
```

The subset is selected because it covers three distinct failure modes:

- `cloud-modalcom` has a confirmed real routing miss for Chinese Modal/GPU cloud
  deployment prompts.
- `ml-torch-geometric` has duplicate-looking entries,
  `torch-geometric` and `torch_geometric`, for what appears to be one PyTorch
  Geometric problem surface.
- `science-quantum` has multiple real ecosystem owners but lacks explicit direct
  route authority.

## 3. Scope

### 3.1 In Scope

This pass will:

- Add explicit direct route authority for retained skills in the selected packs.
- Fix `cloud-modalcom` routing so Modal cloud execution prompts do not fall back
  to `integration-devops/vercel-deploy`.
- Consolidate the `ml-torch-geometric` duplicate surface to one canonical route
  owner unless implementation review proves the two directories have distinct
  useful assets that must be migrated first.
- Preserve separate direct owners in `science-quantum` where the ecosystem or
  task boundary is clear.
- Add regression tests that prove prompt-level routing behavior, not just JSON
  field changes.
- Write a governance note documenting before/after ownership and deletion or
  merge decisions.
- Refresh `skills-lock.json` only after route, skill, test, and governance
  changes are stable.

### 3.2 Out Of Scope

This pass will not:

- Change the six-stage Vibe runtime.
- Modify `config/specialist-consultation-policy.json` or runtime consultation
  behavior.
- Process all 17 zero-route-authority packs.
- Audit dense packs such as `bio-science`, `docs-media`, `data-ml`, or
  `scholarly-publishing-workflow`.
- Add `stage_assistant_candidates`.
- Add primary/secondary skill states.
- Treat route selection as proof that a skill was materially used in a real task.
- Physically delete any skill directory until its content has been inspected for
  scripts, references, examples, assets, or unique instructions.

## 4. Pack Decisions

### 4.1 `cloud-modalcom`

Current candidate:

```text
modal-labs
```

Target decision: keep `modal-labs` as the only direct route owner.

Direct user problem:

```text
Use Modal / modal.com / Modal Labs for Python cloud functions, serverless GPU
jobs, batch jobs, autoscaling containers, cloud execution, and Modal deployment.
```

Known failure to fix:

```text
Prompt: 用 Modal 部署 Python GPU 函数和云端作业
Current selected skill: integration-devops / vercel-deploy
Target selected skill: cloud-modalcom / modal-labs
```

Required routing boundary:

- Modal prompts in Chinese or English must route to `cloud-modalcom/modal-labs`
  even when the prompt contains generic deployment words.
- `vercel-deploy` must not own prompts that explicitly say Modal, modal.com, or
  "not Vercel".
- Frontend UI "modal dialog" prompts must remain blocked by `modal-labs`
  negative keywords.

Representative target prompts:

```text
用 Modal 部署 Python GPU 函数和云端作业
把 FastAPI 部署到 Modal 而不是 Vercel
用 modal.com 部署 Python GPU function
使用 Modal Labs 运行 serverless GPU batch job
```

### 4.2 `ml-torch-geometric`

Current candidates:

```text
torch-geometric
torch_geometric
```

Target decision: keep `torch-geometric` as the canonical direct route owner.

The `torch_geometric` entry is treated as a duplicate alias candidate, not a
separate expert role. During implementation, inspect both directories:

- If `torch_geometric` is an empty shell, thin duplicate, or low-quality alias,
  remove it from routing and physically delete it.
- If `torch_geometric` contains unique scripts, references, examples, or assets,
  migrate useful content into `torch-geometric`, then remove the duplicate
  routing surface.

Direct user problem:

```text
Build, train, debug, or explain graph neural networks with PyTorch Geometric /
PyG, including GCN, GAT, graph classification, node classification, link
prediction, graph datasets, and torch_geometric APIs.
```

Required routing boundary:

- PyTorch Geometric and PyG prompts route to `ml-torch-geometric/torch-geometric`.
- `torch_geometric` is allowed as a keyword/API spelling, not as a separate
  selected skill after consolidation.
- Generic PyTorch prompts without graph neural network or PyG intent should not
  route here by default.

Representative target prompts:

```text
用 PyTorch Geometric 构建 GCN 图神经网络
用 torch_geometric 写 GAT 节点分类模型
训练 PyG graph classification pipeline
```

### 4.3 `science-quantum`

Current candidates:

```text
qiskit
cirq
pennylane
qutip
```

Target decision: keep all four as direct route owners with narrow boundaries.

Direct ownership:

| Skill | Direct user problem |
| --- | --- |
| `qiskit` | IBM/Qiskit quantum circuits, quantum gates, transpilation, simulators, and the default general quantum-computing entry. |
| `cirq` | Google Cirq ecosystem, circuit construction, gates, moments, devices, and Cirq simulators. |
| `pennylane` | Quantum machine learning, variational quantum circuits, differentiable quantum programming, and hybrid quantum-classical models. |
| `qutip` | Open quantum systems, master equations, quantum dynamics, density matrices, and QuTiP simulations. |

Required routing boundary:

- General quantum circuit prompts route to `qiskit` unless another ecosystem is
  explicitly named.
- Cirq prompts route to `cirq`.
- Quantum machine learning, variational circuits, and differentiable quantum
  programming route to `pennylane`.
- Open quantum systems, master equations, and quantum dynamics route to `qutip`.
- None of these skills are helper experts or stage assistants.

Representative target prompts:

```text
用 Qiskit 构建量子电路并在 simulator 上运行
用 Cirq 写 quantum gate circuit
用 PennyLane 做 quantum machine learning 变分量子线路
用 QuTiP 模拟开放量子系统 master equation
```

## 5. Options Considered

### Option A: Focused Second Pass

Clean the three selected packs only.

Benefits:

- Directly addresses the known Modal miss.
- Removes one likely duplicate routing surface.
- Adds route authority where the quantum boundaries are already understandable.
- Keeps review and verification small enough to avoid accidental runtime churn.

Cost:

- Leaves 14 zero-route-authority packs for later passes.

This is the recommended option.

### Option B: Process All Remaining Zero-Authority Packs

Clean all 17 remaining packs in one pass.

Benefits:

- Eliminates the whole zero-authority class faster.

Cost:

- Higher chance of shallow judgments on niche science packs.
- More deletion decisions would be made without enough asset review.
- Larger regression matrix and higher merge risk.

### Option C: Runtime Consultation Cleanup First

Pause pack cleanup and remove or simplify the remaining consultation-policy
runtime surface.

Benefits:

- Directly addresses broader architecture language such as primary/stage buckets.

Cost:

- Touches runtime behavior rather than pack configuration.
- Riskier than this pack-level cleanup.
- Does not fix the confirmed `cloud-modalcom` prompt miss.

## 6. Proposed Design

Proceed with Option A.

Implementation should use a small, evidence-first route cleanup:

1. Add focused RED tests for the three selected packs.
2. Inspect `torch-geometric` and `torch_geometric` directories before deleting
   anything.
3. Update `config/pack-manifest.json` so retained skills have direct
   `route_authority_candidates` and empty `stage_assistant_candidates`.
4. Update `config/skill-keyword-index.json` and
   `config/skill-routing-rules.json` to encode the clarified boundaries.
5. Add negative routing protection where needed, especially around
   `vercel-deploy` versus `modal-labs` and generic PyTorch versus PyG.
6. Write the governance record.
7. Refresh `config/skills-lock.json`.
8. Run focused tests and routing gates before claiming completion.

## 7. Verification Requirements

Focused tests must prove at least:

- `cloud-modalcom` has `modal-labs` as its direct route owner.
- Chinese Modal deployment prompts route to `cloud-modalcom/modal-labs`.
- "Modal rather than Vercel" prompts do not route to `vercel-deploy`.
- `ml-torch-geometric` has one canonical direct owner after consolidation.
- PyTorch Geometric, PyG, and `torch_geometric` API prompts route to
  `torch-geometric`.
- Generic PyTorch prompts are not over-captured by `ml-torch-geometric`.
- `science-quantum` has four direct route owners and no stage assistants.
- Qiskit, Cirq, PennyLane, and QuTiP prompts select the intended skills.

Expected focused test file:

```text
tests/runtime_neutral/test_zero_route_authority_second_pass.py
```

Expected governance note:

```text
docs/governance/zero-route-authority-second-pass-2026-04-29.md
```

Broader verification should include existing pack/routing gates where available,
especially route smoke, offline skills, config parity, and version packaging
checks.

## 8. Success Criteria

This pass is complete only when:

- The three selected packs have explicit direct route ownership.
- No selected pack has `stage_assistant_candidates`.
- The confirmed Modal/Vercel miss is fixed by prompt-level tests.
- The PyTorch Geometric duplicate surface has one clear canonical owner, with
  any useful duplicate content migrated before deletion.
- Quantum ecosystem boundaries are represented by route tests.
- No helper, consultation, primary/secondary, or stage-assistant semantics are
  added.
- The governance note records before/after counts, retained owners, deleted or
  merged directories, and remaining zero-route-authority packs.

Remaining zero-route-authority packs are intentionally deferred unless the
implementation review discovers a tightly coupled issue that must be handled to
make this pass coherent.
