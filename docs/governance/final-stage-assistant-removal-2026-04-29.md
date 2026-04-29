# Final Stage Assistant Removal

Date: 2026-04-29

## Scope

This cleanup removes the last active `stage_assistant_candidates` semantics from pack routing.

The public six-stage Vibe runtime is unchanged. The skill usage model is simplified to:

```text
candidate skill -> selected skill -> used / unused
```

## Before And After

| pack | before route authority | before stage assistants | after route authority | after stage assistants |
| --- | ---: | ---: | ---: | ---: |
| `code-quality` | 9 | 1 | 10 | 0 |
| `data-ml` | 7 | 1 | 8 | 0 |

## Direct Owners Added

| skill | direct task boundary | not for |
| --- | --- | --- |
| `requesting-code-review` | Prepare and request a code review after implementation or before merge. | Actual review findings; review feedback repair. |
| `preprocessing-data-with-automated-pipelines` | Build repeatable ML data preprocessing pipelines for cleaning, encoding, transforming, and validating input data. | Full ML workflow planning; general model training; leakage auditing. |

## Boundary Probes

| prompt class | expected owner |
| --- | --- |
| review request preparation | `code-quality/requesting-code-review` |
| actual code review | `code-quality/code-reviewer` |
| received review feedback | `code-quality/receiving-code-review` |
| preprocessing pipeline | `data-ml/preprocessing-data-with-automated-pipelines` |
| broad ML workflow | `data-ml/ml-pipeline-workflow` |
| data leakage audit | `data-ml/ml-data-leakage-guard` |

## Deletion Decision

`preprocessing-data-with-automated-pipelines` is not physically deleted in this cleanup. The directory contains assets, references, and scripts, and the retained direct task boundary is distinct.

## Verification

Required focused tests:

```powershell
python -m pytest tests/runtime_neutral/test_final_stage_assistant_removal.py -q
python -m pytest tests/runtime_neutral/test_code_quality_pack_consolidation_audit.py tests/runtime_neutral/test_ml_skills_pruning_audit.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py::RouterBridgeTests::test_preprocessing_pipeline_routes_as_direct_data_ml_owner -q
```

Required gates:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
```
