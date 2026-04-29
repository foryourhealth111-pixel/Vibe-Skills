# Science Literature And Peer Review Consolidation Design

Date: 2026-04-29

## Goal

Make `science-literature-citations` smaller and clearer.

The pack should only answer literature discovery, citation management, and evidence extraction problems. It should not own paper quality review, peer review, research-quality scoring, scientific critique, notebook workspaces, or paper promotion outputs.

This design keeps the public six-stage Vibe runtime unchanged and preserves the simplified skill contract:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

## Current Evidence

Current `science-literature-citations` has 12 skill candidates and 10 route authorities:

```text
pubmed-database
openalex-database
biorxiv-database
bgpt-paper-search
paper-2-web
open-notebook
pyzotero
citation-management
literature-review
peer-review
scholar-evaluation
scientific-critical-thinking
```

Observed boundary probes:

| Prompt type | Current result | Problem |
| --- | --- | --- |
| PubMed + BibTeX | `science-literature-citations / pubmed-database` | Correct |
| Zotero programmatic workflow | `science-literature-citations / pyzotero` | Correct |
| Citation formatting | `science-literature-citations / citation-management` | Correct |
| Full-text evidence table | `science-literature-citations / bgpt-paper-search` | Correct |
| Formal peer review | `science-peer-review / peer-review` | Correct |
| Paper quality scoring rubric | `code-quality / code-reviewer` or `data-ml / evaluating-machine-learning-models` | Wrong |
| ScholarEval rubric | `data-ml / evaluating-machine-learning-models` | Wrong |
| Evidence strength / bias critique | `ruc-nlpir-augmentation / flashrag-evidence` | Wrong |
| Rebuttal matrix / cover letter | `scholarly-publishing-workflow / submission-checklist` | Correct |

The main defect is not ordinary literature lookup. The defect is that scholarly review and paper-quality evaluation do not have a clean authority boundary.

## Target Ownership

### `science-literature-citations`

Keep this pack focused on the literature and citation lifecycle.

| User problem | Owner |
| --- | --- |
| Biomedical literature lookup, PMID, MeSH, MEDLINE, PubMed API | `pubmed-database` |
| Broad scholarly metadata, DOI, authors, institutions, citation graph | `openalex-database` |
| Life-science preprints and bioRxiv metadata | `biorxiv-database` |
| Full-text paper search, structured evidence extraction, sample size, effect size, evidence table | `bgpt-paper-search` |
| Zotero library automation and Zotero Web API work | `pyzotero` |
| DOI validation, BibTeX, reference formatting, bibliography cleanup | `citation-management` |
| Systematic review, meta-analysis, PRISMA, cross-database synthesis | `literature-review` |

Target count:

| Field | Before | Target |
| --- | ---: | ---: |
| `skill_candidates` | 12 | 7 |
| `route_authority_candidates` | 10 | 7 |
| `stage_assistant_candidates` | 2 | 0 |

### `science-peer-review`

Make this the clear owner for scholarly review and quality assessment.

| User problem | Owner |
| --- | --- |
| Formal manuscript or grant review, reviewer comments, methodology/statistics/reproducibility review | `peer-review` |
| Evidence strength, bias, confounders, GRADE, Cochrane-style critical appraisal | `scientific-critical-thinking` |
| Quantitative paper quality scoring, ScholarEval, rubric-based research assessment | `scholar-evaluation` |

Target count:

| Field | Before | Target |
| --- | ---: | ---: |
| `skill_candidates` | 3 | 3 |
| `route_authority_candidates` | 0 | 3 |
| `stage_assistant_candidates` | 0 | 0 |

## Removals And Moves

| Skill | Target action | Rationale |
| --- | --- | --- |
| `open-notebook` | Physically delete after live-reference cleanup | It is a research workspace / document chat product integration, not a literature/citation expert. It adds broad notebook/document-chat noise and does not fit the simplified route model. |
| `paper-2-web` | Remove from `science-literature-citations`; keep only where publishing/promotion needs it | It transforms papers into web/poster/video outputs. That belongs with publishing or communication, not literature retrieval. |
| `peer-review` | Remove from `science-literature-citations`; keep in `science-peer-review` | Formal review should have one expert boundary. |
| `scholar-evaluation` | Remove from `science-literature-citations`; keep in `science-peer-review` | Paper scoring and ScholarEval are scholarly review, not citation management. |
| `scientific-critical-thinking` | Remove from `science-literature-citations`; keep in `science-peer-review` | Evidence critique is scholarly review, not literature lookup. |

No other physical directory deletion is in scope for this pass.

## Routing Rules

Implementation should update routing in this order:

1. Shrink `config/pack-manifest.json`.
2. Tighten `config/skill-keyword-index.json`.
3. Tighten `config/skill-routing-rules.json`.
4. Clean live references to removed `open-notebook`.
5. Regenerate `config/skills-lock.json`.

Important guardrails:

- `science-literature-citations` should not select `peer-review`, `scholar-evaluation`, or `scientific-critical-thinking`.
- `science-peer-review` should win for paper quality, ScholarEval, rubric, evidence strength, bias, confounders, formal review, and methodology critique.
- `code-quality` should not win for research paper quality review unless the prompt is explicitly about code.
- `data-ml` should not win for paper scoring unless the prompt is explicitly about ML model evaluation.
- `ruc-nlpir-augmentation / flashrag-evidence` should not win for scholarly evidence critique unless the prompt is about repository-local source-of-truth evidence lookup.
- `scholarly-publishing-workflow` should continue to own cover letters, rebuttal matrices, submission checklists, and LaTeX manuscript builds.

## Regression Probes

Add or update route probes for these boundaries:

| Prompt | Expected |
| --- | --- |
| `在 PubMed 检索文献并导出 BibTeX` | `science-literature-citations / pubmed-database` |
| `用 pyzotero 连接 Zotero library，批量整理条目并导出 BibTeX` | `science-literature-citations / pyzotero` |
| `整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography` | `science-literature-citations / citation-management` |
| `做系统综述和 meta-analysis，输出 PRISMA 流程和纳排标准` | `science-literature-citations / literature-review` |
| `做 full-text 文献检索，提取样本量、effect size、方法学细节，生成系统综述证据表` | `science-literature-citations / bgpt-paper-search` |
| `请对这篇论文做 peer review，指出方法学缺陷和可复现性风险` | `science-peer-review / peer-review` |
| `用 ScholarEval rubric 评估这篇论文的问题 formulation、methodology、analysis 和 writing` | `science-peer-review / scholar-evaluation` |
| `批判性分析这篇论文的证据强度、偏倚和混杂因素` | `science-peer-review / scientific-critical-thinking` |
| `写论文投稿 cover letter 和 response to reviewers rebuttal matrix` | `scholarly-publishing-workflow / submission-checklist` |
| `用 LaTeX 写论文并构建 PDF` | `scholarly-publishing-workflow / latex-submission-pipeline` |

## Verification

Focused checks:

```powershell
python -m pytest tests/runtime_neutral/test_science_literature_peer_review_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1 -Unattended
```

Broad checks:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```

## Out Of Scope

- Reworking `scholarly-publishing-workflow` beyond protecting rebuttal and LaTeX boundaries.
- Deleting `paper-2-web` globally.
- Changing the six-stage Vibe runtime.
- Adding advisory, consult, primary/secondary, or stage-assistant complexity to skill usage reporting.
