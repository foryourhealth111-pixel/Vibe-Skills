# Routing Pack Boundary Cleanup

Date: 2026-04-29

## Scope

This cleanup clarifies routing ownership for document media, Figma implementation, publishing, reporting, slides, figures, and research-method prompts.

It does not change the public six-stage Vibe runtime and does not change the simplified skill-use contract:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

It also does not delete skill directories.

## Pack Counts

| Pack | Before | After | Meaning |
| --- | ---: | ---: | --- |
| `design-implementation` skill candidates | 0 | 2 | New narrow Figma/design implementation owner |
| `design-implementation` route authorities | 0 | 2 | `figma-implement-design`, `figma` |
| `research-design` skill candidates | 24 | 22 | Figma implementation moved out of research-method surface |
| `research-design` route authorities | 14 | 14 | Research-method authority preserved |
| `docs-media` skill candidates | 8 | 8 | Directory/candidate set preserved |
| `docs-media` route authorities | 8 | 8 | Authority now requires explicit file-operation signals for key document skills |
| `scholarly-publishing-workflow` skill candidates | 13 | 13 | Candidate set preserved |

## Ownership Contract

| User intent | Pack | Skill |
| --- | --- | --- |
| Read or extract existing PDF text | `docs-media` | `pdf` |
| Convert PDF or DOCX to Markdown | `docs-markitdown-conversion` | `markitdown` |
| Compile a LaTeX manuscript PDF | `scholarly-publishing-workflow` | `latex-submission-pipeline` |
| Write scientific or technical report with HTML/PDF output | `science-reporting` | `scientific-reporting` |
| Build Slidev / slides-as-code deck and export PDF | `science-communication-slides` | `slides-as-code` |
| Build publication/result/model-evaluation figures | `science-figures-visualization` | `scientific-visualization` |
| Implement Figma/design mockup as code | `design-implementation` | `figma-implement-design` |
| Design quasi-experimental methodology | `research-design` | `designing-experiments` |

## Boundary Decisions

`docs-media` remains XL-capable for explicit existing-file operations, including PDF extraction and requested XLSX workbook edits. It should not own generic XL multi-document orchestration from extension-only prompts.

`design-implementation` owns Figma-to-code and design implementation prompts. Figma implementation no longer lives under `research-design`, and Figma candidates require positive Figma/design implementation wording before they can own a route.

`research-design` remains responsible for research methods, experiment design, causal design, hypothesis generation, and grant planning.

`scholarly-publishing-workflow` owns submission, rebuttal, venue template, camera-ready, manuscript-as-code, and LaTeX manuscript build workflows. It has negative guards so it does not steal Figma implementation prompts.

Python and PowerShell router implementations now skip rows with no actual `selected_candidate` when choosing the final route. This prevents a high-scoring pack with `no_usable_candidate` from producing an empty selected skill or an empty confirmation UI.

## Regression Evidence

Protected by:

```text
tests/runtime_neutral/test_docs_research_publishing_boundary_routing.py
scripts/verify/vibe-pack-regression-matrix.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
tests/runtime_neutral/test_router_bridge.py
```

Required acceptance probes:

```text
读取 PDF 并提取正文 -> docs-media / pdf
把 PDF 转成 Markdown -> docs-markitdown-conversion / markitdown
用 LaTeX 写论文并构建 PDF -> scholarly-publishing-workflow / latex-submission-pipeline
科研技术报告：包含方法结果讨论，输出 HTML 和 PDF -> science-reporting / scientific-reporting
用 Slidev 做组会汇报并导出 PDF -> science-communication-slides / slides-as-code
绘制机器学习模型评估结果图和投稿图 -> science-figures-visualization / scientific-visualization
把这个 Figma 设计稿还原为可运行代码 -> design-implementation / figma-implement-design
帮我设计准实验方法，比较 DiD 和 ITS -> research-design / designing-experiments
xlsx and docx parallel processing -> not docs-media without explicit file-operation or requested skill
process xlsx workbook and preserve formulas, requested xlsx -> docs-media / xlsx
```
