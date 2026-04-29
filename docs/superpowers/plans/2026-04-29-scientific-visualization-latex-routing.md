# Scientific Visualization And LaTeX Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make natural-language result-visualization prompts select `scientific-visualization` and natural-language LaTeX paper/PDF-build prompts select `latex-submission-pipeline`, while preserving `pdf` for existing-PDF operations.

**Architecture:** This is a routing-boundary patch. Add failing route/freeze regressions first, then adjust pack trigger keywords, skill keyword index entries, and skill routing rules. Do not add runtime forced-selection logic unless the regression proves configuration cannot express the intended boundary.

**Tech Stack:** Python `unittest` route tests, PowerShell runtime freeze probe, JSON routing config, existing Vibe pack smoke gates.

---

## Scope Check

This plan covers one subsystem: Vibe-Skills pack/candidate routing precision for scientific visualization and LaTeX paper PDF construction.

It does not:

- Change the six-stage Vibe runtime.
- Change `skill_routing.selected -> skill_usage.used / unused`.
- Add primary/secondary/stage-assistant concepts.
- Delete skill directories.
- Deploy to the installed Codex runtime.

## File Structure

- Create: `tests/runtime_neutral/test_scientific_visualization_latex_routing.py`
  - Owns route and freeze regressions for this boundary.
- Modify: `config/skill-keyword-index.json`
  - Adds natural-language synonyms for `scientific-visualization` and `latex-submission-pipeline`.
- Modify: `config/skill-routing-rules.json`
  - Adds positive keywords for the two intended owners and negative LaTeX-build boundaries for `pdf`.
- Modify: `config/pack-manifest.json`
  - Adds minimal pack trigger keywords if skill-level rules are not visible enough at pack selection time.
- Modify only if a regression proves it is necessary: `tests/runtime_neutral/test_router_bridge.py`
  - Add one broad bridge-level assertion only if the new dedicated test does not protect an existing bridge behavior.

## Task 1: Add Failing Route And Freeze Regressions

**Files:**
- Create: `tests/runtime_neutral/test_scientific_visualization_latex_routing.py`

- [ ] **Step 1: Create the regression test file**

Create `tests/runtime_neutral/test_scientific_visualization_latex_routing.py` with this content:

```python
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"


def route(prompt: str, task_type: str = "research", grade: str = "XL") -> dict[str, object]:
    return route_prompt(
        prompt=prompt,
        grade=grade,
        task_type=task_type,
        repo_root=REPO_ROOT,
    )


def selected_skill(result: dict[str, object]) -> str:
    selected = result.get("selected")
    assert isinstance(selected, dict), result
    return str(selected.get("skill") or "")


def selected_pack(result: dict[str, object]) -> str:
    selected = result.get("selected")
    assert isinstance(selected, dict), result
    return str(selected.get("pack_id") or "")


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


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def freeze_packet(task: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    with tempfile.TemporaryDirectory() as tempdir:
        artifact_root = Path(tempdir) / "artifacts"
        subprocess.run(
            [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(FREEZE_SCRIPT),
                "-Task",
                task,
                "-Mode",
                "interactive_governed",
                "-RunId",
                "pytest-scientific-visualization-latex-routing",
                "-ArtifactRoot",
                str(artifact_root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
        return json.loads(packet_path.read_text(encoding="utf-8"))


class ScientificVisualizationLatexRoutingTests(unittest.TestCase):
    def test_data_visualization_result_figures_route_to_scientific_visualization(self) -> None:
        result = route("对机器学习结果做数据可视化和结果图")

        self.assertEqual("science-figures-visualization", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_model_evaluation_result_figures_route_to_scientific_visualization(self) -> None:
        result = route("绘制模型评估结果图和投稿图")

        self.assertEqual("science-figures-visualization", selected_pack(result), ranked_summary(result))
        self.assertEqual("scientific-visualization", selected_skill(result), ranked_summary(result))

    def test_latex_paper_pdf_build_routes_to_latex_pipeline(self) -> None:
        result = route("用 LaTeX 写论文并构建 PDF")

        self.assertEqual("scholarly-publishing-workflow", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_latex_tooling_paper_build_routes_to_latex_pipeline(self) -> None:
        result = route("配置 latexmk/chktex/latexindent 编译论文 PDF", task_type="coding")

        self.assertEqual("scholarly-publishing-workflow", selected_pack(result), ranked_summary(result))
        self.assertEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_existing_pdf_extraction_still_routes_to_pdf(self) -> None:
        result = route("读取 PDF 并提取正文")

        self.assertEqual("docs-media", selected_pack(result), ranked_summary(result))
        self.assertEqual("pdf", selected_skill(result), ranked_summary(result))

    def test_generic_literature_review_does_not_route_to_latex_pipeline(self) -> None:
        result = route("普通文献综述和论文研究")

        self.assertNotEqual("latex-submission-pipeline", selected_skill(result), ranked_summary(result))

    def test_composite_research_freeze_selects_visualization_and_latex_build_skills(self) -> None:
        packet = freeze_packet(
            "我希望做一个完整研究项目：先做论文研究和文献综述，获取数据后训练机器学习模型，"
            "做数据可视化和结果图，最后用 LaTeX 写成论文 PDF。"
        )

        routing = packet["skill_routing"]
        selected = routing["selected"]
        assert isinstance(selected, list), routing
        selected_ids = {str(item["skill_id"]) for item in selected if isinstance(item, dict)}
        self.assertIn("scientific-visualization", selected_ids)
        self.assertIn("latex-submission-pipeline", selected_ids)
        self.assertNotIn("pdf", selected_ids)
```

- [ ] **Step 2: Run the new tests and confirm the expected failures**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
```

Expected: FAIL on at least these cases:

```text
对机器学习结果做数据可视化和结果图 -> currently scikit-learn
用 LaTeX 写论文并构建 PDF -> currently scholarly-publishing
composite freeze -> currently includes pdf/docs-write but not scientific-visualization/latex-submission-pipeline
```

- [ ] **Step 3: Commit the failing regression tests**

Run:

```powershell
git add tests/runtime_neutral/test_scientific_visualization_latex_routing.py
git commit -m "test: capture scientific visualization latex routing gaps"
```

## Task 2: Update Skill-Level Routing Keywords

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`
- Test: `tests/runtime_neutral/test_scientific_visualization_latex_routing.py`

- [ ] **Step 1: Add keyword-index synonyms**

Modify `config/skill-keyword-index.json`.

Add these strings to `skills.scientific-visualization.keywords`, preserving the existing keywords:

```json
[
  "data visualization",
  "result visualization",
  "result figure",
  "result figures",
  "analysis figure",
  "model result figure",
  "model evaluation plot",
  "evaluation result plot",
  "数据可视化",
  "结果图",
  "结果可视化",
  "可视化结果",
  "模型结果图",
  "模型评估图",
  "评估结果图"
]
```

Add these strings to `skills.latex-submission-pipeline.keywords`, preserving the existing keywords:

```json
[
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
  "论文 PDF",
  "PDF 构建",
  "生成论文 PDF",
  "编译论文",
  "论文编译",
  "构建可投稿 PDF",
  "可投稿 PDF"
]
```

- [ ] **Step 2: Add positive routing-rule keywords**

Modify `config/skill-routing-rules.json`.

Add these strings to `skills.scientific-visualization.positive_keywords`, preserving the existing positives:

```json
[
  "data visualization",
  "result visualization",
  "result figure",
  "result figures",
  "analysis figure",
  "model result figure",
  "model evaluation plot",
  "evaluation result plot",
  "数据可视化",
  "结果图",
  "结果可视化",
  "可视化结果",
  "模型结果图",
  "模型评估图",
  "评估结果图"
]
```

Add these strings to `skills.latex-submission-pipeline.positive_keywords`, preserving the existing positives:

```json
[
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
  "论文 PDF",
  "PDF 构建",
  "生成论文 PDF",
  "编译论文",
  "论文编译",
  "构建可投稿 PDF",
  "可投稿 PDF"
]
```

- [ ] **Step 3: Add `pdf` negative boundary terms**

Modify `config/skill-routing-rules.json`.

Add these strings to `skills.pdf.negative_keywords`, preserving the existing negatives:

```json
[
  "latex",
  "latexmk",
  "tex",
  "LaTeX 论文",
  "LaTeX 写论文",
  "论文 PDF",
  "PDF 构建",
  "生成论文 PDF",
  "编译论文",
  "论文编译",
  "compile latex",
  "build pdf",
  "paper build",
  "manuscript build"
]
```

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
```

Expected: some route tests may still fail if pack-level triggers hide the skill-level improvements. The PDF extraction test should still pass. Do not commit until Task 3 resolves remaining failures.

## Task 3: Update Pack-Level Triggers For The Two Boundaries

**Files:**
- Modify: `config/pack-manifest.json`
- Test: `tests/runtime_neutral/test_scientific_visualization_latex_routing.py`

- [ ] **Step 1: Add science figure pack trigger terms**

Modify `config/pack-manifest.json`.

Add these strings to the `science-figures-visualization.trigger_keywords` array, preserving existing triggers:

```json
[
  "data visualization",
  "result visualization",
  "result figure",
  "result figures",
  "analysis figure",
  "model result figure",
  "model evaluation plot",
  "数据可视化",
  "结果图",
  "结果可视化",
  "模型结果图",
  "模型评估图",
  "评估结果图"
]
```

- [ ] **Step 2: Add scholarly publishing LaTeX build trigger terms**

Modify `config/pack-manifest.json`.

Add these strings to the `scholarly-publishing-workflow.trigger_keywords` array, preserving existing triggers:

```json
[
  "latex paper",
  "latex manuscript",
  "latex pdf",
  "paper pdf build",
  "manuscript pdf build",
  "compile paper",
  "LaTeX 论文",
  "LaTeX 写论文",
  "论文 PDF",
  "PDF 构建",
  "生成论文 PDF",
  "编译论文",
  "论文编译",
  "可投稿 PDF"
]
```

- [ ] **Step 3: Run focused tests until the routing boundary passes**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
```

Expected: PASS.

If the composite freeze test still selects `pdf`, inspect the route result with:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\router\resolve-pack-route.ps1 -Prompt '我希望做一个完整研究项目：先做论文研究和文献综述，获取数据后训练机器学习模型，做数据可视化和结果图，最后用 LaTeX 写成论文 PDF。' -TaskType research -Grade L -Unattended
```

Then adjust only the three config surfaces named in this plan. Do not add runtime forced selection.

- [ ] **Step 4: Commit routing config changes**

Run:

```powershell
git add config/skill-keyword-index.json config/skill-routing-rules.json config/pack-manifest.json
git commit -m "fix: route figures and latex builds to precise skills"
```

## Task 4: Verify Router Bridges And Pack Gates

**Files:**
- Test-only task; no source changes expected.

- [ ] **Step 1: Run focused routing regression**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 2: Run existing router bridge and validation contracts**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_python_validation_contract.py -q
```

Expected: PASS.

- [ ] **Step 3: Run pack routing smoke**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected:

```text
Failed: 0
Pack routing smoke checks passed.
```

- [ ] **Step 4: Run config and offline gates**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
```

Expected: both PASS.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

## Task 5: Final Commit And Status Report

**Files:**
- Modify only if Task 4 exposes a missing validation target: `config/python-validation-targets.txt`
- Otherwise no file changes expected.

- [ ] **Step 1: Check git status**

Run:

```powershell
git status --short --branch
```

Expected: clean except the branch ahead count.

- [ ] **Step 2: Commit the regression tests**

If Task 1 committed the failing tests already, skip this step because the tests are already tracked. If the implementation was done without the Task 1 commit, run:

```powershell
git add tests/runtime_neutral/test_scientific_visualization_latex_routing.py
git commit -m "test: protect scientific visualization latex routing"
```

- [ ] **Step 3: Record final verification evidence**

Collect these exact outputs for the final report:

```powershell
git log -3 --oneline --decorate
git status --short --branch
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_python_validation_contract.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```

Expected: focused tests pass, router bridge tests pass, pack smoke has zero failures, offline skills and config parity gates pass, and worktree is clean.

## Implementation Notes

- Preserve existing keyword order where practical, append new keywords near related entries.
- Do not remove `pdf` from `docs-media`.
- Do not make `scientific-visualization` own generic EDA prompts without figure/result intent.
- Do not make `latex-submission-pipeline` own generic literature-review prompts.
- If a prompt says only `PDF` plus extraction/read/parse language, `pdf` remains the correct owner.
- A routed skill is not a used skill. Final reports must still distinguish selected routing from actual `skill_usage.used` evidence.

