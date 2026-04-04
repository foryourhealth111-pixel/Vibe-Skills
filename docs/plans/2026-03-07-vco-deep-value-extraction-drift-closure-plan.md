# VCO Deep Value Extraction & Drift Closure Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不破坏 VCO 单一控制面、单一默认执行 owner、单一 canonical truth-source 的前提下，继续深度榨取既有 15 个高价值项目的剩余价值，并彻底收口“旧副本可跑但治理不完整”的漂移风险。

**Architecture:** 采用“先收口，再扩张；先运行化，再新增吸收面”的双账本单队列治理：所有工作项必须同时归入 `Value Ledger`（新增可产品化价值）或 `Drift Ledger`（漂移/冗余/双轨收口），并使用统一的 docs + config + script + gate + pilot + mirror 流水线落地。优先把 mirror topology、release/install/runtime freshness、旧副本执行风险和 upstream mirror 治理收口，再把 `docling`、连接器生态、角色/技能生态与 discovery/eval 素材层转成 VCO 原生制度化资产。

**Tech Stack:** PowerShell governance/verify scripts, JSON governance configs, Markdown docs/references, bundled mirrors, installed runtime freshness receipts, promotion board, pilot fixtures, VCO pack/router governance.

---

## 1. Guardrails

1. **Single control plane only**：VCO 仍是唯一控制面，不引入第二 orchestrator。
2. **Single execution default only**：任何 BrowserOps / DesktopOps / connector 扩张都不得成为新的默认执行 owner。
3. **Single canonical truth-source only**：canonical repo root 仍是唯一治理真源；bundled、nested bundled、installed runtime 都只能是 mirror/copy。
4. **No docs+config+script+gate, no absorption claim**：没有进入产物层，不能宣称“已吸收”。
5. **Advice-first / shadow-first / rollback-first**：新增能力一律先 advisory/shadow，再 soft，再 strict/promote。
6. **Single queue only**：所有后续工作项必须进入统一 backlog，并且必须标记属于 `Value Ledger` 或 `Drift Ledger`。
7. **Freshness is an SLO**：release freshness、install freshness、runtime freshness、upstream mirror freshness 必须转成可度量 SLO，而不是手工感知。
8. **No mirror-only authority**：任何只存在于 runtime / bundled / nested mirror、但 canonical repo 没有正式治理合同的资产，默认视为风险项而不是正式能力。

## 2. Current Gaps to Close First

1. `nested bundled root` 已被纳入版本治理说明，但尚未看到专门 parity gate 与 mirror edit hygiene gate 落地，旧副本/镜像副本的独立漂移仍可能漏检。
2. 运行态存在 `third_party/vco-ecosystem-mirror` 的 15 项上游镜像，但 canonical repo 尚未形成对应的 upstream corpus manifest / freshness governance / productization ledger。
3. 运行态已有 `references/docling-output-spec.md` 一类资产，但 canonical repo 未形成对应正式 contract 资产，说明仍存在 runtime-only knowledge。
4. 当前 runtime freshness gate 对官方 mirror scope 很强，但对 upstream corpus / 素材层 / runtime-only extras 还没有完整制度化覆盖。

## 3. Program Metrics

| Metric | Target | Meaning |
|---|---|---|
| `governed_mirror_coverage` | 100% | 所有可执行 mirror target 都被 config + gate + docs 覆盖 |
| `runtime_only_artifact_count` | → 0 | runtime 独有、canonical 缺失的治理关键资产数量 |
| `mirror_only_diff_count` | → 0 | 只改 mirror 不改 canonical 的异常 diff 数 |
| `runtime_freshness_pass_rate` | >= 0.98 | install 后 runtime freshness 通过率 |
| `upstream_manifest_coverage` | 15 / 15 | 15 个上游镜像全部进入 canonical manifest |
| `productization_ratio` | >= 0.80 | 15 项中已进入 docs+config+script+gate 的价值切片占比 |
| `duplicate_surface_count` | 持续下降 | 同题双入口 / 双责任面数量 |
| `pilot_pass_rate` | >= 0.95 | 新 plane/capability 的试点通过率 |

## 4. Execution Order

| Wave | Theme | Primary Outcome | Ledger | Required Verify |
|---|---|---|---|---|
| 31 | Mirror Topology Closure | 把四副本治理升级为显式 mirror topology contract | Drift | `vibe-version-packaging-gate.ps1` |
| 32 | Nested / Mirror Hygiene Gates | 新增 nested parity 与 mirror-only drift 阻断门禁 | Drift | `vibe-nested-bundled-parity-gate.ps1` + `vibe-mirror-edit-hygiene-gate.ps1` |
| 33 | Release / Install / Runtime Coherence | 把 freshness 做成 release/install/runtime 三段式门禁与 SOP | Drift | `vibe-installed-runtime-freshness-gate.ps1` + coherence gate |
| 34 | Upstream Corpus Governance | 15 上游镜像进入 canonical manifest / freshness / ownership | Drift + Value | `vibe-upstream-corpus-manifest-gate.ps1` |
| 35 | Docling Productization | `docling` 从 runtime-only 素材变成正式 document-plane contract | Value | `vibe-docling-contract-gate.ps1` |
| 36 | Connector Admission Layer | `awesome-mcp-servers` / `composio` / `activepieces` 进入 connector governance | Value | `vibe-connector-admission-gate.ps1` |
| 37 | Role / Skill Distillation | `agent-squad` / `claude-skills` / awesome skill catalogs 进入 canonical role-pack 体系 | Value | `vibe-role-pack-governance-gate.ps1` |
| 38 | Discovery / Eval Corpus | `awesome-vibe-coding` / `awesome-ai-tools` / `vibe-coding-cn` / `awesome-ai-agents-e2b` 转成 discovery/eval 语料层 | Value | `vibe-capability-catalog-gate.ps1` |
| 39 | Promotion & Release Closure | 把新能力接入 promotion board、pilot、release cut、bundled mirror | Drift + Value | promotion board + pilot + version/parity gates |

---

## 5. Wave Backlog

### Task 1: Wave 31 — Mirror Topology Closure

**Files**
- Modify: `config/version-governance.json`
- Modify: `docs/version-packaging-governance.md`
- Create: `references/mirror-topology.md`
- Modify: `scripts/common/vibe-governance-helpers.ps1`
- Modify: `scripts/governance/sync-bundled-vibe.ps1`

**Outcome**
- 把 `canonical`、`bundled`、`nested_bundled`、`installed_runtime` 升级为显式 mirror topology contract，而不是分散在多个文档/脚本里的隐式规则。
- 明确哪些 target 是 required、哪些 target 是 conditional、哪些 target 只允许通过 canonical 直接同步。
- 明确 upstream corpus 是否属于 mirror topology 主治理域，还是单独进入 upstream corpus governance 域。

**Verify**
- `pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts`

**Exit Criteria**
- mirror topology 能被单一 config 文件完整表达。
- docs / scripts / config 对 mirror target 的定义一致。

**Rollback Statement**
- 若 topology contract 造成现有 gate/installer 无法解释，回退到当前 `source_of_truth.*` 结构，并保留新增说明文档但不启用新字段。

### Task 2: Wave 32 — Nested / Mirror Hygiene Gates

**Files**
- Create: `scripts/verify/vibe-nested-bundled-parity-gate.ps1`
- Create: `scripts/verify/vibe-mirror-edit-hygiene-gate.ps1`
- Create: `scripts/verify/fixtures/nested-bundled-drift/*`
- Modify: `scripts/verify/README.md`
- Modify: `check.ps1`
- Modify: `check.sh`

**Outcome**
- 新增针对 `nested bundled root` 的专门 parity gate，阻断“旧副本可跑但未被专门审计”的盲区。
- 新增 `mirror-only diff` 检测，识别“只改 bundled/nested/runtime 副本、不改 canonical” 的脏修改。
- 把 runtime 检查从“能跑通”提升为“副本来源、上下文、路径都必须合法”。

**Verify**
- `pwsh -File .\scripts\verify\vibe-nested-bundled-parity-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-mirror-edit-hygiene-gate.ps1 -WriteArtifacts`
- `pwsh -File .\check.ps1 -TargetRoot "$env:USERPROFILE\.codex"`

**Exit Criteria**
- nested bundled drift 能被 blocking 级别稳定识别。
- mirror-only edit 会在 PR / release 前被判为异常，除非有同步脚本与 gate 结果佐证。

**Rollback Statement**
- 如新 gate 对正常 sync 造成大量误报，则回退为 advisory 模式，但必须保留 artifacts 输出用于调参。

### Task 3: Wave 33 — Release / Install / Runtime Coherence

**Files**
- Modify: `install.ps1`
- Modify: `install.sh`
- Modify: `check.ps1`
- Modify: `check.sh`
- Modify: `docs/version-packaging-governance.md`
- Create: `docs/runtime-freshness-install-sop.md`
- Create: `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

**Outcome**
- 把 release cut、install、runtime freshness 串成一条正式链路：release 只管 repo parity，install 负责 force-sync + receipt，runtime 负责 authoritative freshness。
- 定义 freshness SLO、error budget、receipt contract、shell degraded behavior 和 stop-ship 条件。
- 修正 execution-context lock 的文档与安装态 SOP，使“从 mirror root 误执行治理脚本”的行为更早失败、更好解释。

**Verify**
- `pwsh -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex" -WriteReceipt`
- `pwsh -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1 -WriteArtifacts`

**Exit Criteria**
- release/install/runtime 的职责边界被文档、脚本、receipt 一致表达。
- fresh install 与 routine check 都能给出明确的 pass/fail/warn 语义。

**Rollback Statement**
- 若 coherence gate 阻塞过多历史环境，则先允许 warning-only 过渡，但不得删除 receipt contract。

### Task 4: Wave 34 — Upstream Corpus Governance

**Files**
- Create: `config/upstream-corpus-manifest.json`
- Create: `docs/upstream-corpus-governance.md`
- Create: `references/upstream-value-ledger.md`
- Modify: `scripts/governance/audit-upstream.ps1`
- Create: `scripts/verify/vibe-upstream-corpus-manifest-gate.ps1`
- Create: `scripts/verify/vibe-upstream-mirror-freshness-gate.ps1`

**Outcome**
- 把 15 个上游镜像项目全部纳入 canonical manifest：记录 source repo、license、owner、absorption lane、current status、productization target、freshness policy。
- 把 runtime 里现存的 `third_party/vco-ecosystem-mirror` 从“事实存在”升级成“制度存在”。
- 为每个项目声明它是 `已制度化 / 部分吸收 / 主要停留镜像层 / 明确不进入 runtime` 哪一类。

**Verify**
- `pwsh -File .\scripts\verify\vibe-upstream-corpus-manifest-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-upstream-mirror-freshness-gate.ps1 -WriteArtifacts`

**Exit Criteria**
- 15 / 15 上游项目都有 canonical owner、lane、status、next action。
- 再也不存在“runtime 有，但 canonical repo 没有登记”的上游镜像关键资产。

**Rollback Statement**
- 如果无法立即把所有镜像纳入 canonical manifest，至少先把运行态已存在的 15 项全部登记为 advisory tracked corpus，不得继续无登记扩张。

### Task 5: Wave 35 — Docling Productization

**Files**
- Create: `docs/design/docling-document-plane-integration.md`
- Create: `references/docling-output-spec.md`
- Modify: `references/tool-registry.md`
- Create: `config/docling-provider-policy.json`
- Create: `scripts/verify/vibe-docling-contract-gate.ps1`

**Outcome**
- 把 `docling` 从 runtime-only 素材提升为 canonical document-plane contract：明确最小输出结构、fallback、审计字段、降级路径。
- 把当前运行态 `docling-output-spec` 回收到 canonical repo，消灭 runtime-only contract。
- 明确 `docling` 在 VCO 中属于 provider/contract，而不是第二 document orchestrator。

**Verify**
- `pwsh -File .\scripts\verify\vibe-docling-contract-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"`

**Exit Criteria**
- `references/docling-output-spec.md` 在 canonical、bundled、runtime 三处同源可追溯。
- `docling` 的 contract、fallback、owner、provider status 被正式记录。

**Rollback Statement**
- 若 contract 设计不稳定，则保持 reference-only，但不得再把 runtime-only spec 当正式资产使用。

### Task 6: Wave 36 — Connector Admission Layer

**Files**
- Create: `docs/connector-admission-governance.md`
- Create: `references/connector-admission-matrix.md`
- Create: `config/connector-provider-policy.json`
- Modify: `references/tool-registry.md`
- Create: `scripts/verify/vibe-connector-admission-gate.ps1`

**Outcome**
- 把 `awesome-mcp-servers`、`composio`、`activepieces` 的价值收敛为 connector admission layer：连接器分级、allowlist、capability tags、risk class、fallback、rollback。
- 禁止“看到一个 MCP server 就直接并入 runtime surface”；必须先进入 admission matrix。
- 明确哪些连接器进入 `manual`、哪些进入 `provider-candidate`、哪些只能保留为 catalog/reference。

**Verify**
- `pwsh -File .\scripts\verify\vibe-connector-admission-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-cross-plane-conflict-gate.ps1`

**Exit Criteria**
- 新连接器不再靠 ad hoc 方式进入生态。
- 连接器生态被纳入 capability/risk/fallback/rollback 的统一治理口径。

**Rollback Statement**
- 如果 connector policy 过度复杂，优先保留 allowlist + denylist + provider-candidate 三层最小模型。

### Task 7: Wave 37 — Role / Skill Distillation

**Files**
- Create: `docs/role-pack-distillation-governance.md`
- Create: `references/skill-distillation-rules.md`
- Modify: `references/team-templates.md`
- Create: `config/role-pack-policy.json`
- Create: `scripts/verify/vibe-role-pack-governance-gate.ps1`

**Outcome**
- 把 `agent-squad`、`claude-skills`、`awesome-agent-skills`、`awesome-claude-code-subagents`、`antigravity-awesome-skills` 的剩余价值沉淀为 VCO-native role pack / team template / skill quality rules。
- 明确哪些是团队编排模式、哪些是角色卡片、哪些是技能模板、哪些只保留为参考案例。
- 继续坚持“不引入第二 orchestrator、不引入第二 team execution owner”。

**Verify**
- `pwsh -File .\scripts\verify\vibe-role-pack-governance-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-promotion-board-gate.ps1`

**Exit Criteria**
- 角色/子代理/技能模板的吸收不再依赖原始 upstream 目录直接存在。
- team templates 与 role pack policy 能解释“为什么吸收、吸收到哪一层、不吸收什么”。

**Rollback Statement**
- 如 role pack 设计与现有 VCO team template 冲突，则优先保留 team template，新增 upstream 内容降级为参考卡片。

### Task 8: Wave 38 — Discovery / Eval Corpus Productization

**Files**
- Create: `docs/governance/discovery-eval-corpus-governance.md`
- Create: `references/capability-catalog.md`
- Create: `config/capability-catalog.json`
- Create: `scripts/verify/vibe-capability-catalog-gate.ps1`
- Create: `docs/external-tooling/upstream-eval-pilot-scenarios.md`

**Outcome**
- 把 `awesome-vibe-coding`、`awesome-ai-tools`、`vibe-coding-cn`、`awesome-ai-agents-e2b` 的价值沉淀成 discovery / eval corpus，而不是新的 runtime 入口。
- 建立 capability catalog：每个价值切片必须声明问题域、输入、输出、适用平面、重复项、淘汰条件。
- 为“榨取程度”建立正式量化资产，而不是继续停留在口头判断。

**Verify**
- `pwsh -File .\scripts\verify\vibe-capability-catalog-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-keyword-precision-audit.ps1`

**Exit Criteria**
- discovery/eval 项目被正式归位为素材层 / 评估层 / 发现层。
- capability catalog 能覆盖 15 项项目的主要剩余价值切片，并能区分进入产品与仅保留参考的边界。

**Rollback Statement**
- 若 capability catalog 初期过大，允许先覆盖优先级最高的切片，但必须保留统一 schema，禁止重新回到散点记录。

### Task 9: Wave 39 — Promotion & Release Closure

**Files**
- Modify: `config/promotion-board.json`
- Modify: `docs/promotion-board-governance.md`
- Create: `scripts/verify/vibe-deep-extraction-pilot-gate.ps1`
- Modify: `scripts/governance/release-cut.ps1`
- Modify: `docs/releases/*`
- Modify: `references/changelog.md`

**Outcome**
- 把 Wave31-38 新增的治理与能力平面纳入 promotion board、pilot、rollback、release note。
- 把 `productization_ratio`、`runtime_only_artifact_count`、`duplicate_surface_count`、`governed_mirror_coverage` 引入 release/promotion 证据。
- 形成“治理收口完成后，才能宣称新增吸收”的正式发布口径。

**Verify**
- `pwsh -File .\scripts\verify\vibe-promotion-board-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-pilot-scenarios.ps1`
- `pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1 -WriteArtifacts`
- `pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts`

**Exit Criteria**
- 新的深度榨取成果能被 release note、promotion board、pilot、gate 同时证明。
- release cut 不再遗漏 runtime-only contract、mirror-only drift、未登记 upstream corpus。

**Rollback Statement**
- 若 promotion 证据不足，则全部保持在 shadow/advisory，不得以 release note 夸大吸收完成度。

---

## 6. Priority Order

### P0：先收口旧副本与镜像漂移
- Wave 31
- Wave 32
- Wave 33
- Wave 34

### P1：再把高价值剩余资源制度化
- Wave 35
- Wave 36
- Wave 37
- Wave 38

### P2：最后做 promotion / release closure
- Wave 39

## 7. Decision Rule

以后凡是讨论“某个项目还剩什么价值、该不该继续榨取”，统一按 6 个问题判断：
1. 它补哪个平面。
2. 它不补哪个平面。
3. 它与现有哪一层重叠。
4. 最小吸收形态是什么。
5. 需要补哪些 docs/config/script/gate 才能进入 shadow。
6. 如果不吸收，它应该被归入哪个 corpus/ledger，而不是继续游离在 runtime 外层。

如果这 6 个问题回答不完整，则不允许进入执行波次。

## 8. Completion Signal

当以下条件同时满足时，才算真正完成“深度榨取 + 漂移收口”：
- runtime 不再存在 canonical 未登记的关键治理资产；
- 15 项 upstream 全部有 canonical manifest、owner、lane、status、next action；
- `docling`、connector 生态、role/skill 生态、discovery/eval 素材层都进入正式治理；
- mirror-only drift、runtime-only contract、双轨入口数量持续下降到可接受阈值；
- release/install/runtime freshness 成为稳定门禁，而不是人工经验。
