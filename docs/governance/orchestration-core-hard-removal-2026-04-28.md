# Orchestration-Core Hard Removal

Date: 2026-04-28

## Summary

`orchestration-core` is no longer an active routing pack.

The governed entry model is now:

```text
$vibe / /vibe -> vibe six-stage runtime -> internal specialist recommendations -> vibe-owned execution and cleanup
```

In plain terms: `vibe` is the doorway and the boss. The router may recommend a specialist, but it does not become a second doorway.

## Removed Active Surface

| old surface | new ownership |
| --- | --- |
| `orchestration-core/brainstorming` | `vibe.deep_interview` method |
| `orchestration-core/writing-plans` | `vibe.xl_plan` method |
| `orchestration-core/subagent-driven-development` | `vibe.plan_execute` plus `protocols/team.md` |
| `orchestration-core/spec-kit-vibe-compat` | `workflow-compatibility/spec-kit-vibe-compat` explicit compatibility |

## What Did Not Change

- The physical skill directories were not deleted in this pass.
- `vibe` remains the canonical runtime skill.
- Runtime packet field `canonical_router` is retained as a compatibility field name.
- `resolve-pack-route.ps1` remains available as an internal specialist recommender.
- Specialist recommendations stay below `vibe` authority.

## Runtime Meaning

The runtime may show two different facts:

| field | meaning |
| --- | --- |
| runtime selected skill = `vibe` | governed runtime authority stays with `vibe` |
| route snapshot selected skill = a specialist | bounded specialist recommendation inside `vibe` |

That split is expected after this removal. For example, a debugging prompt can recommend `code-quality/systematic-debugging`, while the governed runtime still executes under `vibe`.

## Protected Boundaries

| prompt | expected boundary |
| --- | --- |
| `请输出实施计划和任务拆解` | must not select `orchestration-core` |
| `先做头脑风暴，发散方案` | must not select `orchestration-core` |
| `把任务拆成多个子代理并行执行` | must not select `orchestration-core` |
| `/speckit.plan 生成技术计划` | selects `workflow-compatibility/spec-kit-vibe-compat` |
| `$vibe ...` | enters `vibe`; specialists are subordinate recommendations |

## Verification

```powershell
.\scripts\verify\vibe-orchestration-core-hard-removal-gate.ps1
.\scripts\verify\vibe-orchestration-core-consolidation-gate.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
python -m pytest tests/unit/test_router_contract_selection_guards.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_structured_bounded_reentry_continuation.py tests/runtime_neutral/test_runtime_contract_goldens.py -q
.\scripts\verify\vibe-routing-stability-gate.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-keyword-precision-audit.ps1
.\scripts\verify\vibe-external-corpus-gate.ps1 -CandidateSkillIndexPath references\fixtures\external-corpus\skill-keyword-index.candidate.json
.\scripts\verify\vibe-openspec-governance-gate.ps1
.\scripts\verify\vibe-gsd-overlay-gate.ps1
.\scripts\verify\vibe-router-contract-gate.ps1
```
