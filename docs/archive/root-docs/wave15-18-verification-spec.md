# Wave15–18 Verification Spec

## Goal

本规范定义 Wave15–18 的最终验证边界：

- 它验证新增资产是否存在；
- 它验证关键术语、section、配置映射是否一致；
- 它不替代现有 prompt/tool/team/candidate 的原始 gate。

换言之，这个 gate 解决的是 **cross-artifact consistency**，不是重新证明整个 VCO 治理体系。

## Assertion Families

### 1. Existence assertions

必须存在的资产：

- `config/candidate-watch-decisions.json`
- `config/eval-slicing-policy.json`
- `config/skill-intake-priority.json`
- `config/xl-operator-checkpoints.json`
- `config/watch-lane-priority-bands.json`
- `docs/archive/root-docs/watch-portfolio-rationalization.md`
- `docs/eval-slicing-operationalization.md`
- `docs/design/xl-operator-playbook.md`
- `docs/archive/root-docs/wave15-18-execution-backlog.md`
- `docs/archive/root-docs/watch-lane-remaining-value-cases.md`
- `references/promotion-memos/wave15-18-promotion-prep.md`
- `docs/releases/wave15-18-release-packet.md`

### 2. Structural assertions

- watch lane 必须仍保持 `8` 个候选；
- watch 候选必须全部映射到 `watch-lane-priority-bands`；
- eval slicing 必须覆盖 `prompt / tool / team / portfolio`；
- XL checkpoints 数量不得少于 `5`；
- 所有新增 policy / slice / band 必须保留 `default_surface_change = false` 或等价 guardrail。

### 3. Section assertions

必须出现的文档块：

- backlog：`Wave15 / Wave16 / Wave17 / Wave18 / rollback`
- promotion prep：`decision_context / candidate_snapshot / dedup_review / rubric_summary / routing_impact / verification / rollback`
- release packet：`change-summary / evidence / gate-results / owner-and-landing-zone / degraded-mode / rollback-plan / retro-trigger`

### 4. Terminology assertions

整个 artifact set 中必须显式出现：

- `active`
- `watch`
- `hold`
- `pilot`
- `review-ready`
- `rollback-ready`

目的不是追求术语堆砌，而是确保 board 交付中没有遗漏关键决策语义。

## Pass Standard

`wave15-18-consistency-gate` 通过的最低条件：

- `0` 个硬失败；
- 所有 required files 存在；
- 所有 required sections 可被识别；
- “不扩大默认面”约束在 corpus 中可见。

## Failure Interpretation

如果 gate 失败：

- 允许的最高结论只能是 `hold` 或 `rollback-ready`；
- 不得继续宣称 Wave15–18 已进入 promotion stage；
- 必须修复文档或 policy 后再重新执行 gate。

## Output Artifacts

脚本输出：

- `outputs/verify/wave15-18-consistency-gate.json`
- `outputs/verify/wave15-18-consistency-gate.md`

其中：

- JSON 用于 machine-readable 审核与后续脚本集成；
- Markdown 用于 governance board 与人工复核。
