# Science Clinical Regulatory Pack Consolidation

Date: 2026-04-29

## Summary

`science-clinical-regulatory` is consolidated as a clinical-data, clinical-documentation, treatment-planning, clinical decision support, and medical-device QMS routing pack.

The six-stage Vibe runtime is unchanged, and skill usage remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

No advisory, consult, primary/secondary, or stage-assistant execution model is introduced.

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 7 | 7 |
| `route_authority_candidates` | 0 | 7 |
| `stage_assistant_candidates` | 0 | 0 |
| `task_allow` | planning, coding, research | planning, coding, research, review |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` mirrors `skill_candidates` for compatibility and documentation. It is not a second execution model.

## Kept Route Owners

| User problem | Skill |
| --- | --- |
| ClinicalTrials.gov / NCT lookup, trial phase, eligibility, endpoints, and study status | `clinicaltrials-database` |
| openFDA, FDA drug labels, adverse events, recalls, 510(k), PMA, and regulatory safety data | `fda-database` |
| CPIC, PharmGKB/ClinPGx, PGx, gene-drug evidence, allele function, and genotype-guided dosing lookup | `clinpgx-database` |
| Clinical report writing and review: CARE case reports, CSR, SAE, SOAP notes, discharge summaries, HIPAA/de-identification checks | `clinical-reports` |
| Individual treatment plans, care plans, SMART goals, medication plans, and follow-up plans | `treatment-plans` |
| ISO 13485 medical-device QMS, quality manual, CAPA, gap analysis, and certification documentation | `iso-13485-certification` |
| Clinical decision support documents, GRADE evidence, treatment algorithms, cohort analysis, and biomarker stratification | `clinical-decision-support` |

## No Moved-Out Skills

No skill is moved out of this pack in this pass. Each retained skill owns a distinct user-facing problem and has scripts, references, or templates that should not be deleted without a separate asset review.

## No Physical Deletion

No bundled skill directory is physically deleted. A later pruning pass must separately prove that a directory has no distinct route, no useful migrated assets, and no live config/test/lockfile dependency before deletion.

## Protected Boundaries

| Prompt | Expected route |
| --- | --- |
| `在 ClinicalTrials.gov 按 NCT 编号 NCT01234567 查询试验入排标准、终点和 trial phase` | `science-clinical-regulatory / clinicaltrials-database` |
| `根据 FDA drug label 提取适应症、禁忌、不良反应、recall 和用法用量` | `science-clinical-regulatory / fda-database` |
| `查询 CPIC 药物基因组指南，解释 CYP2C19 和 clopidogrel 的 gene-drug 用药建议` | `science-clinical-regulatory / clinpgx-database` |
| `撰写 CARE guidelines 病例报告，包含临床时间线、诊断、治疗、知情同意和去标识化检查` | `science-clinical-regulatory / clinical-reports` |
| `审查 clinical report 的 HIPAA 合规性、去标识化、完整性和医学术语规范` | `science-clinical-regulatory / clinical-reports` |
| `为糖尿病患者生成一页式 treatment plan，包含 SMART 目标、用药方案和随访计划` | `science-clinical-regulatory / treatment-plans` |
| `准备 ISO 13485 医疗器械 QMS 认证差距分析、质量手册和 CAPA 程序文件` | `science-clinical-regulatory / iso-13485-certification` |
| `生成 clinical decision support 文档，包含 GRADE 证据、治疗算法、队列生存分析和 biomarker 分层` | `science-clinical-regulatory / clinical-decision-support` |
| `读取DICOM并提取tags` | `science-medical-imaging / pydicom` |
| `检索PubMed文献并导出BibTeX` | `science-literature-citations / pubmed-database` |
| `用RDKit解析SMILES并计算Morgan fingerprint` | `science-chem-drug / rdkit` |
| `科研技术报告：包含方法结果讨论，输出 HTML 和 PDF` | not `science-clinical-regulatory` |
| `审查代码质量、测试覆盖率和安全风险` | not `science-clinical-regulatory` |

## Verification

Required checks:

```powershell
python -m pytest tests/runtime_neutral/test_science_clinical_regulatory_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-keyword-precision-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
