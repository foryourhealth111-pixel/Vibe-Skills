# Research Design Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `research-design` routing boundaries while keeping the current 9 route owners and removing stale cross-skill/helper language.

**Architecture:** This is a routing-contract cleanup, not a runtime redesign. The implementation changes focused route tests first, then updates retained `SKILL.md` wording and keyword/routing JSON, then records governance evidence and runs the existing verification gates.

**Tech Stack:** Python `unittest`/`pytest`, PowerShell verification scripts, JSON routing config, Markdown skill/governance docs.

---

## File Structure

Modify these files:

- `tests/runtime_neutral/test_research_design_pack_consolidation.py`: focused red/green regression tests for the second-pass boundaries and stale cross-skill language.
- `bundled/skills/designing-experiments/SKILL.md`: clarify design-before-analysis ownership.
- `bundled/skills/performing-causal-analysis/SKILL.md`: clarify existing-data causal estimation ownership.
- `bundled/skills/hypothesis-generation/SKILL.md`: remove mandatory `scientific-schematics` and `venue-templates` cross-skill language; clarify hypothesis boundary.
- `bundled/skills/scientific-brainstorming/SKILL.md`: remove consultation-style wording and clarify open-ended ideation boundary.
- `bundled/skills/hypogenic/SKILL.md`: clarify explicit HypoGeniC/automated workflow boundary.
- `bundled/skills/literature-matrix/SKILL.md`: clarify matrix/A+B boundary and not-for literature lookup/writing.
- `bundled/skills/research-grants/SKILL.md`: remove mandatory `scientific-schematics` cross-skill language; keep grant visuals as optional in-skill outputs.
- `config/skill-keyword-index.json`: add narrow positive keywords for the new route boundaries.
- `config/skill-routing-rules.json`: add matching positives/negatives to prevent internal collisions.
- `scripts/verify/vibe-skill-index-routing-audit.ps1`: add skill-level audit cases for new boundary prompts.
- `scripts/verify/vibe-pack-regression-matrix.ps1`: add pack-level regression cases for new boundary prompts.
- `scripts/verify/probe-scientific-packs.ps1`: add scientific probe cases for `research-design` second-pass boundaries.
- `docs/governance/research-design-boundary-hardening-2026-04-30.md`: governance note with before/after counts and verification evidence.
- `config/skills-lock.json`: modify only if the existing lock-generation script changes it after skill-file edits.

Do not modify:

- `config/pack-manifest.json`, unless verification reveals drift. The expected 9/9/0 counts already match the approved design.
- Any physical skill directory deletion.
- Six-stage runtime code.

---

### Task 1: Add Failing Boundary And Content Tests

**Files:**
- Modify: `tests/runtime_neutral/test_research_design_pack_consolidation.py`

- [ ] **Step 1: Add a helper for reading retained skill files**

Insert this helper after `pack_by_id()`:

```python
def skill_text(skill_id: str) -> str:
    skill_path = REPO_ROOT / "bundled" / "skills" / skill_id / "SKILL.md"
    return skill_path.read_text(encoding="utf-8-sig")
```

- [ ] **Step 2: Add second-pass content and route tests**

Add these methods inside `ResearchDesignPackConsolidationTests` after `test_research_design_manifest_is_research_methods_only`:

```python
    def test_retained_skills_do_not_require_cross_skill_invocation(self) -> None:
        banned_by_skill = {
            "hypothesis-generation": [
                "scientific-schematics",
                "venue-templates",
                "Related Skills",
            ],
            "research-grants": [
                "scientific-schematics",
                "MANDATORY: Every research grant proposal MUST include",
            ],
            "scientific-brainstorming": [
                "can be consulted",
                "Consult this file",
            ],
        }
        for skill_id, banned_phrases in banned_by_skill.items():
            text = skill_text(skill_id)
            for phrase in banned_phrases:
                self.assertNotIn(phrase, text, f"{skill_id} still contains {phrase!r}")

    def test_design_without_modeling_routes_to_designing_experiments(self) -> None:
        self.assert_selected(
            "帮我设计准实验方案，先决定 DiD 还是中断时间序列，不要开始建模",
            "research-design",
            "designing-experiments",
            task_type="planning",
        )

    def test_existing_data_causal_effect_routes_to_causal_analysis(self) -> None:
        self.assert_selected(
            "我已有面板数据，请用 DiD 估计政策的因果效应并做稳健性检验",
            "research-design",
            "performing-causal-analysis",
            task_type="research",
        )

    def test_plain_hypothesis_generation_without_hypogenic_routes_to_hypothesis_generation(self) -> None:
        self.assert_selected(
            "普通科研假设生成，没有提 HypoGeniC",
            "research-design",
            "hypothesis-generation",
            task_type="planning",
        )

    def test_open_scientific_ideation_routes_to_scientific_brainstorming(self) -> None:
        self.assert_selected(
            "开放式科研构思：围绕这个机制发散研究方向，不要求形成可检验假设报告",
            "research-design",
            "scientific-brainstorming",
            task_type="planning",
        )

    def test_latex_paper_build_stays_outside_research_design(self) -> None:
        self.assert_selected(
            "论文撰写、LaTeX 构建或 PDF 投稿",
            "scholarly-publishing-workflow",
            "latex-submission-pipeline",
            task_type="coding",
        )
```

- [ ] **Step 3: Run the focused test and confirm it fails for the intended reasons**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q
```

Expected before implementation:

```text
FAILED ... test_retained_skills_do_not_require_cross_skill_invocation
```

The open-ideation route test may also fail before keyword tuning because the current prompt can be pulled toward publishing/writing. Keep both failures; they define the work.

- [ ] **Step 4: Commit the failing tests**

```powershell
git add tests/runtime_neutral/test_research_design_pack_consolidation.py
git commit -m "test: add research design boundary hardening coverage"
```

---

### Task 2: Clean Retained Skill Wording

**Files:**
- Modify: `bundled/skills/designing-experiments/SKILL.md`
- Modify: `bundled/skills/performing-causal-analysis/SKILL.md`
- Modify: `bundled/skills/hypothesis-generation/SKILL.md`
- Modify: `bundled/skills/scientific-brainstorming/SKILL.md`
- Modify: `bundled/skills/hypogenic/SKILL.md`
- Modify: `bundled/skills/literature-matrix/SKILL.md`
- Modify: `bundled/skills/research-grants/SKILL.md`

- [ ] **Step 1: Replace `designing-experiments` front matter and overview**

Use this front matter and opening section:

```markdown
---
name: designing-experiments
description: Design experiments and quasi-experiments before analysis. Use when choosing study design, treatment/control structure, outcomes, assumptions, or which of DiD, ITS, synthetic control, or regression discontinuity fits the research question. For fitting models or estimating effects on existing data, use performing-causal-analysis instead.
---

# Designing Experiments

Helps choose and specify a research design before data analysis starts. This skill owns study-design decisions: what is treated, what is compared, what outcome is measured, which assumptions are required, and which design is defensible.

It does not fit causal models, estimate treatment effects, or interpret fitted model output from existing data.
```

Keep the existing decision framework after this opening section unless wording conflicts with the new boundary.

- [ ] **Step 2: Replace `performing-causal-analysis` front matter and overview**

Use this front matter and opening section:

```markdown
---
name: performing-causal-analysis
description: Estimate causal effects from existing data. Use when fitting or interpreting DiD, ITS, synthetic control, regression discontinuity, or other treatment-effect analyses, including robustness checks and counterfactual plots. For choosing a study design before analysis, use designing-experiments instead.
---

# Performing Causal Analysis

Executes causal analysis on existing data. This skill owns model setup, treatment-effect estimation, counterfactual comparison, robustness checks, and interpretation of fitted causal results.

It does not own the earlier question of which experiment or quasi-experiment should be designed before analysis begins.
```

Keep the existing CausalPy workflow and references after this opening section.

- [ ] **Step 3: Replace the visual section in `hypothesis-generation`**

Delete the entire `## Visual Enhancement with Scientific Schematics` section from `hypothesis-generation/SKILL.md`, including the closing `---` before `## Workflow`.

Insert this section in its place:

```markdown
## Outputs

Produce a structured hypothesis report when useful:

- Core observation or anomaly to explain
- Competing mechanistic hypotheses
- Testable predictions for each hypothesis
- Minimal validation experiments or studies
- Decision criteria for supporting, revising, or rejecting each hypothesis

Figures or diagrams may be included when they clarify the hypothesis structure, but this skill does not require a second skill or helper expert to create them.

---
```

- [ ] **Step 4: Remove the cross-skill publication section from `hypothesis-generation`**

Delete this section near the end:

```markdown
### Related Skills

When preparing hypothesis-driven research for publication, consult the **venue-templates** skill for writing style guidance:
- `venue_writing_styles.md` - Master guide comparing styles across venues
- Venue-specific guides for Nature/Science, Cell Press, medical journals, and ML/CS conferences
- `reviewer_expectations.md` - What reviewers look for when evaluating research hypotheses
```

If the surrounding heading becomes empty, remove the empty heading too.

- [ ] **Step 5: Replace the visual section in `research-grants`**

Delete the entire `## Visual Enhancement with Scientific Schematics` section from `research-grants/SKILL.md`, including the closing `---` before `## Agency-Specific Overview`.

Insert this section in its place:

```markdown
## Proposal Outputs

Grant proposals often benefit from clear visual elements, but visuals are outputs of the grant-writing task rather than a required secondary skill route.

Use visuals when they strengthen the proposal:

- Research workflow or methodology diagram
- Project timeline or milestone chart
- Conceptual framework
- Preliminary data figure plan
- Collaboration structure
- Broader impacts activity map

Do not require a separate helper expert before the grant proposal can be considered complete.

---
```

Keep legitimate grant-budget terms such as `consulting`, `consultant roles`, and `program officers`; those are proposal content, not route-helper language.

- [ ] **Step 6: Update `scientific-brainstorming` description and consultation wording**

Replace the front matter description with:

```yaml
description: "Open-ended scientific ideation partner. Use for research gaps, mechanism exploration, interdisciplinary connections, assumptions, and possible research directions. For structured testable hypotheses and validation plans, use hypothesis-generation instead."
```

Replace:

```markdown
- Consult references/brainstorming_methods.md for additional structured techniques
```

with:

```markdown
- Use `references/brainstorming_methods.md` when the session needs a named structured technique
```

Replace:

```markdown
Contains detailed descriptions of structured brainstorming methodologies that can be consulted when standard techniques need supplementation:
```

with:

```markdown
Contains detailed descriptions of structured brainstorming methodologies for sessions that need a named method:
```

Replace:

```markdown
Consult this file when the scientist requests a specific methodology or when the brainstorming session would benefit from a more structured approach.
```

with:

```markdown
Use this file when the scientist requests a specific methodology or when the brainstorming session would benefit from a more structured approach.
```

- [ ] **Step 7: Update `hypogenic` description boundary**

Replace the front matter description with:

```yaml
description: Automated HypoGeniC-style hypothesis generation and testing using large language models. Use when the user explicitly asks for HypoGeniC, automated hypothesis generation/testing, LLM hypothesis discovery, or systematic hypothesis exploration against datasets. For ordinary scientific hypothesis formulation, use hypothesis-generation instead.
```

- [ ] **Step 8: Update `literature-matrix` boundaries**

In `literature-matrix/SKILL.md`, add these bullets under `## Not For / Boundaries`:

```markdown
- General PubMed, Semantic Scholar, or citation lookup without a matrix/composition goal
- Manuscript writing, LaTeX build, PDF construction, or submission packaging
- Ordinary hypothesis generation from one observation or dataset
```

- [ ] **Step 9: Run the content scan tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py::ResearchDesignPackConsolidationTests::test_retained_skills_do_not_require_cross_skill_invocation -q
```

Expected:

```text
1 passed
```

- [ ] **Step 10: Commit skill wording cleanup**

```powershell
git add bundled/skills/designing-experiments/SKILL.md bundled/skills/performing-causal-analysis/SKILL.md bundled/skills/hypothesis-generation/SKILL.md bundled/skills/scientific-brainstorming/SKILL.md bundled/skills/hypogenic/SKILL.md bundled/skills/literature-matrix/SKILL.md bundled/skills/research-grants/SKILL.md
git commit -m "fix: clarify research design skill boundaries"
```

---

### Task 3: Tighten Routing Keywords

**Files:**
- Modify: `config/skill-keyword-index.json`
- Modify: `config/skill-routing-rules.json`

- [ ] **Step 1: Update `skill-keyword-index.json` for boundary positives**

Add these strings to each skill's `keywords` array if absent:

```json
{
  "designing-experiments": [
    "study design",
    "design before analysis",
    "choose research design",
    "design quasi-experiment",
    "设计准实验方案",
    "选择研究设计",
    "先决定",
    "不要开始建模"
  ],
  "performing-causal-analysis": [
    "existing data",
    "estimate causal effect",
    "estimate treatment effect",
    "robustness check",
    "panel data",
    "已有数据",
    "已有面板数据",
    "估计政策",
    "因果效应",
    "稳健性检验"
  ],
  "hypothesis-generation": [
    "ordinary hypothesis generation",
    "plain hypothesis generation",
    "普通科研假设生成",
    "没有提 HypoGeniC"
  ],
  "scientific-brainstorming": [
    "open-ended scientific ideation",
    "open research ideation",
    "divergent research directions",
    "开放式科研构思",
    "发散研究方向",
    "不要求形成可检验假设报告"
  ],
  "hypogenic": [
    "HypoGeniC",
    "HypoRefine"
  ],
  "literature-matrix": [
    "literature matrix",
    "A+B innovation",
    "论文组合矩阵",
    "A+B 创新点"
  ],
  "research-grants": [
    "Specific Aims",
    "NIH proposal",
    "grant review criteria",
    "科研基金申请书"
  ]
}
```

Preserve existing keyword order as much as practical. Do not remove existing keywords unless a later test proves a false positive.

- [ ] **Step 2: Update `skill-routing-rules.json` positives and negatives**

Mirror the positive additions above into each skill's `positive_keywords`.

Then add these negative keywords:

```json
{
  "designing-experiments": [
    "existing data",
    "estimate causal effect",
    "estimate treatment effect",
    "robustness check",
    "已有数据",
    "已有面板数据",
    "估计",
    "稳健性检验"
  ],
  "performing-causal-analysis": [
    "design before analysis",
    "choose research design",
    "不要开始建模",
    "只是设计实验方案",
    "先决定"
  ],
  "hypothesis-generation": [
    "hypogenic",
    "HypoGeniC",
    "automated hypothesis generation",
    "自动假设生成",
    "开放式科研构思",
    "科研头脑风暴",
    "literature matrix",
    "论文组合矩阵",
    "文献矩阵"
  ],
  "scientific-brainstorming": [
    "testable hypothesis report",
    "validation experiment",
    "可检验假设报告",
    "验证实验",
    "hypogenic",
    "HypoGeniC",
    "literature matrix",
    "论文组合矩阵"
  ],
  "hypogenic": [
    "ordinary hypothesis generation",
    "plain hypothesis generation",
    "普通科研假设生成",
    "没有提 HypoGeniC"
  ],
  "literature-matrix": [
    "pubmed",
    "bibtex",
    "latex",
    "pdf submission",
    "普通科研假设生成"
  ],
  "research-grants": [
    "latex",
    "pdf submission",
    "bibtex",
    "pubmed",
    "ordinary research plan"
  ]
}
```

Keep `stage_assistant_candidates` unchanged and empty.

- [ ] **Step 3: Run route tests after keyword changes**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 4: Verify manifest counts stayed unchanged**

Run:

```powershell
@'
import json
from pathlib import Path
p = Path("config/pack-manifest.json")
manifest = json.loads(p.read_text(encoding="utf-8-sig"))
pack = next(row for row in manifest["packs"] if row["id"] == "research-design")
print(len(pack["skill_candidates"]), len(pack["route_authority_candidates"]), len(pack["stage_assistant_candidates"]))
print(pack["skill_candidates"])
'@ | python -
```

Expected:

```text
9 9 0
['designing-experiments', 'experiment-failure-analysis', 'hypogenic', 'hypothesis-generation', 'literature-matrix', 'performing-causal-analysis', 'performing-regression-analysis', 'research-grants', 'scientific-brainstorming']
```

- [ ] **Step 5: Commit routing config changes**

```powershell
git add config/skill-keyword-index.json config/skill-routing-rules.json tests/runtime_neutral/test_research_design_pack_consolidation.py
git commit -m "fix: harden research design route boundaries"
```

---

### Task 4: Extend Route Probe Scripts

**Files:**
- Modify: `scripts/verify/vibe-skill-index-routing-audit.ps1`
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Modify: `scripts/verify/probe-scientific-packs.ps1`

- [ ] **Step 1: Add skill-level route audit cases**

In `scripts/verify/vibe-skill-index-routing-audit.ps1`, add these cases near the existing `research-design` cases:

```powershell
[pscustomobject]@{ Name = "experiment design no modeling"; Prompt = "帮我设计准实验方案，先决定 DiD 还是中断时间序列，不要开始建模"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "designing-experiments" },
[pscustomobject]@{ Name = "existing data causal effect"; Prompt = "我已有面板数据，请用 DiD 估计政策的因果效应并做稳健性检验"; Grade = "L"; TaskType = "research"; ExpectedPack = "research-design"; ExpectedSkill = "performing-causal-analysis" },
[pscustomobject]@{ Name = "plain hypothesis not hypogenic"; Prompt = "普通科研假设生成，没有提 HypoGeniC"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "hypothesis-generation" },
[pscustomobject]@{ Name = "open scientific ideation"; Prompt = "开放式科研构思：围绕这个机制发散研究方向，不要求形成可检验假设报告"; Grade = "L"; TaskType = "planning"; ExpectedPack = "research-design"; ExpectedSkill = "scientific-brainstorming" },
[pscustomobject]@{ Name = "latex paper build outside research design"; Prompt = "论文撰写、LaTeX 构建或 PDF 投稿"; Grade = "L"; TaskType = "coding"; ExpectedPack = "scholarly-publishing-workflow"; ExpectedSkill = "latex-submission-pipeline" },
```

- [ ] **Step 2: Add pack-level regression cases**

In `scripts/verify/vibe-pack-regression-matrix.ps1`, add these cases near the existing `research-design` rows:

```powershell
[pscustomobject]@{ Name = "research-design no-modeling design"; Prompt = "帮我设计准实验方案，先决定 DiD 还是中断时间序列，不要开始建模"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "research-design existing-data causal"; Prompt = "我已有面板数据，请用 DiD 估计政策的因果效应并做稳健性检验"; Grade = "L"; TaskType = "research"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "research-design open ideation"; Prompt = "开放式科研构思：围绕这个机制发散研究方向，不要求形成可检验假设报告"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "research-design"; AllowedModes = @("pack_overlay", "confirm_required") },
[pscustomobject]@{ Name = "scholarly latex not research design"; Prompt = "论文撰写、LaTeX 构建或 PDF 投稿"; Grade = "L"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "scholarly-publishing-workflow"; AllowedModes = @("pack_overlay", "confirm_required") },
```

- [ ] **Step 3: Add scientific probe cases**

In `scripts/verify/probe-scientific-packs.ps1`, add these objects after the current `research-design extensions` block:

```powershell
[pscustomobject]@{
    name = "research_design_no_modeling_design"
    group = "research-design"
    prompt = "/vibe 帮我设计准实验方案，先决定 DiD 还是中断时间序列，不要开始建模"
    grade = "L"
    task_type = "planning"
    expected_pack = "research-design"
    expected_skill = "designing-experiments"
    requested_skill = $null
},
[pscustomobject]@{
    name = "research_existing_data_causal_effect"
    group = "research-design"
    prompt = "/vibe 我已有面板数据，请用 DiD 估计政策的因果效应并做稳健性检验"
    grade = "L"
    task_type = "research"
    expected_pack = "research-design"
    expected_skill = "performing-causal-analysis"
    requested_skill = $null
},
[pscustomobject]@{
    name = "research_open_scientific_ideation"
    group = "research-design"
    prompt = "/vibe 开放式科研构思：围绕这个机制发散研究方向，不要求形成可检验假设报告"
    grade = "L"
    task_type = "planning"
    expected_pack = "research-design"
    expected_skill = "scientific-brainstorming"
    requested_skill = $null
}
```

- [ ] **Step 4: Run the route probes**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1
```

Expected:

```text
all added research-design cases pass
no bad route count increase
```

If `probe-scientific-packs.ps1` reports a pre-existing unrelated failure, capture the exact failing case and do not hide it in the governance note.

- [ ] **Step 5: Commit probe updates**

```powershell
git add scripts/verify/vibe-skill-index-routing-audit.ps1 scripts/verify/vibe-pack-regression-matrix.ps1 scripts/verify/probe-scientific-packs.ps1
git commit -m "test: extend research design route probes"
```

---

### Task 5: Write Governance Note

**Files:**
- Create: `docs/governance/research-design-boundary-hardening-2026-04-30.md`

- [ ] **Step 1: Create the governance note**

Create the file with this content, filling only the verification status lines after running the commands in Task 6:

```markdown
# Research Design Boundary Hardening

Date: 2026-04-30

## Summary

This pass hardens the already-pruned `research-design` pack. It keeps all 9 retained research-method owners, removes stale cross-skill/helper language, and protects the internal boundaries with focused route probes.

The six-stage runtime is unchanged. Skill usage remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

No advisory state, stage assistant state, primary/secondary hierarchy, or helper-expert dispatch was added.

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 9 | 9 |
| `route_authority_candidates` | 9 | 9 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

## Retained Owners

| Skill | Boundary |
| --- | --- |
| `designing-experiments` | Study-design choice and experiment/quasi-experiment specification before analysis |
| `performing-causal-analysis` | Existing-data causal effect estimation, robustness checks, and fitted-result interpretation |
| `performing-regression-analysis` | Regression modeling, diagnostics, coefficient interpretation, and residual analysis |
| `hypothesis-generation` | Testable hypotheses, predictions, mechanisms, and validation experiments from observations |
| `scientific-brainstorming` | Open-ended research ideation, gaps, mechanisms, and possible directions |
| `hypogenic` | Explicit HypoGeniC or automated LLM hypothesis generation/testing workflows |
| `literature-matrix` | Literature matrix, paper-combination, A+B idea generation, and unified frameworks |
| `experiment-failure-analysis` | Failed experiment diagnosis and recovery/abandonment decisions |
| `research-grants` | Grant aims, significance, innovation, budgets, and review logic |

## Removed Cross-Skill Language

| Skill | Cleanup |
| --- | --- |
| `hypothesis-generation` | Removed mandatory `scientific-schematics` and `venue-templates` cross-skill language |
| `research-grants` | Removed mandatory `scientific-schematics` cross-skill language |
| `scientific-brainstorming` | Reworded consultation-style references as local reference usage |

## Protected Route Boundaries

| Prompt type | Expected owner |
| --- | --- |
| Design quasi-experiment and do not model yet | `designing-experiments` |
| Existing panel data causal effect estimation | `performing-causal-analysis` |
| Plain hypothesis generation without HypoGeniC | `hypothesis-generation` |
| Open-ended scientific ideation | `scientific-brainstorming` |
| Explicit HypoGeniC workflow | `hypogenic` |
| Literature matrix / A+B innovation | `literature-matrix` |
| LaTeX/PDF paper build | `scholarly-publishing-workflow / latex-submission-pipeline`, not `research-design` |

## Verification

Record final command outcomes here during implementation:

```text
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```

## Remaining Caveat

Route selection is not proof of material skill use. This pass only makes selection clearer and removes stale helper semantics.
```

- [ ] **Step 2: Commit the draft governance note after final verification text is filled**

Do not commit the command list as final evidence. After Task 6, replace it with pass/fail statuses and then run:

```powershell
git add docs/governance/research-design-boundary-hardening-2026-04-30.md
git commit -m "docs: record research design boundary hardening"
```

---

### Task 6: Regenerate Lock If Needed And Verify

**Files:**
- Modify: `config/skills-lock.json` only if generated by the repo script.

- [ ] **Step 1: Check whether skill-file edits changed lock expectations**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected:

```text
PASS
```

If the gate reports stale `skills-lock.json`, run the existing generator:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
```

Then add the generated lockfile:

```powershell
git add config/skills-lock.json
git commit -m "chore: refresh skills lock after research design cleanup"
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: Run routing probes**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\probe-scientific-packs.ps1
```

Expected:

```text
all research-design boundary cases pass
```

- [ ] **Step 4: Run integrity gates**

Run:

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1
git diff --check
```

Expected:

```text
all gates pass
git diff --check emits no output
```

- [ ] **Step 5: Fill governance verification results**

Update `docs/governance/research-design-boundary-hardening-2026-04-30.md` with the actual command outcomes. Use this format:

```markdown
## Verification

| Command | Result |
| --- | --- |
| `python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q` | PASS, exact pytest count from command output |
| `powershell ... vibe-skill-index-routing-audit.ps1` | PASS |
| `powershell ... vibe-pack-regression-matrix.ps1` | PASS |
| `powershell ... probe-scientific-packs.ps1` | PASS, bad=0 or exact reported count |
| `powershell ... vibe-offline-skills-gate.ps1` | PASS |
| `powershell ... vibe-config-parity-gate.ps1` | PASS |
| `git diff --check` | PASS |
```

If a command fails for an unrelated pre-existing reason, write `FAIL` and the exact failure; do not mark it as passed.

- [ ] **Step 6: Commit final governance verification update**

```powershell
git add docs/governance/research-design-boundary-hardening-2026-04-30.md
git commit -m "docs: record research design boundary verification"
```

---

### Task 7: Final Review And Report

**Files:**
- No new files unless a verification artifact is intentionally produced by an existing gate.

- [ ] **Step 1: Inspect final diff since the design commit**

Run:

```powershell
git status --short --branch
git log --oneline -6
```

Expected:

```text
working tree clean, or only intentional generated artifacts already explained
recent commits include tests, skill wording, route config/probes, governance
```

- [ ] **Step 2: Summarize before/after state**

Prepare the final report with:

```text
branch: main
commits: list the new commit hashes produced during implementation
research-design counts: 9 skill_candidates / 9 route_authority_candidates / 0 stage_assistant_candidates
physical deletion: none
cross-skill helper language: removed from retained skills
route boundary evidence: focused pytest + routing probes
remaining caveat: route selection is not proof of material skill use
```

- [ ] **Step 3: Do not claim broader pack cleanup**

The final report must not say that all remaining packs are fixed. This plan only completes `research-design` boundary hardening.
