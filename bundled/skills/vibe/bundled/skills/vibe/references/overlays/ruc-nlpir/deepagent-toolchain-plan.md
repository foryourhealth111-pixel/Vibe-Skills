## DeepAgent 工具链规划（advice-only）

适用：当任务是复合型/跨域型，或 VCO 路由出现 `confirm_required` 需要人工选技能时，用“工具发现 → 最小技能链 → 验证点”降低选择成本。

### 最小动作

1) 先把任务写成契约：

- 目标（1 句）
- 交付物（代码/报告/计划）
- 约束（不装重依赖/离线/时间等）

2) 跑一次 VCO 路由 probe（白盒）获取候选技能与 overlay 建议：

- `pwsh C:\Users\羽裳\.codex\skills\vibe\scripts\router\resolve-pack-route.ps1 -Prompt "<PROMPT>" -Grade L -TaskType planning -Probe -ProbeLabel "toolchain" -ProbeOutputDir outputs/runtime/router-probes`

3) 用 `deepagent-toolchain-plan` 输出一个链条（3–8 步）：

- 每步：skill/tool + 为什么 + 预期产物
- 至少 1 个可证伪验证点（tests/build/probe）
- 明确 fallback（工具不可用/无 key/无依赖时怎么退）

### 非目标（避免冗余）

- 不取代 VCO 的分级/冲突规则；只补齐“链条编排”能力
- 不做代码依赖图（GitNexus 负责）

