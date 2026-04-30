# Cold Platform And Quantum Pack Deletion

Date: 2026-04-30

## Decision

`cloud-modalcom` and `science-quantum` were removed from live Vibe-Skills routing.

This was a hard removal pass, not a trigger-narrowing pass. The goal was to reduce cold, specialized, high-false-positive route surfaces while keeping the public six-stage Vibe runtime unchanged:

```text
skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
```

The simplified skill-use model remains:

```text
candidate skill -> selected skill -> used / unused
```

No advisory experts, consultation state, helper experts, primary/secondary skill hierarchy, or stage assistants were added.

## Deleted Packs

| Pack | Removed route owners | Reason |
| --- | --- | --- |
| `cloud-modalcom` | `modal-labs` | Cold vendor-specific Modal.com surface; broad GPU/batch keywords created false-positive risk for generic cloud execution prompts. |
| `science-quantum` | `qiskit`, `cirq`, `pennylane`, `qutip` | Cold quantum-computing surface with high boundary-maintenance cost and false-positive risk around quantum chemistry, pKa, DFT, and molecular simulation prompts. |

## Deleted Skill Directories

- `bundled/skills/modal-labs`
- `bundled/skills/modal`
- `bundled/skills/qiskit`
- `bundled/skills/cirq`
- `bundled/skills/pennylane`
- `bundled/skills/qutip`

## Routing Contract After Deletion

| Prompt class | New behavior |
| --- | --- |
| Explicit Modal deployment | Does not select `cloud-modalcom` or Modal skills. It may route to an existing general owner only when that owner clearly matches, otherwise confirmation/fallback is acceptable. |
| Generic cloud GPU or batch job | Does not select `cloud-modalcom`, `modal`, or `modal-labs`. |
| Frontend modal dialog | Remains unrelated to Modal.com routing. |
| Explicit Qiskit/Cirq/PennyLane/QuTiP prompt | Does not select `science-quantum` or the deleted quantum skills. |
| Quantum chemistry / pKa / DFT prompt | Does not select `science-quantum` or `qiskit`; Rowan-specific quantum chemistry still routes to `science-rowan-chemistry / rowan`. |

## Verification

Commands run:

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

Observed outcomes:

| Verification | Outcome |
| --- | --- |
| Focused cold platform/quantum deletion test | 8 passed |
| Zero route authority second/third pass tests | 10 passed |
| Scientific pack probe | completed; `deleted-science-quantum` group had 3 cases, 100% pack match, 100% skill match |
| Skill-index routing audit | 533 assertions passed, 0 failed |
| Pack regression matrix | 495 assertions passed, 0 failed |
| Pack routing smoke | 940 assertions passed, 0 failed |
| Skills lock generation | generated `config/skills-lock.json` with 290 skills |
| Offline skills gate | passed; `present_skills=290`, `lock_skills=290` |
| Config parity gate | passed; 45/45 config pairs matched |
| Diff whitespace check | passed |

## Evidence Boundary

This change proves route/config/docs/tests cleanup only. It does not prove that any skill was materially used in a real task.

Material skill-use evidence still requires task artifacts such as `specialist-execution.json`, `phase-execute.json`, source code, generated outputs, metrics, figures, paper sources, or final PDFs from an actual governed run.
