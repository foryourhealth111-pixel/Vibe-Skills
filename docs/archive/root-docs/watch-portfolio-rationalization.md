# Watch Portfolio Rationalization

## 1. Purpose

本文件把 `candidate-curation` 里的 `8` 个 `watch` 项做正式收口，明确哪些项目只是 **继续保留 advisory 价值**，哪些项目可以进入 **review-ready / pilot**，以及哪些项目必须继续 `hold`，从而避免在 Wave15 之后继续把“看起来有价值”和“现在应该吸收”混为一谈。

本轮判断仍坚持三条硬边界：

- **不扩大默认面**；
- **不自动改 live router**；
- **不把 connector / skill 发现源误当成受信运行面**。

---

## 2. Baseline

截至 `2026-03-06`：

- candidate leaderboard 处于 `7 active / 8 watch / 0 freeze / 0 retire`；
- `watch` 候选分别来自 `tool-governance`、`workflow-governance`、`skill-metadata`、`governance-taxonomy` 四个 cluster；
- 当前缺口不在“继续导入更多项目”，而在“把剩余价值转成受控资产，并给出 board-ready 决策口径”。

因此，Wave15 的目标不是提升任何 watch 项的默认等级，而是把 watch lane 明确拆成以下三类：

1. `review-ready`：剩余价值足够高，可以进入 board review，但仍保持 advisory / shadow-only；
2. `pilot`：存在清晰 pilot 入口，但必须 project-scoped、operator-visible、rollback-first；
3. `hold`：价值仍在，但在当前阶段引入只会造成冗余、重叠或治理噪声。

---

## 3. Decision Table

| Candidate | Cluster | Decision | Why now | Why not promote |
| --- | --- | --- | --- | --- |
| `awesome-ai-tools` | `governance-taxonomy` | `review-ready` | 还能继续支持 eval slicing 与治理分层 | 其价值是 taxonomy，不是直接 runtime surface |
| `awesome-mcp-servers` | `tool-governance` | `review-ready` | 可继续作为 intake registry snapshot 来源 | 不能把外部列表当受信 registry |
| `activepieces` | `tool-governance` | `pilot` | project-scoped automation 模板仍有价值 | connector 写路径和 blast radius 仍偏大 |
| `composio` | `tool-governance` | `pilot` | session-scoped connector contract 值得保留 | 连接器生态过宽，不适合默认面 |
| `awesome-vibe-coding` | `workflow-governance` | `review-ready` | 还能提炼 XL operator discipline | 不应转成第二套默认指令系统 |
| `awesome-agent-skills` | `skill-metadata` | `hold` | 可用于 gap-driven mining | 现在继续导入会放大 overlap |
| `awesome-claude-skills-composio` | `skill-metadata` | `hold` | 仅保留 spec / connector example 价值 | 与 antigravity / claude-skills / composio 高重叠 |
| `awesome-ai-agents-e2b` | `workflow-governance` | `hold` | 保留 execution isolation 参考 | 当前需要的是治理资产，不是第二执行底座 |

---

## 4. Bucket Interpretation

### 4.1 `review-ready`

`review-ready` 不等于 promotion-ready。它只表示：

- 剩余价值已经足够明确；
- 落点已经限定在 `documentation / policy / shadow-eval / board prep`；
- 下一步可以进入 governance board 讨论是否继续运行化；
- **仍然不允许 default surface change**。

本轮进入 `review-ready` 的是：

- `awesome-ai-tools`
- `awesome-mcp-servers`
- `awesome-vibe-coding`

这三项的共同点是：它们能继续增强 VCO 的 **分类、评测、操作纪律、intake 视角**，但都不构成直接扩容默认运行面的理由。

### 4.2 `pilot`

`pilot` 只适用于已经存在清晰 landing zone，但风险仍显著高于 advisory 资产的项目。

本轮限定：

- `activepieces`
- `composio`

共同治理要求：

- project-scoped enablement；
- read-only-first 或最小 connector subset；
- 变更必须保留 rollback-ready 路径；
- 任何 write-path 都不能绕过 board 与 operator 审查。

### 4.3 `hold`

`hold` 不是否定价值，而是承认“现在继续吸收的边际收益低于冗余成本”。

本轮 `hold` 的项目主要体现两类问题：

- **高重叠**：已经能从 active lane 或更高质量来源中获得相同结构价值；
- **高噪声**：继续导入只会进一步恶化 skill/role/connector 去重压力。

---

## 5. What Wave15 Actually Closes

Wave15 的收口结果是：

- 给每个 watch candidate 一个正式 decision label；
- 明确哪些只是 `review-ready`，哪些只是 `pilot`，哪些继续 `hold`；
- 把“剩余价值”从泛泛表述收缩到明确 landing zone；
- 为 Wave16–18 提供 board-readable 的输入，而不是直接推进 default promotion。

换句话说，Wave15 解决的是 **治理口径清晰化**，不是“再推进一轮默认吸收”。

---

## 6. Guardrails for Next Waves

进入 Wave16–18 时，必须继续保留以下约束：

- review-ready 项只允许进入 `shadow`, `reporting-only`, `board-prep`；
- pilot 项只允许进入 `gated`, `project-scoped`, `rollback-ready` 的运行化；
- hold 项只有在出现明确 gap 且 active lane 无法满足时，才能重新开议；
- 本文不是 promotion memo，也不是 release approval；
- 任何“提升默认面”的主张都必须回到 release packet 与 promotion board 审查。
