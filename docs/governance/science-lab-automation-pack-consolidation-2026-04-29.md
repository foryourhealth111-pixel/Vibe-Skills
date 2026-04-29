# Science Lab Automation Pack Consolidation

Date: 2026-04-29

## Decision

`science-lab-automation` is consolidated as a wet-lab automation specialist routing pack.

This consolidation preserves the existing six-stage Vibe runtime. It does not change runtime phases, stage ownership, dispatch mechanics, or closure rules.

The pack also preserves the binary usage model:

```text
skill_routing.selected -> skill_usage.used / unused
```

No additional routing semantics are introduced. In particular, this decision does not add `primary` / `secondary`, `consult`, `advisory`, or `stage-assistant execution` meanings.

## Before / After

| Surface | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 7 | 6 |
| `route_authority_candidates` | 0 | 6 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` is only a compatibility and documentation mirror. The actual simplification is implemented by reducing `skill_candidates` from 7 to 6.

## Retained Route Authorities

| Skill id | Route authority boundary |
| --- | --- |
| `opentrons-integration` | Opentrons OT-2/Flex Protocol API, deck setup, pipetting scripts, and Opentrons modules |
| `pylabrobot` | Hamilton/Tecan/Opentrons backends, plate readers, pumps, resources, simulation, and other multi-vendor lab automation |
| `protocolsio-integration` | protocols.io search/create/update/publish/workspace/file/collaboration workflows |
| `benchling-integration` | Benchling registry/inventory/ELN/workflows/apps/data warehouse automation |
| `labarchive-integration` | LabArchives notebooks/entries/attachments/backups/API workflows |
| `ginkgo-cloud-lab` | Ginkgo Cloud Lab, `cloud.ginkgo.bio` ordering, cell-free protein expression, pricing, and input preparation |

## Moved Out

`latchbio-integration` is moved out of the `science-lab-automation` routing pack.

Reason: LatchBio is a computational bioinformatics workflow platform, centered on the Latch SDK, `LatchFile` / `LatchDir`, Nextflow, Snakemake, and serverless pipelines. It is not a wet-lab automation route owner.

The moved-out skill remains on disk. This consolidation performs no physical directory deletion.

## Protected Route Boundaries

Positive examples that remain inside `science-lab-automation`:

- Opentrons OT-2 protocol automation.
- Opentrons Flex protocol automation.
- PyLabRobot Hamilton/Tecan automation.
- protocols.io search and publish workflows.
- Benchling registry, inventory, and DNA sequence workflows.
- Benchling ELN and Data Warehouse automation.
- LabArchives backup and upload workflows.
- Ginkgo Cloud Lab ordering and cell-free expression workflows.

Negative examples that must not route to `science-lab-automation`:

- LatchBio computational bioinformatics workflows.
- Generic wet-lab protocol Markdown authoring without a supported automation platform.
- PubMed wet-lab methods literature search or summarization.

## Verification

The consolidation is expected to be covered by these checks:

```powershell
python -m pytest tests/runtime_neutral/test_science_lab_automation_pack_consolidation.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
