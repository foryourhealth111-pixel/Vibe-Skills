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
