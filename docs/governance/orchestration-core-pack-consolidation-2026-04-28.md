# Orchestration-Core Pack Consolidation

Date: 2026-04-28

> Superseded by `docs/governance/orchestration-core-hard-removal-2026-04-28.md`.
> This document records the intermediate 8-skill consolidation state, not the current hard-removal target.

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
