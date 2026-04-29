# Scholarly Publishing Pack Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shrink `scholarly-publishing-workflow` into a focused publishing and manuscript-delivery pack and remove figure, slide, and citation owners from its selectable routing surface.

**Architecture:** Add focused manifest and route tests first, then shrink the pack manifest, tighten keyword/routing rules for the 8 kept publishing owners, add route-probe coverage, and record the governance boundary. This pass changes routing/config only; it does not delete bundled skill directories or change the six-stage Vibe runtime.

**Tech Stack:** Python `unittest`/pytest route tests, PowerShell route-probe scripts, JSON config files, Markdown governance docs.

---

## File Map

- Create: `tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py`
- Modify: `config/pack-manifest.json`
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Create: `docs/governance/scholarly-publishing-pack-consolidation-2026-04-29.md`

No `config/skills-lock.json` change is expected because this plan does not physically delete or add bundled skill directories.

## Task 1: Add Focused Failing Tests

**Files:**
- Create: `tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py`

- [ ] **Step 1: Create the focused route and manifest test file**

Use `apply_patch` to add this exact file:

```python
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


SCHOLARLY_PUBLISHING_SKILLS = [
    "scholarly-publishing",
    "submission-checklist",
    "manuscript-as-code",
    "latex-submission-pipeline",
    "scientific-writing",
    "venue-templates",
    "latex-posters",
    "paper-2-web",
]

MOVED_OUT_SKILLS = [
    "slides-as-code",
    "scientific-visualization",
    "scientific-schematics",
    "citation-management",
    "scientific-slides",
]


def route(prompt: str, task_type: str = "research", grade: str = "L") -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        repo_root=REPO_ROOT,
    )


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_summary(result: dict[str, object]) -> list[tuple[str, str, float, str]]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    rows: list[tuple[str, str, float, str]] = []
    for row in ranked[:8]:
        assert isinstance(row, dict), row
        rows.append(
            (
                str(row.get("pack_id") or ""),
                str(row.get("selected_candidate") or ""),
                float(row.get("score") or 0.0),
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


def pack_by_id(pack_id: str) -> dict[str, object]:
    manifest_path = REPO_ROOT / "config" / "pack-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    packs = manifest.get("packs")
    assert isinstance(packs, list), manifest
    for pack in packs:
        assert isinstance(pack, dict), pack
        if pack.get("id") == pack_id:
            return pack
    raise AssertionError(f"pack missing: {pack_id}")


class ScholarlyPublishingPackConsolidationTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def assert_not_scholarly_publishing(
        self,
        prompt: str,
        *,
        task_type: str = "research",
        grade: str = "L",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertNotEqual("scholarly-publishing-workflow", selected(result)[0], ranked_summary(result))

    def test_manifest_is_publishing_workflow_only(self) -> None:
        pack = pack_by_id("scholarly-publishing-workflow")
        self.assertEqual(SCHOLARLY_PUBLISHING_SKILLS, pack.get("skill_candidates"))
        self.assertEqual(SCHOLARLY_PUBLISHING_SKILLS, pack.get("route_authority_candidates"))
        self.assertEqual([], pack.get("stage_assistant_candidates"))
        self.assertEqual(
            {
                "planning": "scholarly-publishing",
                "coding": "latex-submission-pipeline",
                "research": "scientific-writing",
            },
            pack.get("defaults_by_task"),
        )
        for moved_skill in MOVED_OUT_SKILLS:
            self.assertNotIn(moved_skill, pack.get("skill_candidates") or [])

    def test_publishing_workflow_routes_to_scholarly_publishing(self) -> None:
        self.assert_selected(
            "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready",
            "scholarly-publishing-workflow",
            "scholarly-publishing",
            task_type="planning",
        )

    def test_rebuttal_matrix_routes_to_submission_checklist(self) -> None:
        self.assert_selected(
            "写 cover letter 和 response to reviewers rebuttal matrix",
            "scholarly-publishing-workflow",
            "submission-checklist",
            task_type="planning",
        )

    def test_manuscript_as_code_routes_to_manuscript_as_code(self) -> None:
        self.assert_selected(
            "把论文仓库改成 manuscript-as-code，可复现构建 PDF",
            "scholarly-publishing-workflow",
            "manuscript-as-code",
            task_type="planning",
        )

    def test_latex_pipeline_routes_to_latex_submission_pipeline(self) -> None:
        self.assert_selected(
            "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            task_type="coding",
            grade="XL",
        )

    def test_scientific_writing_routes_to_scientific_writing(self) -> None:
        self.assert_selected(
            "请按 IMRAD 结构写科研论文正文",
            "scholarly-publishing-workflow",
            "scientific-writing",
            task_type="research",
        )

    def test_venue_template_routes_to_venue_templates(self) -> None:
        self.assert_selected(
            "查 NeurIPS 模板和匿名投稿格式要求",
            "scholarly-publishing-workflow",
            "venue-templates",
            task_type="planning",
        )

    def test_latex_poster_routes_to_latex_posters(self) -> None:
        self.assert_selected(
            "用 beamerposter 做会议学术海报",
            "scholarly-publishing-workflow",
            "latex-posters",
            task_type="coding",
        )

    def test_paper2web_routes_to_paper_2_web(self) -> None:
        self.assert_selected(
            "把论文转换成 paper2web 项目主页和视频摘要",
            "scholarly-publishing-workflow",
            "paper-2-web",
            task_type="planning",
        )

    def test_result_figures_stay_in_science_figures(self) -> None:
        self.assert_selected(
            "绘制机器学习模型评估结果图和投稿图",
            "science-figures-visualization",
            "scientific-visualization",
            task_type="coding",
        )

    def test_schematics_stay_in_science_figures(self) -> None:
        self.assert_selected(
            "画一个机制示意图和流程图",
            "science-figures-visualization",
            "scientific-schematics",
            task_type="planning",
        )

    def test_slidev_stays_in_science_communication_slides(self) -> None:
        self.assert_selected(
            "用 Slidev 做组会汇报并导出 PDF",
            "science-communication-slides",
            "slides-as-code",
            task_type="coding",
        )

    def test_scientific_slide_deck_stays_in_science_communication_slides(self) -> None:
        self.assert_selected(
            "顶级PPT制作：组会汇报 slide deck",
            "science-communication-slides",
            "scientific-slides",
            task_type="planning",
        )

    def test_citation_management_stays_in_literature_citations(self) -> None:
        self.assert_selected(
            "整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography",
            "science-literature-citations",
            "citation-management",
            task_type="planning",
        )

    def test_existing_pdf_extraction_stays_in_docs_media(self) -> None:
        self.assert_selected(
            "读取 PDF 并提取正文",
            "docs-media",
            "pdf",
            task_type="coding",
            grade="XL",
        )

    def test_scientific_report_stays_in_science_reporting(self) -> None:
        self.assert_selected(
            "科研技术报告：包含方法结果讨论，输出 HTML 和 PDF",
            "science-reporting",
            "scientific-reporting",
            task_type="planning",
        )

    def test_generic_figure_or_slide_prompts_do_not_route_to_publishing(self) -> None:
        self.assert_not_scholarly_publishing(
            "做一套科研图表和组会幻灯片",
            task_type="planning",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm it fails before implementation**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py -q
```

Expected: FAIL. At minimum, the manifest test fails because `scholarly-publishing-workflow` still has 13 candidates and no explicit `route_authority_candidates`.

Do not commit this failing test alone.

## Task 2: Shrink `scholarly-publishing-workflow` In Pack Manifest

**Files:**
- Modify: `config/pack-manifest.json`

- [ ] **Step 1: Replace the `scholarly-publishing-workflow` routing surface**

In the `scholarly-publishing-workflow` object in `config/pack-manifest.json`, set these fields exactly:

```json
"trigger_keywords": [
  "scholarly publishing",
  "publishing workflow",
  "journal submission workflow",
  "submission",
  "rebuttal",
  "revision",
  "resubmission",
  "camera-ready",
  "proof",
  "cover letter",
  "response to reviewers",
  "submission checklist",
  "submission package",
  "manuscript as code",
  "paper as code",
  "reproducible manuscript",
  "venue template",
  "submission guidelines",
  "formatting requirements",
  "anonymous submission",
  "page limit",
  "latexmk",
  "latexindent",
  "chktex",
  "latex",
  "latex paper",
  "latex manuscript",
  "latex pdf",
  "paper pdf build",
  "manuscript pdf build",
  "compile paper",
  "submission zip",
  "beamerposter",
  "paper2web",
  "paper2poster",
  "paper2video",
  "scientific writing",
  "imrad",
  "manuscript prose",
  "投稿",
  "投稿流程",
  "期刊投稿",
  "投稿包",
  "投稿清单",
  "返修",
  "回复审稿意见",
  "相机就绪",
  "校样",
  "论文工程化",
  "可复现写作",
  "投稿模板",
  "格式要求",
  "匿名投稿",
  "页数限制",
  "LaTeX 论文",
  "LaTeX 写论文",
  "LaTeX 论文 PDF",
  "写成论文 PDF",
  "论文 PDF",
  "PDF 构建",
  "生成论文 PDF",
  "编译论文",
  "论文编译",
  "可投稿 PDF",
  "学术海报",
  "论文转网站",
  "科研写作",
  "论文正文"
],
"skill_candidates": [
  "scholarly-publishing",
  "submission-checklist",
  "manuscript-as-code",
  "latex-submission-pipeline",
  "scientific-writing",
  "venue-templates",
  "latex-posters",
  "paper-2-web"
],
"route_authority_candidates": [
  "scholarly-publishing",
  "submission-checklist",
  "manuscript-as-code",
  "latex-submission-pipeline",
  "scientific-writing",
  "venue-templates",
  "latex-posters",
  "paper-2-web"
],
"stage_assistant_candidates": [],
"defaults_by_task": {
  "planning": "scholarly-publishing",
  "coding": "latex-submission-pipeline",
  "research": "scientific-writing"
}
```

Do not delete any directories under `bundled/skills/`.

- [ ] **Step 2: Run the focused test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py -q
```

Expected: manifest assertions pass; route assertions may still fail until Task 3 tightens keywords and routing rules.

Do not commit yet.

## Task 3: Tighten Keyword Index And Routing Rules

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`

- [ ] **Step 1: Update keyword index entries for the eight kept skills**

In `config/skill-keyword-index.json`, ensure the `skills` object contains these entries with the listed `keywords` arrays. Preserve the surrounding JSON structure.

```json
"scholarly-publishing": {
  "keywords": [
    "scholarly publishing",
    "publishing workflow",
    "journal submission workflow",
    "submission package",
    "camera-ready",
    "proof",
    "journal submission",
    "conference submission",
    "投稿",
    "投稿流程",
    "期刊投稿",
    "投稿包",
    "出版流程",
    "相机就绪",
    "校样"
  ]
},
"submission-checklist": {
  "keywords": [
    "submission checklist",
    "pre-submission",
    "cover letter",
    "rebuttal",
    "response to reviewers",
    "rebuttal matrix",
    "revision",
    "resubmission",
    "camera-ready checklist",
    "proof checklist",
    "highlights",
    "graphical abstract",
    "投稿清单",
    "投稿前自检",
    "附信",
    "返修",
    "回复审稿意见",
    "逐条回应",
    "相机就绪清单",
    "校样清单"
  ]
},
"manuscript-as-code": {
  "keywords": [
    "manuscript as code",
    "paper as code",
    "reproducible manuscript",
    "reproducible build",
    "version control",
    "git manuscript",
    "repository structure",
    "figure pipeline",
    "ci build",
    "final_v7",
    "论文工程化",
    "可复现写作",
    "可复现构建",
    "论文仓库",
    "版本控制论文",
    "图表流水线"
  ]
},
"latex-submission-pipeline": {
  "keywords": [
    "latex",
    "latexmk",
    "latexmkrc",
    "overleaf",
    "chktex",
    "latexindent",
    "bibtex",
    "biber",
    "texlive",
    "pdflatex",
    "xelatex",
    "lualatex",
    "latex action",
    "github actions",
    "submission zip",
    "latex投稿",
    "latex paper",
    "latex manuscript",
    "latex pdf",
    "paper pdf build",
    "manuscript pdf build",
    "build manuscript pdf",
    "compile paper",
    "compile manuscript",
    "LaTeX 论文",
    "LaTeX 写论文",
    "LaTeX 论文 PDF",
    "LaTeX 写成论文",
    "LaTeX 写成论文 PDF",
    "写成论文 PDF",
    "论文 PDF",
    "PDF 构建",
    "生成论文 PDF",
    "编译论文",
    "论文编译",
    "构建可投稿 PDF",
    "可投稿 PDF"
  ]
},
"scientific-writing": {
  "keywords": [
    "scientific writing",
    "imrad",
    "manuscript prose",
    "paper writing",
    "abstract",
    "introduction",
    "methods section",
    "results section",
    "discussion section",
    "journal manuscript",
    "research manuscript",
    "科研写作",
    "论文写作",
    "论文正文",
    "摘要",
    "引言",
    "方法",
    "结果",
    "讨论",
    "学术稿件"
  ]
},
"venue-templates": {
  "keywords": [
    "venue template",
    "latex template",
    "author guidelines",
    "submission guidelines",
    "formatting requirements",
    "camera-ready format",
    "anonymous submission",
    "page limit",
    "neurips",
    "icml",
    "cvpr",
    "chi",
    "nature",
    "science",
    "ieee",
    "acm",
    "投稿模板",
    "格式要求",
    "版式要求",
    "匿名投稿",
    "页数限制",
    "作者指南"
  ]
},
"latex-posters": {
  "keywords": [
    "poster",
    "conference poster",
    "academic poster",
    "research poster",
    "beamerposter",
    "tikzposter",
    "baposter",
    "poster latex",
    "a0 poster",
    "学术海报",
    "科研海报",
    "会议海报",
    "展板",
    "a0海报"
  ]
},
"paper-2-web": {
  "keywords": [
    "paper2web",
    "paper2poster",
    "paper2video",
    "paper to web",
    "paper to poster",
    "paper to video",
    "convert paper",
    "project homepage",
    "paper website",
    "video abstract",
    "conference poster from paper",
    "论文转网站",
    "论文转网页",
    "论文项目主页",
    "论文转海报",
    "论文转视频",
    "视频摘要"
  ]
}
```

- [ ] **Step 2: Update routing rules for the eight kept skills**

In `config/skill-routing-rules.json`, ensure the `skills` object contains or updates these rules. Preserve unrelated fields outside each rule.

```json
"scholarly-publishing": {
  "task_allow": ["planning", "research", "review"],
  "positive_keywords": [
    "scholarly publishing",
    "publishing workflow",
    "journal submission workflow",
    "submission package",
    "camera-ready",
    "proof",
    "journal submission",
    "conference submission",
    "投稿",
    "投稿流程",
    "期刊投稿",
    "投稿包",
    "出版流程",
    "相机就绪",
    "校样"
  ],
  "negative_keywords": [
    "rebuttal matrix",
    "response to reviewers",
    "cover letter",
    "latexmk",
    "chktex",
    "latexindent",
    "slidev",
    "ppt",
    "result figure",
    "model evaluation plot",
    "bibtex",
    "reference formatting",
    "figma"
  ],
  "equivalent_group": "scholarly-publishing",
  "canonical_for_task": ["planning", "research"]
}
```

```json
"submission-checklist": {
  "task_allow": ["planning", "research", "review"],
  "positive_keywords": [
    "submission checklist",
    "pre-submission",
    "cover letter",
    "rebuttal",
    "response to reviewers",
    "rebuttal matrix",
    "revision",
    "resubmission",
    "camera-ready checklist",
    "proof checklist",
    "highlights",
    "graphical abstract",
    "投稿清单",
    "投稿前自检",
    "附信",
    "返修",
    "回复审稿意见",
    "逐条回应",
    "相机就绪清单",
    "校样清单"
  ],
  "negative_keywords": [
    "latexmkrc",
    "latexmk",
    "latexindent",
    "chktex",
    "github actions",
    "ci pipeline",
    "slidev",
    "ppt"
  ],
  "equivalent_group": "scholarly-publishing",
  "canonical_for_task": ["planning", "review"]
}
```

```json
"manuscript-as-code": {
  "task_allow": ["planning", "coding", "research"],
  "positive_keywords": [
    "manuscript as code",
    "paper as code",
    "reproducible manuscript",
    "reproducible build",
    "version control",
    "git manuscript",
    "repository structure",
    "figure pipeline",
    "ci build",
    "final_v7",
    "论文工程化",
    "可复现写作",
    "可复现构建",
    "论文仓库",
    "版本控制论文",
    "图表流水线"
  ],
  "negative_keywords": [
    "rebuttal",
    "cover letter",
    "latexindent",
    "chktex",
    "slidev",
    "ppt",
    "pubmed",
    "bibtex"
  ],
  "equivalent_group": "scholarly-publishing",
  "canonical_for_task": ["planning", "coding"]
}
```

```json
"latex-submission-pipeline": {
  "task_allow": ["planning", "coding", "debug", "research"],
  "positive_keywords": [
    "latex submission pipeline",
    "latexmk",
    "latexmkrc",
    "latexindent",
    "chktex",
    "biber",
    "bibtex",
    "pdflatex",
    "xelatex",
    "lualatex",
    "github actions",
    "ci pipeline",
    "compile latex",
    "build pdf",
    "submission zip",
    "自动编译",
    "latex",
    "latex paper",
    "latex manuscript",
    "latex pdf",
    "paper pdf build",
    "manuscript pdf build",
    "build manuscript pdf",
    "compile paper",
    "compile manuscript",
    "LaTeX 论文",
    "LaTeX 写论文",
    "LaTeX 论文 PDF",
    "LaTeX 写成论文",
    "LaTeX 写成论文 PDF",
    "写成论文 PDF",
    "论文 PDF",
    "PDF 构建",
    "生成论文 PDF",
    "编译论文",
    "论文编译",
    "构建可投稿 PDF",
    "可投稿 PDF"
  ],
  "negative_keywords": [
    "rebuttal",
    "response to reviewers",
    "cover letter",
    "highlights",
    "graphical abstract",
    "read pdf",
    "extract pdf",
    "pdf extraction",
    "读取 PDF",
    "提取正文",
    "figma",
    "slidev",
    "ppt"
  ],
  "equivalent_group": "latex-pipeline",
  "canonical_for_task": ["coding"]
}
```

```json
"scientific-writing": {
  "task_allow": ["planning", "research", "review"],
  "positive_keywords": [
    "scientific writing",
    "imrad",
    "manuscript prose",
    "paper writing",
    "abstract",
    "introduction",
    "methods section",
    "results section",
    "discussion section",
    "journal manuscript",
    "research manuscript",
    "科研写作",
    "论文写作",
    "论文正文",
    "摘要",
    "引言",
    "方法",
    "结果",
    "讨论",
    "学术稿件"
  ],
  "negative_keywords": [
    "ci pipeline",
    "latexmk",
    "chktex",
    "rebuttal matrix",
    "cover letter",
    "slide deck",
    "ppt",
    "result figure",
    "technical report",
    "科研技术报告"
  ],
  "equivalent_group": "scientific-writing",
  "canonical_for_task": ["research"]
}
```

```json
"venue-templates": {
  "task_allow": ["planning", "research", "coding"],
  "positive_keywords": [
    "venue template",
    "latex template",
    "author guidelines",
    "submission guidelines",
    "formatting requirements",
    "camera-ready format",
    "anonymous submission",
    "page limit",
    "neurips",
    "icml",
    "cvpr",
    "chi",
    "nature",
    "science",
    "ieee",
    "acm",
    "投稿模板",
    "格式要求",
    "版式要求",
    "匿名投稿",
    "页数限制",
    "作者指南"
  ],
  "negative_keywords": [
    "rebuttal",
    "response to reviewers",
    "latexmk",
    "chktex",
    "plot",
    "作图",
    "slide deck",
    "ppt"
  ],
  "equivalent_group": "venue-format",
  "canonical_for_task": ["planning", "research"]
}
```

```json
"latex-posters": {
  "task_allow": ["planning", "coding", "research"],
  "positive_keywords": [
    "poster",
    "conference poster",
    "academic poster",
    "research poster",
    "beamerposter",
    "tikzposter",
    "baposter",
    "poster latex",
    "a0 poster",
    "学术海报",
    "科研海报",
    "会议海报",
    "展板",
    "a0海报"
  ],
  "negative_keywords": [
    "slidev",
    "marp",
    "ppt",
    "powerpoint",
    "paper2web",
    "paper2video"
  ],
  "equivalent_group": "posters",
  "canonical_for_task": ["planning", "coding"]
}
```

```json
"paper-2-web": {
  "task_allow": ["planning", "coding", "research"],
  "positive_keywords": [
    "paper2web",
    "paper2poster",
    "paper2video",
    "paper to web",
    "paper to poster",
    "paper to video",
    "convert paper",
    "project homepage",
    "paper website",
    "video abstract",
    "conference poster from paper",
    "论文转网站",
    "论文转网页",
    "论文项目主页",
    "论文转海报",
    "论文转视频",
    "视频摘要"
  ],
  "negative_keywords": [
    "pubmed",
    "pmid",
    "citation format",
    "bibtex",
    "latexmk",
    "chktex",
    "slidev",
    "ppt"
  ],
  "equivalent_group": "paper-transform",
  "canonical_for_task": ["planning", "coding"]
}
```

- [ ] **Step 3: Run the focused test**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py -q
```

Expected: all focused tests pass.

- [ ] **Step 4: Commit focused pack and route-rule changes**

Run:

```powershell
git add config\pack-manifest.json config\skill-keyword-index.json config\skill-routing-rules.json tests\runtime_neutral\test_scholarly_publishing_pack_consolidation.py
git commit -m "fix: consolidate scholarly publishing routing"
```

Expected: commit succeeds.

## Task 4: Add Script-Level Route Probe Coverage

**Files:**
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`

- [ ] **Step 1: Add skill-index audit cases**

In `scripts/verify/vibe-skill-index-routing-audit.ps1`, append these cases near the existing `rebuttal matrix`, `scientific writing`, and LaTeX-related publishing cases:

```powershell
    [pscustomobject]@{ Name = "publishing workflow package"; Prompt = "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scholarly-publishing" },
    [pscustomobject]@{ Name = "submission checklist rebuttal matrix"; Prompt = "写 cover letter 和 response to reviewers rebuttal matrix"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "submission-checklist" },
    [pscustomobject]@{ Name = "manuscript as code reproducible build"; Prompt = "把论文仓库改成 manuscript-as-code，可复现构建 PDF"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "manuscript-as-code" },
    [pscustomobject]@{ Name = "latex submission zip build"; Prompt = "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip"; Grade = "XL"; TaskType = "coding"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline" },
    [pscustomobject]@{ Name = "venue template anonymous submission"; Prompt = "查 NeurIPS 模板和匿名投稿格式要求"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "venue-templates" },
    [pscustomobject]@{ Name = "latex academic poster"; Prompt = "用 beamerposter 做会议学术海报"; Grade = "L"; TaskType = "coding"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-posters" },
    [pscustomobject]@{ Name = "paper2web video abstract"; Prompt = "把论文转换成 paper2web 项目主页和视频摘要"; Grade = "L"; TaskType = "planning"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "paper-2-web" },
```

If the last existing case in the PowerShell array has no trailing comma, add a comma before appending these rows.

- [ ] **Step 2: Add pack-regression matrix cases**

In `scripts/verify/vibe-pack-regression-matrix.ps1`, append these rows near existing scholarly publishing, report, figure, and slide cases:

```powershell
    [pscustomobject]@{ Name = "publishing workflow package"; Prompt = "规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "scholarly-publishing"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing latex pipeline"; Prompt = "配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline"; AllowedModes = @("pack_overlay", "confirm_required") },
    [pscustomobject]@{ Name = "publishing venue template"; Prompt = "查 NeurIPS 模板和匿名投稿格式要求"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "venue-templates"; AllowedModes = @("pack_overlay", "confirm_required") },
```

Keep false-positive checks in the focused Python test because their expected owners are already covered by existing script probes.

- [ ] **Step 3: Run route probe scripts**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected:

```text
VCO Skill-Index Routing Audit: Failed: 0
VCO Pack Regression Matrix: Failed: 0
```

- [ ] **Step 4: Commit probe updates**

Run:

```powershell
git add scripts\verify\vibe-skill-index-routing-audit.ps1 scripts\verify\vibe-pack-regression-matrix.ps1
git commit -m "test: cover scholarly publishing routing boundaries"
```

Expected: commit succeeds.

## Task 5: Add Governance Note

**Files:**
- Create: `docs/governance/scholarly-publishing-pack-consolidation-2026-04-29.md`

- [ ] **Step 1: Create the governance note**

Use `apply_patch` to add this exact file:

````markdown
# Scholarly Publishing Pack Consolidation

Date: 2026-04-29

## Summary

This pass shrinks `scholarly-publishing-workflow` into a focused publishing and manuscript-delivery pack. It keeps submission workflow, rebuttal/checklist handling, reproducible manuscript engineering, LaTeX manuscript/PDF builds, scientific manuscript prose, venue templates, LaTeX posters, and paper-to-web/video/poster dissemination.

The six-stage Vibe runtime is unchanged, and skill usage remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 13 | 8 |
| `route_authority_candidates` | 0 | 8 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` is retained only as a compatibility mirror of `skill_candidates`. It is not a second execution model.

## Kept Publishing Owners

| User problem | Skill |
| --- | --- |
| End-to-end journal/conference publishing workflow and submission package planning | `scholarly-publishing` |
| Submission checklist, cover letter, rebuttal matrix, response-to-reviewers workflow | `submission-checklist` |
| Reproducible manuscript repository, version control, figure pipeline, CI build discipline | `manuscript-as-code` |
| LaTeX manuscript/PDF build, latexmk, chktex, latexindent, BibTeX/Biber, submission zip | `latex-submission-pipeline` |
| Scientific manuscript prose: IMRAD, abstract, methods, results, discussion | `scientific-writing` |
| Venue-specific templates, formatting requirements, anonymous submission, page limits | `venue-templates` |
| LaTeX poster or conference poster build | `latex-posters` |
| Paper-to-web, paper-to-video, paper-to-poster dissemination assets | `paper-2-web` |

## Moved Out Of Scholarly Publishing

| Skill | Action | Rationale |
| --- | --- | --- |
| `scientific-visualization` | Removed from `scholarly-publishing-workflow` routing surface | Result figures and publication plots belong to `science-figures-visualization`. |
| `scientific-schematics` | Removed from `scholarly-publishing-workflow` routing surface | Scientific diagrams and schematics belong to `science-figures-visualization`. |
| `slides-as-code` | Removed from `scholarly-publishing-workflow` routing surface | Slidev/Marp/Reveal/Quarto deck building belongs to `science-communication-slides`. |
| `scientific-slides` | Removed from `scholarly-publishing-workflow` routing surface | Scientific talks, seminar slides, and defense decks belong to `science-communication-slides`. |
| `citation-management` | Removed from `scholarly-publishing-workflow` routing surface | Citation formatting and BibTeX management belongs to `science-literature-citations`. |

## No Physical Deletion

No bundled skill directory is physically deleted in this pass. Moved-out skills remain available through their target packs.

## Protected Boundaries

| Prompt | Expected route |
| --- | --- |
| `规划一套期刊投稿工作流，包含投稿包、校样和 camera-ready` | `scholarly-publishing-workflow / scholarly-publishing` |
| `写 cover letter 和 response to reviewers rebuttal matrix` | `scholarly-publishing-workflow / submission-checklist` |
| `把论文仓库改成 manuscript-as-code，可复现构建 PDF` | `scholarly-publishing-workflow / manuscript-as-code` |
| `配置 latexmk/chktex/latexindent 编译论文 PDF 并打包 submission zip` | `scholarly-publishing-workflow / latex-submission-pipeline` |
| `请按 IMRAD 结构写科研论文正文` | `scholarly-publishing-workflow / scientific-writing` |
| `查 NeurIPS 模板和匿名投稿格式要求` | `scholarly-publishing-workflow / venue-templates` |
| `用 beamerposter 做会议学术海报` | `scholarly-publishing-workflow / latex-posters` |
| `把论文转换成 paper2web 项目主页和视频摘要` | `scholarly-publishing-workflow / paper-2-web` |
| `绘制机器学习模型评估结果图和投稿图` | `science-figures-visualization / scientific-visualization` |
| `画一个机制示意图和流程图` | `science-figures-visualization / scientific-schematics` |
| `用 Slidev 做组会汇报并导出 PDF` | `science-communication-slides / slides-as-code` |
| `顶级PPT制作：组会汇报 slide deck` | `science-communication-slides / scientific-slides` |
| `整理参考文献格式，修正 DOI，生成 Nature 格式 bibliography` | `science-literature-citations / citation-management` |
| `读取 PDF 并提取正文` | `docs-media / pdf` |
| `科研技术报告：包含方法结果讨论，输出 HTML 和 PDF` | `science-reporting / scientific-reporting` |

## Verification

Required checks:

```powershell
python -m pytest tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```
````

- [ ] **Step 2: Commit governance note**

Run:

```powershell
git add docs\governance\scholarly-publishing-pack-consolidation-2026-04-29.md
git commit -m "docs: record scholarly publishing boundary"
```

Expected: commit succeeds.

## Task 6: Run Full Verification And Final Status

**Files:**
- No additional source files expected.

- [ ] **Step 1: Run focused and broad checks**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scholarly_publishing_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```

Expected:

```text
test_scholarly_publishing_pack_consolidation.py: all tests pass
vibe-skill-index-routing-audit.ps1: Failed: 0
vibe-pack-regression-matrix.ps1: Failed: 0
vibe-pack-routing-smoke.ps1: Failed: 0
vibe-offline-skills-gate.ps1: PASS
vibe-config-parity-gate.ps1: PASS
git diff --check: no output
```

- [ ] **Step 2: Confirm no physical deletion occurred**

Run:

```powershell
git diff --name-status HEAD~3..HEAD
```

Expected: no `D` entries under `bundled/skills/`.

- [ ] **Step 3: Final status check**

Run:

```powershell
git status --short --branch
git log --oneline -8
```

Expected: worktree is clean. Recent commits include:

```text
docs: record scholarly publishing boundary
test: cover scholarly publishing routing boundaries
fix: consolidate scholarly publishing routing
```

No lockfile commit is expected unless a later implementation intentionally deletes or adds bundled skill directories.
