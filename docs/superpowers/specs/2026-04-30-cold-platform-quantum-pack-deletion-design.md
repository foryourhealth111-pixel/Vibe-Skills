# Cold Platform And Quantum Pack Deletion Design

Date: 2026-04-30

## 1. Decision

Remove `cloud-modalcom` and `science-quantum` from the live Vibe-Skills routing surface.

This is a hard removal pass, not a trigger-narrowing pass. The goal is to reduce cold, low-frequency, or high-false-positive route surfaces instead of continuing to maintain narrow boundaries for capabilities that are not central to the current Vibe-Skills package.

The public Vibe runtime remains unchanged:

```text
skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
```

The simplified usage model remains unchanged:

```text
candidate skill -> selected skill -> used / unused
```

No advisory experts, consultation state, helper experts, primary/secondary skill hierarchy, or stage assistants will be added.

## 2. Current State

### 2.1 `cloud-modalcom`

`config/pack-manifest.json` currently defines `cloud-modalcom` as a single-owner pack:

| Surface | Current value |
| --- | --- |
| Pack | `cloud-modalcom` |
| `skill_candidates` | `modal-labs` |
| `route_authority_candidates` | `modal-labs` |
| `stage_assistant_candidates` | empty |
| Defaults | planning/coding/research -> `modal-labs` |

Bundled Modal-related skill directories found in this checkout:

```text
bundled/skills/modal-labs
bundled/skills/modal
```

`modal-labs` is the live route owner. `modal` is not the pack candidate, but it remains in the bundled skill tree and lock-related surfaces as a historical Modal asset directory.

### 2.2 `science-quantum`

`config/pack-manifest.json` currently defines `science-quantum` as a four-owner pack:

| Surface | Current value |
| --- | --- |
| Pack | `science-quantum` |
| `skill_candidates` | `qiskit`, `cirq`, `pennylane`, `qutip` |
| `route_authority_candidates` | `qiskit`, `cirq`, `pennylane`, `qutip` |
| `stage_assistant_candidates` | empty |
| Defaults | planning/coding/research -> `qiskit` |

Bundled skill directories:

```text
bundled/skills/qiskit
bundled/skills/cirq
bundled/skills/pennylane
bundled/skills/qutip
```

These directories contain self-contained `SKILL.md` files and references. They are not being removed because they are low-quality; they are being removed because the pack is cold, specialized, and creates route noise relative to the simplified package direction.

## 3. Problems

### 3.1 Modal Is A Cold Vendor Platform Surface

`cloud-modalcom` is specific to Modal.com / Modal Labs. It can be useful in a narrow deployment scenario, but it is not a core Vibe-Skills route owner.

The current trigger set includes broad phrases such as:

```text
serverless gpu
gpu function
python gpu function
batch job
gpu container
cloud gpu
```

That makes ordinary cloud GPU, container, or batch-job prompts vulnerable to Modal capture even when the user did not ask for Modal.

### 3.2 Duplicate Modal Surfaces Increase Maintenance Cost

The checkout contains both `modal-labs` and `modal` bundled skill directories. Keeping a non-routed Modal directory after deleting the live Modal pack would preserve a confusing historical artifact and keep unnecessary lock/index churn.

The deletion target therefore includes both directories.

### 3.3 Quantum Computing Is Cold And Easy To Misroute

`science-quantum` currently includes broad pack triggers:

```text
quantum
量子
```

Those terms can overlap with quantum chemistry, pKa, DFT, computational chemistry, molecular simulation, and chemistry/drug prompts that should not route to `qiskit` by default.

Example false-positive class:

```text
quantum chemistry pKa DFT, not quantum circuit
```

This should not select `science-quantum / qiskit`.

### 3.4 Maintaining Quantum Boundaries Is Not Worth The Current Package Cost

The quantum skills are not thin wrappers, but preserving them would require ongoing maintenance for:

- Qiskit versus Cirq hardware/ecosystem boundaries
- PennyLane quantum ML versus generic ML and quantum chemistry boundaries
- QuTiP open-quantum-system boundaries
- quantum chemistry versus chemistry/drug/Rowan/RDKit boundaries

For the current cleanup direction, removal is cleaner than another explicit-trigger-only pass.

## 4. Goals

- Remove `cloud-modalcom` from live routing.
- Remove `science-quantum` from live routing.
- Physically delete:

```text
bundled/skills/modal-labs
bundled/skills/modal
bundled/skills/qiskit
bundled/skills/cirq
bundled/skills/pennylane
bundled/skills/qutip
```

- Remove deleted skills from:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
```

- Remove or rewrite route tests and probes that expect Modal or quantum owners.
- Add negative route regressions proving broad cloud GPU and quantum chemistry prompts do not select deleted packs.
- Keep `zero_route_authority = 0`.
- Keep every pack's `stage_assistant_candidates` empty.

## 5. Non-Goals

This pass will not:

- Replace Modal with another cloud deployment skill.
- Move Modal into `integration-devops`.
- Replace quantum skills with a new generic `quantum-computing` owner.
- Move Qiskit/PennyLane quantum chemistry content into `science-chem-drug`.
- Change Vibe's six-stage runtime.
- Add helper experts, stage assistants, primary/secondary route state, advisory state, or consultation state.
- Claim that any skill was materially used in a real task.

## 6. Routing Migration

### 6.1 Modal Prompt Classes

| Prompt class | Old behavior | Target behavior |
| --- | --- | --- |
| Explicit Modal deployment | `cloud-modalcom / modal-labs` | no Modal route; route to a general deployment/devops owner if one clearly applies, otherwise confirmation/fallback |
| Generic cloud GPU or batch job | may select `cloud-modalcom / modal-labs` | must not select `cloud-modalcom` or `modal-labs` |
| Frontend modal dialog | must not select `cloud-modalcom` | remains not Modal |

Representative negative regressions:

```text
Run a Python batch job on a cloud GPU without specifying Modal.
Deploy a serverless GPU function, but use any cloud container platform except Modal.
Build a React modal dialog.
```

### 6.2 Quantum Prompt Classes

| Prompt class | Old behavior | Target behavior |
| --- | --- | --- |
| Qiskit/Cirq/PennyLane/QuTiP explicit prompts | `science-quantum / <tool>` | no quantum route; route should fall back or require confirmation unless another non-deleted owner clearly applies |
| Generic quantum circuit prompts | usually `science-quantum / qiskit` | no `science-quantum` route |
| Quantum chemistry / pKa / DFT prompts | can select `science-quantum / qiskit` | must not select `science-quantum`; should prefer chemistry/drug/Rowan-like routes only when their explicit boundaries match |

Representative negative regressions:

```text
Quantum chemistry pKa and DFT analysis, not a quantum circuit.
Use Qiskit to create a Bell-state quantum circuit.
Use QuTiP to simulate an open quantum system master equation.
```

The latter two should prove the deleted pack is absent, not that a replacement route exists.

## 7. Files To Change

Expected implementation files:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
config/skills-lock.json
tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py
tests/runtime_neutral/test_zero_route_authority_second_pass.py
scripts/verify/vibe-pack-regression-matrix.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
scripts/verify/probe-scientific-packs.ps1
scripts/verify/vibe-pack-routing-smoke.ps1
docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md
```

Expected deleted directories:

```text
bundled/skills/modal-labs
bundled/skills/modal
bundled/skills/qiskit
bundled/skills/cirq
bundled/skills/pennylane
bundled/skills/qutip
```

If additional live references are found during implementation, remove or rewrite them in the same pass if they are directly tied to the deleted packs.

## 8. Verification Design

Add a focused runtime-neutral test proving:

- no `cloud-modalcom` pack remains in `config/pack-manifest.json`
- no `science-quantum` pack remains in `config/pack-manifest.json`
- none of the six deleted skill directories remains under `bundled/skills`
- no deleted skill appears in `config/skill-keyword-index.json`
- no deleted skill appears in `config/skill-routing-rules.json`
- no deleted skill appears in `config/skills-lock.json` after lock refresh
- broad cloud GPU prompts do not select `cloud-modalcom` or Modal skills
- quantum chemistry prompts do not select `science-quantum` or quantum-computing skills
- explicit Qiskit/Cirq/PennyLane/QuTiP prompts do not resurrect the deleted pack
- all remaining packs have non-empty `route_authority_candidates`
- all remaining packs have empty `stage_assistant_candidates`

Update existing tests that currently expect the old packs:

- zero-route-authority second-pass tests should stop expecting `cloud-modalcom` and `science-quantum`
- route matrix/probe scripts should remove positive Modal and quantum expectations and add negative absence checks
- smoke gates should assert absence rather than selection

Final verification should include:

```powershell
python -m pytest tests/runtime_neutral/test_cold_platform_quantum_pack_deletion.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_second_pass.py tests/runtime_neutral/test_zero_route_authority_third_pass.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

## 9. Governance Record

The implementation should create:

```text
docs/governance/cold-platform-quantum-pack-deletion-2026-04-30.md
```

The note should record:

- deleted packs
- deleted skill directories
- reason for deleting Modal as a cold vendor platform surface
- reason for deleting quantum as a cold, high-boundary-cost science surface
- route behavior after deletion
- verification commands and outcomes
- evidence boundary: route/config/docs/tests only, not real task material skill use

## 10. Risks

Some users may explicitly ask for Qiskit, Cirq, PennyLane, QuTiP, or Modal. After this pass those prompts will not have a bundled specialist. That is acceptable for this cleanup because the user has chosen package slimming over retaining cold longtail capability.

Some existing tests and replay fixtures intentionally expect Modal or quantum routes. These expectations should be rewritten as absence checks, not silently deleted without replacement.

Removing `modal` deletes more bundled reference content than removing only `modal-labs`. This is intentional: retaining non-routed Modal assets would keep a confusing historical surface after the pack is removed.

## 11. Success Criteria

- `cloud-modalcom` is absent from `config/pack-manifest.json`.
- `science-quantum` is absent from `config/pack-manifest.json`.
- `modal-labs`, `modal`, `qiskit`, `cirq`, `pennylane`, and `qutip` directories are gone.
- Deleted skills are absent from keyword index, routing rules, and lock.
- No route probe selects the deleted packs or skills.
- Broad cloud GPU prompts no longer route to Modal.
- Quantum chemistry prompts no longer route to `science-quantum / qiskit`.
- `zero_route_authority = 0`.
- all remaining `stage_assistant_candidates` are empty.
- Required focused and broader verification gates pass.
