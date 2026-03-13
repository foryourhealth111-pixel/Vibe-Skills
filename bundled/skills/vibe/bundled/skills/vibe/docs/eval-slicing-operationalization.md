# Eval Slicing Operationalization

## 1. Why Wave16 Exists

Wave15 收口了 watch lane，但仅有 decision label 还不够。下一步必须把 `awesome-ai-tools`、`Prompt-Engineering-Guide`、`awesome-ai-agents-e2b` 的剩余价值转成 **真正能运行的治理资产**，否则“review-ready” 只是一个更好看的标签。

Wave16 的答案不是引入更多 prompt 或 agent runtime，而是建立 **evaluation slicing**：

- 用统一的切片语言解释 prompt / tool / team / portfolio 的差异；
- 让 operator 可以对 warning、hold、rollback-ready 作结构化说明；
- 让 board 拿到可比的 artifact，而不是杂乱的叙述。

---

## 2. What Gets Operationalized

本轮运行化的对象是三类剩余价值：

1. `awesome-ai-tools` 提供的 taxonomy 与风险分层视角；
2. `Prompt-Engineering-Guide` 提供的 prompt pattern / risk checklist 语言；
3. `awesome-ai-agents-e2b` 提供的执行隔离、degraded mode、rollback thinking 参考。

这些价值都被限制在 **slice policy + catalog + operator explanation**，而不是 runtime mutation。所有 slice 默认运行在 **shadow** / reporting-only 语义里，并且继续保留 **default surface** 不扩张的约束。

---

## 3. Operational Model

### 3.1 Slice 是什么

一个 slice 必须回答四个问题：

- 它属于哪个 `plane`？
- 它靠什么 `evidence_mode` 支撑？
- 它处于什么 `decision_horizon`？
- 它是否明确声明 `default_surface_change = false`？

只要这四点有任何一项不清楚，这个 slice 就不能进入 board-readable 资产。

### 3.2 Slice 解决什么问题

Wave16 重点解决的是：

- 如何把 prompt 风险解释与 regression 结果放在同一页上看；
- 如何把 tool taxonomy 变成 governance board 能理解的证据，而不是一堆外部名词；
- 如何把“执行隔离很重要”这种抽象说法，降到 hold / rollback-ready 这种可操作语义。

### 3.3 Slice 不解决什么问题

本轮明确不做：

- 不让 slice 直接控制 live router；
- 不让 slice 代替已有 gates；
- 不把 sandbox / agent runtime ideas 升级成新执行平面；
- 不因为 eval 维度更细，就自动推高 promotion readiness。

---

## 4. Expected Outputs

Wave16 完成后，最少要看到：

- `config/eval-slicing-policy.json`：统一 policy；
- `references/eval-slicing-taxonomy.md`：面向 operator / reviewer 的解释层；
- `outputs/governance/eval-slicing/eval-slicing-catalog.json|md`：catalog artifact；
- 与 Wave18 consistency gate 的字段对齐。

---

## 5. Governance Rule

任何新的 eval slice 如想进入正式 board 讨论，必须同时满足：

- 能挂到现有 artifact family；
- 能明确落在 `hold / review-ready / rollback-ready` 之一；
- 有 operator 可读解释；
- 不产生默认面扩张。

如果做不到，允许继续 research，但不得进入 promotion prep。

