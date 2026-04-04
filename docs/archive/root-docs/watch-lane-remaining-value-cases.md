# Watch Lane Remaining-Value Cases

## Purpose

本文件把 watch lane 中仍然值得继续榨取的价值，整理成 **案例化资产**，用于回答一个更严格的问题：

> 哪些价值还能继续用？应该怎么用？为什么现在还不能直接吸收？

这里的关键词不是“还能吸多少”，而是“还能在不制造冗余的前提下提炼出什么”。

---

## Case Buckets

### 1. `high-yield-advisory`

适用于：

- `awesome-ai-tools`
- `awesome-mcp-servers`
- `awesome-vibe-coding`

共同特征：

- 仍有明显信息价值；
- 可以被转成 taxonomy、intake map、operator playbook；
- 不需要碰默认运行面。

允许吸收方式：

- docs / policy / catalog / board artifacts
- shadow evaluation or intake comparison

明确不允许：

- 直接启用 router defaults
- 把 discovery list 当 approved runtime registry

### 2. `gated-pilot-only`

适用于：

- `activepieces`
- `composio`

共同特征：

- 剩余价值在 control plane / connector subset / template layer；
- 一旦失控，容易扩大 write-path 和 blast radius。

允许吸收方式：

- project-scoped template
- read-only-first or minimum connector subset
- explicit rollback-ready pilot

明确不允许：

- 默认写操作
- 无 operator 可见性的自动启用

### 3. `hold-until-gap`

适用于：

- `awesome-agent-skills`
- `awesome-claude-skills-composio`
- `awesome-ai-agents-e2b`

共同特征：

- 不是没有价值；
- 而是当前的价值已被 active lane、现有 policy 或更优来源部分覆盖；
- 继续吸收会带来更高 overlap / noise / governance cost。

允许吸收方式：

- 只在明确 gap 出现时做 targeted extraction
- 只抽 spec delta、role pattern、isolation idea

明确不允许：

- 因为“项目很强”就继续入库
- 把 hold 项包装成 latent promotion queue

---

## Practical Use

这些案例材料适合被用于：

- quarterly governance board
- release packet evidence
- watch expiry review
- pilot proposal rebuttal

不适合被用于：

- 宣称“价值已经全部榨取干净”
- 宣称“下一步就是 promotion”
- 绕开 candidate curation 与 release packet 流程

---

## Output Constraint

本文件所有案例都必须服从同一个限制：

- **不扩大默认面**；
- **不自动改 live router**；
- **不让 advisory 资产伪装成批准态资产**。

