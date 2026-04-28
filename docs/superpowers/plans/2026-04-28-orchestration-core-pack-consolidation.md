# Orchestration-Core Pack Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shrink `orchestration-core` into a problem-first routing surface where planning, brainstorming, explicit spec-kit compatibility, and explicit subagent work have clear boundaries.

**Architecture:** This change is a routing/config consolidation with one small router guard. The guard lets a skill opt out of fallback selection unless the prompt has one of its positive keywords, which prevents `subagent-driven-development` from winning ordinary coding/debug prompts by default. The canonical `vibe` runtime entry stays unchanged.

**Tech Stack:** JSON routing config, PowerShell router modules and gates, Python runtime router parity code, pytest runtime-neutral/unit tests, Markdown governance docs.

---

## File Structure

- Modify: `config/pack-manifest.json`
  - Shrinks `orchestration-core.skill_candidates`.
  - Keeps only problem-owning route authorities and a small stage assistant set.
  - Removes coding/debug/review defaults that point to `subagent-driven-development`.
- Modify: `config/skill-routing-rules.json`
  - Adds `requires_positive_keyword_match` to guarded route authorities.
  - Removes `subagent-driven-development` as canonical for generic coding.
  - Adds a guarded rule for `/speckit.*` compatibility routing.
- Modify: `config/skill-keyword-index.json`
  - Tightens `subagent-driven-development`, `brainstorming`, `writing-plans`, and `spec-kit-vibe-compat` keyword entries.
- Modify: `scripts/router/modules/41-candidate-selection.ps1`
  - Blocks guarded skills from route-authority selection when no positive keyword matched.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`
  - Mirrors the PowerShell guard for runtime contract parity.
- Create: `tests/unit/test_router_contract_selection_guards.py`
  - Unit-tests the guarded fallback behavior in the Python selector.
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
  - Adds negative generic coding probes and explicit subagent/spec-kit probes.
- Create: `scripts/verify/vibe-orchestration-core-consolidation-gate.ps1`
  - Focused static and route gate for this pack.
- Create: `docs/governance/orchestration-core-pack-consolidation-2026-04-28.md`
  - Records before/after counts, moved-out skills, guarded authorities, and verification.
- Verify only: `config/vibe-entry-surfaces.json`
  - Must remain unchanged because `vibe` runtime authority is not being removed.

---

### Task 1: Add Failing Guard Tests

**Files:**
- Create: `tests/unit/test_router_contract_selection_guards.py`
- Read: `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`

- [ ] **Step 1: Create the Python unit test file**

Create `tests/unit/test_router_contract_selection_guards.py` with this content:

```python
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.router_contract_selection import select_pack_candidate


def _selection(prompt: str, *, requested: str | None = None) -> dict[str, object]:
    return select_pack_candidate(
        prompt_lower=prompt.casefold(),
        candidates=["subagent-driven-development"],
        task_type="coding",
        requested_canonical=requested,
        skill_keyword_index={
            "selection": {
                "weights": {"keyword_match": 0.8, "name_match": 0.2},
                "fallback_to_first_when_score_below": 0.2,
            },
            "skills": {
                "subagent-driven-development": {
                    "keywords": ["subagent", "子代理", "并行执行", "multi-agent"]
                }
            },
        },
        routing_rules={
            "skills": {
                "subagent-driven-development": {
                    "task_allow": ["planning", "coding", "review", "debug", "research"],
                    "positive_keywords": [
                        "subagent",
                        "parallel agents",
                        "multi-agent",
                        "子代理",
                        "多代理",
                        "并行执行",
                        "拆成多个代理",
                    ],
                    "negative_keywords": [],
                    "canonical_for_task": [],
                    "requires_positive_keyword_match": True,
                }
            }
        },
        pack={
            "id": "orchestration-core",
            "route_authority_candidates": ["subagent-driven-development"],
            "stage_assistant_candidates": [],
            "defaults_by_task": {},
        },
        candidate_selection_config={
            "rule_positive_keyword_bonus": 0.2,
            "rule_negative_keyword_penalty": 0.25,
            "canonical_for_task_bonus": 0.12,
        },
    )


def test_guarded_subagent_does_not_win_generic_coding_fallback() -> None:
    selection = _selection("实现这个功能并修改代码")

    assert selection["selected"] is None
    assert selection["reason"] == "no_route_authority_candidate"
    assert selection["route_authority_eligible"] is False


def test_guarded_subagent_can_win_with_explicit_positive_keyword() -> None:
    selection = _selection("请用子代理并行执行这个代码修改")

    assert selection["selected"] == "subagent-driven-development"
    assert selection["reason"] == "keyword_ranked"
    assert selection["route_authority_eligible"] is True


def test_requested_subagent_bypasses_guard() -> None:
    selection = _selection("实现这个功能并修改代码", requested="subagent-driven-development")

    assert selection["selected"] == "subagent-driven-development"
    assert selection["reason"] == "requested_skill"
```

- [ ] **Step 2: Run the new test and confirm it fails before implementation**

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py -q
```

Expected before Task 2: at least `test_guarded_subagent_does_not_win_generic_coding_fallback` fails because the selector still falls back to `subagent-driven-development`.

---

### Task 2: Implement Guarded Route Authority Selection

**Files:**
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`
- Modify: `scripts/router/modules/41-candidate-selection.ps1`

- [ ] **Step 1: Update the Python selector to read `requires_positive_keyword_match`**

In `packages/runtime-core/src/vgo_runtime/router_contract_selection.py`, find this block inside the scoring loop:

```python
route_authority_eligible = candidate_key in authority_allowlist if authority_allowlist is not None else True
stage_assistant_eligible = candidate_key in stage_assistant_allowlist
```

Replace it with:

```python
route_authority_eligible = candidate_key in authority_allowlist if authority_allowlist is not None else True
requires_positive_keyword_match = bool(rule.get("requires_positive_keyword_match"))
if route_authority_eligible and requires_positive_keyword_match and positive_score <= 0:
    route_authority_eligible = False
stage_assistant_eligible = candidate_key in stage_assistant_allowlist
```

- [ ] **Step 2: Add guard visibility to Python ranking rows**

In the same scored row dictionary, after:

```python
"routing_role": routing_role,
```

add:

```python
"requires_positive_keyword_match": requires_positive_keyword_match,
```

The row should still include the existing `ordinal` field.

- [ ] **Step 3: Update the PowerShell selector to read the same property**

In `scripts/router/modules/41-candidate-selection.ps1`, find this block inside the scoring loop:

```powershell
$canonicalHit = Get-CanonicalForTaskHit -Rule $rule -TaskType $TaskType
$candidateKey = ([string]$candidate).Trim().ToLowerInvariant()
$routeAuthorityEligible = if ($authorityAllowlistSpecified) { $authorityAllowlist -contains $candidateKey } else { $true }
$stageAssistantEligible = $stageAssistantAllowlist -contains $candidateKey
```

Replace it with:

```powershell
$canonicalHit = Get-CanonicalForTaskHit -Rule $rule -TaskType $TaskType
$candidateKey = ([string]$candidate).Trim().ToLowerInvariant()
$routeAuthorityEligible = if ($authorityAllowlistSpecified) { $authorityAllowlist -contains $candidateKey } else { $true }
$requiresPositiveKeywordMatch = $false
if ($rule -and ($rule.PSObject.Properties.Name -contains 'requires_positive_keyword_match')) {
    $requiresPositiveKeywordMatch = [bool]$rule.requires_positive_keyword_match
}
if ($routeAuthorityEligible -and $requiresPositiveKeywordMatch -and ([double]$positiveScore -le 0.0)) {
    $routeAuthorityEligible = $false
}
$stageAssistantEligible = $stageAssistantAllowlist -contains $candidateKey
```

- [ ] **Step 4: Add guard visibility to PowerShell ranking rows**

In the same `[pscustomobject]` ranking row, after:

```powershell
routing_role = $routingRole
```

add:

```powershell
requires_positive_keyword_match = [bool]$requiresPositiveKeywordMatch
```

Keep `equivalent_group` and `ordinal` unchanged.

- [ ] **Step 5: Run the new Python guard tests**

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py -q
```

Expected: all 3 tests pass.

---

### Task 3: Consolidate `orchestration-core` Pack Roles

**Files:**
- Modify: `config/pack-manifest.json`

- [ ] **Step 1: Replace `orchestration-core.skill_candidates`**

In the `orchestration-core` pack, replace the current 27-item `skill_candidates` list with:

```json
"skill_candidates":  [
                         "brainstorming",
                         "writing-plans",
                         "subagent-driven-development",
                         "context-hunter",
                         "think-harder",
                         "dialectic",
                         "local-vco-roles",
                         "spec-kit-vibe-compat"
                     ],
```

- [ ] **Step 2: Replace route authorities with problem owners plus guarded explicit spec-kit compatibility**

Replace the current `route_authority_candidates` list with:

```json
"route_authority_candidates":  [
                                 "brainstorming",
                                 "writing-plans",
                                 "subagent-driven-development",
                                 "spec-kit-vibe-compat"
                             ],
```

Interpretation:

- `brainstorming`, `writing-plans`, and `subagent-driven-development` own the normal orchestration problem types.
- `spec-kit-vibe-compat` is a guarded explicit compatibility route. It must not win without `/speckit`, `speckit`, `spec-kit`, or `.specify` style positive keywords.

- [ ] **Step 3: Replace stage assistants with only true internal helpers**

Replace the current `stage_assistant_candidates` list with:

```json
"stage_assistant_candidates":  [
                                 "context-hunter",
                                 "think-harder",
                                 "dialectic",
                                 "local-vco-roles"
                             ],
```

- [ ] **Step 4: Replace task defaults**

Replace the current `defaults_by_task` block with:

```json
"defaults_by_task":  {
                       "planning":  "writing-plans",
                       "research":  "brainstorming"
                   }
```

Do not add `coding`, `debug`, or `review` defaults to `subagent-driven-development`.

- [ ] **Step 5: Validate the JSON**

Run:

```powershell
Get-Content -LiteralPath 'config\pack-manifest.json' -Raw | ConvertFrom-Json | Out-Null
```

Expected: command exits successfully with no parse error.

- [ ] **Step 6: Confirm the intended counts**

Run:

```powershell
$manifest = Get-Content -LiteralPath 'config\pack-manifest.json' -Raw | ConvertFrom-Json
$pack = @($manifest.packs) | Where-Object { $_.id -eq 'orchestration-core' }
[pscustomobject]@{
  SkillCandidates = @($pack.skill_candidates).Count
  RouteAuthorities = @($pack.route_authority_candidates).Count
  StageAssistants = @($pack.stage_assistant_candidates).Count
  Defaults = ($pack.defaults_by_task | ConvertTo-Json -Compress)
  HasVibeCandidate = @($pack.skill_candidates) -contains 'vibe'
}
```

Expected:

```text
SkillCandidates  8
RouteAuthorities 4
StageAssistants  4
Defaults         {"planning":"writing-plans","research":"brainstorming"}
HasVibeCandidate False
```

---

### Task 4: Tighten Routing Rules And Keyword Index

**Files:**
- Modify: `config/skill-routing-rules.json`
- Modify: `config/skill-keyword-index.json`

- [ ] **Step 1: Replace the `subagent-driven-development` routing rule**

In `config/skill-routing-rules.json`, replace the existing `subagent-driven-development` object with:

```json
"subagent-driven-development":  {
                                  "task_allow":  [
                                                     "planning",
                                                     "coding",
                                                     "review",
                                                     "debug",
                                                     "research"
                                                 ],
                                  "positive_keywords":  [
                                                            "subagent",
                                                            "parallel agents",
                                                            "multi-agent",
                                                            "independent tasks",
                                                            "子代理",
                                                            "多代理",
                                                            "并行执行",
                                                            "拆成多个代理",
                                                            "多个 agent"
                                                        ],
                                  "negative_keywords":  [
                                                            "single file typo",
                                                            "ordinary coding",
                                                            "普通改代码",
                                                            "普通调试"
                                                        ],
                                  "equivalent_group":  null,
                                  "canonical_for_task":  [],
                                  "requires_positive_keyword_match":  true
                              },
```

- [ ] **Step 2: Add or replace the `spec-kit-vibe-compat` routing rule**

If `spec-kit-vibe-compat` has no rule, add it under `skills`. If it already has a rule, replace it with:

```json
"spec-kit-vibe-compat":  {
                           "task_allow":  [
                                              "planning",
                                              "coding",
                                              "review",
                                              "debug",
                                              "research"
                                          ],
                           "positive_keywords":  [
                                                     "/speckit",
                                                     "speckit",
                                                     "spec-kit",
                                                     ".specify",
                                                     "specify cli",
                                                     "spec.md",
                                                     "tasks.md",
                                                     "constitution.md"
                                                 ],
                           "negative_keywords":  [
                                                     "ordinary implementation plan",
                                                     "普通实施计划",
                                                     "普通任务拆解"
                                                 ],
                           "equivalent_group":  null,
                           "canonical_for_task":  [],
                           "requires_positive_keyword_match":  true
                       },
```

- [ ] **Step 3: Expand `brainstorming` positives for Chinese prompts**

Ensure `brainstorming.positive_keywords` contains these values:

```json
"positive_keywords":  [
                         "brainstorm",
                         "ideation",
                         "头脑风暴",
                         "方案发散",
                         "创意讨论",
                         "比较几个方案",
                         "比较几个方向"
                     ],
```

Keep its existing negative keywords for direct implementation, bug fixing, and deployment.

- [ ] **Step 4: Keep `writing-plans` focused on plans**

Ensure `writing-plans.positive_keywords` contains these values:

```json
"positive_keywords":  [
                         "implementation plan",
                         "task breakdown",
                         "execution plan",
                         "milestone roadmap",
                         "migration plan",
                         "governance rollout",
                         "rollout plan",
                         "runbook",
                         "wave plan",
                         "计划",
                         "实施计划",
                         "执行计划",
                         "任务拆解",
                         "里程碑",
                         "迁移计划"
                     ],
```

Keep its negative keywords for bug, traceback, and security audit.

- [ ] **Step 5: Update keyword index entries**

In `config/skill-keyword-index.json`, ensure these entries exist:

```json
"brainstorming":  {
                    "keywords":  [
                                     "brainstorm",
                                     "ideation",
                                     "头脑风暴",
                                     "方案发散",
                                     "创意讨论",
                                     "比较几个方案",
                                     "比较几个方向"
                                 ]
                },
"writing-plans":  {
                    "keywords":  [
                                     "implementation plan",
                                     "task breakdown",
                                     "execution plan",
                                     "milestone roadmap",
                                     "migration plan",
                                     "governance rollout",
                                     "rollout plan",
                                     "runbook",
                                     "wave plan",
                                     "cross-module migration",
                                     "routing governance",
                                     "计划书",
                                     "实施计划",
                                     "执行计划",
                                     "任务拆解",
                                     "里程碑规划",
                                     "迁移计划"
                                 ]
                },
"subagent-driven-development":  {
                                  "keywords":  [
                                                   "subagent",
                                                   "parallel agents",
                                                   "multi-agent",
                                                   "independent tasks",
                                                   "子代理",
                                                   "多代理",
                                                   "并行执行",
                                                   "拆成多个代理",
                                                   "多个 agent"
                                               ]
                              },
"spec-kit-vibe-compat":  {
                           "keywords":  [
                                            "/speckit",
                                            "speckit",
                                            "spec-kit",
                                            ".specify",
                                            "specify cli",
                                            "spec.md",
                                            "tasks.md",
                                            "constitution.md"
                                        ]
                       },
```

- [ ] **Step 6: Validate both JSON files**

Run:

```powershell
Get-Content -LiteralPath 'config\skill-routing-rules.json' -Raw | ConvertFrom-Json | Out-Null
Get-Content -LiteralPath 'config\skill-keyword-index.json' -Raw | ConvertFrom-Json | Out-Null
```

Expected: both commands exit successfully.

---

### Task 5: Add Focused Orchestration Gate

**Files:**
- Create: `scripts/verify/vibe-orchestration-core-consolidation-gate.ps1`

- [ ] **Step 1: Create the focused gate script**

Create `scripts/verify/vibe-orchestration-core-consolidation-gate.ps1` with this content:

```powershell
param()

$ErrorActionPreference = "Stop"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message,
        [string]$Details = ""
    )

    if ($Condition) {
        Write-Host "[PASS] $Message"
        return $true
    }

    if ($Details) {
        Write-Host "[FAIL] $Message - $Details" -ForegroundColor Red
    } else {
        Write-Host "[FAIL] $Message" -ForegroundColor Red
    }
    return $false
}

function Invoke-Route {
    param(
        [string]$Prompt,
        [string]$Grade,
        [string]$TaskType,
        [string]$RequestedSkill = ""
    )

    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $resolver = Join-Path $repoRoot "scripts\router\resolve-pack-route.ps1"
    $args = @{
        Prompt = $Prompt
        Grade = $Grade
        TaskType = $TaskType
    }
    if ($RequestedSkill) {
        $args.RequestedSkill = $RequestedSkill
    }

    return (& $resolver @args | ConvertFrom-Json)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot "config\pack-manifest.json") -Raw | ConvertFrom-Json
$rules = Get-Content -LiteralPath (Join-Path $repoRoot "config\skill-routing-rules.json") -Raw | ConvertFrom-Json
$entrySurfaces = Get-Content -LiteralPath (Join-Path $repoRoot "config\vibe-entry-surfaces.json") -Raw | ConvertFrom-Json
$pack = @($manifest.packs) | Where-Object { $_.id -eq "orchestration-core" } | Select-Object -First 1

$results = @()

$expectedCandidates = @(
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "context-hunter",
    "think-harder",
    "dialectic",
    "local-vco-roles",
    "spec-kit-vibe-compat"
)
$expectedAuthorities = @(
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "spec-kit-vibe-compat"
)
$expectedStageAssistants = @(
    "context-hunter",
    "think-harder",
    "dialectic",
    "local-vco-roles"
)
$removedFromPack = @(
    "autonomous-builder",
    "cancel-ralph",
    "claude-skills",
    "context-fundamentals",
    "create-plan",
    "hive-mind-advanced",
    "planning-with-files",
    "ralph-loop",
    "superclaude-framework-compat",
    "speckit-analyze",
    "speckit-checklist",
    "speckit-clarify",
    "speckit-constitution",
    "speckit-implement",
    "speckit-plan",
    "speckit-specify",
    "speckit-tasks",
    "speckit-taskstoissues",
    "vibe"
)

$results += Assert-True -Condition ($null -ne $pack) -Message "orchestration-core pack exists"
$results += Assert-True -Condition (@($pack.skill_candidates).Count -eq 8) -Message "orchestration-core has 8 skill candidates"
$results += Assert-True -Condition (@($pack.route_authority_candidates).Count -eq 4) -Message "orchestration-core has 4 route authorities"
$results += Assert-True -Condition (@($pack.stage_assistant_candidates).Count -eq 4) -Message "orchestration-core has 4 stage assistants"

foreach ($skill in $expectedCandidates) {
    $results += Assert-True -Condition (@($pack.skill_candidates) -contains $skill) -Message "candidate retained: $skill"
}
foreach ($skill in $expectedAuthorities) {
    $results += Assert-True -Condition (@($pack.route_authority_candidates) -contains $skill) -Message "route authority retained: $skill"
}
foreach ($skill in $expectedStageAssistants) {
    $results += Assert-True -Condition (@($pack.stage_assistant_candidates) -contains $skill) -Message "stage assistant retained: $skill"
}
foreach ($skill in $removedFromPack) {
    $results += Assert-True -Condition (-not (@($pack.skill_candidates) -contains $skill)) -Message "removed from orchestration-core candidates: $skill"
}

$defaults = @($pack.defaults_by_task.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" })
$results += Assert-True -Condition (@($pack.defaults_by_task.PSObject.Properties).Count -eq 2) -Message "only planning and research defaults remain" -Details ($defaults -join ", ")
$results += Assert-True -Condition ([string]$pack.defaults_by_task.planning -eq "writing-plans") -Message "planning defaults to writing-plans"
$results += Assert-True -Condition ([string]$pack.defaults_by_task.research -eq "brainstorming") -Message "research defaults to brainstorming"
$results += Assert-True -Condition (-not ($pack.defaults_by_task.PSObject.Properties.Name -contains "coding")) -Message "coding has no orchestration-core default"
$results += Assert-True -Condition (-not ($pack.defaults_by_task.PSObject.Properties.Name -contains "debug")) -Message "debug has no orchestration-core default"
$results += Assert-True -Condition (-not ($pack.defaults_by_task.PSObject.Properties.Name -contains "review")) -Message "review has no orchestration-core default"

$subagentRule = $rules.skills.'subagent-driven-development'
$specKitRule = $rules.skills.'spec-kit-vibe-compat'
$results += Assert-True -Condition ($subagentRule.requires_positive_keyword_match -eq $true) -Message "subagent route requires positive keyword"
$results += Assert-True -Condition ($specKitRule.requires_positive_keyword_match -eq $true) -Message "spec-kit compat route requires positive keyword"
$results += Assert-True -Condition (@($subagentRule.canonical_for_task).Count -eq 0) -Message "subagent is not canonical for generic coding"
$results += Assert-True -Condition ([string]$entrySurfaces.canonical_runtime_skill -eq "vibe") -Message "canonical runtime skill remains vibe"

$blockedCases = @(
    [pscustomobject]@{ Name = "generic coding M"; Prompt = "实现这个功能并修改代码"; Grade = "M"; TaskType = "coding" },
    [pscustomobject]@{ Name = "generic coding L"; Prompt = "实现这个功能并修改代码"; Grade = "L"; TaskType = "coding" },
    [pscustomobject]@{ Name = "generic coding XL"; Prompt = "实现这个功能并修改代码"; Grade = "XL"; TaskType = "coding" }
)
foreach ($case in $blockedCases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType
    $badSelection = ([string]$route.selected.pack_id -eq "orchestration-core" -and [string]$route.selected.skill -eq "subagent-driven-development")
    $results += Assert-True -Condition (-not $badSelection) -Message "generic coding does not route to subagent: $($case.Name)" -Details ("selected={0}/{1}" -f $route.selected.pack_id, $route.selected.skill)
}

$positiveCases = @(
    [pscustomobject]@{ Name = "brainstorming"; Prompt = "先做头脑风暴，比较几个方案"; Grade = "L"; TaskType = "planning"; ExpectedSkill = "brainstorming" },
    [pscustomobject]@{ Name = "writing plans"; Prompt = "请输出实施计划和任务拆解"; Grade = "L"; TaskType = "planning"; ExpectedSkill = "writing-plans" },
    [pscustomobject]@{ Name = "subagent planning"; Prompt = "把任务拆成多个子代理并行执行"; Grade = "XL"; TaskType = "planning"; ExpectedSkill = "subagent-driven-development" },
    [pscustomobject]@{ Name = "subagent coding"; Prompt = "请用子代理并行执行这个代码修改"; Grade = "XL"; TaskType = "coding"; ExpectedSkill = "subagent-driven-development" },
    [pscustomobject]@{ Name = "speckit explicit"; Prompt = "/speckit.plan 生成技术计划"; Grade = "L"; TaskType = "planning"; ExpectedSkill = "spec-kit-vibe-compat" }
)
foreach ($case in $positiveCases) {
    $route = Invoke-Route -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType
    $results += Assert-True -Condition ([string]$route.selected.pack_id -eq "orchestration-core") -Message "positive case selected orchestration-core: $($case.Name)" -Details ("selected={0}/{1}" -f $route.selected.pack_id, $route.selected.skill)
    $results += Assert-True -Condition ([string]$route.selected.skill -eq $case.ExpectedSkill) -Message "positive case selected expected skill: $($case.Name)" -Details ("selected={0}" -f $route.selected.skill)
}

$passCount = @($results | Where-Object { $_ }).Count
$failCount = @($results | Where-Object { -not $_ }).Count
$total = @($results).Count

Write-Host ""
Write-Host "=== Orchestration-Core Consolidation Summary ==="
Write-Host "Total assertions: $total"
Write-Host "Passed: $passCount"
Write-Host "Failed: $failCount"

if ($failCount -gt 0) {
    exit 1
}
```

- [ ] **Step 2: Run the new focused gate before config changes are complete**

Run:

```powershell
.\scripts\verify\vibe-orchestration-core-consolidation-gate.ps1
```

Expected before Tasks 3 and 4 are complete: the gate fails because the old pack still has 27 candidates and generic coding still reaches `subagent-driven-development`.

- [ ] **Step 3: Run the focused gate after Tasks 3 and 4**

Run:

```powershell
.\scripts\verify\vibe-orchestration-core-consolidation-gate.ps1
```

Expected after Tasks 3 and 4: all assertions pass.

---

### Task 6: Update Regression Matrix Boundaries

**Files:**
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`

- [ ] **Step 1: Add blocked-skill assertion support**

In the loop that checks `$case.BlockedPack`, add this block immediately after it:

```powershell
if ($case.BlockedSkill) {
    $results += Assert-True -Condition ($route.selected.skill -ne $case.BlockedSkill) -Message "[$($case.Name)] blocked skill $($case.BlockedSkill) not selected"
}

if ($case.BlockedPackAndSkill) {
    $pair = [string]$case.BlockedPackAndSkill
    $actualPair = "{0}/{1}" -f $route.selected.pack_id, $route.selected.skill
    $results += Assert-True -Condition ($actualPair -ne $pair) -Message "[$($case.Name)] blocked pair $pair not selected"
}
```

- [ ] **Step 2: Insert orchestration boundary cases near the existing orchestration cases**

Add these cases after the existing orchestration planning/subagent cases:

```powershell
[pscustomobject]@{ Name = "orchestration generic coding M not subagent"; Prompt = "实现这个功能并修改代码"; Grade = "M"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPackAndSkill = "orchestration-core/subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration generic coding L not subagent"; Prompt = "实现这个功能并修改代码"; Grade = "L"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPackAndSkill = "orchestration-core/subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration generic coding XL not silent subagent"; Prompt = "实现这个功能并修改代码"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = $null; BlockedPackAndSkill = "orchestration-core/subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration explicit subagent coding"; Prompt = "请用子代理并行执行这个代码修改"; Grade = "XL"; TaskType = "coding"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; ExpectedSkill = "subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration explicit speckit"; Prompt = "/speckit.plan 生成技术计划"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; ExpectedSkill = "spec-kit-vibe-compat"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
```

- [ ] **Step 3: Run the regression matrix**

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected: new orchestration boundary cases pass.

---

### Task 7: Add Governance Note

**Files:**
- Create: `docs/governance/orchestration-core-pack-consolidation-2026-04-28.md`

- [ ] **Step 1: Create the governance note**

Create `docs/governance/orchestration-core-pack-consolidation-2026-04-28.md` with this content:

```markdown
# Orchestration-Core Pack Consolidation

Date: 2026-04-28

## Summary

This pass shrinks `orchestration-core` from a broad 27-skill surface into a problem-first orchestration surface.

The pack now handles:

- brainstorming and divergent solution design;
- implementation plans and task breakdowns;
- explicit subagent or multi-agent execution requests;
- explicit spec-kit compatibility routing.

It no longer treats ordinary coding, debugging, review, legacy loop commands, or external framework compatibility skills as normal orchestration-core routes.

## Before And After

| field | before | after |
| --- | --- | --- |
| `skill_candidates` | 27 | 8 |
| `route_authority_candidates` | 3 | 4 |
| `stage_assistant_candidates` | 23 | 4 |
| `defaults_by_task.coding` | `subagent-driven-development` | removed |
| `defaults_by_task.debug` | `subagent-driven-development` | removed |
| `defaults_by_task.review` | `writing-plans` | removed |
| `defaults_by_task.planning` | `writing-plans` | `writing-plans` |
| `defaults_by_task.research` | `brainstorming` | `brainstorming` |

## Kept Route Authorities

| skill | role | boundary |
| --- | --- | --- |
| `brainstorming` | route authority | explicit brainstorming, ideation, solution comparison |
| `writing-plans` | route authority | implementation plan, task breakdown, migration plan, runbook |
| `subagent-driven-development` | guarded route authority | explicit subagent, parallel agents, multi-agent work |
| `spec-kit-vibe-compat` | guarded explicit compatibility route | `/speckit.*`, `speckit`, `spec-kit`, `.specify` workflows |

`subagent-driven-development` and `spec-kit-vibe-compat` use `requires_positive_keyword_match = true`, so they cannot win by low-score fallback alone.

## Kept Stage Assistants

| skill | why stage-only |
| --- | --- |
| `context-hunter` | useful before implementation, but should not own broad user prompts |
| `think-harder` | useful for deeper analysis, but should not replace planning or domain packs |
| `dialectic` | useful for multi-perspective review, but should be explicit or Vibe-internal |
| `local-vco-roles` | useful role set for VCO reviews, not a user problem owner |

## Removed From This Pack Surface

These skill directories are not physically deleted in this pass:

| skill | reason |
| --- | --- |
| `autonomous-builder` | too broad; would compete with ordinary coding and feature work |
| `cancel-ralph` | compatibility command, not an orchestration problem owner |
| `claude-skills` | skill creation/governance meta-skill, belongs outside orchestration-core |
| `context-fundamentals` | explanatory context-engineering material, not task routing authority |
| `create-plan` | overlaps with `writing-plans`; content can be migrated later |
| `hive-mind-advanced` | external collective-agent framework, not default Vibe routing |
| `planning-with-files` | overlaps with `writing-plans`; file-planning ideas can be migrated later |
| `ralph-loop` | compatibility command, not ordinary route authority |
| `superclaude-framework-compat` | external framework compatibility, not ordinary route authority |
| `speckit-*` | specific spec-kit subcommands are covered by guarded `spec-kit-vibe-compat` |
| `vibe` | canonical runtime authority, not an ordinary specialist candidate |

## Protected Route Boundaries

| prompt | expected |
| --- | --- |
| `实现这个功能并修改代码` | must not select `orchestration-core/subagent-driven-development` |
| `先做头脑风暴，比较几个方案` | `orchestration-core/brainstorming` |
| `请输出实施计划和任务拆解` | `orchestration-core/writing-plans` |
| `把任务拆成多个子代理并行执行` | `orchestration-core/subagent-driven-development` |
| `请用子代理并行执行这个代码修改` | `orchestration-core/subagent-driven-development` |
| `/speckit.plan 生成技术计划` | `orchestration-core/spec-kit-vibe-compat` |

## Verification

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py -q
.\scripts\verify\vibe-orchestration-core-consolidation-gate.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Report any pre-existing unrelated failures separately from this pack.
```

- [ ] **Step 2: Scan the governance note for incomplete markers**

Run:

```powershell
$pattern = 'TO' + 'DO|TB' + 'D|place' + 'holder|待' + '定|占' + '位'
rg -n $pattern docs\governance\orchestration-core-pack-consolidation-2026-04-28.md
```

Expected: no output.

---

### Task 8: Verify Full Change And Commit

**Files:**
- Verify all files changed in Tasks 1-7.
- Possibly modify: `config/skills-lock.json` only if offline gate reports lock drift.

- [ ] **Step 1: Run focused unit test**

Run:

```powershell
python -m pytest tests/unit/test_router_contract_selection_guards.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 2: Run focused orchestration gate**

Run:

```powershell
.\scripts\verify\vibe-orchestration-core-consolidation-gate.ps1
```

Expected: all assertions pass and the summary shows `Failed: 0`.

- [ ] **Step 3: Run pack regression**

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected: all assertions pass.

- [ ] **Step 4: Run routing audit**

Run:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected: no `orchestration-core` failures. If historical unrelated failures remain, list their case names and confirm they are not caused by this change.

- [ ] **Step 5: Run broad smoke gate**

Run:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
```

Expected: gate passes.

- [ ] **Step 6: Run offline skills gate**

Run:

```powershell
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected: gate passes. If it reports lock drift, run:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected after regeneration: offline gate passes.

- [ ] **Step 7: Confirm canonical `vibe` runtime files did not change**

Run:

```powershell
git diff -- config/vibe-entry-surfaces.json core/skills/vibe SKILL.md
```

Expected: no output.

- [ ] **Step 8: Review intended diff**

Run:

```powershell
git diff --check
git status --short
```

Expected changed files:

```text
M config/pack-manifest.json
M config/skill-routing-rules.json
M config/skill-keyword-index.json
M scripts/router/modules/41-candidate-selection.ps1
M packages/runtime-core/src/vgo_runtime/router_contract_selection.py
M scripts/verify/vibe-pack-regression-matrix.ps1
?? tests/unit/test_router_contract_selection_guards.py
?? scripts/verify/vibe-orchestration-core-consolidation-gate.ps1
?? docs/governance/orchestration-core-pack-consolidation-2026-04-28.md
```

`config/skills-lock.json` may also appear only if Step 6 required lock regeneration.

- [ ] **Step 9: Commit the implementation**

Run:

```powershell
git add -- config/pack-manifest.json config/skill-routing-rules.json config/skill-keyword-index.json
git add -- scripts/router/modules/41-candidate-selection.ps1 packages/runtime-core/src/vgo_runtime/router_contract_selection.py
git add -- scripts/verify/vibe-pack-regression-matrix.ps1 scripts/verify/vibe-orchestration-core-consolidation-gate.ps1
git add -- tests/unit/test_router_contract_selection_guards.py docs/governance/orchestration-core-pack-consolidation-2026-04-28.md
git status --short config/skills-lock.json
```

If `config/skills-lock.json` changed, also run:

```powershell
git add -- config/skills-lock.json
```

Then commit:

```powershell
git commit -m "feat: consolidate orchestration core routing"
```

Expected: commit succeeds and contains only the intended consolidation files.

---

## Self-Review

Spec coverage:

- `vibe` remains canonical runtime authority: Task 8 checks no diff in `config/vibe-entry-surfaces.json`, `core/skills/vibe`, and root `SKILL.md`.
- Ordinary coding/debug is not silently routed to subagents: Tasks 1, 2, 5, and 6 add the guard and route probes.
- M/L/XL intent is preserved: generic M/L/XL coding prompts are blocked from silent subagent selection, while explicit XL subagent prompts still route correctly.
- Duplicate planning skills are removed from the pack route surface: Task 3 removes `create-plan` and `planning-with-files` from `orchestration-core.skill_candidates`.
- spec-kit compatibility remains available without polluting normal planning: Tasks 3 and 4 add guarded `spec-kit-vibe-compat` routing.
- Physical directory deletion is not performed: no task removes `bundled/skills/*` directories.
- Verification is explicit: Tasks 5, 6, and 8 define focused and broad gates.

Placeholder scan:

- This plan uses concrete file paths, exact snippets, exact commands, and expected outcomes.
- It does not leave implementation sections for later filling.

Type and property consistency:

- New config property name is `requires_positive_keyword_match` in both JSON and selector code.
- PowerShell ranking rows and Python ranking rows use the same visibility field name.
- Existing output fields `selected.pack_id`, `selected.skill`, `route_mode`, and `candidate_selection_reason` remain unchanged.
