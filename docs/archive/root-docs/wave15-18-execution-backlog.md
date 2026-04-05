# VCO Wave15–18 正式执行文档

## 1. 文档目的

本文件把 Wave15–18 的执行范围正式收敛为一组 **可验证、可回滚、可交付** 的 backlog。相较于 Wave10–14，本轮不再继续扩大吸收面，而是贯彻两条主线：

1. **先收口，再扩张**；
2. **先运行化，再新增吸收面**。

因此，Wave15–18 的重点不是“再从 15 个项目中吸更多东西”，而是把这些项目的剩余价值压缩成 VCO 可以稳定持有的资产：

- watch lane 的正式决策；
- evaluation slicing 的运行化；
- XL operator checkpoints 与 intake priority；
- consistency gate、promotion prep、release packet。

---

## 2. 承接基线

按 `2026-03-06` 的治理基线：

- `governance_score = 94.3`
- `promotion_readiness = review-required`
- `7 active / 8 watch / 0 freeze / 0 retire`
- `prompt-intelligence-gate = pass_with_warning`
- `skill-metadata-gate = 4766 / 4766 pass`

这意味着本轮执行必须遵守：

- 不能把 `watch` 候选直接推成默认面；
- 不能让 shadow / advisory 结果直接改 live router；
- 不能因为文档或 taxonomy 更完整，就跳过 board review；
- 必须把 rollback-ready 写成明确资产，而不是口头承诺。

---

## 3. Wave15–18 总览

| Wave | 核心目标 | 产物类型 | 结果姿态 |
| --- | --- | --- | --- |
| Wave15 | 收口 `watch` 组合 | decision register + review + gate | board-readable, reporting-only |
| Wave16 | 运行化评测切片 | eval policy + taxonomy + catalog | shadow / explanation-first |
| Wave17 | 运行化协作纪律 | intake priority + checkpoints + playbook | XL operator standard |
| Wave18 | 组合优化与交付 | consistency gate + promotion prep + release packet | review-ready / rollback-ready |

---

## 4. Wave15 Backlog — Watch Lane 收口

### 4.1 Objective

把 `8` 个 watch 候选从“继续观察”升级为“有正式 decision label、有 landing zone、有下一步动作”的治理资产。

### 4.2 Deliverables

- `config/candidate-watch-decisions.json`
- `scripts/research/build-watch-portfolio-review.ps1`
- `scripts/verify/watch-portfolio-gate.ps1`
- `docs/archive/root-docs/watch-portfolio-rationalization.md`
- `outputs/governance/watch-portfolio/watch-portfolio-review.json|md`
- `outputs/verify/watch-portfolio-gate.json|md`

### 4.3 Definition of Done

- 八个 watch 候选全部有 `hold / pilot / review-ready` 之一；
- 每个候选都写明 `landing_zone` 与 `next_action`；
- gate 能证明：
  - 仍停留在 watch lane；
  - 没有 default surface expansion；
  - 文档保留 board 语言与 guardrails。

### 4.4 Rollback Rule

若任何 watch 候选被错误表述为默认晋升路径，回退到 `watch` 文案，并重新执行 portfolio gate。

---

## 5. Wave16 Backlog — Eval Slicing 运行化

### 5.1 Objective

把 `awesome-ai-tools`、`Prompt-Engineering-Guide`、`awesome-ai-agents-e2b` 的剩余价值落成 **evaluation slicing policy**，供 operator 与 governance board 使用。

### 5.2 Deliverables

- `config/eval-slicing-policy.json`
- `references/eval-slicing-taxonomy.md`
- `scripts/research/build-eval-slicing-catalog.ps1`
- `docs/eval-slicing-operationalization.md`
- `outputs/governance/eval-slicing/eval-slicing-catalog.json|md`

### 5.3 Definition of Done

- 切片能覆盖 `prompt / tool / team / portfolio` 四个 plane；
- 每个 slice 都带有 `evidence_mode`、`decision_horizon`、`default_surface_change = false`；
- catalog 可生成 machine-readable 与 human-readable 产物；
- operator 文档能解释 slice 的用途与边界。

### 5.4 Rollback Rule

若发现某个 eval slice 被当成 runtime 路由控制输入，则将该 slice 降回 `reference-only`，并更新 policy / docs。

---

## 6. Wave17 Backlog — XL Operator 与 Intake 运行化

### 6.1 Objective

从 `awesome-vibe-coding`、`vibe-coding-cn`、`awesome-agent-skills` 的剩余价值中提炼 **XL 执行纪律**，而不是引入新的默认命令面。

### 6.2 Deliverables

- `config/skill-intake-priority.json`
- `docs/archive/config/xl-operator-checkpoints.json`
- `scripts/research/build-xl-operator-checklist.ps1`
- `docs/design/xl-operator-playbook.md`
- `outputs/governance/xl-operator/xl-operator-checklist.json|md`

### 6.3 Definition of Done

- intake 至少分成 `bridge-core-gap / operator-lift / niche-pilot / hold-until-gap` 四类；
- XL checkpoints 覆盖 `intake → wave contract → sync → verification → board handoff`；
- playbook 明确说明高并发如何避免重复吸收、文件竞争、无证据宣称。

### 6.4 Rollback Rule

若 playbook 被错误理解为“新的默认 router 规则”，则其状态退回 documentation-only，并阻断任何 runtime 绑定。

---

## 7. Wave18 Backlog — 组合优化、验证与交付

### 7.1 Objective

把 Wave15–17 的资产组合成 **board-ready but non-promoting** 的正式交付包。

### 7.2 Deliverables

- `config/watch-lane-priority-bands.json`
- `docs/archive/root-docs/watch-lane-remaining-value-cases.md`
- `references/candidate-case-files/remaining-value-case-matrix.md`
- `scripts/verify/wave15-18-consistency-gate.ps1`
- `docs/archive/root-docs/wave15-18-verification-spec.md`
- `references/promotion-memos/wave15-18-promotion-prep.md`
- `docs/archive/releases/wave15-18-release-packet.md`
- `outputs/verify/wave15-18-consistency-gate.json|md`

### 7.3 Definition of Done

- consistency gate 能检查关键 config / docs / memo / packet 的结构与术语；
- release packet 明确 `change-summary / evidence / gate-results / owner-and-landing-zone / degraded-mode / rollback-plan / retro-trigger`；
- promotion prep 能把 `review-ready / pilot / hold / rollback-ready` 的边界说清楚；
- 交付结果仍保持 `advice-first / shadow-first / rollback-first`。

### 7.4 Rollback Rule

若 consistency gate 失败或 release packet 缺段，则本轮允许的最高状态只能是 `hold` 或 `rollback-ready`，不得继续对外宣称“可晋升”。

---

## 8. Success Metrics

本轮完成标准采用可量化口径：

- watch lane 决策覆盖率：`8 / 8`
- eval slicing planes 覆盖数：`4`
- XL checkpoints 数量：`>= 5`
- release packet 必填 section 覆盖率：`100%`
- consistency gate：`0 hard fail`

---

## 9. Out of Scope

Wave15–18 明确不做：

- 不新增 live router 默认面；
- 不自动推广任何 watch candidate；
- 不把 Activepieces / Composio 变成默认写操作控制面；
- 不把外部 skills 目录当成可直接导入的 VCO runtime surface；
- 不宣称 15 个项目的价值“已被彻底榨干”。

---

## 10. Board Handoff Statement

Wave15–18 的交付口径应被理解为：

- `watch` 已收口；
- `remaining value` 已被压缩为可管理资产；
- `promotion discussion` 的输入已经准备好；
- 但 **默认面扩张仍未被批准**。
