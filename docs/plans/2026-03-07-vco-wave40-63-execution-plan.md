# VCO Wave40-63 Formal Execution Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

> **Execution Mode:** XL / unattended / `vibe`-first. Every delegated subtask must end with `$vibe` and remain inside the existing VCO single-control-plane, single-default-execution-owner, single-canonical-truth-source constraints.

**Goal:** 在 Wave31-39 完成“先收口，再扩张”的基础上，把 Wave40-63 落成一个正式、可审计、可执行、可验证的治理执行面：先把 UTF-8 BOM / frontmatter / runtime freshness / execution-context 这类会直接破坏运行态解析与副本新鲜度的风险彻底制度化，再把去重图谱、评测自适应路由、持续价值榨取与 release 运营闭环固化为 VCO 原生资产。

**Core Principle:** 任何“吸收完成”的声明都必须至少对应 `docs + config + reference + verify gate (+ install/runtime linkage if applicable)`；没有产物层与门禁层，就只能算候选吸收，不能算已完成吸收。

---

## 1. Program Guardrails

1. **Single control plane only**：VCO 仍是唯一 orchestrator。
2. **Single default execution owner only**：不得让 browser / desktop / memory / eval 新增平面变成第二默认执行 owner。
3. **Single canonical truth-source only**：canonical repo root 仍是唯一治理真源；bundled / nested bundled / installed runtime 都只是 mirror/copy。
4. **Runtime-first hardening before new intake**：任何新增吸收面必须晚于 runtime freshness / frontmatter / execution-context 基础治理。
5. **Byte-0 frontmatter safety is stop-ship**：若 frontmatter-sensitive 文件在字节 0 不是 `---`，一律视为 stop-ship 风险。
6. **Advice-first / shadow-first / rollback-first**：任何新的路由、评测、价值榨取面必须先 advisory/shadow，再 soft，再 strict/promote。
7. **No duplicate role ownership**：同一问题域只能有一个 canonical owner；其他上游资源只能提供 pattern / contract / provider / reference 价值。
8. **Evidence before promotion**：所有 Wave40-63 交付都必须被 gate 或 board 证据链覆盖。

## 2. Why BOM / Frontmatter Is a First-Class Risk

用户已经给出真实运行态故障：`C:\Users\羽裳\.codex\skills\vibe\SKILL.md` 因缺少“字节 0 处的真实 `---`”而被解析器拒绝加载。这里的关键不是 Markdown 内容本身，而是：

- UTF-8 BOM (`EF BB BF`) 会占据字节 0-2；
- 某些解析器不会先移除 BOM，再寻找 YAML frontmatter；
- 因此即使文件“文本上看起来”是以 `---` 开头，解析器仍可能在 byte 0 看不到真正的 `---`；
- 对 `SKILL.md` 这类 frontmatter-sensitive 文件来说，这不是样式问题，而是**加载失败 / 路由失效 / 运行态不可用**问题。

**结论：** Wave40-45 必须先把 BOM/frontmatter 风险制度化，并且把 no-BOM 写入策略接入 release/install/runtime 流水线。

## 3. Program Metrics

| Metric | Target | Meaning |
|---|---:|---|
| `frontmatter_bom_incidents` | 0 | frontmatter-sensitive 文件 BOM 事故数 |
| `byte0_frontmatter_pass_rate` | 100% | frontmatter-sensitive 文件 byte-0 integrity 通过率 |
| `runtime_freshness_pass_rate` | >= 0.98 | install 后 runtime freshness 通过率 |
| `duplicate_owner_cluster_count` | 持续下降 | 重复 owner/重复入口 cluster 数 |
| `adaptive_routing_readiness` | >= shadow-ready | adaptive routing 进入 shadow-ready 的比例 |
| `upstream_value_ops_coverage` | 15/15 + 深化条目 | 持续价值榨取 board 覆盖率 |
| `release_evidence_completeness` | 100% | release note / ledger / board / gates 完整率 |

## 4. Execution Order

| Wave | Theme | Primary Outcome | Ledger | Required Verify |
|---|---|---|---|---|
| 40 | Formalization | Wave40-63 正式执行文档 + execution board | Drift | `vibe-wave40-63-board-gate.ps1` |
| 41 | Frontmatter Integrity Policy | 明确 BOM/frontmatter stop-ship contract | Drift | `vibe-bom-frontmatter-gate.ps1` |
| 42 | No-BOM Writers | 关键治理写路径改为 UTF-8 no-BOM | Drift | `vibe-bom-frontmatter-gate.ps1` |
| 43 | BOM Gate | canonical / bundled / nested / installed 的 frontmatter gate | Drift | `vibe-bom-frontmatter-gate.ps1` |
| 44 | Runtime Freshness + BOM SOP | install/check/SOP 串联 frontmatter integrity | Drift | `vibe-installed-runtime-freshness-gate.ps1` |
| 45 | Installed Runtime Closure | 运行态副本 frontmatter 风险收口 | Drift | `vibe-bom-frontmatter-gate.ps1 -TargetRoot` |
| 46 | Capability Dedup Taxonomy | 重复能力聚类与 canonical owner 确认 | Value | `vibe-capability-dedup-gate.ps1` |
| 47 | Capability Graph | 把去重从清单升级为 owner / source / landing 图谱 | Value | `vibe-capability-dedup-gate.ps1` |
| 48 | Role / Pack Overlap Closure | 角色包/技能生态重叠收口 | Drift + Value | `vibe-capability-dedup-gate.ps1` |
| 49 | Router Evidence Schema | 路由输入/输出/证据结构统一 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 50 | Boarded Governance | 去重/路由/价值榨取进入同一 execution board | Drift + Value | `vibe-wave40-63-board-gate.ps1` |
| 51 | Dedup Gate Closure | 去重治理具备独立 verify gate | Drift | `vibe-capability-dedup-gate.ps1` |
| 52 | Eval Contract | adaptive routing / replay / benchmark 合同化 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 53 | Adaptive Routing Baseline | shadow-ready 的阈值、启发式、证据面 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 54 | Replay Ledger | 路由 replay / audit / rollback 证据契约 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 55 | Pilot Extension | 把自适应路由纳入 pilot / scenario 合同 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 56 | Promotion Heuristics | adaptive routing 的 shadow→soft 决策条件 | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 57 | Adaptive Gate Closure | adaptive routing 有独立 readiness gate | Eval | `vibe-adaptive-routing-readiness-gate.ps1` |
| 58 | Value Ops Operating Model | 持续榨取 15 个上游项目的操作模型 | Value | `vibe-upstream-value-ops-gate.ps1` |
| 59 | Upstream Intake Board | 新一轮剩余价值 intake/backlog 化 | Value | `vibe-upstream-value-ops-gate.ps1` |
| 60 | Distillation Quality Bar | 价值蒸馏的最小质量门槛 | Value | `vibe-upstream-value-ops-gate.ps1` |
| 61 | Continuous Release Evidence | value ops 与 release evidence 联动 | Ops | `vibe-upstream-value-ops-gate.ps1` |
| 62 | Release Packaging Closure | 新增治理项进入 release evidence 栈 | Ops | `vibe-wave40-63-board-gate.ps1` |
| 63 | Runtime Sync Closure | repo → bundled → nested → installed 全链路收口 | Ops | `vibe-release-install-runtime-coherence-gate.ps1` |

## 5. Deliverable Groups

### Wave40-45: Runtime Hardening First
- `config/frontmatter-integrity-policy.json`
- `docs/governance/frontmatter-bom-governance.md`
- `scripts/verify/vibe-bom-frontmatter-gate.ps1`
- `scripts/governance/release-cut.ps1` 的 no-BOM writer 修复
- `docs/runtime-freshness-install-sop.md` 的 frontmatter/install SOP 增补

### Wave46-51: Dedup / Graph / Ownership
- `docs/governance/capability-dedup-graph-governance.md`
- `config/capability-dedup-governance.json`
- `references/capability-dedup-matrix.md`
- `scripts/verify/vibe-capability-dedup-gate.ps1`

### Wave52-57: Eval / Adaptive Routing / Replay
- `docs/governance/adaptive-routing-eval-governance.md`
- `config/adaptive-routing-eval-governance.json`
- `references/eval-replay-ledger-contract.md`
- `scripts/verify/vibe-adaptive-routing-readiness-gate.ps1`

### Wave58-63: Continuous Value Extraction / Release Ops
- `docs/continuous-value-extraction-operations.md`
- `config/upstream-value-ops-board.json`
- `references/upstream-distillation-quality-bar.md`
- `scripts/verify/vibe-upstream-value-ops-gate.ps1`
- `config/wave40-63-execution-board.json`

## 6. BOM-Safe Authoring Rules

1. 对 `SKILL.md` 这类 frontmatter-sensitive 文件，**禁止**使用可能写入 UTF-8 BOM 的默认写法。
2. PowerShell 治理脚本必须优先使用：`Write-VgoUtf8NoBomText`、`Append-VgoUtf8NoBomText`，或 `[System.Text.UTF8Encoding]::new($false)`。
3. release-cut / install 前必须运行 `vibe-bom-frontmatter-gate.ps1`。
4. 若 gate 检测到 BOM：canonical fail = stop-ship；bundled / nested fail = sync 前禁止 release；installed fail = 立即重装或重写 receipt 前的运行态副本。
5. shell/python 读取逻辑可以使用 `utf-8-sig` 做容错，但**写入端必须 no-BOM**。

## 7. Verification Stack

```powershell
pwsh -NoProfile -File .\scripts\verify\vibe-bom-frontmatter-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-wave40-63-board-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-capability-dedup-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-adaptive-routing-readiness-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-upstream-value-ops-gate.ps1 -WriteArtifacts
pwsh -NoProfile -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"
```

Runtime sync closure additionally requires:

```powershell
pwsh -NoProfile -File .\install.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex"
pwsh -NoProfile -File .\check.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex"
pwsh -NoProfile -File .\scripts\verify\vibe-bom-frontmatter-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex" -WriteArtifacts
```
