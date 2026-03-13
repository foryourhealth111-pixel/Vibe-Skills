# Universal VibeSkills No-Regression Migration Plan

> Goal: 在严格保证当前 `vco-skills-codex` 官方满血运行时不退化的前提下，把项目演进为一个面向 Claude Code、Codex、OpenCode 以及其他宿主可消费的通用 `VibeSkills` 生态包。  
> Core position: **可以做，但只能采用“官方运行时冻结 + 宿主无关 core 抽象 + 宿主适配器分层 + 证据驱动晋级”的并轨迁移路线，不能采用原地大一统替换。**

> Baseline proof bundle: `docs/universalization/official-runtime-baseline.md`, `references/proof-bundles/official-runtime-baseline/baseline-manifest.json`

## Executive Conclusion

### Final Judgment

**结论一：目标合理。**  
把 `VibeSkills` 从当前偏 `Codex/Claude` 官方运行时，升级为一个“通用 skills 基座”，从产品方向、生态方向和治理方向上都是合理且必要的。

**结论二：不退化迁移是可实现的，但有严格前提。**  
只有在下面四条前提同时成立时，才可以宣称“通用化不会导致当前功能退化”：

1. 当前官方运行时继续作为 `Tier-1 Official Runtime` 保留，不被通用化改造直接替换。
2. 通用化新增内容只能先落到 `core + adapters + compatibility verification` 新层，不允许先改现有 `install/check/router/bundled/runtime` 主链。
3. 所有宿主差异必须显式建模为 `capabilities + degrade contract`，不能靠 prompt 约定隐式兼容。
4. 任意通用化产物要提升到默认分发面之前，必须通过跨宿主 replay、route parity、install parity、safety parity 的验证链。

**结论三：错误的做法会造成真实退化。**  
如果采用“把现有官方运行时直接改造成所有宿主共用的一套逻辑”这种方式，极大概率退化在以下区域：

- Router 精度
- 满血执行闭环
- 插件与 MCP 物化安装体验
- 多智能体执行能力
- Release / install / runtime freshness 治理
- 对外承诺的真实性

### Strategic Translation

本计划不追求“一份宿主无差别运行时”。  
本计划追求的是：

- **一份宿主无关的 skill 真相层**
- **多份宿主适配层**
- **一个继续保持满血能力的官方参考运行时**

也就是：

- `VibeSkills Core` = 通用真相层
- `Host Adapters` = Claude Code / Codex / OpenCode / Generic Host 的适配层
- `Official Runtime` = 当前 `vco-skills-codex` 满血官方实现

## Current Reality Baseline

基于当前仓库，可以明确判断出以下现实：

### 1. 当前仓库不是宿主无关 core，而是一个官方运行时

证据：

- 存在明显宿主物化文件：
  - `config/plugins-manifest.codex.json`
  - `config/settings.template.codex.json`
  - `config/settings.template.claude.json`
- 存在明显宿主物化脚本：
  - `scripts/setup/materialize-codex-mcp-profile.ps1`
  - `scripts/setup/sync-codex-settings-to-user-env.ps1`
  - `scripts/setup/persist-codex-openai-env.ps1`
  - `scripts/setup/persist-codex-ark-env.ps1`
- 现有依赖映射仍显式引用本地宿主目录：
  - `config/dependency-map.json` 中直接使用 `C:/Users/羽裳/.codex/...`

这意味着当前项目的强项是：

- 官方 runtime 完整
- 治理链完整
- 本地安装链完整
- mirror / parity / release 体系完整

而不是：

- 天然宿主无关
- 一份 contract 到处直接跑

### 2. 当前最重要的资产不是单个 skill，而是运行时治理链

当前真正不能丢的资产包括：

- `install.ps1` / `install.sh`
- `check.ps1` / `check.sh`
- `scripts/bootstrap/one-shot-setup.ps1`
- `scripts/governance/release-cut.ps1`
- `scripts/governance/sync-bundled-vibe.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`
- `scripts/verify/vibe-version-consistency-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-offline-skills-gate.ps1`

这些资产构成了当前官方运行时的“可靠性护城河”。

### 3. 当前宿主差异已经存在，但尚未被抽象成统一能力层

当前差异至少体现为：

- plugin provisioning 的方式不同
- settings 文件结构不同
- env 持久化方式不同
- hook 安装模型不同
- MCP 注册方式不同
- agent team API 可用性不同
- shell / browser / memory / external CLI 的能力暴露不同

现在这些差异主要靠：

- 配置文件
- 宿主专用模板
- 文档说明
- operator 常识

来维持，而不是靠一个正式的 `host capability contract` 来维持。

**这就是通用化必须补上的核心缺口。**

### 4. 当前双端体验并不对称，Linux/macOS 仍有“接近满血但未权威闭环”的现实边界

当前仓库已经同时提供：

- Windows 路径：`powershell` / `pwsh` + `install.ps1` / `check.ps1`
- Linux/macOS 路径：`bash` + `install.sh` / `check.sh`

但这两条路径当前还不是严格等价的。现状是：

- Linux/macOS 在没有 `pwsh` 时，可以完成仓库内容安装与 MCP active profile 物化
- 但 authoritative PowerShell doctor / freshness / coherence gates 仍然会进入 shell degraded behavior
- 这意味着 Linux/macOS 目前更接近“可用且诚实降级”，而不是“与 Windows 完全等价的官方闭环”

因此，通用化不能只做宿主适配，还必须把 **Windows / Linux 双端体验等价性** 升级为正式目标。

### 5. 当前治理面已经足够强，但规模过大，必须做“收口”而不是继续平铺

从当前仓库状态看：

- `config/` 下已有 **110** 个配置文件
- `scripts/verify/` 下已有 **124** 个 gate / verify 资产

这说明当前问题已经不是“治理不够”，而是：

- 治理资产过多
- 新加入的开发者和用户不容易判断哪些是核心、哪些是扩展、哪些是历史波次遗留
- 如果继续以“每个 concern 一个新 policy + 一个新 gate”的方式推进，认知复杂度会超过收益

所以本次通用化改造，必须把 **治理简化 / 家族收口 / 面向人类的入口压缩** 作为并列目标，而不是留到后面再做。

## Additional Transformation Goals

除了“宿主通用化且不退化”，本次改造再增加两个一级目标：

### Goal A: Windows / Linux Dual-End First-Class Support

目标不是“两个平台都能勉强装起来”，而是：

- 两端都存在正式、清晰、可验证的安装路径
- 两端都存在官方支持等级表
- 两端的差异以 capability / gate / doctor 报告显式揭示
- 能自动化的部分尽量等价，不能等价的部分要被诚实标注

### Goal B: Governance Compression Without Losing Auditability

目标不是简单删除 policy / gate，而是：

- 收敛人类入口
- 收敛 family 级别文档
- 收敛默认 operator 路径
- 收敛“同类规则的散落表达”

同时保留：

- 可审计性
- 回滚能力
- 家族级证据
- 细粒度 gate 的机器可执行性

换句话说，**先压缩认知面，再决定是否压缩文件数**。

### Goal C: Model-Neutral Routing Intelligence Without Losing Governance Quality

目标不是把 GPT / OpenAI 从系统里“完全拿掉”，而是把它从“隐式唯一前提”收敛为“可替换的路由智能后端”。

本次通用化必须额外解决三个问题：

- 当前路由治理里已经存在 OpenAI / GPT 相关默认值与调用辅助，若不显式抽象，会形成 provider lock-in
- 宿主通用化以后，不同宿主、不同企业环境、不同地区网络条件下，不一定都允许同一模型提供方直连
- 如果把“模型调用”直接写死成“路由真相来源”，一旦 provider 不可用，系统就会从“通用”退化成“名义通用、实质绑定”

因此，本次改造必须把路由智能层升级为：

- `single routing authority` 不变
- `model provider` 可替换
- `provider unavailable` 时有显式降级契约
- `provider-specific env / endpoint / model id` 不再被误当成 canonical routing contract

## Non-Negotiable Principle

### Principle 1: Official Runtime Must Remain Authoritative

当前 `vco-skills-codex` 必须继续作为：

- 官方参考运行时
- 治理真源
- 满血功能承诺载体
- 版本与 release 的 authoritative implementation

它不是未来被“抽空”的 legacy；它是未来各宿主适配的基准。

### Principle 2: Universalization Is Additive, Not Replacement

通用化只能是新增三个面：

1. `canonical core`
2. `host adapters`
3. `cross-host verification`

而不能先去改：

- 现有 router 主行为
- 现有 install/check 主入口
- 现有 bundled mirror 语义
- 现有 release/runtime freshness contract

### Principle 3: Capability Model Before Compatibility Claims

在没有形成统一 capability vocabulary 之前，不允许使用“已支持某某宿主”的宣传表述。

必须先定义：

- skill 需要什么能力
- 宿主能提供什么能力
- 缺失能力时如何降级
- 降级是否仍满足该 skill 的最低完成标准

### Principle 4: No Silent Degrade

一旦某个宿主不支持某项能力，必须显式进入以下状态之一：

- `full`
- `degraded-but-supported`
- `advisory-only`
- `unsupported`

不能出现“看起来装上了，但其实执行闭环已经断了”的假兼容。

### Principle 5: Platform Parity Must Be Explicitly Modeled

Windows 与 Linux/macOS 的支持等级不能靠 README 段落暗示，必须进入正式合同层。

必须建模：

- 每个平台的 install surface
- 每个平台的 authoritative gates
- 每个平台的 degraded path
- 每个平台的 optional prerequisites
- 每个平台的 host-managed surfaces

### Principle 6: Governance Must Be Compressed at the Human Layer First

治理收口必须优先发生在：

- docs 入口
- family index
- operator runbook
- contributor decision table

而不是先粗暴合并配置或删除 gates。

原因很简单：

- 很多细粒度 gate 对机器和审计是有价值的
- 让人困惑的往往不是“文件太多”本身，而是“看不出从哪里进入、哪些必须跑、哪些只是扩展”

因此，本计划禁止为了“看起来简洁”而先删掉细粒度治理资产。

### Principle 7: Routing Intelligence Must Be Provider-Neutral and Non-Authoritative

对于通用 `VibeSkills` 而言，必须把“路由控制面”与“模型推理面”分离：

- **路由控制面**：仍然由 canonical VCO pack router / routing rules / thresholds / replay contract 担任唯一权威
- **模型推理面**：只负责 semantic extraction、candidate rerank、advice、shadow evaluation 或 explainability enhancement

严格禁止：

- 让某个 GPT / OpenAI provider 成为唯一可运行前提
- 让 provider 直接接管 pack selection ownership
- 让 provider-specific prompt / response schema 成为 host adapter 的公共契约
- 用“模型不可用时 silent fallback”冒充“依然 fully supported”

允许的方向只有：

- provider-neutral contract
- provider swap without router rewrite
- explicit degrade state when provider is absent
- offline / heuristic-only path with truthful support labeling

## Target Architecture

## A. Four-Layer Model

### Layer 0: Official Runtime

现有 `vco-skills-codex` 继续承担：

- 官方满血执行链
- 官方治理链
- 官方 release / install / check / doctor
- 官方 proof bundle

这是 `Tier-1 Official Runtime`。

### Layer 1: Canonical VibeSkills Core

新增一个宿主无关的核心层，负责表达 skill 的真相，不负责宿主物化。

建议目录：

- `core/skills/`
- `core/contracts/`
- `core/examples/`
- `core/tests/`
- `schemas/`

建议每个 skill 的 canonical 资产至少包含：

- `skill.json`
- `instruction.md`
- `compatibility.json`
- `examples/*.json`
- `tests/*.json`

### Layer 2: Host Adapters

新增宿主适配层：

- `adapters/codex/`
- `adapters/claude-code/`
- `adapters/opencode/`
- `adapters/generic/`

它们的职责是：

- 映射宿主配置目录
- 映射宿主 settings schema
- 映射宿主 hooks / MCP / plugin surface
- 映射宿主能力到统一 capability 名称
- 提供 degrade contract

### Layer 3: Distribution Packs

新增分发包层：

- `dist/core`
- `dist/host-codex`
- `dist/host-claude-code`
- `dist/host-opencode`
- `dist/official-runtime`

用户面对的是不同层次的产品，而不是一个混合包。

## C. Routing Intelligence Control Plane

通用化之后，必须把“路由器”与“路由智能增强”拆成两个显式层：

### C1. Canonical Routing Authority

这一层继续由现有资产代表：

- `scripts/router/resolve-pack-route.ps1`
- `config/pack-manifest.json`
- `config/router-thresholds.json`
- `config/skill-routing-rules.json`
- `config/skill-alias-map.json`

这一层负责：

- pack / skill assignment
- confirm-required decision
- fallback-to-legacy decision
- route probe and route replay contract

这一层 **不得** 绑定某一家模型提供方。

### C2. Routing Intelligence Provider Layer

这一层表达“如果需要 LLM 辅助，可通过什么 provider、以什么约束、在什么风险边界内运行”。

当前仓库里已经存在需要被治理化的实证资产：

- `scripts/router/modules/01-openai-responses.ps1`
- `config/settings.template.codex.json`
- `config/ruc-nlpir-runtime.json`

这些资产说明：

- 仓库已经支持以 OpenAI-compatible surface 作为一部分智能治理能力来源
- 但目前这层还没有被正式抽象成 provider-neutral contract

通用化后，这一层必须只承担：

- semantic enrichment
- advisory rerank
- replay comparison
- shadow evaluation
- explainability augmentation

并且必须支持至少三种运行状态：

- `provider-assisted`
- `heuristic-only`
- `offline-frozen`

### C3. Hard Separation Rule

任何 provider layer 都不得：

- 成为第二个 router
- 修改 canonical pack ownership
- 绕过 explicit command priority
- 改写 official runtime 的 release / verify 主链
- 在 host adapter 内写死成不可替换的唯一模型依赖

## D. Platform Support Model

建议把“宿主兼容”和“操作系统兼容”拆开，不混为一谈。

### Host Compatibility

- Claude Code
- Codex
- OpenCode
- Generic Host

### Platform Compatibility

- Windows
- Linux
- macOS

每个 `host adapter` 之下，再显式声明平台能力矩阵，例如：

- `adapters/codex/platform-windows.json`
- `adapters/codex/platform-linux.json`
- `adapters/claude-code/platform-windows.json`
- `adapters/claude-code/platform-linux.json`

这样你不会再陷入“宿主支持了，但平台侧没闭环”的模糊状态。

## E. Governance Compression Model

治理收口建议分三层：

### Layer 1: Human Entry Compression

面向用户 / 开发者 / operator 的入口压缩成少数几个面：

- `README`
- `CONTRIBUTING`
- `docs/README`
- `scripts/verify/gate-family-index.md`
- `docs/status/non-regression-proof-bundle.md`

### Layer 2: Family-Level Governance

把 110 个 config、124 个 verify 资产先按 family 显式分组，并给出：

- family owner
- family purpose
- default run order
- when not to care
- escalation conditions

### Layer 3: Physical Consolidation Candidates

只有在 family-level 使用稳定后，才允许进入真正的物理合并，例如：

- 把多份高度重叠的 overlay policy 合并成 family bundle
- 把多份重复表达的 README/plan 归并到正式 index
- 把部分波次遗留 gate 迁入 archival / historical lane

**先做逻辑收口，再做物理收口。**

## B. Capability Model

建议定义统一 capability vocabulary，例如：

- `fs.read`
- `fs.write`
- `shell.exec`
- `web.search`
- `browser.automation`
- `mcp.client`
- `settings.materialize`
- `plugin.provision`
- `agent.spawn`
- `route.semantic_extract`
- `route.semantic_rerank`
- `route.provider_call`
- `route.offline_fallback`
- `route.explainability`
- `memory.session`
- `memory.project`
- `secret.prompt`
- `release.verify`

每个 skill 申明：

- `required_capabilities`
- `optional_capabilities`
- `degrade_paths`

每个宿主申明：

- `available_capabilities`
- `host_constraints`
- `unsupported_capabilities`
- `manual_surfaces`

路由器以后基于 capability 做决策，而不是基于品牌名做决策。

## C. Compatibility Tier Model

建议对外只公布分层兼容矩阵，不公布“统一满血”。

### Tier-1 Official Full Runtime

含义：

- 路由、安装、MCP、治理、验证、同步、多智能体闭环都被官方验证过

初始成员：

- Codex runtime
- 当前仓库支持的 Claude 风格 runtime

### Tier-2 Host Adapter Runtime

含义：

- 核心 skill contract 可用
- 部分自动化可用
- 部分 surfaces 为 manual
- 有明确 degrade contract

目标成员：

- OpenCode
- 其他支持 shell/settings/MCP 的宿主

### Tier-3 Contract Consumer

含义：

- 可消费 canonical skills
- 可读 instruction / metadata / examples
- 可手动执行或半自动执行
- 不承诺官方运行时闭环

目标成员：

- 其他 agent hosts
- 只具备 prompt + tool 的轻宿主

## No-Regression Migration Strategy

## Phase 0: Freeze the Current Baseline

### Goal

先证明“当前什么东西绝对不能退”。

### Deliverables

- `docs/universalization/baseline-scope.md`
- `references/proof-bundles/official-runtime-baseline/`
- `config/official-runtime-baseline.json`

### Must Record

- 当前官方 runtime 支持的能力全集
- 当前 install / check / deep doctor 通过链
- 当前 router replay golden set
- 当前 multi-agent / fallback / confirm_required 行为集
- 当前 README 对满血版、手工前置条件的真实边界
- 当前 Windows / Linux/macOS 双端差异矩阵
- 当前治理资产规模与家族分布图

### Gates

- `vibe-version-consistency-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-offline-skills-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`
- 新增 `vibe-official-runtime-baseline-gate.ps1`

### Hard Rule

在 Phase 0 未完成前，禁止开始任何 core/adapters 目录层面的宣传或发布。

## Phase 1: Extract Canonical Skill Contract Without Changing Runtime Behavior

### Goal

把“skill 真相”从现有运行时文件中抽出来，但不改变现有运行时。

### Deliverables

- `schemas/skill.schema.json`
- `schemas/host-capability.schema.json`
- `schemas/skill-compatibility.schema.json`
- `core/skills/<skill-id>/...`
- `docs/universalization/core-contract.md`

### Scope

第一批只挑核心技能试点，不全量迁移。推荐首批：

- `vibe`
- `tdd-guide`
- `systematic-debugging`
- `code-reviewer`
- `security-reviewer`
- `brainstorming`
- `writing-plans`
- `subagent-driven-development`

### Rule

现有 `SKILL.md` 不删除，不替换，不改变运行面语义。  
只建立 canonical 映射关系，例如：

- `SKILL.md` -> `core/skills/vibe/instruction.md`
- `config/...` -> `core/contracts/...`

### Gates

- 新增 `skill-contract-schema-gate.ps1`
- 新增 `skill-contract-parity-gate.ps1`
- 新增 `skill-example-replay-gate.ps1`

## Phase 1.5: Freeze Platform Contract and Dual-End Truth

### Goal

把 Windows / Linux/macOS 的真实差异固化为合同，而不是留在文档注释里。

### Deliverables

- `docs/universalization/platform-support-matrix.md`
- `config/platform-support-policy.json`
- `references/platform-gap-ledger.md`

### Must Record

- Windows 官方闭环路径
- Linux/macOS 在有 `pwsh` 时的权威路径
- Linux/macOS 在无 `pwsh` 时的降级路径
- 哪些脚本是跨平台等价的
- 哪些脚本仍然带平台前提

### Gates

- 新增 `vibe-platform-support-contract-gate.ps1`
- 新增 `vibe-windows-linux-doctor-parity-gate.ps1`

## Phase 1.75: Freeze Routing Intelligence Contract and Provider Neutrality

### Goal

把当前 GPT / OpenAI 参与的路由智能增强能力，从“事实存在但治理未明示”升级为“单一路由权威之下的可替换 provider 层”。

### Deliverables

- `docs/universalization/router-model-neutrality.md`
- `config/router-model-governance.json`

### Must Record

- 哪些现有资产已经直接引用 OpenAI-compatible base URL / API key / model id
- 当前 provider 在系统中的职责边界：advice、shadow、rerank、semantic extraction、还是 assignment
- provider 缺失时，哪些能力可以继续运行，哪些能力只能 truthful degrade
- 哪些 host / platform 组合默认允许 provider-assisted，哪些只能 heuristic-only

### Hard Rule

本阶段开始之后，通用化改造一律遵守：

- pack router remains the only routing authority
- provider layer can enhance but cannot own assignment
- provider unavailability must become an explicit runtime state
- provider-specific env names are runtime bindings, not canonical cross-host truth

### Gates

- 新增 `vibe-router-provider-neutrality-gate.ps1`
- 新增 `vibe-router-no-provider-lockin-gate.ps1`
- 新增 `vibe-router-offline-degrade-contract-gate.ps1`

## Phase 2: Build Host Capability Registry and Adapters

### Goal

先建立宿主能力差异表，再做 adapter。

### Deliverables

- `adapters/codex/host-profile.json`
- `adapters/claude-code/host-profile.json`
- `adapters/opencode/host-profile.json`
- `adapters/generic/host-profile.json`
- `docs/universalization/host-capability-matrix.md`

### Adapter Responsibilities

每个 adapter 必须只处理：

- settings schema 映射
- install/materialize 入口
- plugin / MCP / hooks 映射
- capability exposure
- degrade contract

每个 adapter 明确禁止：

- 修改 canonical skill truth
- 修改官方 runtime 的 release / verify 主链
- 自行引入第二套 router truth

### Gates

- 新增 `host-capability-schema-gate.ps1`
- 新增 `adapter-contract-gate.ps1`
- 新增 `adapter-no-runtime-takeover-gate.ps1`

## Phase 2.5: Governance Family Convergence and Human-Layer Simplification

### Goal

在不损失审计能力的前提下，把治理面从“文件海”收口为“家族化入口”。

### Deliverables

- `docs/governance-family-map.md`
- `config/governance-family-index.json`
- `docs/operator-default-runbooks.md`
- `docs/contributor-default-runbooks.md`

### Tasks

1. 盘点并标注当前 110 个 config 的 family 归属
2. 盘点并标注当前 124 个 verify 资产的 family 归属
3. 定义每个 family 的：
   - `authoritative entry`
   - `default operator path`
   - `required for release` / `advisory only`
   - `active` / `historical` / `experimental`
4. 统一 README / docs / release notes 中的 family 入口
5. 对高度重叠的 family 给出后续物理合并候选，但本阶段只做标记，不强行合并

### Hard Rule

本阶段默认只做：

- 索引化
- 分层化
- 入口收口
- 状态标记

不默认做：

- 大规模删配置
- 大规模删 gate
- 把历史波次资产直接移除

### Gates

- 新增 `vibe-governance-family-index-gate.ps1`
- 新增 `vibe-governance-entry-compression-gate.ps1`
- 复用 `vibe-wave125-gate-family-convergence-gate.ps1` 作为历史对齐参考

## Phase 3: Cross-Host Replay and No-Regression Proof

### Goal

证明通用化是“增量兼容”，而不是“把官方功能做没了”。

### Replay Types

1. Route Replay
- 同一批任务输入，比较 official runtime 与 canonical+adapter 的 route result

2. Capability Replay
- 验证同一 skill 在不同宿主上的 capability resolution 是否符合 contract

3. Degrade Replay
- 验证缺失能力时是否进入正确 degrade state

4. Safety Replay
- 验证 manual surfaces 不会被假装成 auto-ready

5. Install Replay
- 验证 host-pack 安装不会污染 official runtime

### Deliverables

- `tests/replay/route/*.json`
- `tests/replay/degrade/*.json`
- `tests/replay/install/*.json`
- `docs/universalization/no-regression-proof-standard.md`
- `tests/replay/router-provider/*.json`

### Gates

- 新增 `vibe-cross-host-route-parity-gate.ps1`
- 新增 `vibe-cross-host-degrade-contract-gate.ps1`
- 新增 `vibe-cross-host-install-isolation-gate.ps1`
- 新增 `vibe-cross-host-router-provider-parity-gate.ps1`
- 新增 `vibe-universalization-no-regression-gate.ps1`

## Phase 4: Dist Packs and Controlled Promotion

### Goal

在 proof 通过前提下，把 core 和 adapters 做成正式分发包。

### Deliverables

- `dist/core/manifest.json`
- `dist/host-codex/manifest.json`
- `dist/host-claude-code/manifest.json`
- `dist/host-opencode/manifest.json`
- `dist/official-runtime/manifest.json`
- `docs/universalization/install-matrix.md`
- `docs/universalization/platform-install-matrix.md`

### Promotion Policy

只有满足以下条件，宿主适配器才能从 `experimental` 升到 `supported`：

1. adapter contract gate 通过
2. cross-host replay 通过
3. 没有侵入 official runtime 主链
4. 安装与卸载都有 isolation 证明
5. README 中对该宿主的支持等级表述真实

## Frozen Zones During Migration

以下区域在通用化 Phase 0-3 期间属于冻结区：

- `SKILL.md`
- `install.ps1`
- `install.sh`
- `check.ps1`
- `check.sh`
- `scripts/bootstrap/**`
- `scripts/router/**`
- `scripts/governance/release-cut.ps1`
- `scripts/governance/sync-bundled-vibe.ps1`
- `bundled/skills/vibe/**`
- `config/version-governance.json`

这些区域只能做：

- 必要 bugfix
- baseline verification 修复
- 已有 contract 的一致性修复

不能做：

- 为适配新宿主而修改主链
- 为了通用化删除现有 behavior
- 为了抽象美观而改变当前 release/install/runtime semantics

## Allowed Development Zones

通用化阶段的首选开发区：

- `core/**`
- `adapters/**`
- `schemas/**`
- `dist/**`
- `docs/universalization/**`
- `tests/replay/**`
- 新增 verify gates

这样可以最大限度降低对现有运行面的冲击。

## Anti-Regression Test Program

## A. Official Runtime Must Not Get Worse

每一波通用化改造结束后，官方运行时至少要重复以下检查：

- `git diff --check`
- `check.ps1 -Profile full`
- `check.ps1 -Profile full -Deep`
- `scripts/verify/vibe-offline-skills-gate.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-router-contract-gate.ps1`
- `scripts/verify/vibe-version-consistency-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

### Passing Rule

新改造后结果不得弱于 Phase 0 记录的 baseline。

## B. New Universal Surfaces Must Prove They Are Honest

新增通用层必须通过：

- schema validation
- skill parity
- host capability contract validation
- degrade-state validation
- install isolation validation
- replay consistency validation

### Passing Rule

如果某宿主只达到了 `degraded-but-supported`，文档必须写成 `degraded-but-supported`，不能写成 `full support`。

## Release and Rollback Strategy

## Release Lanes

建议引入三条 lane：

- `official-runtime-stable`
- `universal-core-preview`
- `host-adapter-preview`

### Meaning

- 官方运行时稳定线继续对外承诺满血体验
- core preview 只对开发者和生态伙伴开放
- adapter preview 只在证据足够时逐个宿主放量

## Rollback Rule

出现以下任一情况，必须立即停止 promotion 并回退到上一稳定点：

- official runtime baseline gate 变差
- cross-host replay 出现不可解释分叉
- adapter 修改触碰 runtime 主链
- README 承诺与真实兼容等级不一致
- install profile 污染现有 `~/.codex` 运行时

## Success Criteria

只有当以下条件全部成立，才算完成“不退化通用化迁移”的第一阶段闭环：

1. 官方 runtime 继续保持 `Tier-1 Official Runtime` 地位。
2. 已形成正式 `core contract`，至少覆盖第一批核心 skills。
3. 已形成正式 capability vocabulary。
4. 已形成 `codex / claude-code / opencode / generic` 四个 host profile。
5. 已形成跨宿主 replay 和 degrade contract。
6. 通用化改造没有让现有 release/install/runtime gates 变差。
7. README 可以真实表达：
   - 官方满血运行时是什么
   - 通用 core 是什么
   - 各宿主支持等级是什么
8. Windows / Linux 双端都存在正式、诚实、可验证的支持矩阵。
9. 治理入口已从“海量离散文件”收口为少数 family 级入口，新增开发者能在短路径内找到正确规则。
10. GPT / OpenAI 不再是通用 `VibeSkills` 路由治理的隐式唯一前提，而是被治理为可替换 provider。
11. 在 provider 缺失时，系统仍能以 `heuristic-only` 或 `offline-frozen` 方式保持 truthful 可运行，而不是 silent failure 或虚假满血声明。

## What This Means for Your Two New Requirements

### Windows / Linux 双端优化是否应该纳入这次改建

应该，而且必须纳入。

原因是：

- 这不是纯安装体验问题，而是通用化真实性问题
- 如果平台侧仍然是“Windows 权威、Linux 准权威”，那通用化会天然带着不对称
- 通用 skill 生态如果不能说明不同平台的能力边界，就会在推广时制造误解

### 治理框架是否应该精简合并

应该，但必须分两步：

1. **先收口入口和家族**
   - 让人知道看哪里、跑哪些、忽略哪些
2. **再决定物理合并**
   - 只合并那些经过使用证明确实重复、且不会损失审计价值的部分

换句话说，不是“少文件 = 更清晰”，而是“更少的默认入口 + 更明确的家族边界 = 更清晰”。

## Practical Recommendation

### What To Do Next

最务实的执行顺序如下：

1. 先落 `Phase 0 baseline freeze`
2. 再落 `schemas + core contract`
3. 再落 `host capability matrix`
4. 再落 `codex / claude-code / opencode adapters`
5. 最后才做对外发布口径升级

### What Not To Do

以下做法必须避免：

- 直接把现有官方 runtime 重命名成“通用 runtime”
- 先写 README 宣称通用，再补 capability contract
- 先让 adapter 改 install/check/router，再谈兼容
- 用宿主特有 prompt 约定冒充“宿主无关”
- 用一个混合大包同时承诺所有宿主都满血

## Final Position

**不退化通用化是可以做到的。**  
但前提不是“把现有系统统一掉”，而是“把现有官方系统保护住，然后在它旁边长出一个宿主无关 core 和多宿主 adapter 体系”。

换句话说：

不是把 `vco-skills-codex` 改没。  
而是让它从“唯一运行时”升级成“官方参考运行时 + 通用技能基座的治理真源”。

这才是既不退化、又能真正通用的迁移路线。
