# Science Literature And Peer Review Consolidation

Date: 2026-04-29

## Summary

This pass shrinks `science-literature-citations` into a literature discovery, citation management, and evidence extraction pack. Scholarly paper review and paper-quality scoring now belong to `science-peer-review`.

The six-stage Vibe runtime is unchanged, and skill usage remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

## Counts

| Pack | Field | Before | After |
| --- | --- | ---: | ---: |
| `science-literature-citations` | `skill_candidates` | 12 | 7 |
| `science-literature-citations` | `route_authority_candidates` | 10 | 7 |
| `science-literature-citations` | `stage_assistant_candidates` | 2 | 0 |
| `science-peer-review` | `skill_candidates` | 3 | 3 |
| `science-peer-review` | `route_authority_candidates` | 0 | 3 |
| `science-peer-review` | `stage_assistant_candidates` | 0 | 0 |

## Kept Literature Owners

| User problem | Skill |
| --- | --- |
| PubMed, PMID, MeSH, MEDLINE | `pubmed-database` |
| OpenAlex, DOI, authors, institutions, citation graph | `openalex-database` |
| bioRxiv and life-science preprints | `biorxiv-database` |
| Full-text evidence extraction and evidence tables | `bgpt-paper-search` |
| Zotero API and Zotero library automation | `pyzotero` |
| BibTeX, DOI validation, bibliography formatting | `citation-management` |
| Systematic review, meta-analysis, PRISMA | `literature-review` |

## Peer Review Owners

| User problem | Skill |
| --- | --- |
| Formal manuscript or grant review | `peer-review` |
| Evidence strength, bias, confounders, GRADE, Cochrane-style critique | `scientific-critical-thinking` |
| ScholarEval, paper-quality rubric, quantitative research scoring | `scholar-evaluation` |

## Removed Or Moved

| Skill | Action |
| --- | --- |
| `open-notebook` | Physically deleted after live-reference cleanup; it is a broad notebook/document-chat product integration, not a literature/citation expert. |
| `paper-2-web` | Removed from `science-literature-citations`; retained for publishing/promotion surfaces. |
| `peer-review` | Removed from `science-literature-citations`; owned by `science-peer-review`. |
| `scholar-evaluation` | Removed from `science-literature-citations`; owned by `science-peer-review`. |
| `scientific-critical-thinking` | Removed from `science-literature-citations`; owned by `science-peer-review`. |

## Protected Boundaries

| Prompt | Expected route |
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

Required checks:

```powershell
python -m pytest tests/runtime_neutral/test_science_literature_peer_review_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1 -Unattended
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```
