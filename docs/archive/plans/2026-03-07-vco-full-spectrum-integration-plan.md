# VCO Full-Spectrum Integration Implementation Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

**Date:** 2026-03-07
**Scope:** Wave19-30
**Target:** 在不破坏 VCO 单一控制面、单一默认执行 owner、单一 canonical memory truth-source 的前提下，把 `mem0`、`Letta`、`Prompt-Engineering-Guide`、`browser-use`、`Agent-S` 及其衍生治理方法吸收到 VCO 的 Memory / Prompt / BrowserOps / DesktopOps / Governance / Observability 六个平面。

---

## 1. Program Guardrails

1. **Single control plane only**：VCO 仍是唯一控制面，不引入第二 orchestrator。
2. **Single execution default only**：任何 BrowserOps / DesktopOps 吸收都不得成为新的默认执行 owner。
3. **Single memory truth-source only**：`state_store` / `Serena` / `ruflo` / `Cognee` 的 canonical 边界保持不变。
4. **Advice-first / shadow-first / rollback-first**：所有新增吸收面默认从 `off` 或 `shadow` 起步。
5. **No docs+config+script+gate, no absorption claim**：没有文档、配置、脚本与门禁，不能宣称“已吸收”。
6. **Evidence before promotion**：只有 pilot 场景、promotion board、verify gates 同时给出正向证据，才可进入 soft/strict/promote。

## 2. Execution Order

| Wave | Theme | Primary Outcome | Required Verify |
|---|---|---|---|
| 19 | Admission Closure | 统一准入与落点边界 | `vibe-ecosystem-absorption-contract-gate.ps1` |
| 20 | Memory Runtime v2 | 固化 memory tier contract | `vibe-memory-tier-gate.ps1` |
| 21 | Mem0 Opt-in Backend | `mem0` 成为 opt-in external preference backend | `vibe-mem0-backend-gate.ps1` |
| 22 | Letta Policy Contracts | `Letta` 成为 policy / contract source | `vibe-letta-contract-gate.ps1` |
| 23 | Prompt Intelligence | PEG 转成 pattern/risk/checklist 资产层 | `vibe-prompt-intelligence-assets-gate.ps1` |
| 24 | BrowserOps Provider Router | `browser-use` 进入 provider candidate 平面 | `vibe-browserops-gate.ps1` |
| 25 | DesktopOps Shadow Advisor | `Agent-S` 进入 DesktopOps shadow 合同层 | `vibe-desktopops-shadow-gate.ps1` |
| 26 | Cross-Plane Conflict | 解决 memory/prompt/browser/desktop 冲突 | `vibe-cross-plane-conflict-gate.ps1` |
| 27 | Promotion Board | 建立 evidence-gated rollout / rollback | `vibe-promotion-board-gate.ps1` |
| 28 | Pilot & Eval | 用四类 pilot 场景验证新平面 | `vibe-pilot-scenarios.ps1` |
| 29 | Bundled Mirror & Packaging | 把新增资产同步到 bundled 镜像 | `sync-bundled-vibe.ps1` + packaging gates |
| 30 | Scoped Promotion & Release Cut | 在证据充分的前提下做最小 promotion 与 release cut | version / packaging / parity gates |

---

## 3. Wave Backlog

### Task 1: Wave 19 — Admission Closure

**Files**
- `docs/ecosystem-absorption-dedup-governance.md`
- `docs/absorption-admission-matrix.md`
- `docs/external-tooling/mcp-vs-skill-vs-manual.md`

**Outcome**
- 明确 external resource 只能落到 `skill` / `provider-candidate` / `contract-source` / `reference-source` / `manual-workflow` 之一。
- 明确 MCP server 不等于 skill，不等于 orchestrator。
- 明确“重复功能默认不重复吸收，只吸收治理价值或合同价值”。

**Verify**
- `pwsh -File .\scripts\verify\vibe-ecosystem-absorption-contract-gate.ps1`

**Rollback Statement**
- 若 admission contract 无法自洽，则冻结后续 wave，回退到总纲唯一解释权。

### Task 2: Wave 20 — Memory Runtime v2 Contractization

**Files**
- `docs/design/memory-runtime-v2-integration.md`
- `config/memory-tier-router.json`
- `references/memory-block-contract.md`
- `scripts/verify/vibe-memory-tier-gate.ps1`
- `docs/design/memory-governance-integration.md`

**Outcome**
- 把 session / project_decision / short_term_semantic / long_term_graph / external_preference / policy_contract 六类 memory tier 明确化。
- 明确 `episodic-memory` 继续禁用。

**Verify**
- `pwsh -File .\scripts\verify\vibe-memory-governance-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-memory-tier-gate.ps1`

**Rollback Statement**
- 若 memory tier 出现 owner 重叠，立刻移除新增 tier 映射并保留原 memory governance。

### Task 3: Wave 21 — Mem0 Opt-in Backend

**Files**
- `docs/design/mem0-optin-backend-integration.md`
- `config/mem0-backend-policy.json`
- `scripts/governance/invoke-mem0-policy.ps1`
- `scripts/verify/vibe-mem0-backend-gate.ps1`

**Outcome**
- `mem0` 只允许保存 preference / style_hint / recurring_constraint。
- 禁止 `route_assignment`、`canonical_project_decision`、`primary_session_state`。

**Verify**
- `pwsh -File .\scripts\verify\vibe-mem0-backend-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-memory-tier-gate.ps1`

**Rollback Statement**
- 任何 forbidden payload 被接收，都回退到 `enabled=false` 或 `mode=off`。

### Task 4: Wave 22 — Letta Policy Contracts

**Files**
- `docs/design/letta-policy-integration.md`
- `config/letta-governance-contract.json`
- `references/tool-rule-contract.md`
- `scripts/verify/vibe-letta-contract-gate.ps1`

**Outcome**
- 把 `Letta` 吸收为 `memory blocks` / `archival search contract` / `tool rules` / `token pressure policy` 的 vocabulary source。
- 明确禁止 runtime takeover、route mutation、second orchestrator。

**Verify**
- `pwsh -File .\scripts\verify\vibe-letta-contract-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-router-contract-gate.ps1`

**Rollback Statement**
- 任何 Letta contract 试图拥有 runtime authority，立即回退为 reference-only。

### Task 5: Wave 23 — Prompt Intelligence Layer

**Files**
- `references/prompt-pattern-cards.md`
- `references/prompt-risk-checklist.md`
- `docs/governance/prompt-intelligence-governance.md`
- `config/prompt-intelligence-policy.json`
- `scripts/verify/vibe-prompt-intelligence-assets-gate.ps1`
- `docs/design/prompt-overlay-integration.md`

**Outcome**
- Prompt-Engineering-Guide 被吸收为 pattern cards、risk checklist、policy input，而不是第二 prompt router。
- `allow_route_override = false`、`allow_second_prompt_surface = false`。

**Verify**
- `pwsh -File .\scripts\verify\vibe-prompt-intelligence-assets-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-prompt-overlay-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-prompt-asset-boost-gate.ps1`

**Rollback Statement**
- 若 prompt intelligence 影响 selected pack/skill，则立刻回退到 reference-only。

### Task 6: Wave 24 — BrowserOps Provider Router

**Files**
- `docs/design/browserops-provider-integration.md`
- `config/browserops-provider-policy.json`
- `references/browser-task-contract.md`
- `scripts/overlay/suggest-browserops-provider.ps1`
- `scripts/verify/vibe-browserops-gate.ps1`
- `docs/design/turix-cua-overlay.md`

**Outcome**
- 把 `browser-use` 定义为 BrowserOps provider candidate。
- 保留现有 `API / Playwright / Chrome / TuriX-CUA` 面，禁止 browser-use takeover。
- provider suggestion 只输出建议、理由、置信度、是否需要确认。

**Verify**
- `pwsh -File .\scripts\verify\vibe-browserops-gate.ps1`

**Rollback Statement**
- 若 provider policy 允许隐式接管，则回退到现有 TuriX/Playwright/API 路径。

### Task 7: Wave 25 — DesktopOps Shadow Advisor

**Files**
- `docs/design/agent-s-shadow-integration.md`
- `config/desktopops-shadow-policy.json`
- `references/aci-dsl.md`
- `references/openworld-task-contract.md`
- `scripts/verify/vibe-desktopops-shadow-gate.ps1`

**Outcome**
- 把 `Agent-S` 的 ACI / DAG / open-world 价值收敛到 DesktopOps shadow/advisory/contract 层。
- 禁止默认执行接管与隐式 promote。

**Verify**
- `pwsh -File .\scripts\verify\vibe-desktopops-shadow-gate.ps1`

**Rollback Statement**
- 若 desktop shadow 被识别为默认执行 owner，则立即回退到 `off` 或 `shadow`。

### Task 8: Wave 26 — Cross-Plane Conflict Governance

**Files**
- `docs/governance/cross-plane-conflict-governance.md`
- `config/cross-plane-conflict-policy.json`
- `scripts/verify/vibe-cross-plane-conflict-gate.ps1`
- `references/conflict-rules.md`

**Outcome**
- 明确 memory / prompt / browser / desktop 的优先级、禁止条件、人工确认边界。
- 明确“prompt/policy 只能 advisory，browser/desktop 不能越权到 control plane，memory 不能变成 route owner”。

**Verify**
- `pwsh -File .\scripts\verify\vibe-cross-plane-conflict-gate.ps1`

**Rollback Statement**
- 任一平面试图跨越 contract scope 时，冻结该平面并降回 `shadow`。

### Task 9: Wave 27 — Promotion Board Governance

**Files**
- `docs/promotion-board-governance.md`
- `config/promotion-board.json`
- `scripts/governance/publish-absorption-soft-rollout.ps1`
- `scripts/verify/vibe-promotion-board-gate.ps1`
- `docs/governance/observability-consistency-governance.md`

**Outcome**
- 定义 shadow → soft → strict → promote 的证据门槛。
- 明确 rollback owner、rollback command、freeze triggers、negative signals。
- 发布脚本仅做 advice-first soft rollout，不做危险自动 promote。

**Verify**
- `pwsh -File .\scripts\verify\vibe-promotion-board-gate.ps1`

**Rollback Statement**
- rollout 失败时不自动 promote；仅输出 rollback 建议与手动回退命令。

### Task 10: Wave 28 — Pilot Scenarios and Evaluation Harness

**Files**
- `docs/pilot-scenarios-and-eval.md`
- `scripts/verify/vibe-pilot-scenarios.ps1`
- `scripts/verify/fixtures/pilot-memory.json`
- `scripts/verify/fixtures/pilot-prompt.json`
- `scripts/verify/fixtures/pilot-browserops.json`
- `scripts/verify/fixtures/pilot-desktopops.json`

**Outcome**
- 用四个 pilot fixtures 覆盖 memory / prompt / browser / desktop 四个平面。
- gate 能读取场景并给出 pass/fail。

**Verify**
- `pwsh -File .\scripts\verify\vibe-pilot-scenarios.ps1`

**Rollback Statement**
- pilot 未通过时，新增平面不得离开 shadow。

### Task 11: Wave 29 — Bundled Mirror and Packaging

**Files**
- `bundled/skills/vibe/**`（通过同步生成）
- `docs/README.md`
- `references/index.md`
- `scripts/verify/README.md`
- `config/upstream-lock.json`

**Outcome**
- 把新增 docs / config / references / scripts 同步到 bundled mirror。
- 更新 verify index、docs navigation、upstream lock。

**Verify**
- `pwsh -File .\scripts\governance\sync-bundled-vibe.ps1 -PruneBundledExtras`
- `pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1`

**Rollback Statement**
- bundled 与 canonical 不一致时，冻结 release cut，优先修复镜像一致性。

### Task 12: Wave 30 — Scoped Promotion and Release Cut

**Files**
- `config/version-governance.json`
- `references/changelog.md`
- `references/release-ledger.jsonl`
- `docs/releases/v2.3.29.md`（目标版本）

**Outcome**
- 在证据充分前提下，仅对通过 promotion board 的子面进入 soft 或 strict。
- 产出新的 release note / changelog / ledger 记录。

**Verify**
- `pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1`

**Rollback Statement**
- 任何关键 gate 失败时，取消 release cut，保持当前稳定版本为准。

---

## 4. Validation Strategy

### New Gates
- `vibe-ecosystem-absorption-contract-gate.ps1`
- `vibe-memory-tier-gate.ps1`
- `vibe-mem0-backend-gate.ps1`
- `vibe-letta-contract-gate.ps1`
- `vibe-prompt-intelligence-assets-gate.ps1`
- `vibe-browserops-gate.ps1`
- `vibe-desktopops-shadow-gate.ps1`
- `vibe-cross-plane-conflict-gate.ps1`
- `vibe-promotion-board-gate.ps1`
- `vibe-pilot-scenarios.ps1`

### Existing Gates That Must Still Pass
- `vibe-router-contract-gate.ps1`
- `vibe-routing-stability-gate.ps1`
- `vibe-prompt-overlay-gate.ps1`
- `vibe-prompt-asset-boost-gate.ps1`
- `vibe-memory-governance-gate.ps1`
- `vibe-version-consistency-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-config-parity-gate.ps1`

## 5. Completion Criteria

Wave19-30 只能在以下条件全部满足时视为完成：

1. 每个 wave 的 docs/config/scripts/gates 都存在且可读取。
2. 新增平面全部保持在 VCO 单一控制面下，不产生第二默认 owner。
3. `bundled/skills/vibe` 镜像同步完成且 parity gate 通过。
4. promotion board 与 pilot scenarios 有完整证据链。
5. release cut 产物完整，且关键 version / packaging / parity gates 全部通过。
