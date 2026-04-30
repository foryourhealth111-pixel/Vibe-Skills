# Science Medical Imaging Pack Consolidation

Date: 2026-04-30

## Summary

`science-medical-imaging` is consolidated as a direct medical-imaging routing pack.

The Vibe six-stage runtime is unchanged. The routing state remains intentionally simple:

```text
candidate skill -> selected skill -> used / unused
```

This pass does not introduce advisory experts, consultation state, primary/secondary skill hierarchy, or stage assistants.

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 5 | 5 |
| `route_authority_candidates` | 5 | 5 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` mirrors the five direct route owners for compatibility and documentation. It is not a separate execution state.

## Direct Route Owners

| User problem | Skill |
| --- | --- |
| DICOM file workflows, pydicom, DICOM tags, metadata extraction, anonymization, CT/MRI/PET/X-ray medical pixel data, and PACS-oriented processing | `pydicom` |
| NCI Imaging Data Commons, IDC, TCIA cancer imaging cohorts, DICOMWeb, and public radiology/pathology imaging cohort retrieval | `imaging-data-commons` |
| Histolab, whole-slide image tile extraction, tissue detection, H&E tile preprocessing, and basic WSI dataset preparation | `histolab` |
| OMERO server/API work, microscopy image-server projects/datasets, ROI annotations, and high-content screening image management | `omero-integration` |
| PathML, computational pathology WSI pipelines, nucleus segmentation, tissue/cell graphs, spatial pathology, and multiplex pathology workflows | `pathml` |

## Boundary Decisions

| Boundary | Decision |
| --- | --- |
| DICOM / pydicom | `pydicom` owns concrete DICOM file, tag, metadata, anonymization, pixel-array, and medical-scan workflows. It does not own generic clinical literature, report writing, OCR, PNG/JPEG, or unrelated biomedical analysis. |
| Imaging Data Commons / generic Data Commons | `imaging-data-commons` owns NCI IDC, TCIA, DICOMWeb, and cancer imaging cohorts. Generic Data Commons statistical graph prompts with population indicators, statistical variables, or DCIDs do not route here. |
| Histolab / PathML | `histolab` owns basic WSI tiling, tissue detection, and H&E tile preprocessing. `pathml` owns full computational pathology workflows, PathML pipelines, nucleus segmentation, spatial pathology, multiplex pathology, and tissue/cell graph analysis. |
| OMERO | `omero-integration` requires OMERO server/API, microscopy image-server, project/dataset, ROI, annotation, or high-content screening management signals. Generic microscopy literature or bioinformatics prompts do not route here. |

## Protected Negative Boundaries

`science-medical-imaging` is explicitly protected against false positives from:

- PubMed, PMID, citation, literature review, systematic review, and evidence-table prompts.
- ClinicalTrials.gov, NCT identifiers, trial endpoints, and eligibility prompts.
- LaTeX manuscript, submission PDF, scientific report, and generic document/PDF work.
- Generic image processing, screenshots, OCR, media, PNG/JPEG, and frontend visual tasks without medical-imaging signals.
- Bioinformatics prompts such as scRNA-seq, RNA-seq, BAM/VCF, protein embeddings, flow cytometry, KEGG, STRING, and gene database work.
- Chemistry and drug-discovery prompts such as RDKit, SMILES, docking, ChEMBL, DrugBank, PubChem, and molecular fingerprints.
- Generic machine-learning prompts that do not mention DICOM, radiology, WSI, pathology imaging, IDC, OMERO, or PathML.

## No Physical Deletion

No `bundled/skills/*` directory is deleted in this pass. The five medical-imaging skills remain on disk because each owns a distinct user problem and has route documentation worth preserving.

## Verification

Final verification was run after the route config, bundled skill docs, verification scripts, governance note, and `skills-lock.json` were updated.

```powershell
python -m pytest tests/runtime_neutral/test_science_medical_imaging_pack_consolidation.py -q
# 9 passed in 3.27s

.\scripts\verify\probe-scientific-packs.ps1
# groups=19
# cases=99
# pack_match_false=0
# skill_match_false=0
# science-medical-imaging: case_count=8, pack_match_ratio=1.0, skill_match_text=100%, confirm_required_ratio=0.0, avg_confidence=0.6349

.\scripts\verify\vibe-skill-index-routing-audit.ps1
# Total assertions: 473
# Passed: 473
# Failed: 0

.\scripts\verify\vibe-pack-regression-matrix.ps1
# Total assertions: 415
# Passed: 415
# Failed: 0

.\scripts\verify\vibe-pack-routing-smoke.ps1
# Total assertions: 958
# Passed: 958
# Failed: 0

.\scripts\verify\vibe-offline-skills-gate.ps1
# present_skills=296
# lock_skills=296
# [PASS] offline skill closure gate passed.

git diff --check
# no output
```

## Evidence Boundary

This governance note proves routing, config, bundled skill documentation, lockfile, and regression coverage cleanup only.

It does not prove that a real user task materially used any of these skills. Material use still requires task artifacts such as execution logs, produced files, model/report outputs, or other concrete deliverables from a real routed run.
