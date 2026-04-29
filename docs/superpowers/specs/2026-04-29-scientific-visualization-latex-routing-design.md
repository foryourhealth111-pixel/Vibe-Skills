# Scientific Visualization And LaTeX Routing Design

Date: 2026-04-29

## 1. Goal

This design fixes two routing precision gaps in Vibe-Skills without changing the public six-stage Vibe runtime or the simplified skill usage model.

Target behavior:

```text
data visualization / result figures -> scientific-visualization
LaTeX paper / PDF build -> latex-submission-pipeline
PDF extraction / PDF reading -> pdf
general writing / documentation -> docs-write or scientific-writing as appropriate
```

The fix must preserve the current authority model:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

## 2. Problem

A compound research prompt such as:

```text
Do literature research, train a machine-learning model, create result visualizations, and write a LaTeX/PDF paper.
```

currently can select useful skills such as `research-lookup`, `scikit-learn`, `pdf`, and `docs-write`, but it does not reliably select:

```text
scientific-visualization
latex-submission-pipeline
```

This creates two incorrect ownership boundaries:

| User intent | Current likely owner | Desired owner |
| --- | --- | --- |
| Data visualization, result figures, model result plots | `data-ml` / `scikit-learn` or broad research routing | `science-figures-visualization` / `scientific-visualization` |
| LaTeX paper PDF build | `scholarly-publishing` or `pdf` | `latex-submission-pipeline` |
| Read or extract an existing PDF | `pdf` | `pdf` |

The issue is routing precision, not the simplified execution model.

## 3. Root Cause

The current keyword surfaces are too narrow or too broad in specific places.

### Visualization Gap

`scientific-visualization` already routes correctly for strong publication-figure prompts such as:

```text
publication figure
multi-panel
600dpi
投稿图
科研绘图
```

It is weaker for common natural-language prompts such as:

```text
数据可视化
结果图
结果可视化
模型结果图
可视化结果
analysis figure
result figure
model evaluation plot
```

Because those terms are missing or underweighted, the prompt can fall back to `data-ml` or `research-design`.

### LaTeX/PDF Build Gap

`latex-submission-pipeline` already routes correctly for tool-explicit prompts such as:

```text
latexmk
chktex
latexindent
compile latex
pdflatex
```

It is weaker for user-facing wording such as:

```text
LaTeX 论文
LaTeX 写论文
论文 PDF
PDF 构建
生成论文 PDF
构建可投稿 PDF
latex pdf
```

When the prompt contains `PDF` but not explicit build-tool terms, generic `pdf` or `scholarly-publishing` can win.

### Boundary Gap

The `pdf` skill should own existing-PDF operations:

```text
read PDF
extract PDF text
split / merge / parse / render PDF
```

It should not own LaTeX source compilation or paper build workflows. Those belong to `latex-submission-pipeline`.

## 4. Approved Approach

Use a narrow routing boundary patch:

1. Add natural-language visualization keywords to `scientific-visualization`.
2. Add natural-language LaTeX paper build keywords to `latex-submission-pipeline`.
3. Add negative boundary keywords to `pdf` so it does not steal LaTeX build prompts.
4. Add regression tests that prove the intended routing and protect unaffected PDF extraction behavior.

Rejected alternatives:

| Option | Reason rejected |
| --- | --- |
| Only add keywords | Too weak; `pdf` and broad research packs can still steal ambiguous prompts. |
| Add runtime forced-selection logic in freeze | Works but makes the simplified routing model more complex. |
| Change the six-stage runtime | Unnecessary; this is a pack and candidate-selection precision problem. |

## 5. Routing Contract

After the fix, these prompts should route as follows.

### Visualization

| Prompt class | Expected selected skill |
| --- | --- |
| `对机器学习结果做数据可视化和结果图` | `scientific-visualization` |
| `绘制模型评估结果图和投稿图` | `scientific-visualization` |
| `create result figures for model evaluation` | `scientific-visualization` |
| `publication figure multi-panel 600dpi` | `scientific-visualization` |

### LaTeX Build

| Prompt class | Expected selected skill |
| --- | --- |
| `用 LaTeX 写论文并构建 PDF` | `latex-submission-pipeline` |
| `把论文编译成可投稿 PDF` | `latex-submission-pipeline` |
| `configure latexmk chktex latexindent for paper build` | `latex-submission-pipeline` |
| `LaTeX 论文 PDF 构建` | `latex-submission-pipeline` |

### Preserved Behavior

| Prompt class | Expected selected skill |
| --- | --- |
| `读取 PDF 并提取正文` | `pdf` |
| `extract tables from a PDF` | `pdf` |
| `普通文献综述和论文研究` | not `latex-submission-pipeline` unless LaTeX/PDF build is present |

## 6. Configuration Changes

The implementation should update only the routing configuration and route regression tests unless a failing test proves a code path is insufficient.

Expected config surfaces:

```text
config/skill-keyword-index.json
config/skill-routing-rules.json
config/pack-manifest.json
```

`skill-keyword-index.json` should add natural-language synonyms for:

```text
scientific-visualization:
  数据可视化
  结果图
  结果可视化
  模型结果图
  评估结果图
  result figure
  result visualization
  model evaluation plot

latex-submission-pipeline:
  LaTeX 论文
  LaTeX 写论文
  论文 PDF
  PDF 构建
  生成论文 PDF
  编译论文
  可投稿 PDF
  latex pdf
```

`skill-routing-rules.json` should add matching positive keywords and add `pdf` negative keywords for LaTeX build language:

```text
latex
latexmk
tex
论文 PDF
PDF 构建
生成论文 PDF
compile latex
build pdf
paper build
```

`pack-manifest.json` may need trigger keyword additions if route probes show the correct skill-level rules are still hidden by pack-level selection. Any manifest change should be minimal and focused on these two boundaries.

## 7. Tests And Gates

Add focused regression coverage before relying on the fix.

Preferred test location:

```text
tests/runtime_neutral/test_scientific_visualization_latex_routing.py
```

The tests should call the existing router path or the smallest existing route helper used by nearby router tests. They should assert selected skill behavior, not only pack score changes.

Required regression cases:

```text
对机器学习结果做数据可视化和结果图 -> scientific-visualization
绘制模型评估结果图和投稿图 -> scientific-visualization
用 LaTeX 写论文并构建 PDF -> latex-submission-pipeline
配置 latexmk/chktex/latexindent 编译论文 PDF -> latex-submission-pipeline
读取 PDF 并提取正文 -> pdf
普通文献综述和论文研究 -> not latex-submission-pipeline
```

Post-change verification should include:

```powershell
python -m pytest tests/runtime_neutral/test_scientific_visualization_latex_routing.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_python_validation_contract.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
```

If config parity or lock files are affected, also run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## 8. Non-Goals

This fix does not:

- Change the six-stage Vibe runtime.
- Add a new primary/secondary/stage-assistant model.
- Force every research task to select visualization or LaTeX skills.
- Treat routed skills as actually used.
- Delete or rename skill directories.
- Deploy the source checkout into Codex.

Actual usage still depends on execution evidence in `skill_usage.used / unused`.

## 9. Acceptance Criteria

The implementation is accepted when:

- Natural-language visualization prompts select `scientific-visualization`.
- Natural-language LaTeX paper/PDF build prompts select `latex-submission-pipeline`.
- Existing-PDF extraction prompts still select `pdf`.
- Generic literature-review prompts do not incorrectly select `latex-submission-pipeline`.
- Composite research prompts include the visualization and LaTeX build skills when those sub-intents are explicit.
- Route tests and pack smoke verification pass on `main`.

