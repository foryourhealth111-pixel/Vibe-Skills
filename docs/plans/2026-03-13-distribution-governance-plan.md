# Distribution Governance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不影响现有功能、严格防止功能退化的前提下，为 `vco-skills-codex` 建立一套可执行的分发治理方案：把上游来源捋清、把本地保留策略做成制度、把许可证与溯源边界补齐，并让用户仍然能用尽可能简单的本地部署方式获得完整能力。

**Architecture:** 采用 `runtime-freeze + registry-first + provenance-per-asset + tiered-distribution` 架构。第一阶段只动文档、清单、合规与验证门禁，不改路由、安装、打包、sync、技能装载等运行面；第二阶段才在证据充足时推进本地 upstream 保留落地。核心原则是“先把真相系统做好，再决定哪些上游代码进入仓库”，而不是先大规模搬代码、再补治理。

**Tech Stack:** Git, PowerShell governance/verify scripts, Markdown governance docs, JSON registries/manifests, NOTICE/license artifacts, bundled mirror sync pipeline, runtime freshness/parity gates.

---

## Status

- **Target repo:** `_ext/vco-skills-codex`
- **Current baseline:** 工作树当前干净，可进行纯文档/治理类改动。
- **Primary constraint:** 本计划把“分发治理”定义为高风险基础设施工作，默认禁止直接修改现有 runtime owner、router contract、bundled mirror behavior、install/check path。
- **Why now:** 当前仓库已经有较强的 verify/gate 体系，但 upstream 来源、公开披露、镜像落点、仓库内本地保留策略之间仍然没有完全收口成一套对外一致、对内可执行的真相系统。

## Hard Guardrails

1. **Runtime freeze first:** 在本计划 Phase 0-2 内，不修改 `SKILL.md` 路由行为、不改 pack/router 判定、不改安装路径、不改 sync 语义、不改默认启用的外部 provider。
2. **Canonical-first only:** 任何治理、分发、合规、镜像调整都先改 canonical root；禁止 mirror-first 修补。
3. **No functional ownership transfer:** 即便把更多 upstream 保存在仓库本地，也不得让任何上游框架接管 VCO 的默认控制面、默认执行 owner、默认 memory truth-source。
4. **No unlicensed bundling:** 没有明确 license、NOTICE、redistribution posture、ORIGIN 记录的上游代码，不允许进入默认分发面。
5. **No new truth surface unless necessary:** 除非现有 registry 无法承载约束，否则优先扩展现有 `config/upstream-lock.json` 与 `config/upstream-corpus-manifest.json`，不新增第三套“上游真相表”。
6. **Evidence before promotion:** 任何“已纳入仓库本地保留”“已进入默认 release”“已可对外分发”的结论，都必须先过 proof bundle + upstream/compliance 专项 gates。
7. **Developer zones before broad contribution:** 在开放 repo-local retention 或大规模开发前，必须先用开发者边界规则明确哪些路径属于 frozen control plane、哪些属于 guarded mirror/compliance surface、哪些才是普通贡献者的默认开发区。

## Developer-Facing Change Control

如果这个仓库要面向更多开发者协作，就不能假设“所有目录都可以自由开发”。

分发治理要和开发者边界治理一起落地，至少要明确：

- `install/check`、`scripts/router/**`、`protocols/**`、核心 routing config 属于 frozen zone；
- `bundled/**`、`references/fixtures/**`、tracked `outputs/**`、`third_party/**`、未来 `vendor/**` 属于 guarded zone；
- `docs/**`、`references/**` 非 fixture、`scripts/governance/**`、`scripts/verify/**`、`templates/**` 才是首选的 additive contribution zone。

也就是说，repo-local retention 做得越多，越需要开发者知道：

- 哪些地方可以扩展；
- 哪些地方只能 canonical-first；
- 哪些地方完全不能“顺手改一改”。

这套规则应由长期治理文档承载，而不是只写在一次性计划里。推荐落点：

- `docs/developer-change-governance.md`

并把它接入：

- `docs/README.md`
- `repo-cleanliness-governance.md`
- `output-artifact-boundary-governance.md`
- 后续 release / contribution SOP

## What Is Broken Today

### 1. 上游真相分裂

当前至少存在三种并行但未完全对齐的上游事实源：

- `config/upstream-lock.json`：记录分发/运行/打包相关 upstream。
- `config/upstream-corpus-manifest.json`：记录 corpus/watchlist/value-extraction 相关 upstream。
- `THIRD_PARTY_LICENSES.md`：对外披露的上游与许可证摘要。

这三者的覆盖范围和字段语义还没有完全对齐，因此会出现以下问题：

- 某些来源已经公开披露，但没有进入 canonical registry。
- 某些来源进入了 registry，但对外披露不足。
- 某些 entry 仍存在 `HEAD_FROM_UPSTREAM_LOCK` 这种占位符，说明 freshness 真相未完全闭合。
- 某些 upstream 在 lock 与 corpus 两边同时存在，但分发边界、owner 与更新策略没有被正式写成单一解释。

### 2. 本地保留诉求与当前目录契约冲突

用户希望“尽可能把上游代码也保存在本地仓库里，让部署更简单”，但当前仓库已经明确定义：

- `third_party/` 是 **compliance-only** 边界；
- 它不是活跃 upstream clone 的承载目录；
- 活跃 mirror/backup/vendor 若直接塞入 `third_party/`，会破坏现有合规语义。

因此，如果要把更多 upstream 真正保存在 repo 内，不能粗暴复用现有 `third_party/`。

### 3. 逐资产溯源缺位

当前没有发现统一的 `ORIGIN.md` 级别逐资产溯源文件。这意味着：

- 哪些 bundled skill 是“改写自上游”、哪些是“仅参考上游”、哪些是“直接保留原样”，没有资产级证据；
- 当用户下载仓库时，很难判断某个目录是否可再分发、如何更新、需要保留哪些 notice；
- 一旦未来引入更多本地 upstream 代码，侵权和漂移风险会迅速放大。

### 4. 公共披露仍有悬空来源

`THIRD_PARTY_LICENSES.md` 当前提到、但未明确进入现有 canonical registry 的来源至少包括：

- `SynkraAI/aios-core`
- `x1xhlol/system-prompts-and-models-of-ai-tools`
- `muratcankoylan/Agent-Skills-for-Context-Engineering`

这些来源要么需要正式登记到现有 registry，要么需要从公开披露中降级/改写为更准确的“仅参考说明”。不能继续保持“对外说用了、对内没有受控记录”的状态。

## Complete Upstream Inventory Baseline

本节给出当前应纳入治理视野的 **全量来源联合视图**。它不是最终分发清单，而是本计划的清点基线。

### A. `upstream-lock` 中的 22 个分发/运行相关来源

- `obra/superpowers`
- `frankbria/ralph-claude-code`
- `f/prompts.chat`
- `SuperClaude-Org/SuperClaude_Framework`
- `feiskyer/claude-code-settings`
- `github/spec-kit`
- `ruvnet/claude-flow`
- `medialab/xan`
- `Done-0/fuck-u-code`
- `ivy-llc/ivy`
- `GokuMohandas/Made-With-ML`
- `zedr/clean-code-python`
- `donnemartin/system-design-primer`
- `xlite-dev/LeetCUDA`
- `RUC-NLPIR/FlashRAG`
- `RUC-NLPIR/WebThinker`
- `RUC-NLPIR/DeepAgent`
- `mem0ai/mem0`
- `letta-ai/letta`
- `dair-ai/Prompt-Engineering-Guide`
- `browser-use/browser-use`
- `simular-ai/Agent-S`

### B. `upstream-corpus-manifest` 中的 19 个 corpus/watchlist 来源

- `activepieces`
- `agent-s`
- `agent-squad`
- `antigravity-awesome-skills`
- `awesome-agent-skills`
- `awesome-ai-agents-e2b`
- `awesome-ai-tools`
- `awesome-claude-code-subagents`
- `awesome-claude-skills-composio`
- `awesome-mcp-servers`
- `awesome-vibe-coding`
- `browser-use`
- `claude-skills`
- `composio`
- `docling`
- `letta`
- `mem0`
- `prompt-engineering-guide`
- `vibe-coding-cn`

### C. 当前同时存在于两套 registry 的 5 个重叠来源

- `agent-s`
- `browser-use`
- `letta`
- `mem0`
- `prompt-engineering-guide`

这些来源未来必须形成“同一来源、双角色”的清晰解释：

- 在 `upstream-lock` 中说明它如何影响分发/安装/运行边界；
- 在 `upstream-corpus-manifest` 中说明它如何作为 corpus/policy/provider source 被治理；
- 两边禁止出现相互矛盾的 owner、license、promotion posture。

### D. 对外披露但未 canonicalized 的 3 个悬空来源

- `SynkraAI/aios-core`
- `x1xhlol/system-prompts-and-models-of-ai-tools`
- `muratcankoylan/Agent-Skills-for-Context-Engineering`

### E. 当前联合视图结论

- 现有 canonical registry 明确记录的来源总数：`22 + 19 - 5 = 36`
- 再加上公开披露但未 canonicalized 的来源：`3`
- **当前需要治理的联合来源总数：39**

这 39 个来源必须在计划执行后落入以下四种状态之一：

1. `distributed-local`：仓库内保留，且允许随仓库/发布物一起分发。
2. `repo-local-mirror-not-shipped`：仓库内保留，仅作本地参考或简化部署，不进入默认 release/install。
3. `external-optional`：不进仓库，仅通过 install/fetch/服务接入。
4. `reference-only`：只保留治理/方法/知识引用，不保留上游代码。

## Recommended Distribution Model

### Tier Model

| Tier | Meaning | Can Stay in Repo | Can Ship by Default | Typical Examples |
| --- | --- | --- | --- | --- |
| T0 Core Canonical | VCO 自有代码、改写后的兼容层、治理资产 | Yes | Yes | `bundled/` 下已改写 compat 技能、docs/config/scripts |
| T1 Repo-Local Vendored | 允许本地保留的 upstream 源码快照，带完整 provenance | Yes | Conditional | MIT/Apache/BSD 类 upstream，且确有简化部署价值 |
| T2 Repo-Local Mirror Only | 为开发/审计方便保留在 repo 内，但默认不装入 runtime/release | Yes | No | 大体积 corpus、灰度 provider、仅研究用镜像 |
| T3 External Optional | 只记录 contract/lock/ref，不随仓库携带源码 | No | Optional fetch/install | `f/prompts.chat`, `ruvnet/claude-flow` 等 |
| T4 Reference Only | 只保留方法论、风险清单、治理结论 | No code | No | `Made-With-ML`, `clean-code-python`, `system-design-primer` |

### Why This Model

这套分层同时满足四个目标：

- 尽量把真正有部署价值的上游代码放进 repo；
- 不把 license 不清、copyleft、高风险 provider 直接混进 Apache-2.0 core release；
- 不让“本地保留”自动等于“默认启用”；
- 不破坏当前 `third_party/` 的 compliance-only 语义。

## Directory Design

### Keep Unchanged

- `third_party/`：继续只做许可证、NOTICE、合规文档存放区。
- `bundled/`：继续作为 VCO 自身可分发镜像/兼容层，不作为生 upstream 仓库容器。

### Introduce a New Local-Upstream Surface

建议新增一个**明确区分于 `third_party/`** 的本地 upstream 承载目录：

- `vendor/upstreams/<canonical-slug>/`

或者，如果需要更强调“本地镜像而非核心代码”：

- `vendor/mirrors/<canonical-slug>/`

本计划推荐优先使用：

- `vendor/upstreams/<slug>/`：用于 T1 `distributed-local`
- `vendor/mirrors/<slug>/`：用于 T2 `repo-local-mirror-not-shipped`

### Why Not Reuse `third_party/`

因为当前仓库已经明确规定：

- `third_party/` 只承载 compliance artifacts；
- 如果把 active upstream code 直接塞进去，会让“许可证材料”和“可执行镜像”重新混淆；
- 这会直接破坏当前 repo-cleanliness 和第三方边界治理。

## Provenance Model

每一个本地保留的 upstream 根目录都必须带一个 `ORIGIN.md`，最少包含：

- `upstream_repo`
- `upstream_ref` / pinned commit
- `license`
- `distribution_tier`
- `integration_mode`
- `local_path`
- `shipped_by_default`
- `refresh_command`
- `modified_by_vco` / `verbatim_copy`
- `required_notice_files`
- `trademark_notes`
- `security_or_compliance_notes`

同时建议新增一个仓库级模板：

- `templates/ORIGIN.md.tmpl`

并新增一个 operator：

- `scripts/governance/new-origin-record.ps1`

这样后续任何新增本地 upstream 时，都必须先生成 provenance 骨架，而不是靠人工口头约定。

## License and Infringement Risk Policy

### Safe to Prioritize for Repo-Local Retention

优先考虑进入 `vendor/upstreams/` 的，是这类来源：

- MIT / Apache-2.0 / BSD 等宽松许可；
- 明确有源码 redistributable 权限；
- 对“本地部署更简单”有直接帮助；
- 不会替代 VCO control plane，只是作为 backend、参考实现或适配基础。

### Must Be Fenced Before Any Repo-Local Retention

以下来源在没有额外法律/合规确认前，不能直接进入默认分发面：

- GPL / copyleft 类：如 `xlite-dev/LeetCUDA`、`x1xhlol/system-prompts-and-models-of-ai-tools`
- `NOASSERTION` 类：如 `activepieces`、`awesome-ai-agents-e2b`、`awesome-claude-skills-composio`
- “Upstream project license applies”但当前仓库未写明具体许可证文本与义务的来源
- 服务型/条款型集成：如 `f/prompts.chat`

对这些来源，推荐策略是：

- 可留作 T2 `repo-local-mirror-not-shipped`，前提是仓库明确标注不属于默认 release；
- 或继续保持 T3 `external-optional` / T4 `reference-only`；
- 绝不把这类代码直接揉进 `bundled/` 或 Apache-2.0 core 逻辑里。

### Trademark and Naming Rule

- 上游名称只能用于 attribution、compatibility、source disclosure；
- 不得让上游项目名看起来像本项目自有子品牌；
- README/文档中出现上游名时，要明确“来源于谁、以什么方式使用、是否默认启用”。

## Canonical Source-of-Truth Split

### `config/upstream-lock.json`

保留为 **distribution/install/runtime-affecting** 上游锁文件，并补充字段：

- `distribution_tier`
- `repo_local_retention`
- `local_root`
- `shipped_by_default`
- `origin_record`
- `notice_status`
- `license_class`
- `update_channel`

### `config/upstream-corpus-manifest.json`

保留为 **corpus/watchlist/value-extraction** 登记册，并补充字段：

- `repo_local_retention`
- `bundling_forbidden`
- `disclosure_status`
- `mirror_mode`
- `origin_required`

### `THIRD_PARTY_LICENSES.md`

改造成**对外披露视图**，但不再作为手工自由发挥文档。它应来自上述两套 canonical registry 的受控摘要，至少实现下面两个规则：

1. 出现在默认分发面或 repo-local mirror 面的来源，必须出现在 `THIRD_PARTY_LICENSES.md`。
2. 出现在 `THIRD_PARTY_LICENSES.md` 的来源，必须能回溯到至少一个 canonical registry entry 或显式 exception note。

## Zero-Regression Execution Strategy

### Phase 0: Freeze and Baseline

只做两件事：

- 冻结当前 runtime 行为；
- 记录现有 gate baseline。

必须先跑的 proof bundle：

- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-router-contract-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-mirror-edit-hygiene-gate.ps1`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`
- `scripts/verify/vibe-repo-cleanliness-gate.ps1`

补充必须跑的 upstream/compliance 基线：

- `scripts/verify/vibe-upstream-corpus-manifest-gate.ps1`
- `scripts/verify/vibe-upstream-mirror-freshness-gate.ps1`

在这些基线没有形成记录前，禁止进入任何会影响 release/install/runtime 的目录调整。

### Phase 1: Registry and Disclosure Closure

先统一真相，再谈本地保留：

- 清点 39 个来源；
- 解决 registry overlap；
- 解决 public-only dangling sources；
- 消灭 `HEAD_FROM_UPSTREAM_LOCK` 占位符；
- 补齐 `THIRD_PARTY_LICENSES.md` 与 canonical registry 的映射关系。

这一阶段仍然不改变任何 runtime 加载路径。

### Phase 2: Provenance and Tier Scaffolding

只新增 passive 治理资产：

- `vendor/README.md`
- `templates/ORIGIN.md.tmpl`
- `ORIGIN.md` 模板和生成器
- 新 verify gates

仍不移动现有执行面代码。

### Phase 3: Canary Local-Retention Pilot

只选择 1-2 个 **宽松许可、低风险、明确有部署价值** 的来源做 canary：

- 例如 permissive backend/tooling source
- 不选 GPL / NOASSERTION / service terms / unclear-license 源

canary 目标不是切换默认运行，而是验证：

- repo-local retention 目录设计成立；
- provenance / notice / gates 能闭环；
- 打包和安装行为不回退。

### Phase 4: Controlled Expansion

只有 canary 稳定后，才逐类扩展：

- permissive local vendor
- repo-local mirror only
- external optional
- reference-only

每次只扩一类来源，不混批。

## Implementation Backlog

### Task 1: Freeze Runtime and Record a Baseline

**Files**
- Modify: `docs/governance/distribution-governance.md` (new evergreen governance doc)
- Modify: `docs/runtime-freshness-install-sop.md`
- Modify: `docs/version-packaging-governance.md`
- Modify: `references/release-evidence-bundle-contract.md`

**Outcome**
- 明确“分发治理 Phase 0-2 不触碰 runtime owner”的冻结规则。
- 在治理正文中固定 baseline/proof bundle 作为 stop-ship 合同。

**Verify**
- 运行现有 proof bundle。
- 记录基线 artifact 到 `outputs/verify/` / `outputs/upstream-audit/`。

**Rollback**
- 若 baseline 本身不稳定，停止全部后续分发治理，仅先修 gate 可靠性。

### Task 2: Normalize the 39-Source Inventory

**Files**
- Modify: `config/upstream-lock.json`
- Modify: `config/upstream-corpus-manifest.json`
- Modify: `config/upstream-source-aliases.json`
- Modify: `THIRD_PARTY_LICENSES.md`
- Modify: `NOTICE`
- Create: `docs/governance/upstream-distribution-governance.md`
- Create: `scripts/governance/export-upstream-inventory-union.ps1`

**Outcome**
- 形成“39 个来源联合视图”。
- 为每个来源指定唯一 canonical slug、registry role、distribution tier、public disclosure posture。
- 解决 overlap 和 public-only 悬空来源。

**Verify**
- 现有：`vibe-upstream-corpus-manifest-gate.ps1`
- 新增：`vibe-upstream-lock-coverage-gate.ps1`
- 新增：`vibe-third-party-disclosure-parity-gate.ps1`

**Rollback**
- 若任何来源无法确定 license/status，先降级为 `reference-only` 或 `external-optional`，绝不强行标记为可分发本地代码。

### Task 3: Establish Repo-Local Upstream Directories Without Touching Runtime

**Files**
- Create: `vendor/README.md`
- Create: `vendor/upstreams/.gitkeep`
- Create: `vendor/mirrors/.gitkeep`
- Create: `templates/ORIGIN.md.tmpl`
- Create: `scripts/governance/new-origin-record.ps1`
- Modify: `docs/repo-cleanliness-governance.md`
- Modify: `third_party/README.md`

**Outcome**
- 为 repo-local upstream retention 建立正式目录，但先不迁入任何运行时代码。
- 保持 `third_party/` 的 compliance-only 契约不被破坏。

**Verify**
- `vibe-repo-cleanliness-gate.ps1`
- `vibe-output-artifact-boundary-gate.ps1`
- 新增：`vibe-origin-provenance-gate.ps1`

**Rollback**
- 若新增目录影响现有 cleanup policy，就先只保留 `README + template`，不建实际 vendor 根。

### Task 4: Add Per-Asset Provenance and Notice Rules

**Files**
- Create/Modify: `vendor/**/ORIGIN.md`
- Modify: `third_party/licenses/**`
- Modify: `THIRD_PARTY_LICENSES.md`
- Modify: `NOTICE`
- Modify: `references/upstream-value-ledger.md`

**Outcome**
- 每个 repo-local upstream 根都有 provenance。
- 每个默认分发来源都有 license/notice 闭环。
- 每个 mirror-only 来源都明确“为什么在 repo 里、为什么不默认发布”。

**Verify**
- 新增：`vibe-origin-provenance-gate.ps1`
- 新增：`vibe-third-party-disclosure-parity-gate.ps1`

**Rollback**
- 若某来源的 notice/license 无法闭环，回退为 external/reference posture。

### Task 5: Fence High-Risk and Unclear-License Sources

**Files**
- Modify: `config/upstream-lock.json`
- Modify: `config/upstream-corpus-manifest.json`
- Modify: `docs/governance/upstream-distribution-governance.md`
- Modify: `docs/upstream-corpus-governance.md`

**Outcome**
- 对 GPL、NOASSERTION、service-terms、unclear-license 来源建立硬边界。
- 把“可保存在 repo 内”与“可默认发布”正式拆开。

**Verify**
- 新增：`vibe-distribution-tier-boundary-gate.ps1`
- 新增：`vibe-upstream-license-risk-gate.ps1`

**Rollback**
- 若边界定义仍不清晰，默认全部降级为 `repo-local-mirror-not-shipped` 或 `external-optional`。

### Task 6: Build a Canary Pilot for Repo-Local Retention

**Files**
- Create: `vendor/upstreams/<pilot-slug>/`
- Create: `vendor/upstreams/<pilot-slug>/ORIGIN.md`
- Modify: `config/upstream-lock.json`
- Modify: `THIRD_PARTY_LICENSES.md`
- Modify: `NOTICE`
- Create: `scripts/governance/refresh-vendored-upstream.ps1`

**Outcome**
- 用一个低风险 upstream 验证 repo-local retention 的可操作性。
- 保证其存在不改变现有运行时默认路径，只新增受控本地资产。

**Verify**
- 现有 proof bundle 全量复跑。
- `vibe-upstream-lock-coverage-gate.ps1`
- `vibe-third-party-disclosure-parity-gate.ps1`
- `vibe-origin-provenance-gate.ps1`

**Rollback**
- 只要 proof bundle 任一关键项回退，立即删除 canary vendor 目录并恢复 registry/disclosure 改动。

### Task 7: Promote to Operator SOP and Release Governance

**Files**
- Modify: `scripts/governance/README.md`
- Modify: `scripts/verify/README.md`
- Modify: `docs/runtime-freshness-install-sop.md`
- Modify: `docs/releases/README.md`
- Modify: `references/index.md`

**Outcome**
- 明确“新增 upstream 如何入仓、如何更新、如何验证、如何回退”的 operator SOP。
- release/install 文档明确区分 shipped local upstream 与 repo-only mirror。

**Verify**
- proof bundle
- release/install coherence gates
- 新 compliance/provenance gates

**Rollback**
- 若 operator 路径仍然需要人工猜测，冻结 release-side adoption，继续只保留治理资产。

## Test Matrix

### A. Contract and Inventory Tests

- `vibe-upstream-corpus-manifest-gate.ps1`
- `vibe-upstream-mirror-freshness-gate.ps1`
- `vibe-upstream-lock-coverage-gate.ps1` (new)
- `vibe-third-party-disclosure-parity-gate.ps1` (new)

目的：

- 保证 every source is accounted for；
- 保证 registry 与 public disclosure 不再漂移；
- 保证 overlap sources 的双角色解释一致。

### B. Runtime Non-Regression Tests

- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-mirror-edit-hygiene-gate.ps1`
- `vibe-output-artifact-boundary-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`
- `vibe-repo-cleanliness-gate.ps1`

目的：

- 证明治理落地没有改变当前 router/install/package/runtime 行为；
- 证明 repo-local upstream 增量不会污染 mirror、output、cleanliness boundary。

### C. Provenance and Compliance Tests

- `vibe-origin-provenance-gate.ps1` (new)
- `vibe-distribution-tier-boundary-gate.ps1` (new)
- `vibe-upstream-license-risk-gate.ps1` (new)

目的：

- 保证每个本地保留 upstream 都有 ORIGIN；
- 保证高风险来源不会误进默认 release；
- 保证 notice/license/disclosure 闭环。

### D. Deployment Simplicity Tests

建议新增一个 canary 安装 smoke：

- fresh clone
- fresh install to temp target
- verify core runtime still works without vendored optional upstream
- verify vendored local upstream, if present, does not break install/check scripts

这一类测试不要求新功能，只要求“更简单部署的新增资产不能把原部署路径搞坏”。

## Acceptance Criteria

满足以下条件，才能宣称分发治理方案正确落地：

1. 39 个来源全部被 canonical registry 或 explicit exception 管理。
2. `THIRD_PARTY_LICENSES.md` 与 canonical registry 达成可验证的一致性。
3. 任一 repo-local upstream 目录都具备 `ORIGIN.md`、license、notice、refresh path。
4. `third_party/` 仍保持 compliance-only，不被重新污染为活跃 clone 容器。
5. proof bundle 全绿，且结果不弱于治理前 baseline。
6. 新目录和新门禁不会让 repo cleanliness、mirror hygiene、runtime freshness 变差。
7. 高风险来源全部被成功 fenced，未混入默认分发面。
8. 用户可以通过 repo-local retention 获得更简单部署，但不需要承担“默认就启用高风险上游”的副作用。

## Explicit Non-Goals

- 不在本计划第一轮就把 39 个来源全部搬进仓库。
- 不把 submodule 作为默认方案。submodule 会增加部署心智负担，与“更简便部署”目标冲突。
- 不让任何 upstream 直接接管 VCO orchestrator、router、memory truth-source。
- 不为了“完整保留”而牺牲当前可运行性和可发布性。
- 不把 copyleft/unclear-license 代码直接混进 Apache-2.0 core。

## Recommended Immediate Sequence

1. 先执行 Task 1 和 Task 2，只做 baseline、inventory、registry、disclosure 收口。
2. 再执行 Task 3 和 Task 4，建立 vendor/provenance 脚手架，但不迁移现有运行时代码。
3. 然后执行 Task 5，把所有高风险来源先 fence 住。
4. 最后只选一个 permissive upstream 做 Task 6 canary，验证 repo-local retention 模式。
5. Canary 稳定后，再把 SOP 和 release governance 升级到 Task 7。

## Success Signal

本计划完成后，`vco-skills-codex` 会获得以下能力：

- 上游来源不再是“文档写一点、lock 记一点、notice 漏一点”的分裂状态；
- 你可以明确知道哪些 upstream 被真正保存在 repo 内，哪些只是外部依赖，哪些只是参考来源；
- 用户可以享受“更多本地保留、更少外部准备”的部署体验，但不会因此引入隐性 license 风险或运行时退化；
- 分发治理本身成为一条受 gate 保护的工程化路径，而不是一次性人工整理。
