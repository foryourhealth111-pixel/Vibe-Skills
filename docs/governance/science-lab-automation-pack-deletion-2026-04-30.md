# Science Lab Automation Pack Deletion

Date: 2026-04-30

## Decision

`science-lab-automation` is removed from the active Vibe-Skills routing surface.

This is a cold-pack hard removal. It is not a boundary narrowing pass and does not create a replacement explicit-only, helper, advisory, consultation, primary/secondary, or stage-assistant route.

The public six-stage Vibe runtime remains unchanged:

```text
skeleton_check -> deep_interview -> requirement_doc -> xl_plan -> plan_execute -> phase_cleanup
```

The skill usage model remains:

```text
candidate skill -> selected skill -> used / unused
```

## Before / After

| Surface | Before | After |
| --- | ---: | ---: |
| `science-lab-automation.skill_candidates` | 6 | 0, pack removed |
| `science-lab-automation.route_authority_candidates` | 6 | 0, pack removed |
| `science-lab-automation.stage_assistant_candidates` | 0 | 0, pack removed |
| deleted bundled skill directories | 0 | 6 |

## Deleted Skill Directories

| Skill id | Reason |
| --- | --- |
| `opentrons-integration` | Cold Opentrons OT-2/Flex product/API surface. |
| `pylabrobot` | Cold multi-vendor lab robot framework surface. |
| `protocolsio-integration` | Product-specific protocols.io API surface rather than a core expert role. |
| `benchling-integration` | Benchling SaaS/ELN/registry integration surface rather than core routing. |
| `labarchive-integration` | LabArchives ELN integration surface rather than core routing. |
| `ginkgo-cloud-lab` | Cold cloud-lab ordering/pricing service surface. |

## Out Of Scope

`latchbio-integration` is not deleted in this pass. It was already outside the `science-lab-automation` pack and represents computational bioinformatics workflow deployment, not wet-lab automation.

## Route Migration

The following prompts no longer select `science-lab-automation`:

| Prompt class | Old owner | Target behavior |
| --- | --- | --- |
| Opentrons OT-2/Flex protocol code | `science-lab-automation / opentrons-integration` | deleted pack not selected |
| Hamilton/Tecan/PyLabRobot automation | `science-lab-automation / pylabrobot` | deleted pack not selected |
| protocols.io API workflows | `science-lab-automation / protocolsio-integration` | deleted pack not selected |
| Benchling registry, inventory, ELN, workflow API | `science-lab-automation / benchling-integration` | deleted pack not selected |
| LabArchives notebook, entry, attachment backup | `science-lab-automation / labarchive-integration` | deleted pack not selected |
| Ginkgo Cloud Lab order preparation | `science-lab-automation / ginkgo-cloud-lab` | deleted pack not selected |

No replacement owner is required for these cold product-specific prompts.

## Verification

Focused checks:

```powershell
python -m pytest tests/runtime_neutral/test_science_lab_automation_pack_consolidation.py -q
python -m pytest tests/runtime_neutral/test_zero_route_authority_third_pass.py tests/runtime_neutral/test_final_stage_assistant_removal.py -q
```

Routing and packaging gates:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

## Boundary

This evidence proves repository routing and bundled skill cleanup. It does not prove real task execution or material skill use in a live Vibe run.
