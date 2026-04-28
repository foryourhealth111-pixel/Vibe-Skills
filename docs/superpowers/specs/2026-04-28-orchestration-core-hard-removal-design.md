# Orchestration-Core Hard Removal Design

Date: 2026-04-28

## 一句话结论

`orchestration-core` 不再作为主动调度 pack 存在。

整改后的核心语义是：

```text
唯一治理入口：$vibe / /vibe
唯一运行时权威：vibe
内部专家推荐器：scripts/router/resolve-pack-route.ps1
领域专家来源：各领域 pack
```

普通用户请求如果没有显式进入 `$vibe`，不应该被 Vibe-Skills 强行接入治理路由。只有 `$vibe` 启动后，`vibe` 才在自己的六阶段里做需求冻结、计划、执行、子代理判断、验证和清理。

## 背景

前两轮治理已经把 `orchestration-core` 从一个 27-skill 的大包收敛成 8 个候选，并移除了普通 coding/debug/review 默认进入 `subagent-driven-development` 的问题。

但这个状态仍然留下一个更深层的问题：`orchestration-core` 仍然像一个中间总调度。

当前旧语义大致是：

```text
用户请求
  -> resolve-pack-route.ps1
  -> orchestration-core
  -> brainstorming / writing-plans / subagent-driven-development / spec-kit-vibe-compat
```

这和新的产品目标冲突。新的目标是入口收敛：

```text
用户显式输入 $vibe
  -> vibe governed runtime
  -> 内部专家推荐
  -> vibe 保持总控
```

因此，本轮不是继续给 `orchestration-core` 做小修小补，而是把它从主动调度框架里移除，把有价值方法吸收到 `vibe` 阶段。

## 设计目标

1. `$vibe` / `/vibe` 是唯一公开治理入口。
2. `vibe` 是唯一运行时权威，负责六阶段推进和最终闭环。
3. `resolve-pack-route.ps1` 保留为内部专家推荐器，不再被描述成用户侧 canonical 入口。
4. `orchestration-core` 从 active pack 中移除，不再抢普通 planning、brainstorming、workflow、subagent 等宽泛请求。
5. 有价值的过程方法被揉进 `vibe` 阶段，而不是继续通过二级调度包调用。
6. 非 `$vibe` 的普通规划请求不进入 Vibe 治理路由。
7. 子代理开启逻辑回到 `vibe` 的 M/L/XL 阶段设计中。
8. 旧测试、golden、fixture、文档中的 `orchestration-core` 期望被同步迁移。

## 不做什么

本设计不要求第一步物理删除所有 skill 目录。

原因是部分目录可能仍有参考价值、脚本、兼容说明或历史 fixture。第一阶段先移除 active routing 身份，后续再按资产价值决定是否保留、迁移或删除目录。

本设计也不把 `resolve-pack-route.ps1` 删除。它仍然有价值，但身份要降级：

```text
不是入口
不是总调度
不是第二套 runtime
只是 vibe 内部的 specialist recommendation router
```

## 新架构

### 用户侧入口

用户侧只认两个公开治理入口：

```text
$vibe
/vibe
```

`vibe-upgrade` 仍然是单独升级入口，不归本轮 `orchestration-core` 治理范围。

非 `$vibe` 的普通请求，例如：

```text
先头脑风暴一下
请写实施计划
帮我拆任务
```

不再默认进入 Vibe-Skills 治理路由。宿主可以按普通对话或普通工具调用处理，不能因为这些宽泛词自动进入 `orchestration-core`。

### Vibe 内部阶段

`vibe` 继续保持六阶段：

| 阶段 | 职责 |
| --- | --- |
| `skeleton_check` | 检查项目骨架、已有文件、风险边界 |
| `deep_interview` | 澄清目标、吸收 brainstorming / dialectic / think-harder 的方法 |
| `requirement_doc` | 冻结需求和文件语义 |
| `xl_plan` | 吸收 writing-plans 的任务拆解、里程碑、验收标准 |
| `plan_execute` | 执行计划，按 M/L/XL 和依赖关系决定是否启用子代理 |
| `phase_cleanup` | 验证、清理、交付报告 |

### 内部专家推荐器

`scripts/router/resolve-pack-route.ps1` 继续可以返回候选 pack / skill，但语义变成：

```text
给 vibe 推荐可能需要哪些领域专家
```

它不能改变以下事实：

```text
runtime_selected_skill = vibe
runtime_authority = vibe
```

如果内部推荐器建议 `code-quality/systematic-debugging`、`data-ml/scikit-learn`、`docs-media/pdf`，这些都只是 specialist 候选。是否采纳、何时采纳、如何写入计划和验收，仍由 `vibe` 阶段决定。

## 旧能力迁移表

| 旧 skill / 能力 | 新归属 | 处理方式 |
| --- | --- | --- |
| `brainstorming` | `deep_interview` | 吸收发散方案、选项比较、用户意图澄清方法 |
| `think-harder` | `deep_interview` / `xl_plan` | 吸收高风险决策前的深度分析检查 |
| `dialectic` | `deep_interview` / `review` | 吸收多视角、反例、冲突检查 |
| `writing-plans` | `xl_plan` | 吸收实施计划、任务拆解、里程碑、验收标准 |
| `planning-with-files` | `requirement_doc` / `xl_plan` | 只吸收文件存储纪律；不得创建第二套根目录计划文件 |
| `subagent-driven-development` | `plan_execute` / `protocols/team.md` | 回到 M/L/XL 受控子代理策略 |
| `context-hunter` | `skeleton_check` / `plan_execute` | 吸收上下文检索、相似实现搜索 |
| `local-vco-roles` | `review` / `phase_cleanup` | 吸收角色化审查，但不作为主动路由 |
| `spec-kit-vibe-compat` | explicit compatibility | 只处理显式 `/speckit.*` 或 spec-kit 文件语义 |

## M/L/XL 子代理策略

子代理不再由 `orchestration-core/subagent-driven-development` 抢路由决定。

整改后由 `vibe` 的执行阶段决定：

| 等级 | 子代理策略 |
| --- | --- |
| M | 默认不开子代理，除非用户显式要求且任务确实可拆 |
| L | 可以建议子代理，但需要计划阶段说明理由和边界 |
| XL | 可以主动规划子代理，但必须经过需求冻结、计划确认、写入 delegation envelope、再执行 |

普通 coding/debug/review 不能因为任务是 XL 就静默进入子代理。

## 配置整改范围

实施阶段需要调整这些配置：

| 文件 | 目标 |
| --- | --- |
| `config/pack-manifest.json` | 移除 active `orchestration-core` pack |
| `config/runtime-contract.json` | 把 `canonical_router` 语义改成内部 specialist recommender |
| `config/retrieval-intent-profiles.json` | 移除 `orchestration-core` 推荐 pack |
| `config/skill-keyword-index.json` | 删除或迁移 `orchestration-core` 宽泛关键词 |
| `config/skill-routing-rules.json` | 确保子代理、spec-kit、规划类规则不再通过 `orchestration-core` 抢路由 |
| `config/vibe-entry-surfaces.json` | 保持 `vibe` 为 canonical runtime skill，不新增公开阶段入口 |

## 文档整改范围

需要把这些说法统一改掉：

```text
Canonical router picks which skill handles your task
```

改成：

```text
vibe is the runtime authority.
The internal specialist recommender may suggest skills, but it does not transfer authority away from vibe.
```

重点文档：

| 文件 | 目标 |
| --- | --- |
| `SKILL.md` | 将 `Canonical router` 改成 `Internal specialist recommendation router` |
| `protocols/runtime.md` | 重写 Key terms 和 Router Integration Rules |
| `scripts/router/README.md` | 明确这是内部推荐器，不是用户入口 |
| `docs/governance/orchestration-core-*.md` | 追加新治理说明，标记旧设计被替代 |

## 测试整改范围

旧测试里很多地方写死：

```text
selected_pack = orchestration-core
```

这些测试要迁移成新期望。

### 应删除或改写的旧期望

| 旧期望 | 新期望 |
| --- | --- |
| 普通 planning 命中 `orchestration-core/writing-plans` | 非 `$vibe` 不要求 Vibe 治理路由 |
| 头脑风暴命中 `orchestration-core/brainstorming` | `$vibe` 内由 `deep_interview` 吸收方法 |
| 子代理命中 `orchestration-core/subagent-driven-development` | `$vibe` 内由 `plan_execute` / `protocols/team.md` 决定 |
| `/speckit.plan` 命中 `orchestration-core/spec-kit-vibe-compat` | 显式 spec-kit compatibility，不属于 core |

### 新增防回归门禁

至少新增或更新这些断言：

1. `config/pack-manifest.json` 不存在 active `orchestration-core`。
2. `$vibe` canonical entry 仍然生成 `host-launch-receipt.json`、`runtime-input-packet.json`、`governance-capsule.json`、`stage-lineage.json`。
3. `runtime_selected_skill` 仍然是 `vibe`。
4. 内部推荐器可以推荐 specialist，但不能把 runtime authority 转移给 specialist。
5. 普通 planning prompt 不再期待 `orchestration-core`。
6. 明确子代理请求只有在 `$vibe` 的 M/L/XL 计划语义里进入子代理流程。
7. `planning-with-files` 不得在 Vibe session 外创建第二套根目录 `task_plan.md` / `progress.md` 语义。
8. spec-kit 只在显式 `/speckit.*` 或 spec-kit 文件语义下触发 compatibility。

## 迁移顺序

推荐按这个顺序实施：

1. 先更新文档术语，把 `canonical router` 改成内部专家推荐器，避免后续实现继续沿用错误概念。
2. 新增 hard-removal gate，先检查 active `orchestration-core` 仍存在，形成明确失败目标。
3. 从 `config/pack-manifest.json` 移除 `orchestration-core`。
4. 清理 `retrieval-intent-profiles`、keyword index、routing rules 里的 `orchestration-core` 引用。
5. 把 `brainstorming`、`writing-plans`、`subagent-driven-development` 的核心方法迁入 `vibe` 阶段文档和 runtime 输出语义。
6. 更新 router bridge、pack regression、routing stability、skill index、external corpus、golden replay 等测试。
7. 保留旧 skill 目录，先不物理删除，等资产迁移审计完成后再处理。
8. 运行 focused gates，再运行 pack smoke、offline skills、config parity、version packaging gates。
9. 写 governance note，说明旧 `orchestration-core` 设计被 hard removal 设计替代。

## 风险与控制

| 风险 | 控制 |
| --- | --- |
| 旧测试大量失败 | 分批迁移 golden 和 gate，先保留一条 hard-removal gate 作为主验收 |
| `$vibe` 入口被误伤 | 不改 `config/vibe-entry-surfaces.json` 的 canonical runtime skill |
| 内部专家推荐消失 | 保留 `resolve-pack-route.ps1`，只改语义和调用期望 |
| 子代理不再触发 | 把子代理规则迁入 `plan_execute` 和 `protocols/team.md`，用 M/L/XL gate 保护 |
| spec-kit 兼容失效 | 建立 explicit compatibility 期望，不挂在 `orchestration-core` 下 |
| 优秀 skill 内容丢失 | 第一阶段不物理删除目录；先做内容迁移表和资产审计 |

## 完成标准

本轮实施完成后，必须满足：

1. `config/pack-manifest.json` 不再有 active `orchestration-core`。
2. 文档不再把 `resolve-pack-route.ps1` 描述为用户侧入口或第二套调度权威。
3. `$vibe` 仍然是唯一公开治理入口和唯一 runtime authority。
4. 普通非 `$vibe` planning / brainstorming prompt 不再要求命中 Vibe-Skills 治理路由。
5. `$vibe` 内部仍然能推荐领域 specialist，但 specialist 不能替代 `vibe` 的需求、计划、执行、清理权威。
6. M/L/XL 子代理策略有测试保护。
7. spec-kit compatibility 不再依赖 `orchestration-core`。
8. 所有旧 `orchestration-core` golden、fixture、gate 都被改写、归档或删除，不能留下假通过。

## 推荐决策

采用硬移除设计：

```text
active orchestration-core：取消
vibe 阶段能力：增强
resolve-pack-route.ps1：保留为内部 specialist recommender
优秀过程方法：迁入 vibe 阶段
显式兼容命令：移出 core，单独治理
```

这比继续收缩 `orchestration-core` 更干净，也更符合入口收敛目标。
