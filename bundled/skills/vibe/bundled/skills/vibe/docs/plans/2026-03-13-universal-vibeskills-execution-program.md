# Universal VibeSkills Execution Program

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.
>
> Companion documents:
> - `docs/plans/2026-03-13-universal-vibeskills-no-regression-migration-plan.md`
> - `docs/universalization/platform-support-matrix.md`
> - `docs/universalization/router-model-neutrality.md`
> - `docs/governance-family-map.md`

**Goal:** 在不削弱当前 `vco-skills-codex` 官方满血运行时的前提下，把项目演进为一个可被 Codex、Claude Code、OpenCode 以及其他宿主消费的通用 `VibeSkills` 生态包，并用可重复验证的方式证明没有功能退化。

**Architecture:** 采用“双轨并行、冻结官方运行时、增量抽取 core、显式 host adapter、证据驱动 promotion”的改造路径。当前仓库继续承担 `Tier-1 Official Runtime`，新建 `core/`、`adapters/`、`schemas/`、`dist/`、`tests/replay/` 等通用化层，任何跨宿主能力都先进入新层验证，再决定是否提升为正式分发面。

**Tech Stack:** PowerShell gates, Bash install wrappers, JSON policy contracts, replay fixtures, MCP profile materialization, host settings templates, route-control-plane verification.

---

## 1. Current Code-Grounded Judgment

本次通用化重建可以做，但当前仓库的真实形态必须先讲清楚，否则后续改造会天然引入退化风险。

### 1.1 当前仓库不是宿主无关 core，而是强治理的官方运行时

直接证据：

- `scripts/router/resolve-pack-route.ps1` 是单一的真实路由控制面，并且加载大量运行时模块，包括 `01-openai-responses.ps1`、`42-ai-rerank-overlay.ps1`、`43-retrieval-overlay.ps1`、`44-exploration-overlay.ps1`、`46-confirm-ui.ps1`。
- `install.ps1`、`check.ps1`、`scripts/bootstrap/one-shot-setup.ps1`、`scripts/setup/materialize-codex-mcp-profile.ps1` 已经形成安装、体检、配置物化、运行时 freshness/coherence 的完整链路。
- `config/version-governance.json` 明确声明 canonical root、bundled root、nested bundled root、installed runtime markers、receipt contract、shell degraded behavior。
- `config/settings.template.codex.json` 与 `config/settings.template.claude.json` 说明当前已经有宿主特化的配置模板，不存在“天然通用”的运行时层。

### 1.2 当前治理面规模很大，问题不是治理不够，而是入口不够收敛

当前仓库实证：

- `config/` 下已有 `113` 个配置文件。
- `scripts/verify/` 下已有 `124` 个验证脚本。
- `core/`、`adapters/`、`schemas/`、`dist/`、`tests/replay/` 这些通用化目录目前仍不存在。

结论：

- 不能继续把“新增治理”当成默认动作。
- 必须先做“治理入口收敛”和“家族化索引”，再考虑物理合并配置或删除 gate。

### 1.3 当前 OpenAI/GPT 能力是真实存在的运行时增强面，但还没有被治理成 provider-neutral contract

直接证据：

- `scripts/router/modules/01-openai-responses.ps1`
- `config/settings.template.codex.json`
- `config/ruc-nlpir-runtime.json`

结论：

- 这层能力不应被删除。
- 这层能力也不能再被默认当成“唯一合法的路由智能来源”。
- 必须变成“单一路由权威之下的可替换 provider layer”。

### 1.4 Windows 和 Linux 当前不应被夸大为完全等价

当前事实：

- Windows 路径由 `install.ps1`、`check.ps1` 和 PowerShell 权威 gate 主导。
- Linux/macOS 可以通过 `install.sh`、`check.sh` 完成安装，但若无 `pwsh`，仍会进入 `warn_and_skip_authoritative_runtime_gate` 这类降级逻辑。

结论：

- 本次通用化必须显式建模平台支持等级。
- 不允许在 README 或分发文案中把“可运行”偷换为“满血等价”。

## 2. Non-Negotiable Rules

以下规则在整个通用化重建中不可违反。

### 2.1 官方运行时冻结优先

在 Phase 0 到 Phase 3 之间，以下区域默认冻结，不为通用化直接改写：

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

冻结含义：

- 允许修复明确 bug。
- 允许做不改变语义的验证性补丁。
- 不允许为了迁移方便直接改成“新的通用运行时”。

### 2.2 通用化只允许增量新增，不允许原地替换

优先新增：

- `core/**`
- `adapters/**`
- `schemas/**`
- `dist/**`
- `tests/replay/**`
- `docs/universalization/**`
- 新的 `scripts/verify/vibe-universal-*` 或 `scripts/verify/vibe-cross-host-*` gate

### 2.3 路由控制权不能外包给模型 provider

必须保持：

- `scripts/router/resolve-pack-route.ps1` 仍是唯一 route assignment authority。
- provider 只能做 semantic extraction、rerank、shadow eval、explainability advice。
- provider 不得绕过 `pack-manifest.json`、`router-thresholds.json`、`skill-routing-rules.json` 的 canonical ownership。

### 2.4 任何降级都必须被显式标记

只允许四种状态：

- `full`
- `degraded-but-supported`
- `advisory-only`
- `unsupported`

不允许 silent degrade，不允许“看起来可用，实际核心链路未闭环”的伪兼容。

## 3. Proof Standard

“不退化”不是主观判断，而是下面这些证据同时成立。

### 3.1 官方运行时不退化

每一波通用化改造之后，以下基线命令必须保持通过：

```powershell
git diff --check
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-contract-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-version-consistency-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-version-packaging-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1
```

### 3.2 新通用层必须证明自己诚实

新增的 core/adapter/dist 侧必须建立新的 proof bundle：

- schema validity
- route parity
- capability honesty
- degrade honesty
- install isolation
- provider-neutral routing behavior
- Windows/Linux support-level truthfulness

### 3.3 Promotion 必须满足“三次连续通过”原则

任一 adapter 或 dist pack 要从 `experimental` 提升为 `supported`，必须满足：

1. 连续三次完整验证通过。
2. 三次运行来自至少两个独立 clean workspace。
3. Windows 和 Linux 至少各有一次真实验证记录。
4. 没有对官方运行时基线造成任何新增失败。

## 4. Workstreams

本次重建拆成 8 条并行但带依赖的工作流。

### WS0: Baseline Freeze and Evidence Capture

目标：冻结官方运行时的真实基线，并把它变成后续一切通用化工作的裁判。

### WS1: Canonical Skill Contract Extraction

目标：从当前运行时抽取宿主无关的 skill truth，而不是重写现有 `SKILL.md`。

### WS2: Provider-Neutral Routing Governance

目标：把当前 GPT/OpenAI 参与的路由增强面治理为 replaceable provider layer。

### WS3: Host Capability Registry and Adapters

目标：显式表达 Codex、Claude Code、OpenCode、Generic Host 的能力差异、配置差异和降级路径。

### WS4: Platform Parity Modeling

目标：把 Windows、Linux、macOS 的真实支持差异纳入正式 contract。

### WS5: Governance Family Convergence

目标：压缩治理入口，不牺牲审计颗粒度。

### WS6: Replay Harness and No-Regression Gates

目标：把“不退化”变成自动验证，而不是口头保证。

### WS7: Distribution and Install Experience

目标：最终实现面向不同宿主的可分发包，同时不污染官方运行时主链。

## 5. Detailed Execution Tasks

下面的任务按实际执行顺序排列。每个任务都说明修改范围、禁止触碰范围、验证方式和完成标准。

### Task 0: 建立官方运行时零退化基线

**Files:**
- Create: `docs/universalization/official-runtime-baseline.md`
- Create: `references/proof-bundles/official-runtime-baseline/README.md`
- Create: `references/proof-bundles/official-runtime-baseline/baseline-manifest.json`
- Create: `scripts/verify/vibe-official-runtime-baseline-gate.ps1`
- Modify: `docs/plans/2026-03-13-universal-vibeskills-no-regression-migration-plan.md`

**Design:**
- 把当前官方运行时的关键资产、关键 gate、关键命令、关键输出，写成可比对 baseline。
- 该 baseline 以后成为所有通用化改造的裁判。

**Do not touch:**
- `install.ps1`
- `check.ps1`
- `scripts/router/**`

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-official-runtime-baseline-gate.ps1
```

**Done when:**
- 官方运行时的最小判定面被文档化。
- baseline gate 可以判断“当前结果是否弱于基线”。

### Task 1: 建立 canonical skill schema 和 core 目录骨架

**Files:**
- Create: `schemas/skill.schema.json`
- Create: `schemas/host-capability.schema.json`
- Create: `schemas/skill-compatibility.schema.json`
- Create: `core/README.md`
- Create: `core/skills/vibe/skill.json`
- Create: `core/skills/vibe/instruction.md`
- Create: `core/skills/vibe/compatibility.json`
- Create: `core/skills/tdd-guide/skill.json`
- Create: `core/skills/systematic-debugging/skill.json`
- Create: `core/skills/code-reviewer/skill.json`
- Create: `core/skills/brainstorming/skill.json`
- Create: `core/skills/writing-plans/skill.json`
- Create: `core/skills/subagent-driven-development/skill.json`
- Create: `docs/universalization/core-contract.md`
- Create: `scripts/verify/vibe-skill-contract-schema-gate.ps1`
- Create: `scripts/verify/vibe-skill-contract-parity-gate.ps1`

**Design:**
- 第一批只抽 7 个核心技能，避免一次性全量迁移造成 schema 抖动。
- `instruction.md` 代表 canonical instruction，而不是替换运行时的 `SKILL.md`。
- `compatibility.json` 负责声明 required/optional capabilities 与 degrade rules。

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-contract-schema-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-contract-parity-gate.ps1
```

**Done when:**
- 新 schema 可以校验第一批 core skills。
- core skill truth 与现有 `SKILL.md` 没有语义漂移。

### Task 2: 把路由增强面治理为 provider-neutral layer

**Files:**
- Create: `schemas/router-provider.schema.json`
- Create: `config/router-provider-registry.json`
- Create: `config/router-provider-defaults.json`
- Create: `docs/universalization/router-provider-layer.md`
- Create: `scripts/verify/vibe-router-provider-neutrality-gate.ps1`
- Create: `scripts/verify/vibe-router-offline-degrade-contract-gate.ps1`
- Modify: `docs/universalization/router-model-neutrality.md`
- Modify: `config/router-model-governance.json`

**Design:**
- 不改 `resolve-pack-route.ps1` 的 owner 语义。
- 只补 provider contract，把 OpenAI-compatible layer、ARK layer、heuristic-only layer 的职责边界写清楚。
- 把 “provider missing” 明确成运行时状态，而不是 warning 文案。

**Do not touch until gate exists:**
- `scripts/router/modules/01-openai-responses.ps1`
- `scripts/router/modules/42-ai-rerank-overlay.ps1`

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-provider-neutrality-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-offline-degrade-contract-gate.ps1
```

**Done when:**
- provider 可替换，但 canonical router ownership 不变。
- provider 不可用时，系统能诚实输出 `heuristic-only` 或 `advisory-only`。

### Task 3: 建立 host capability registry

**Files:**
- Create: `adapters/README.md`
- Create: `adapters/codex/host-profile.json`
- Create: `adapters/claude-code/host-profile.json`
- Create: `adapters/opencode/host-profile.json`
- Create: `adapters/generic/host-profile.json`
- Create: `adapters/codex/settings-map.json`
- Create: `adapters/claude-code/settings-map.json`
- Create: `adapters/opencode/settings-map.json`
- Create: `adapters/generic/settings-map.json`
- Create: `docs/universalization/host-capability-matrix.md`
- Create: `scripts/verify/vibe-host-capability-schema-gate.ps1`
- Create: `scripts/verify/vibe-host-adapter-contract-gate.ps1`

**Design:**
- 每个 host profile 都必须显式声明：
  - available capabilities
  - unsupported capabilities
  - manual surfaces
  - degrade rules
  - settings materialization strategy
- 不能借 README 暗示某宿主“差不多支持”，必须有正式 profile。

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-host-capability-schema-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-host-adapter-contract-gate.ps1
```

**Done when:**
- 四类宿主的能力边界可被机器读取。
- 没有任何 adapter 伪装成“新的官方运行时”。

### Task 4: 建立平台支持合同，补 Windows/Linux/macOS 真实边界

**Files:**
- Create: `adapters/codex/platform-windows.json`
- Create: `adapters/codex/platform-linux.json`
- Create: `adapters/codex/platform-macos.json`
- Create: `adapters/claude-code/platform-windows.json`
- Create: `adapters/claude-code/platform-linux.json`
- Create: `adapters/claude-code/platform-macos.json`
- Create: `docs/universalization/platform-parity-contract.md`
- Create: `references/platform-gap-ledger.md`
- Create: `scripts/verify/vibe-platform-support-contract-gate.ps1`
- Create: `scripts/verify/vibe-platform-doctor-parity-gate.ps1`
- Modify: `docs/universalization/platform-support-matrix.md`
- Modify: `config/platform-support-policy.json`

**Design:**
- 把 “Linux 无 pwsh 时属于什么状态” 明确成 contract。
- 把 “Windows 权威路径”和 “Linux/macOS 权威路径/降级路径” 区分清楚。

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-platform-support-contract-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-platform-doctor-parity-gate.ps1
```

**Done when:**
- README 以后引用的是 contract，而不是手写叙述。
- 平台差异有正式证据，不再依赖记忆或口头解释。

### Task 5: 治理家族收敛，不删 gate，先收入口

**Files:**
- Create: `docs/governance/operator-runbook.md`
- Create: `docs/governance/contributor-runbook.md`
- Create: `docs/governance/gate-family-index.md`
- Create: `docs/governance/config-family-index.md`
- Create: `scripts/verify/vibe-governance-entry-compression-gate.ps1`
- Modify: `docs/governance-family-map.md`
- Modify: `config/governance-family-index.json`

**Design:**
- 先把 `113` 个 config 和 `124` 个 verify 资产做 family-level indexing。
- 明确：
  - authoritative entry
  - default run order
  - required-for-release / advisory-only
  - active / historical / experimental

**Hard rule:**
- 本阶段不做大规模删除文件。
- 只做入口收敛、索引收敛、默认路径收敛。

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-governance-entry-compression-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-wave125-gate-family-convergence-gate.ps1
```

**Done when:**
- 新 contributor/operator 不需要理解整个文件海才能开始工作。
- 但审计粒度没有丢。

### Task 6: 建立 replay harness，真正证明“不退化”

**Files:**
- Create: `tests/replay/route/README.md`
- Create: `tests/replay/route/official-runtime-golden.json`
- Create: `tests/replay/degrade/README.md`
- Create: `tests/replay/degrade/provider-missing.json`
- Create: `tests/replay/install/README.md`
- Create: `tests/replay/install/host-isolation.json`
- Create: `tests/replay/platform/README.md`
- Create: `tests/replay/platform/windows-vs-linux.json`
- Create: `scripts/verify/vibe-cross-host-route-parity-gate.ps1`
- Create: `scripts/verify/vibe-cross-host-degrade-contract-gate.ps1`
- Create: `scripts/verify/vibe-cross-host-install-isolation-gate.ps1`
- Create: `scripts/verify/vibe-universalization-no-regression-gate.ps1`
- Create: `docs/universalization/no-regression-proof-standard.md`

**Design:**
- route replay 证明“路由判断没有跑偏”
- degrade replay 证明“能力缺失时没有说谎”
- install replay 证明“新分发不会污染官方运行时”
- platform replay 证明“不同平台的支持等级陈述真实”

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-route-parity-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-degrade-contract-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-install-isolation-gate.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-universalization-no-regression-gate.ps1
```

**Done when:**
- “不退化”从口头承诺变成可自动执行的证明链。

### Task 7: 建立分发包结构，但不接管官方安装面

**Files:**
- Create: `dist/core/manifest.json`
- Create: `dist/host-codex/manifest.json`
- Create: `dist/host-claude-code/manifest.json`
- Create: `dist/host-opencode/manifest.json`
- Create: `dist/official-runtime/manifest.json`
- Create: `docs/universalization/distribution-lanes.md`
- Create: `docs/universalization/install-matrix.md`
- Create: `docs/universalization/platform-install-matrix.md`
- Create: `scripts/verify/vibe-dist-manifest-gate.ps1`

**Design:**
- `dist/official-runtime` 指向当前官方运行时，不重写它。
- `dist/core` 和 `dist/host-*` 只表达打包结果和 capability promise。
- promotion 之前不改主 README 的官方承诺。

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-dist-manifest-gate.ps1
```

**Done when:**
- 不同消费层有不同分发物，而不是一个混合大包。

### Task 8: 面向开发者和用户整理最终入口

**Files:**
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Create: `docs/universalization/quick-start-official-runtime.md`
- Create: `docs/universalization/quick-start-universal-core.md`
- Create: `docs/universalization/quick-start-host-adapters.md`
- Create: `docs/universalization/developer-safe-zones.md`
- Create: `docs/universalization/no-touch-zones.md`
- Create: `docs/universalization/change-approval-matrix.md`
- Create: `scripts/verify/vibe-developer-entry-universalization-gate.ps1`

**Design:**
- 用户入口必须先区分：
  - 官方满血运行时
  - 通用 core
  - 某宿主 adapter
- 开发者入口必须先区分：
  - 可自由开发区
  - 冻结区
  - 需要证明后才能动的敏感区

**Verification:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-developer-entry-universalization-gate.ps1
```

**Done when:**
- 新用户不会把 preview adapter 误认为官方满血运行时。
- 新开发者不会因为不清楚边界而破坏主链。

## 6. Wave and Batch Order

执行顺序必须严格按下面推进，不能跳步。

### Batch A: 只做基线和合同，不碰运行时主链

包含：

- Task 0
- Task 1
- Task 2 的文档与 schema 部分

退出条件：

- 官方运行时 baseline 固化完成。
- core schema 可用。
- provider-neutral contract 起草完成。

### Batch B: 建立宿主与平台 truth layer

包含：

- Task 3
- Task 4

退出条件：

- host/profile/platform 合同齐全。
- 还没有任何宿主被宣传为 fully supported，除非证据已经补齐。

### Batch C: 建立治理收敛和 replay harness

包含：

- Task 5
- Task 6

退出条件：

- family entry 收敛完成。
- no-regression proof chain 能自动跑通。

### Batch D: 建立分发面和开发者入口

包含：

- Task 7
- Task 8

退出条件：

- 分发 lane 清晰。
- README/CONTRIBUTING 口径与真实支持等级一致。

## 7. Test Matrix

### 7.1 Mandatory matrix

每个 batch 结束后至少执行以下矩阵：

| Surface | Windows | Linux | Expected |
| --- | --- | --- | --- |
| Official runtime health | required | required | must pass |
| Route parity | required | required | must match contract |
| Provider missing degrade | required | required | must emit explicit degrade state |
| Install isolation | required | required | must not pollute official runtime |
| Host adapter contract | required | required | must pass schema and policy gates |

### 7.2 Regression budget

本次改造的 regression budget 是严格零容忍：

- `0` 个 official runtime critical regression
- `0` 个 official runtime high regression
- `0` 个 silent degrade
- `0` 个 host-support overclaim

### 7.3 Stability proof

每个要晋升的阶段必须提供：

1. gate 通过日志
2. replay output
3. support-level report
4. 变更摘要
5. 回滚点

## 8. Rollback Rules

任意时刻出现以下情况，立即停止当前 batch，回到上一个稳定点：

- `check.ps1 -Profile full -Deep` 新增失败
- `vibe-pack-routing-smoke.ps1` 新增失败
- `vibe-router-contract-gate.ps1` 新增失败
- provider-neutral 改造影响 canonical router ownership
- adapter 改造污染官方运行时安装面
- README 或文档承诺超过真实支持等级

回滚策略：

1. 先撤回本 batch 的 preview 文档承诺。
2. 再撤回本 batch 的 adapter/core/dist 变更。
3. 官方运行时基线相关文件绝不跟着一起回滚，除非基线本身记录错误。

## 9. Developer Safety Rules

在本次通用化重建期间，开发者必须遵守以下边界。

### Allowed by default

- `core/**`
- `adapters/**`
- `schemas/**`
- `dist/**`
- `tests/replay/**`
- `docs/universalization/**`
- 新增 verify gates

### Require explicit proof before touching

- `config/settings.template.codex.json`
- `config/settings.template.claude.json`
- `scripts/setup/materialize-codex-mcp-profile.ps1`
- `config/pack-manifest.json`
- `config/router-thresholds.json`
- `config/skill-routing-rules.json`

### No-touch until Phase 4 review

- `scripts/router/resolve-pack-route.ps1`
- `scripts/router/modules/01-openai-responses.ps1`
- `install.ps1`
- `check.ps1`
- `install.sh`
- `check.sh`
- `config/version-governance.json`

## 10. Immediate Next Execution Batch

如果下一步开始真正实施，本轮应只执行下面这些动作，不要越界：

1. 创建 `official-runtime-baseline` 文档、manifest 和 baseline gate。
2. 创建 `schemas/`、`core/` 的最小骨架以及第一批 7 个核心 skill contract。
3. 创建 `router-provider` schema 与 neutrality gate 草案。
4. 不改 `install/check/router` 主链，不做任何 README 宣传升级。

## 11. Completion Standard

只有满足以下全部条件，才能宣称“此次全面通用化重建的第一阶段设计已经正确落地”：

1. 官方运行时仍然是唯一的 `Tier-1 Official Runtime`。
2. core contract 已建立，且与现有关键 skill 语义一致。
3. provider-neutral routing governance 已建立，但未削弱 canonical router authority。
4. host/platform capability contract 已建立，支持等级真实、诚实、可验证。
5. governance family 入口已收敛，开发者不会被文件海淹没。
6. replay harness 已建立，零退化可以被脚本证明。
7. 任何 preview adapter 和 dist pack 都不会污染官方运行时主链。

