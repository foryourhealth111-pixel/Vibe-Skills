# Science Medical Imaging Pack Consolidation Design

Date: 2026-04-30

## 1. Goal

This pass hardens `science-medical-imaging` routing boundaries without changing the public Vibe six-stage runtime.

The routing model remains:

```text
candidate skill -> selected skill -> used / unused
```

This pass does not introduce advisory experts, consultation state, primary/secondary skill hierarchy, or stage assistants.

The main goal is to keep the existing 5 direct route owners while making their trigger boundaries precise enough that generic image, literature, clinical-trial, report-writing, bioinformatics, chemistry, and Data Commons prompts do not get pulled into the medical-imaging pack.

## 2. Current State

Current `config/pack-manifest.json` state for `science-medical-imaging`:

| Field | Current Value |
|---|---:|
| `skill_candidates` | 5 |
| `route_authority_candidates` | 5 |
| `stage_assistant_candidates` | 0 |
| `defaults_by_task` | 3 |

Current direct route owners:

```text
pydicom
imaging-data-commons
histolab
omero-integration
pathml
```

Current defaults:

```json
{
  "planning": "pathml",
  "coding": "pydicom",
  "research": "imaging-data-commons"
}
```

This pack already has a clean direct-owner structure. The remaining risk is boundary thinness, not missing route authority.

## 3. Current Problems

### 3.1 Negative Boundaries Are Too Thin

Each current owner has only about two negative keywords:

| Skill | Current Problem |
|---|---|
| `pydicom` | Strong DICOM owner, but weakly protected against generic image processing, report/PDF work, and non-imaging biomedical tasks. |
| `imaging-data-commons` | Correct for NCI IDC/TCIA/DICOMWeb, but risks overlap with generic `Data Commons`, public datasets, PubMed, and clinical-trial prompts. |
| `histolab` | Correct for WSI tile extraction and tissue detection, but needs clearer separation from full PathML workflows and generic image tiling. |
| `omero-integration` | Correct for OMERO server, microscopy image management, ROIs, and annotations, but needs stronger guards against generic microscopy literature and bioinformatics prompts. |
| `pathml` | Correct for computational pathology workflows, but can overlap with histolab, generic machine learning, generic image segmentation, and bio-science tasks. |

### 3.2 Imaging Data Commons vs Data Commons Is Ambiguous

`imaging-data-commons` should own NCI Imaging Data Commons, IDC, TCIA cancer imaging cohorts, DICOMWeb, and cancer imaging dataset retrieval.

It must not own generic Data Commons statistical graph prompts such as population indicators, statistical variables, DCIDs, or broad public statistical data. Those belong to `finance-edgar-macro/datacommons-client` only when Data Commons context is explicit.

### 3.3 Digital Pathology Split Needs To Be Stable

The pack has two related pathology owners:

| Prompt Type | Owner |
|---|---|
| Basic WSI tile extraction, tissue detection, H&E tile preprocessing | `histolab` |
| Full computational pathology workflow, PathML, nucleus segmentation, spatial pathology, multiplex pathology | `pathml` |

This split should be protected by focused route tests.

### 3.4 Neighboring Pack Boundaries Need Protection

`science-medical-imaging` should not own:

- PubMed, PMID, citation, literature review, systematic review, or evidence table prompts.
- ClinicalTrials.gov, NCT, clinical trial registry, FDA label, CPIC, or clinical decision-support prompts.
- Scientific report, paper writing, LaTeX manuscript, submission PDF, or generic PDF/document tasks.
- Generic image processing, screenshots, OCR, media/video, or frontend visual tasks without medical-imaging signals.
- Bioinformatics prompts such as scRNA-seq, RNA-seq, BAM/VCF, protein embeddings, flow cytometry, gene databases, KEGG, or STRING.
- Chemistry/drug prompts such as RDKit, SMILES, molecule docking, ChEMBL, DrugBank, or PubChem.
- Generic ML modeling that does not mention DICOM, radiology, WSI, pathology imaging, IDC, OMERO, or PathML.

## 4. Target Ownership Contract

Keep 5 direct route owners:

| Problem ID | User Task Boundary | Direct Owner |
|---|---|---|
| `dicom_file_workflow` | DICOM files, pydicom, DICOM tags, metadata extraction, anonymization, CT/MRI/PET/X-ray medical pixel data, PACS-oriented processing | `pydicom` |
| `cancer_imaging_data_commons` | NCI Imaging Data Commons, IDC, TCIA cancer imaging cohort, DICOMWeb, public radiology/pathology imaging cohorts | `imaging-data-commons` |
| `wsi_tile_preprocessing` | Histolab, whole-slide image tile extraction, tissue detection, H&E tile preprocessing, basic WSI dataset preparation | `histolab` |
| `omero_microscopy_server` | OMERO, microscopy image server, image datasets/projects, ROI annotations, high-content screening image management | `omero-integration` |
| `computational_pathology_workflow` | PathML, digital pathology workflow, WSI analysis pipeline, nucleus segmentation, tissue/cell graphs, spatial pathology, multiplex pathology | `pathml` |

## 5. Non-Goals

This pass will not:

- Change Vibe's six-stage runtime.
- Add `stage_assistant_candidates`.
- Add advisory, consultation, helper, primary, or secondary skill states.
- Physically delete any `bundled/skills/*` directory.
- Move `histolab` under `pathml` or make it a hidden helper.
- Claim that a real Vibe task materially used these skills.
- Install or deploy the changed repository into Codex.

## 6. Routing And Documentation Changes

The implementation plan should modify only the surfaces needed to prove the boundary:

```text
config/skill-keyword-index.json
config/skill-routing-rules.json
bundled/skills/pydicom/SKILL.md
bundled/skills/imaging-data-commons/SKILL.md
bundled/skills/histolab/SKILL.md
bundled/skills/omero-integration/SKILL.md
bundled/skills/pathml/SKILL.md
scripts/verify/vibe-pack-regression-matrix.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
scripts/verify/probe-scientific-packs.ps1
tests/runtime_neutral/test_science_medical_imaging_pack_consolidation.py
docs/governance/science-medical-imaging-pack-consolidation-2026-04-30.md
config/skills-lock.json
```

`config/pack-manifest.json` should remain structurally unchanged unless focused tests prove a manifest-level trigger term is too broad.

Expected keyword/rule direction:

- Strengthen positive keywords with owner-specific terms such as `dicom tag`, `dicom anonymization`, `nci imaging data commons`, `tcia`, `dicomweb`, `whole slide image`, `wsi tile extraction`, `omero server`, `roi annotation`, `pathml`, `computational pathology`, and `nucleus segmentation`.
- Add negative keywords for neighboring packs: PubMed/literature, ClinicalTrials/NCT, LaTeX/PDF/manuscript, generic image processing/OCR/screenshots, bioinformatics, chemistry/drug discovery, generic Data Commons, and generic ML.
- Add a short routing boundary note to each retained `SKILL.md` only where the current description is ambiguous.

## 7. Regression Test Design

Create a focused test:

```text
tests/runtime_neutral/test_science_medical_imaging_pack_consolidation.py
```

Required assertions:

- Manifest keeps the exact 5 direct owners and `stage_assistant_candidates == []`.
- Positive prompts route to all 5 owners.
- `pydicom` wins explicit DICOM tags, anonymization, CT/MRI/PET/X-ray DICOM pixel workflows.
- `imaging-data-commons` wins NCI IDC, TCIA, DICOMWeb, and cancer imaging cohort prompts.
- `histolab` wins basic WSI tile extraction and tissue detection prompts.
- `omero-integration` wins OMERO server, ROI, annotation, microscopy image management prompts.
- `pathml` wins full computational pathology, PathML, WSI pipeline, nucleus segmentation, and spatial pathology prompts.
- Generic Data Commons statistical graph prompts do not select `imaging-data-commons`.
- PubMed, ClinicalTrials.gov, LaTeX submission PDF, scientific report PDF, and generic image processing prompts do not select `science-medical-imaging`.
- Histolab and PathML split is stable: simple tile extraction does not select `pathml`; full PathML workflow does not select `histolab`.

Extend existing script checks with the same boundary cases:

```text
scripts/verify/vibe-pack-regression-matrix.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
scripts/verify/probe-scientific-packs.ps1
```

## 8. Verification Plan

Focused verification should run first:

```powershell
python -m pytest tests/runtime_neutral/test_science_medical_imaging_pack_consolidation.py -q
```

Then broader gates:

```powershell
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
git diff --check
```

If bundled skill docs change, regenerate and verify the lock:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

## 9. Governance Note

Create:

```text
docs/governance/science-medical-imaging-pack-consolidation-2026-04-30.md
```

It should record:

- 5 retained direct route owners.
- `stage_assistant_candidates = []`.
- No physical directory deletion.
- No advisory/consultation state.
- No primary/secondary skill hierarchy.
- The direct owner table and boundary fixes.
- Exact verification command results after implementation.
- Evidence boundary: this proves routing/config/bundled cleanup only, not real task material skill use.

## 10. Risks And Handling

| Risk | Handling |
|---|---|
| Over-penalizing `imaging-data-commons` so it no longer wins IDC prompts | Add positive IDC/TCIA/DICOMWeb probes before adding broad Data Commons negatives. |
| `histolab` and `pathml` conflict on WSI prompts | Use prompt-level split: preprocessing/tile extraction -> `histolab`; full pathology workflow/PathML/spatial or nucleus analysis -> `pathml`. |
| Generic microscopy prompts drift into OMERO | Require OMERO server/API/ROI/annotation/image-server signals for `omero-integration`. |
| DICOM term appears in neighboring biomedical prompts | Keep `pydicom` strong only for file/tag/pixel/anonymization/medical scan workflows, not generic clinical literature or bioinformatics. |
| Verification scripts disagree with Python runtime | Add the same positive and blocked prompts to both Python and PowerShell checks. |

## 11. Acceptance Criteria

The cleanup is acceptable when:

- `science-medical-imaging` still has exactly 5 direct route owners.
- `stage_assistant_candidates` remains empty.
- No medical-imaging skill directory is deleted.
- All 5 direct owners have positive route coverage.
- Neighboring pack false positives are blocked by focused tests and script probes.
- `skills-lock.json` is refreshed if any bundled `SKILL.md` file changes.
- Governance evidence is written with exact pass counts.
- The final report does not claim real task material skill use.
