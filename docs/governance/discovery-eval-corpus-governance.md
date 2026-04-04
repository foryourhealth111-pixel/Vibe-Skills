# Discovery / Eval Corpus Governance

## 1. 目标

Wave38 要解决的问题不是“再接入几个社区仓库”，而是把 `awesome-vibe-coding`、`awesome-ai-tools`、`vibe-coding-cn`、`awesome-ai-agents-e2b` 的剩余价值沉淀为 **discovery / eval / capability material layer**。

这意味着：

1. VCO 仍然是唯一控制面与执行编排入口。
2. `config/capability-catalog.json` 记录 capability slice 与 material-layer retained value。
3. discovery/eval 语料只能进入 catalog、pilot、evidence、gate，不得形成新的运行入口。
4. 保证这些上游不会变成第二 runtime surface / second runtime surface。

## 2. Canonical 边界

### 2.1 控制权边界

- **唯一 orchestrator**：VCO 仍然是唯一运行时编排面。
- **唯一 team execution owner**：team-template / protocol 仍然决定执行所有权。
- **唯一 runtime surface**：curated list 只能成为 material layer，不得长成新的 runtime entrypoint。

### 2.2 Canonical 落点

本 wave 相关 canonical 资产限定为：

- `docs/governance/discovery-eval-corpus-governance.md`
- `references/capability-catalog.md`
- `config/capability-catalog.json`
- `scripts/verify/vibe-capability-catalog-gate.ps1`
- `docs/external-tooling/upstream-eval-pilot-scenarios.md`

## 3. Upstream → Material layer 映射

| Upstream | 保留价值 | Canonical landing | 明确不吸收 |
|---|---|---|---|
| `awesome-vibe-coding` | workflow heuristics、社区提示表达、vibe-style anti-pattern | discovery corpus / capability slice | 新的 vibe runtime、社区 prompt 直连 router |
| `awesome-ai-tools` | 工具生态 watchlist、能力缺口、供应商分类 | discovery corpus / tool landscape evidence | 新 tool registry runtime surface |
| `vibe-coding-cn` | 中文任务表达、术语对齐、localized eval prompts | localization corpus / eval scenario | 独立中文 router |
| `awesome-ai-agents-e2b` | sandbox / E2B / remote execution eval pattern、环境隔离案例 | eval corpus / pilot scenario | 新 sandbox execution owner |

## 4. Material layer 模型

material layer 只回答三类问题：

1. 这个上游还剩什么 retained value？
2. 它和现有 capability / pack / template 重叠在哪里？
3. 它应该保留为 discovery 证据、eval 试点，还是仅作参考？

它**不**负责：

- 改写 pack 路由；
- 引入新的 team owner；
- 引入新的 tool runtime；
- 直接发布新的 skill / tool surface。

## 5. Capability catalog 边界

### 5.1 capability slice，不是第二 orchestrator

`config/capability-catalog.json` 的每个条目描述的是：

- capability slice；
- retained value；
- applicable plane；
- dedup 关系；
- retirement condition；
- materialization boundary。

它不是新的 pack manifest，也不是新的 orchestrator。

### 5.2 禁止第二 runtime surface

对所有 `discovery_corpus` / `eval_corpus` 条目，必须满足：

- `materialization.mode = material_only`
- `materialization.runtime_surface = none`
- `materialization.canonical_owner` 指向现有 canonical 资产

否则视为越界。

## 6. 去冗余规则

1. curated list 的 retained value 先做 `dedup_with` 声明，再决定 landing。
2. 能被现有 capability 吸收的，不再生成第二份 runtime-facing 条目。
3. 只能做 discovery / eval 证据的，必须保持 material-only。
4. 无法解释 canonical owner 的条目，不应进入 catalog。

## 7. Gate 责任

`vibe-capability-catalog-gate.ps1` 至少验证：

- schema 顶层字段存在；
- Deep Discovery 兼容字段仍在；
- 4 个 upstream source 已登记；
- material-only 条目全部 `runtime_surface = none`；
- skills 都来自 `config/skills-lock.json`；
- 文档与 pilot scenario 能解释边界与去冗余。

## 8. Promotion 前的状态说明

在 promotion board / index / tool-registry 尚未显式接线之前，这些资产只承担：

- discovery evidence
- eval pilot input
- capability ledger accounting
- dedup / boundary governance

而不承担 runtime authority。

## 9. 当前结论

> `awesome-vibe-coding`、`awesome-ai-tools`、`vibe-coding-cn`、`awesome-ai-agents-e2b` 只被吸收到 discovery / eval / capability material layer；它们可以影响 catalog、pilot、evidence，但不能直接长成第二 runtime surface / second runtime surface。

## 10. 2026-03-17 Wave D Re-Audit Notes

- `awesome-vibe-coding` 在 2026-03 继续新增 workflow/tool references，适合刷新 discovery phrasing 与 anti-pattern evidence，但不形成新的 vibe runtime。
- `vibe-coding-cn` 持续更新 Codex guidance 与 multi-agent 说明，适合补强中文术语、localized eval prompts 与 discovery 语料，但不允许长出独立中文 router。
- `awesome-ai-tools` 仍是宽泛 watchlist，适合登记 capability gap 与 vendor landscape，不适合作为新的 tool registry runtime。
- `awesome-ai-agents-e2b` 近期更新明显放缓，但其 sandbox / remote execution 示例仍能服务 eval corpus；因此保留为 eval-only material layer，不进入执行 owner。
