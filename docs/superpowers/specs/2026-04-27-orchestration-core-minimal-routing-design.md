# Orchestration-Core Minimal Routing Cleanup Design

Date: 2026-04-27

## 背景

`orchestration-core` 现在有 27 个 `skill_candidates`，但只有 `vibe` 是 `route_authority_candidates`。同时，`defaults_by_task` 把 `debug`、`planning`、`research`、`coding`、`review` 都默认到 `vibe`。

这会造成一个混淆：`vibe` 本来是 canonical runtime entry 和运行时权威，却又在 `orchestration-core` 里像普通专家 skill 一样被路由选中。结果是头脑风暴、实施计划、子代理拆分这些本应由具体专家处理的问题，也会显示成 `orchestration-core / vibe`。

## 目标

用最小修改修正 `orchestration-core` 的主路由角色，让具体问题命中具体专家，同时保持 `$vibe` / `/vibe` 的 canonical 入口能力不退化。

## 不改什么

- 不删除任何 skill 目录。
- 不删除或重命名 repo 根部 `SKILL.md`。
- 不修改 `core/skills/vibe`。
- 不修改 `config/vibe-entry-surfaces.json` 里的 `canonical_runtime_skill = vibe`。
- 不修改 canonical launch、runtime proof、governance capsule 对 `vibe` runtime authority 的要求。
- 不引入新的 `no-specialist` / `host-led` fallback 机制。
- 不在本轮大规模清理 `orchestration-core` 的 27 个候选。

## 改什么

本轮只调整 `orchestration-core` 的路由角色：

| skill | 目标角色 | 负责的问题 |
| --- | --- | --- |
| `brainstorming` | route authority | 头脑风暴、方案发散、创意讨论 |
| `writing-plans` | route authority | 实施计划、任务拆解、里程碑、runbook、迁移计划 |
| `subagent-driven-development` | route authority | 子代理、多代理、并行拆分执行 |
| `vibe` | runtime authority only | 保留为 canonical runtime entry，不再作为普通专家主路由 |

`brainstorming`、`writing-plans`、`subagent-driven-development` 提升为主路由候选后，应从 `stage_assistant_candidates` 中移出，避免同一个 skill 同时扮演主专家和阶段助手。

`defaults_by_task` 不再全部指向 `vibe`。最小安全默认值如下：

| task type | 默认 skill |
| --- | --- |
| `planning` | `writing-plans` |
| `coding` | `subagent-driven-development` |
| `research` | `brainstorming` |
| `debug` | `subagent-driven-development` |
| `review` | `writing-plans` |

这些默认值只在低分 fallback 时使用。实际有明显关键词时，仍由关键词打分决定。

## 预期路由

| prompt | 预期结果 |
| --- | --- |
| `先做头脑风暴，发散方案` | `orchestration-core / brainstorming` |
| `请输出实施计划并做任务拆解` | `orchestration-core / writing-plans` |
| `把任务拆成多个子代理并行执行` | `orchestration-core / subagent-driven-development` |
| 显式 `$vibe` / `/vibe` canonical 入口 | 仍进入 canonical `vibe` runtime |

## 文件范围

预计修改：

- `config/pack-manifest.json`
- `docs/governance/orchestration-core-minimal-routing-cleanup-2026-04-27.md`

按测试结果决定是否需要微调：

- `config/skill-keyword-index.json`
- `config/skill-routing-rules.json`
- `scripts/verify/vibe-pack-regression-matrix.ps1`
- `scripts/verify/vibe-skill-index-routing-audit.ps1`

## 测试方法

先跑定向路由：

```powershell
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
```

再跑基础回归：

```powershell
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```

如果全局门禁存在历史无关失败，报告时必须区分：

- 本轮 `orchestration-core` 相关用例是否通过。
- 旧失败是否仍然存在。
- 旧失败是否与本轮改动无关。

## 风险与控制

主要风险是把 `vibe` 从普通专家路由中拿掉时，误伤 canonical `$vibe` 入口。控制方式是只改 `orchestration-core` 的 pack 路由配置，不改 canonical runtime entry 的配置和代码。

另一个风险是低信息量 prompt 可能落到新的默认 skill。这个风险本轮接受，因为它已经比全部落到 `vibe` 更接近真实专家路由。更完整的 `no-specialist` / `host-led` fallback 语义留到后续独立治理。

## 完成标准

- `orchestration-core` 不再把 `vibe` 作为唯一主路由专家。
- 三个核心路由探针分别命中 `brainstorming`、`writing-plans`、`subagent-driven-development`。
- `$vibe` / `/vibe` 仍保留 canonical runtime entry 语义。
- 不删除任何 skill 目录。
- 相关验证命令已运行并记录结果。
