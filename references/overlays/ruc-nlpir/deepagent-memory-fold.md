## DeepAgent 记忆折叠（advice-only）

适用：长程任务/长对话需要“压缩上下文、保留关键决策与证据、方便续跑/交接”。

### 治理边界（必须遵守）

- VCO 禁用 `episodic-memory`
- 默认使用 state_store（会话级），只在用户明确批准时写 Serena（项目决策）

### 最小动作

输出一个结构化 memory fold：

- working_memory（目标/子目标/阻塞/下一步）
- tool_memory（用过什么、哪些有效、哪些失败、可用性）
- evidence_memory（Top 5 anchors：file:line 或 URL）
- decision_log（只记录真实做出的决定）
- resume_prompt（可复制到新会话继续）

推荐落盘到：`outputs/runtime/memory-fold.json`（并可选 `memory-fold.md`）

