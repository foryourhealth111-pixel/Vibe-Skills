# VCO Wave64-82 Formal Execution Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

**Date:** 2026-03-07
**Mode:** XL / unattended / vibe-first
**Program Goal:** 把前期已吸收的优秀项目价值，从“治理资产 / shadow 能力 / 策略合同”继续压缩为 VCO 可晋升、可评测、可回滚、可发布的默认能力候选；坚持 **先运行化，再扩张；先晋升，再新增吸收面**。

## 1. Program Position

Wave40-63 解决的是：
- runtime freshness
- BOM / frontmatter stop-ship 风险
- bundled / nested / installed 漂移
- capability dedup / adaptive routing readiness / upstream value ops

Wave64-82 的任务不再是“大面积继续吸新项目”，而是把现有吸收面做成可运行、可晋升、可产品化的 plane：
- Memory plane：`mem0` + `Letta`
- BrowserOps plane：`browser-use`
- DesktopOps plane：`Agent-S`
- Document plane：`Docling`
- Connector plane：`Composio` + `activepieces` + MCP connector landscape
- Prompt intelligence plane：`Prompt-Engineering-Guide` + 已蒸馏的 prompt / skill / route assets

## 2. Guardrails

1. **VCO remains the only control plane**：不得引入第二 orchestrator、第二默认执行 owner、第二默认记忆真源。
2. **Operationalization precedes new intake**：在至少 3 个 plane 达到 `soft` 可运行候选之前，不再扩张新的顶层吸收平面。
3. **Promotion is evidence-based**：任何 `shadow -> soft -> strict_candidate` 晋升，都必须有 gate、telemetry、replay、rollback 证据。
4. **Rollback-first remains mandatory**：每个可执行 plane 都必须有 fallback、kill switch、operator SOP。
5. **Cross-plane contracts beat ad-hoc scripts**：Browser / Desktop / Document / Connector 的动作必须逐步归一为统一任务合同。
6. **Prompt intelligence remains advisory-first**：Prompt 资产只能增强 pack/router/confirm，不得成为第二路由器。
7. **Release follows runtime truth**：未通过 freshness / coherence / release evidence 的能力，不得进入 promoted release 面。

## 3. Program Metrics

| Metric | Target by Wave82 | Meaning |
|---|---:|---|
| `soft_candidate_planes` | >= 4 | Memory / BrowserOps / DesktopOps / Document / Connector 中至少 4 个形成 soft 候选 |
| `strict_candidate_planes` | >= 2 | 至少 2 个平面进入 strict_candidate 而非停留在 shadow |
| `rollback_drill_pass_rate` | 100% | 所有 promoted candidate 的回滚演练通过 |
| `cross_plane_contract_coverage` | >= 80% | 高风险动作被统一任务合同覆盖 |
| `route_replay_coverage` | >= 80% | 路由与动作有可回放证据 |
| `release_evidence_completeness` | 100% | 所有 promoted candidate 都进入 release evidence 栈 |
| `new_top_level_planes_added` | 0 | 本轮不新增新的顶层控制平面 |

## 4. Execution Order

### Stage A — Plane Runtime Contracts First
先把每个 plane 从“理念吸收态”推进到“合同化、可评测态”：
- Wave64-66：Memory / Letta / Prompt policy spine
- Wave67-72：BrowserOps / DesktopOps / Document plane runtime contractization
- Wave73-75：Connector plane + Prompt intelligence productization

### Stage B — Cross-Plane Execution Unification
把局部 plane 变成系统能力：
- Wave76-77：统一 task contract / replay ledger
- Wave78：promotion board v2 + plane scorecards

### Stage C — Operations / Release Closure
把可运行能力接到 operator / release 面：
- Wave79-82：ops cockpit / drills / release train / closure gate

## 5. Wave Backlog

| Wave | Track | Title | Primary Goal | Upstream Value Source | Candidate Gate |
|---|---|---|---|---|---|
| 64 | memory-runtime | memory runtime v3 governance | 把 `mem0` / Letta / memory tier router 收束成统一 memory runtime contract | `mem0`, `Letta` | `vibe-memory-runtime-v3-gate.ps1` |
| 65 | memory-runtime | mem0 soft rollout pilot | 把 `mem0` 从 opt-in policy 提升到可审计的 soft pilot | `mem0` | `vibe-mem0-softrollout-gate.ps1` |
| 66 | memory-runtime | Letta conformance evaluator | 把 Letta policy vocabulary 变成可校验 contract / tool-rule / compaction 检查 | `Letta` | `vibe-letta-policy-conformance-gate.ps1` |
| 67 | browser-runtime | BrowserOps provider scorecard v2 | 把 `browser-use` 与既有 providers 做统一 scorecard / route evidence | `browser-use` | `vibe-browserops-scorecard-gate.ps1` |
| 68 | browser-runtime | BrowserOps soft rollout candidate | 形成 BrowserOps soft candidate，要求 fallback / telemetry / confirm bias 全量接线 | `browser-use` | `vibe-browserops-softrollout-gate.ps1` |
| 69 | desktop-runtime | DesktopOps replay suite | 为 Agent-S shadow 合同层建立 replay / failure taxonomy / checkpoint corpus | `Agent-S` | `vibe-desktopops-replay-gate.ps1` |
| 70 | desktop-runtime | DesktopOps soft candidate | 把 DesktopOps 从 shadow plan 推进到可运行 soft candidate，但仍禁止默认 takeover | `Agent-S` | `vibe-desktopops-softrollout-gate.ps1` |
| 71 | document-runtime | Docling extraction contract v2 | 形成 `Docling` 输出 schema、模板、admission filter 的第二代合同 | `Docling` | `vibe-docling-contract-v2-gate.ps1` |
| 72 | document-runtime | document plane benchmark | 为 Docling / markitdown / pdf/docx 路由建立 golden corpus 与 benchmark | `Docling`, document skills | `vibe-document-plane-benchmark-gate.ps1` |
| 73 | connector-runtime | connector admission scorecard | 把 connector landscape 变成有风险等级、能力映射、准入证据的 scorecard | `Composio`, `activepieces`, `awesome-mcp-servers` | `vibe-connector-scorecard-gate.ps1` |
| 74 | connector-runtime | connector action ledger | 为外部动作建立 action contract、side-effect ledger、rollback contract | `Composio`, `activepieces` | `vibe-connector-action-ledger-gate.ps1` |
| 75 | prompt-intelligence | prompt intelligence productization | 把 Prompt-Engineering-Guide 的模式沉淀为 prompt cards / risk checklist / route hints | `Prompt-Engineering-Guide` | `vibe-prompt-intelligence-productization-gate.ps1` |
| 76 | cross-plane | unified task contract | 打通 Browser / Desktop / Document / Connector 的统一任务合同 | multiple absorbed planes | `vibe-cross-plane-task-contract-gate.ps1` |
| 77 | cross-plane | replay and execution ledger | 把跨平面动作、confirm、rollback、replay 归一到一套 ledger | multiple absorbed planes | `vibe-cross-plane-replay-gate.ps1` |
| 78 | promotion | promotion board v2 | 把各 plane 的 scorecard / threshold / stage / evidence 并入 promotion board v2 | all current planes | `vibe-promotion-scorecard-gate.ps1` |
| 79 | operations | operator cockpit and SLOs | 把 telemetry / drift / replay / rollback 变成 operator 可读 cockpit 与 SLO | all promoted candidates | `vibe-ops-cockpit-gate.ps1` |
| 80 | operations | rollback and freshness drills | 把 rollback / install / freshness / parity drill 固化成 operator playbook | runtime governance | `vibe-rollback-drill-gate.ps1` |
| 81 | release | release train v2 | 把 soft / strict_candidate 的 release evidence、install SOP、operator readiness 统一到 release train | promoted planes | `vibe-release-train-v2-gate.ps1` |
| 82 | closure | wave64-82 closure gate | 对 Wave64-82 做 closure gate，并决定是否允许下一轮 upstream intake 扩张 | all tracks | `vibe-wave64-82-closure-gate.ps1` |

## 6. Deliverable Groups

### Wave64-66 — Memory Runtime & Policy Spine
目标：让 Memory plane 从“边界清晰”升级到“可运行、可检查、可晋升”。

Planned assets:
- `docs/memory-runtime-v3-governance.md`
- `config/memory-runtime-v3-policy.json`
- `references/memory-runtime-v3-contract.md`
- `scripts/verify/vibe-memory-runtime-v3-gate.ps1`
- `scripts/verify/vibe-mem0-softrollout-gate.ps1`
- `scripts/verify/vibe-letta-policy-conformance-gate.ps1`

### Wave67-72 — Browser / Desktop / Document Productization
目标：把 `browser-use`、`Agent-S`、`Docling` 从吸收态推进到 plane 候选运行态。

Planned assets:
- `docs/browserops-scorecard-governance.md`
- `config/browserops-scorecard.json`
- `docs/browserops-soft-rollout-governance.md`
- `docs/desktopops-replay-governance.md`
- `docs/desktopops-soft-rollout-governance.md`
- `docs/docling-contract-v2-governance.md`
- `docs/document-plane-benchmark-governance.md`
- `references/document-golden-corpus.md`

### Wave73-75 — Connector & Prompt Intelligence Productization
目标：把外部连接器和 prompt intelligence 从“资料与策略”推进到“可产品化的增强层”。

Planned assets:
- `docs/connector-scorecard-governance.md`
- `references/connector-action-ledger.md`
- `docs/prompt-intelligence-productization.md`
- `references/prompt-pattern-cards.md`
- `references/prompt-risk-checklist.md`

### Wave76-82 — Cross-Plane Promotion / Ops / Release Closure
目标：让 plane 不再是孤立 patch，而是进入统一合同、统一回放、统一晋升、统一发布。

Planned assets:
- `docs/cross-plane-task-contract-governance.md`
- `references/unified-task-contract.md`
- `docs/cross-plane-replay-governance.md`
- `references/cross-plane-replay-ledger.md`
- `docs/promotion-board-v2-governance.md`
- `references/plane-scorecards.md`
- `docs/ops-cockpit-governance.md`
- `docs/rollback-drill-governance.md`
- `docs/release-train-v2-governance.md`
- `scripts/verify/vibe-wave64-82-closure-gate.ps1`

## 7. Priority Rules

1. **Wave64 / 67 / 69 / 71 / 73 / 75 first**：先做每个 plane 的合同化与评分基线。
2. **Wave65 / 68 / 70 / 72 / 74 second**：再推进 soft rollout candidate。
3. **Wave76-82 last**：等局部 plane 有证据后，再做跨平面统一、ops、release。
4. **No new top-level intake before Wave78**：在 promotion board v2 出来之前，不新增新的顶层平面。

## 8. Exit Criteria

Wave64-82 完成，不以“文件写完”为准，而以以下条件为准：
- 至少 4 个 plane 形成 `soft_candidate`
- 至少 2 个 plane 形成 `strict_candidate`
- 所有 promoted candidate 都具备 rollback drill 与 release evidence
- cross-plane task contract 与 replay ledger 生效
- operator cockpit 可用于日常巡检
- Wave82 closure gate 明确给出下一轮 intake 是 `allow`、`hold` 还是 `narrow_only`

## 9. Recommended First Execution Slice

如果立即开始执行，推荐按以下顺序开工：
1. Wave64：memory runtime v3 governance
2. Wave67：BrowserOps provider scorecard v2
3. Wave69：DesktopOps replay suite
4. Wave71：Docling extraction contract v2
5. Wave73：connector admission scorecard
6. Wave75：prompt intelligence productization

这 6 个 wave 是整轮计划的“基座波”；没有它们，后面的 soft rollout、promotion、release 都会再次变成漂浮治理。
