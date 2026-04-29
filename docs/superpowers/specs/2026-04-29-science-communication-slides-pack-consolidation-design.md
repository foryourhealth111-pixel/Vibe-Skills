# Science Communication Slides Pack Consolidation Design

Date: 2026-04-29

## Goal

Consolidate `science-communication-slides` into a focused scientific presentation and communication-deliverable pack.

This pass keeps the six-stage Vibe runtime unchanged and preserves the simplified skill-use model:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

The pack should own scientific slide decks, slides-as-code builds, explicitly PowerPoint/PPTX posters, and explicitly requested infographics. It should not own general diagrams, Mermaid documentation, file-to-Markdown conversion, document dispatching, or general-purpose image generation.

## Current State

`science-communication-slides` currently has 8 `skill_candidates`, no explicit `route_authority_candidates`, and no `stage_assistant_candidates`.

Current candidates:

```text
scientific-slides
slides-as-code
pptx-posters
infographics
markdown-mermaid-writing
markitdown
document-skills
generate-image
```

Current defaults:

| Task | Default |
| --- | --- |
| `planning` | `scientific-slides` |
| `coding` | `markdown-mermaid-writing` |
| `research` | `infographics` |

Several candidates duplicate ownership already present in other packs:

| Skill | Existing stronger owner |
| --- | --- |
| `markdown-mermaid-writing` | `science-reporting` as a workflow/documentation assistant, and `science-figures-visualization` for diagram-style prompts |
| `markitdown` | `docs-markitdown-conversion` |
| `document-skills` | document dispatcher surface, not a slide expert |
| `generate-image` | general image-generation surface, not a slide route authority |

The current trigger list is too broad because it includes `poster`, `infographic`, `mermaid`, `diagram`, `flowchart`, `海报`, `信息图`, `流程图`, and `示意图` at the pack level. Those terms can pull non-slide work into the slides pack before candidate selection runs.

## Target Routing Contract

After consolidation:

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 8 | 4 |
| `route_authority_candidates` | 0 | 4 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` is a compatibility mirror of `skill_candidates`, not a second execution model. No `primary/secondary`, `consult`, `advisory`, or stage-assistant execution semantics are introduced.

## Kept Route Owners

| User problem | Skill |
| --- | --- |
| Scientific slide deck, PowerPoint deck, research talk, seminar talk, group-meeting deck, thesis defense, roadshow or grant pitch presentation | `scientific-slides` |
| Slidev, Marp, Reveal.js, Quarto slides, reproducible slides-as-code source, PDF export from text-first slide source | `slides-as-code` |
| Explicit PowerPoint/PPTX poster, PPT poster, or HTML-to-PPTX poster where the user needs editable PowerPoint output | `pptx-posters` |
| Explicit infographic, visual summary, visual one-pager, or research-summary graphic that is not a data-result figure or technical schematic | `infographics` |

## Moved Out Of This Pack

These skills remain valuable and should not be physically deleted in this pass. They are removed only from `science-communication-slides` routing ownership.

| Skill | Target boundary | Rationale |
| --- | --- | --- |
| `markdown-mermaid-writing` | `science-reporting` or diagram/documentation surfaces | Mermaid and Markdown diagrams are documentation/reporting tools. A user asking for a flowchart should not be routed to a slide pack unless they also ask for a deck. |
| `markitdown` | `docs-markitdown-conversion` | File-to-Markdown conversion already has a dedicated one-skill pack and should not appear as a slide candidate. |
| `document-skills` | document dispatcher surface | It is an umbrella dispatcher for PDF/DOCX/XLSX/PPTX work, not a specialist that should own a scientific-communication route. |
| `generate-image` | general image-generation surface | General image generation is too broad and can weakly capture unrelated prompts such as concept art or product images. |

## Trigger Design

Keep pack triggers that clearly indicate a presentation deliverable:

```text
slides
slide deck
ppt
pptx
powerpoint
presentation
talk
seminar
defense
slidev
marp
reveal.js
quarto slides
slides as code
幻灯片
演示文稿
组会汇报
答辩
路演
学术报告
```

Remove broad figure/report/document triggers from the pack-level list:

```text
poster
infographic
mermaid
diagram
flowchart
海报
信息图
流程图
示意图
```

Poster and infographic routing should be expressed at the skill-rule level, not as broad pack triggers:

| Prompt intent | Target |
| --- | --- |
| `conference poster`, `academic poster`, `学术海报`, `会议海报` | `scholarly-publishing-workflow / latex-posters` by default |
| `PPTX poster`, `PowerPoint poster`, `PPT海报` | `science-communication-slides / pptx-posters` |
| `infographic`, `信息图`, `visual summary` | `science-communication-slides / infographics` only when explicitly requested |
| `flowchart`, `diagram`, `机制示意图`, `流程图` | `science-figures-visualization / scientific-schematics` unless the user also asks for a deck |
| `PDF to Markdown`, `docx to markdown`, `markitdown` | `docs-markitdown-conversion / markitdown` |

## Defaults

After consolidation:

| Task | Default |
| --- | --- |
| `planning` | `scientific-slides` |
| `coding` | `slides-as-code` |
| `research` | `scientific-slides` |

The `coding` default changes from `markdown-mermaid-writing` to `slides-as-code` because code-oriented work inside this pack should mean text-first slide source and reproducible export, not Mermaid documentation.

## Expected Route Probes

The implementation should add or update focused route regressions for these boundaries:

| Prompt | Expected route |
| --- | --- |
| `顶级PPT制作：组会汇报 slide deck，需要讲述结构与视觉规范` | `science-communication-slides / scientific-slides` |
| `用 Slidev 做组会汇报并导出 PDF` | `science-communication-slides / slides-as-code` |
| `用 Marp 做科研 presentation 并导出 PDF` | `science-communication-slides / slides-as-code` |
| `制作 PowerPoint PPTX 学术海报` | `science-communication-slides / pptx-posters` |
| `制作学术海报 conference poster` | `scholarly-publishing-workflow / latex-posters` |
| `做一个研究结论信息图 infographic visual summary` | `science-communication-slides / infographics` |
| `用 Mermaid 写一个实验流程图 flowchart，并给出可复制的 markdown` | not `science-communication-slides`; expected owner should be the reporting or figures boundary chosen during implementation |
| `画一个机制示意图和流程图` | `science-figures-visualization / scientific-schematics` |
| `绘制机器学习模型评估结果图和投稿图` | `science-figures-visualization / scientific-visualization` |
| `把 PDF 转成 Markdown，要求保留表格与标题结构` | `docs-markitdown-conversion / markitdown` |
| `生成一张产品概念图 image generation` | not `science-communication-slides` |

## Implementation Scope

The implementation should edit only routing/config/test/governance surfaces needed for this pack:

```text
config/pack-manifest.json
config/skill-keyword-index.json
config/skill-routing-rules.json
tests/runtime_neutral/test_science_communication_slides_pack_consolidation.py
scripts/verify/probe-scientific-packs.ps1
scripts/verify/vibe-skill-index-routing-audit.ps1
docs/governance/science-communication-slides-pack-consolidation-2026-04-29.md
config/skills-lock.json, if regenerated by the existing gate
```

Do not physically delete skill directories in this pass. Directory deletion requires a separate review because several moved-out skills contain scripts, references, templates, or assets.

## Verification

Focused verification should run first:

```powershell
python -m pytest tests/runtime_neutral/test_science_communication_slides_pack_consolidation.py -q
```

Then run broader routing and config gates:

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

If an existing broad probe still expects Mermaid flowcharts to route to `science-communication-slides`, update that probe to the new boundary instead of preserving the old behavior.
