# Adaptive Routing & Eval Governance

Wave52-57 关注的不是“立刻自动改路由”，而是先把 adaptive routing 所需的证据面与安全边界合同化。

## Guardrails

- 仍保持 `advice-first` / `shadow-first`
- 没有 replay ledger，不允许宣称 adaptive routing 可回放
- 没有 benchmark scenario，不允许宣称 adaptive routing 可评估
- 没有 promotion heuristic，不允许宣称 adaptive routing 可升级阶段

## Shadow-Ready Means

`shadow-ready` 仅表示：

- 已能记录候选路由建议
- 已能把建议与原始路由结果并行比较
- 已能把关键证据写入 replay ledger
- 仍不会自动替换 VCO 既有 canonical route
