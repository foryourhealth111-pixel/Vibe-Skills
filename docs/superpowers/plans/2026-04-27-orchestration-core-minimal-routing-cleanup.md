# Orchestration-Core Minimal Routing Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `orchestration-core` from routing ordinary orchestration subproblems to `vibe` while preserving canonical `$vibe` runtime authority.

**Architecture:** This is a narrow routing/config cleanup. Keep `vibe` in the candidate list for compatibility, but remove it from primary route authority and task defaults. Promote the three already-scored orchestration specialists to route authority and keep the existing router algorithm unchanged.

**Tech Stack:** PowerShell router gates, JSON config, Markdown governance docs.

---

## File Structure

- Modify: `config/pack-manifest.json`
  - Owns pack membership, route authority roles, stage assistant roles, and task defaults.
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`
  - Adds skill-level expectations to existing orchestration planning regression cases.
- Create: `docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md`
  - Records before/after counts, role ownership, verification, and caveats.
- Read-only verification: `scripts/verify/vibe-skill-index-routing-audit.ps1`
  - Already has the three expected orchestration skill probes and should pass after the manifest change.
- Read-only verification: `config/vibe-entry-surfaces.json`
  - Confirms canonical runtime skill remains `vibe`; this file must not be modified.

---

### Task 1: Capture Current Failure Evidence

**Files:**
- Read: `config/pack-manifest.json`
- Read: `scripts/router/resolve-pack-route.ps1`
- Read: `scripts/verify/vibe-skill-index-routing-audit.ps1`

- [ ] **Step 1: Confirm clean starting tree**

Run:

```powershell
git status --short --branch
```

Expected: branch is `feature/ml-skills-pruning-audit`; no modified tracked files before implementation starts.

- [ ] **Step 2: Run the three direct route probes before editing**

Run:

```powershell
$cases = @(
  @{Name='brainstorm'; Prompt='先做头脑风暴，发散方案'; Grade='L'; TaskType='planning'},
  @{Name='plan'; Prompt='请输出实施计划并做任务拆解'; Grade='L'; TaskType='planning'},
  @{Name='subagent'; Prompt='把任务拆成多个子代理并行执行'; Grade='XL'; TaskType='planning'}
)
foreach ($case in $cases) {
  $route = .\scripts\router\resolve-pack-route.ps1 -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType | ConvertFrom-Json
  "$($case.Name): pack=$($route.selected.pack_id), skill=$($route.selected.skill), reason=$($route.selected.selection_reason)"
}
```

Expected before the fix:

```text
brainstorm: pack=orchestration-core, skill=vibe, reason=fallback_task_default
plan: pack=orchestration-core, skill=vibe, reason=fallback_task_default
subagent: pack=orchestration-core, skill=vibe, reason=fallback_task_default
```

- [ ] **Step 3: Run the existing routing audit to prove the expected failing cases already exist**

Run:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
```

Expected before the fix: the script exits non-zero. The three orchestration cases should show actual skill `vibe` instead of `brainstorming`, `writing-plans`, and `subagent-driven-development`. Other pre-existing unrelated failures may also appear; record them separately.

---

### Task 2: Update Orchestration-Core Route Roles

**Files:**
- Modify: `config/pack-manifest.json`

- [ ] **Step 1: Edit `orchestration-core.route_authority_candidates`**

Replace the current route authority block:

```json
"route_authority_candidates":  [
                                 "vibe"
                             ],
```

with:

```json
"route_authority_candidates":  [
                                 "brainstorming",
                                 "writing-plans",
                                 "subagent-driven-development"
                             ],
```

- [ ] **Step 2: Edit `orchestration-core.stage_assistant_candidates`**

Remove these three entries from the `stage_assistant_candidates` array:

```json
"brainstorming",
"subagent-driven-development",
"writing-plans"
```

Keep the other stage assistants in their existing order:

```json
"stage_assistant_candidates":  [
                                 "autonomous-builder",
                                 "cancel-ralph",
                                 "claude-skills",
                                 "context-fundamentals",
                                 "context-hunter",
                                 "create-plan",
                                 "dialectic",
                                 "hive-mind-advanced",
                                 "local-vco-roles",
                                 "planning-with-files",
                                 "ralph-loop",
                                 "speckit-analyze",
                                 "speckit-checklist",
                                 "speckit-clarify",
                                 "speckit-constitution",
                                 "speckit-implement",
                                 "speckit-plan",
                                 "speckit-specify",
                                 "speckit-tasks",
                                 "speckit-taskstoissues",
                                 "spec-kit-vibe-compat",
                                 "superclaude-framework-compat",
                                 "think-harder"
                             ],
```

- [ ] **Step 3: Edit `orchestration-core.defaults_by_task`**

Replace:

```json
"defaults_by_task":  {
                       "debug":  "vibe",
                       "planning":  "vibe",
                       "research":  "vibe",
                       "coding":  "vibe",
                       "review":  "vibe"
                   }
```

with:

```json
"defaults_by_task":  {
                       "debug":  "subagent-driven-development",
                       "planning":  "writing-plans",
                       "research":  "brainstorming",
                       "coding":  "subagent-driven-development",
                       "review":  "writing-plans"
                   }
```

- [ ] **Step 4: Validate JSON parses**

Run:

```powershell
Get-Content -LiteralPath 'config\pack-manifest.json' -Raw | ConvertFrom-Json | Out-Null
```

Expected: command exits successfully with no parse error.

- [ ] **Step 5: Confirm `vibe` remains a candidate but not a route authority**

Run:

```powershell
$manifest = Get-Content -LiteralPath 'config\pack-manifest.json' -Raw | ConvertFrom-Json
$pack = @($manifest.packs) | Where-Object { $_.id -eq 'orchestration-core' }
[pscustomobject]@{
  CandidateHasVibe = @($pack.skill_candidates) -contains 'vibe'
  RouteAuthorityHasVibe = @($pack.route_authority_candidates) -contains 'vibe'
  RouteAuthorities = (@($pack.route_authority_candidates) -join ', ')
  StageAssistants = @($pack.stage_assistant_candidates).Count
}
```

Expected:

```text
CandidateHasVibe      True
RouteAuthorityHasVibe False
RouteAuthorities      brainstorming, writing-plans, subagent-driven-development
StageAssistants       23
```

---

### Task 3: Strengthen Pack Regression Skill Expectations

**Files:**
- Modify: `scripts/verify/vibe-pack-regression-matrix.ps1`

- [ ] **Step 1: Add skill expectations to the two existing orchestration planning cases**

Change the first two `$cases` entries from pack-only assertions to pack-and-skill assertions.

Replace:

```powershell
[pscustomobject]@{ Name = "orchestration planning EN"; Prompt = "create implementation plan and task breakdown with milestones"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration planning ZH"; Prompt = "请给我实施计划和任务拆解"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
```

with:

```powershell
[pscustomobject]@{ Name = "orchestration planning EN"; Prompt = "create implementation plan and task breakdown with milestones"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; ExpectedSkill = "writing-plans"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
[pscustomobject]@{ Name = "orchestration planning ZH"; Prompt = "请给我实施计划和任务拆解"; Grade = "L"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; ExpectedSkill = "writing-plans"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
```

- [ ] **Step 2: Add an explicit subagent pack regression case**

Insert this case immediately after the two orchestration planning cases:

```powershell
[pscustomobject]@{ Name = "orchestration subagent ZH"; Prompt = "把任务拆成多个子代理并行执行"; Grade = "XL"; TaskType = "planning"; RequestedSkill = $null; ExpectedPack = "orchestration-core"; ExpectedSkill = "subagent-driven-development"; AllowedModes = @("pack_overlay", "confirm_required", "legacy_fallback") },
```

- [ ] **Step 3: Run the regression matrix**

Run:

```powershell
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected after Task 2 and Task 3: orchestration planning EN, orchestration planning ZH, and orchestration subagent ZH all pass their selected pack and selected skill assertions.

---

### Task 4: Add Governance Note

**Files:**
- Create: `docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md`

- [ ] **Step 1: Create the governance note**

Create `docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md` with this content:

```markdown
# Orchestration-Core Minimal Routing Cleanup

Date: 2026-04-27

## Summary

This pass keeps canonical `vibe` as the runtime authority while removing it from ordinary `orchestration-core` primary specialist selection.

## Before

| field | value |
| --- | --- |
| `skill_candidates` | 27 |
| `route_authority_candidates` | `vibe` |
| `stage_assistant_candidates` | 26 |
| `defaults_by_task` | all task types defaulted to `vibe` |

## After

| field | value |
| --- | --- |
| `skill_candidates` | 27 |
| `route_authority_candidates` | `brainstorming`, `writing-plans`, `subagent-driven-development` |
| `stage_assistant_candidates` | 23 |
| `defaults_by_task.planning` | `writing-plans` |
| `defaults_by_task.coding` | `subagent-driven-development` |
| `defaults_by_task.research` | `brainstorming` |
| `defaults_by_task.debug` | `subagent-driven-development` |
| `defaults_by_task.review` | `writing-plans` |

## Role Boundaries

| skill | role | owns |
| --- | --- | --- |
| `brainstorming` | route authority | ideation, brainstorming, divergent solution exploration |
| `writing-plans` | route authority | implementation plans, task breakdowns, milestones, runbooks, migration plans |
| `subagent-driven-development` | route authority | subagent decomposition, parallel agent execution, multi-agent work splitting |
| `vibe` | runtime authority only | canonical `$vibe` / `/vibe` runtime entry and governance ownership |

## Deferred Work

This pass does not introduce a `no-specialist` or `host-led` fallback. Low-information prompts may still choose a concrete default specialist. That is acceptable for this minimal cleanup and should be handled in a later router-semantics pass.

This pass does not prune the full 27-candidate `orchestration-core` surface. Remaining stage assistants should be reviewed separately.

## Regression Probes

| prompt | expected |
| --- | --- |
| `先做头脑风暴，发散方案` | `orchestration-core / brainstorming` |
| `请输出实施计划并做任务拆解` | `orchestration-core / writing-plans` |
| `把任务拆成多个子代理并行执行` | `orchestration-core / subagent-driven-development` |

## Verification

Run:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Report any pre-existing unrelated failures separately from `orchestration-core` results.
```

- [ ] **Step 2: Confirm the note has no incomplete-marker terms**

Run:

```powershell
Select-String -LiteralPath 'docs\governance\orchestration-core-minimal-routing-cleanup-2026-04-27.md' -Pattern 'TO' + 'DO|TB' + 'D|place' + 'holder|待' + '定|占' + '位' -CaseSensitive:$false
```

Expected: no output.

---

### Task 5: Verify, Refresh Lock If Needed, And Commit

**Files:**
- Verify: `config/pack-manifest.json`
- Verify: `scripts/verify/vibe-pack-regression-matrix.ps1`
- Verify: `docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md`
- Possibly modify: `config/skills-lock.json` only if `vibe-offline-skills-gate.ps1` reports lock drift.

- [ ] **Step 1: Run direct route probes after the change**

Run:

```powershell
$cases = @(
  @{Name='brainstorm'; Prompt='先做头脑风暴，发散方案'; Grade='L'; TaskType='planning'; Expected='brainstorming'},
  @{Name='plan'; Prompt='请输出实施计划并做任务拆解'; Grade='L'; TaskType='planning'; Expected='writing-plans'},
  @{Name='subagent'; Prompt='把任务拆成多个子代理并行执行'; Grade='XL'; TaskType='planning'; Expected='subagent-driven-development'}
)
foreach ($case in $cases) {
  $route = .\scripts\router\resolve-pack-route.ps1 -Prompt $case.Prompt -Grade $case.Grade -TaskType $case.TaskType | ConvertFrom-Json
  "$($case.Name): pack=$($route.selected.pack_id), skill=$($route.selected.skill), expected=$($case.Expected)"
  if ($route.selected.pack_id -ne 'orchestration-core' -or $route.selected.skill -ne $case.Expected) {
    throw "Unexpected route for $($case.Name)"
  }
}
```

Expected: all three probes print `pack=orchestration-core` and the expected specialist skill, with no thrown error.

- [ ] **Step 2: Run focused routing audits**

Run:

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

Expected: all `orchestration-core` cases pass. If unrelated old failures remain in `vibe-skill-index-routing-audit.ps1`, list their names and verify they are not caused by this change.

- [ ] **Step 3: Run broader smoke and offline gates**

Run:

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected: `vibe-pack-routing-smoke.ps1` passes. `vibe-offline-skills-gate.ps1` passes without lock drift.

- [ ] **Step 4: Refresh lock only if the offline gate reports lock drift**

Run this only if Step 3 reports that `config/skills-lock.json` is stale:

```powershell
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

Expected: lock generation completes and the offline gate passes.

- [ ] **Step 5: Confirm canonical `vibe` entry config was not changed**

Run:

```powershell
git diff -- config/vibe-entry-surfaces.json core/skills/vibe SKILL.md
```

Expected: no output.

- [ ] **Step 6: Review intended diff**

Run:

```powershell
git diff -- config/pack-manifest.json scripts/verify/vibe-pack-regression-matrix.ps1 docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md
git status --short
```

Expected changed files:

```text
M config/pack-manifest.json
M scripts/verify/vibe-pack-regression-matrix.ps1
?? docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md
```

`config/skills-lock.json` may also appear only if Step 4 was necessary.

- [ ] **Step 7: Commit the implementation**

Run:

```powershell
git add -- config/pack-manifest.json scripts/verify/vibe-pack-regression-matrix.ps1 docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md
if (Test-Path -LiteralPath 'config\skills-lock.json') {
  git status --short config/skills-lock.json
}
git commit -m "feat: clean orchestration core routing"
```

If `config/skills-lock.json` changed in Step 4, include it in the same commit:

```powershell
git add -- config/skills-lock.json
git commit -m "feat: clean orchestration core routing"
```

Expected: commit succeeds and contains only intended routing/config/test/governance files.

---

## Self-Review

Spec coverage:

- Preserve canonical `vibe` runtime authority: Task 2 keeps `vibe` in `skill_candidates`; Task 5 checks no diff in canonical entry files.
- Promote concrete specialists: Task 2 promotes `brainstorming`, `writing-plans`, and `subagent-driven-development`.
- Avoid directory deletion: no task deletes any file or directory.
- Add regression evidence: Task 3 strengthens pack regression, Task 5 runs route probes and gates.
- Governance note: Task 4 creates the governance note.

Red-flag scan:

- The plan avoids incomplete-marker terms that would indicate unfinished work.

Type and property consistency:

- Router output uses `route.selected.pack_id`, `route.selected.skill`, and `route.selected.selection_reason`, matching existing verification scripts.
- Manifest properties use existing names: `skill_candidates`, `route_authority_candidates`, `stage_assistant_candidates`, and `defaults_by_task`.
