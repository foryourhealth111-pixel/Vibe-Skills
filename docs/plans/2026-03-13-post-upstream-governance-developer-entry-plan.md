# Post-Upstream-Governance Developer Entry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在上游治理与仓库收敛的基础上，为 `vco-skills-codex` 建立一个正式、可执行、对开发者友好的入口体系，让外部贡献者和内部维护者都能明确知道从哪里开始、哪些区域可以开发、哪些区域禁止随意修改、如何通过验证链证明改动稳定落地且没有功能退化。

**Architecture:** 本计划采用 `entry-first + zone-gated + proof-required + additive-default` 架构。它不把“开发者入口”理解成单一的 `CONTRIBUTING.md`，而是把开发者进入仓库所需的入口文档、区域分级规则、提交流程、验证门槛、模板与 stop-ship 条件整合成一条统一路径。执行顺序是：先统一入口导航，再固化贡献分区，再接入验证与模板，最后用 canary contributor journey 和 proof bundle 证明这套开发者入口真的可用、不会诱导错误开发，也不会造成运行面退化。

**Tech Stack:** Markdown governance docs, CONTRIBUTING surface, PR/issue templates, PowerShell verify gates, plan/status reports, developer path zoning, proof bundle and canary contributor workflow checks.

---

## Positioning

- **This plan is downstream of:** [2026-03-13-distribution-governance-plan.md](2026-03-13-distribution-governance-plan.md)
- **This plan is downstream of:** [2026-03-13-post-upstream-governance-repo-convergence-plan.md](2026-03-13-post-upstream-governance-repo-convergence-plan.md)
- **This plan operationalizes:** [../developer-change-governance.md](../developer-change-governance.md)

这份计划解决的问题不是“仓库里有没有开发规则”，而是：

- 一个新开发者进入仓库时，看什么文档；
- 如何在 3 分钟内知道自己能改哪里、不能改哪里；
- 如果要碰高风险区域，必须补哪些计划与验证；
- 如何把这些规则做成真正可执行的入口，而不是散落在治理正文里的隐含知识。

## Current Verified Gap

### 1. 已有边界规则，但还没有正式开发者入口

当前仓库已经具备：

- [../developer-change-governance.md](../developer-change-governance.md)
- [../repo-cleanliness-governance.md](../repo-cleanliness-governance.md)
- [../output-artifact-boundary-governance.md](../output-artifact-boundary-governance.md)

但目前仍然缺少：

- `CONTRIBUTING.md`
- 明确的“新贡献者从哪里开始”入口
- 针对 zone 的 PR checklist / template
- 开发者任务类型与 required proof 的映射表

因此现在的状态是：

- 维护者能理解规则；
- 新开发者不一定能快速找到规则；
- 贡献入口仍然偏隐性；
- 高风险路径被误改的概率仍然存在。

### 2. 当前仓库还不能算“对开发者足够干净”

一个“对开发者足够干净”的仓库，不仅要：

- git/worktree 足够干净；
- output/fixture 边界足够清晰；
- upstream/disclosure 足够闭环；

还必须做到：

- 开发者入口单跳可达；
- 默认安全工作面一眼可见；
- 高风险区域有明确 stop rule；
- 验证要求不是维护者私下知道，而是贡献者公开可见。

### 3. 当前没有 contributor journey 的可验证证明

目前还没有一套“从新开发者视角验证入口是否可用”的证明链，例如：

- 是否能从 `README.md` 在 2 跳内到达贡献规则；
- 是否能在 5 分钟内定位默认安全工作面；
- 是否能明确知道什么时候必须先写计划；
- 是否能明确知道不能直接改 `bundled/**` / `scripts/router/**` / `install.*`。

没有这类 journey proof，就不能证明“开发者入口设计已经正确落地”。

## Design Principles

1. **Entry must be explicit, not folklore.**
   开发者入口不能依赖“你问维护者”或“看久了就懂了”。

2. **Safe-by-default contribution path.**
   默认贡献路径必须把开发者引向低风险 additive zone，而不是默认暴露控制面。

3. **High-risk changes require ceremony.**
   碰到 control plane、mirror、fixture、upstream/compliance 边界时，必须显式升级流程。

4. **Contributor UX is part of repo cleanliness.**
   开发者入口混乱，本质上也是仓库脏乱的一部分。

5. **Proof is mandatory for process claims.**
   不能只写“请跑测试”；必须明确哪些改动跑哪些 gates。

6. **Do not create a fake open repo.**
   这个仓库可以欢迎贡献，但不能伪装成“任何目录都欢迎随意修改”的宽松仓库。

## Definition of a Clean Developer Entry

开发者入口达到 `clean enough` 至少要满足以下条件：

1. 根入口能在 2 跳内到达贡献规则。
2. 存在正式的 `CONTRIBUTING.md`。
3. `CONTRIBUTING.md` 会把开发者引导到：
   - 默认安全工作面
   - 高风险冻结区
   - 计划文档
   - proof bundle
4. 有模板化的提交流程，不依赖口头提醒。
5. 有 canary contributor journey 验证结果。

## Entry Surface Design

### Layer 1: Root Entry

建议开发者入口主链路如下：

- `README.md`
- `CONTRIBUTING.md`
- `docs/developer-change-governance.md`
- `docs/repo-cleanliness-governance.md`
- `docs/governance/output-artifact-boundary-governance.md`

目标是让开发者从仓库根目录出发，不需要先理解全部治理体系，就能完成路径判断：

- 我是普通贡献者还是维护者？
- 我的改动属于哪一类？
- 我该从哪类目录开始？
- 我是否需要 plan 和 full proof bundle？

### Layer 2: Zone Decision Table

`CONTRIBUTING.md` 需要把 zone 规则浓缩成一张贡献决策表，至少包括：

- `Z0 Frozen Control Plane`
- `Z1 Guarded Governance/Policy`
- `Z2 Guarded Mirror/Fixture/Compliance`
- `Z3 Preferred Contribution Zones`

并且每类都要回答：

- 是否允许普通贡献者直接改；
- 需要哪些前置文档；
- 需要哪些验证；
- 什么情况下必须 stop and escalate。

### Layer 3: Task-Type Entry

开发者入口还要按任务类型给出起点：

- 文档改动
- gate / governance operator 改动
- upstream/provenance/compliance 改动
- mirror / fixture 改动
- runtime / router / install 改动

避免开发者只按“我想改哪个文件”思考，而忽略系统层级。

### Layer 4: Template Surface

需要让开发者入口连接到模板化流程，而不是纯文字说明：

- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/*`
- `docs/plans/*.md`
- future `templates/change-proof-checklist.md`

## Convergence Scope

本计划聚焦开发者入口，不直接重写运行时。范围包括：

- `README.md`
- `CONTRIBUTING.md`
- `docs/README.md`
- `docs/developer-change-governance.md`
- `docs/repo-cleanliness-governance.md`
- `docs/governance/output-artifact-boundary-governance.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/**`
- `docs/plans/README.md`

本计划明确不在第一轮处理：

- router 行为改写
- install/check 逻辑改写
- gate 内核重构
- bundled mirror 拓扑调整

## Execution Plan

### Batch 0: Freeze Developer Entry Baseline

**Objective**

先把当前“开发者进入仓库会看到什么”冻结成基线。

**Files**

- Create: `docs/status/developer-entry-baseline-2026-03-13.md`
- Reference:
  - `README.md`
  - `docs/README.md`
  - `docs/developer-change-governance.md`
  - `docs/plans/README.md`
  - `.github/**`

**Actions**

- 记录当前 root README 是否直接指向贡献入口
- 记录当前是否存在 `CONTRIBUTING.md`
- 记录当前 PR / issue template 状态
- 记录当前开发者需要几跳才能看到 zone 规则

**Exit criteria**

- baseline 文档完成
- 当前入口缺口被显式记录

### Batch 1: Establish Root Developer Entry

**Objective**

把开发者入口从“散落治理文档”收敛为正式 root entry。

**Files**

- Create: `CONTRIBUTING.md`
- Modify: `README.md`
- Modify: `docs/README.md`

**Actions**

- 在 root README 明确加入 Developer Entry / Contributing 入口
- 新建 `CONTRIBUTING.md`
- 在 `CONTRIBUTING.md` 中明确：
  - quick start
  - zone model summary
  - default safe contribution path
  - when to write a plan
  - when to run full proof bundle

**Exit criteria**

- 从 root README 一跳能到 `CONTRIBUTING.md`
- 从 `CONTRIBUTING.md` 一跳能到 zone 规则正文

### Batch 2: Convert Rules into Contributor Workflow

**Objective**

把已有规则从“治理说明”变成“开发者执行流程”。

**Files**

- Modify: `docs/developer-change-governance.md`
- Create: `references/contributor-zone-decision-table.md`
- Create: `references/change-proof-matrix.md`

**Actions**

- 从正文中抽出一张 zone decision table
- 建立 task-type -> required proof matrix
- 给每类变更指定最低验证集合

**Exit criteria**

- 普通贡献者不需要通读所有 docs，也能判定自己属于哪个变更类
- high-risk change 的 proof 要求不再隐含

### Batch 3: Add Template and Review Guardrails

**Objective**

把开发者入口和 GitHub 提交流程绑定，减少“看完规则但提交时忘了”的情况。

**Files**

- Create or modify: `.github/PULL_REQUEST_TEMPLATE.md`
- Create or modify: `.github/ISSUE_TEMPLATE/config.yml`
- Optional create:
  - `.github/ISSUE_TEMPLATE/docs-change.yml`
  - `.github/ISSUE_TEMPLATE/runtime-change.yml`
  - `.github/ISSUE_TEMPLATE/governance-change.yml`

**Actions**

- PR 模板要求提交者声明：
  - touched zones
  - 是否涉及 frozen / guarded area
  - 跑了哪些 gates
  - 是否附带 plan
- 对高风险 change class 提醒 stop-ship 条件

**Exit criteria**

- 开发者入口不再只是阅读材料，而是进入 PR 时仍有提醒

### Batch 4: Add Developer Entry Verification

**Objective**

建立“开发者入口本身”的验证，而不是只验证代码。

**Files**

- Create: `scripts/verify/vibe-developer-entry-gate.ps1`
- Create: `references/developer-entry-contract.md`
- Modify: `scripts/verify/README.md`

**Actions**

- 验证以下条件：
  - `CONTRIBUTING.md` 存在
  - root README 链接到 `CONTRIBUTING.md`
  - `CONTRIBUTING.md` 链接到 `docs/developer-change-governance.md`
  - zone / proof / plan 三类入口都存在

**Exit criteria**

- developer entry 可以被 gate 自动检查，而不是靠人工记忆

### Batch 5: Canary Contributor Journey

**Objective**

从“新开发者第一次进入仓库”的视角，证明入口真的可用。

**Files**

- Create: `docs/status/developer-entry-canary-report.md`

**Journey design**

模拟一个新开发者完成以下路径：

1. 从 `README.md` 找到贡献入口；
2. 判断自己是 docs-only change；
3. 判断自己不能直接修改 `scripts/router/**`；
4. 知道需要在哪些目录开始；
5. 知道什么情况下必须先写 plan；
6. 知道如何找到 required gates。

**Exit criteria**

- canary journey 无断链
- 没有“必须靠维护者解释才能继续”的关键节点

### Batch 6: Prove Non-Regression and Release-Safe Developer UX

**Objective**

证明开发者入口增强没有导致运行面退化，也没有制造新的治理冲突。

**Proof bundle**

- `scripts/verify/vibe-developer-entry-gate.ps1`
- `scripts/verify/vibe-repo-cleanliness-gate.ps1`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-router-contract-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

**Exit criteria**

- developer entry gate PASS
- runtime gates 不弱于治理前 baseline
- 没有因为新增开发者入口文档/模板影响现有运行合同

## Test Matrix

### A. Navigation and Discoverability

- root README -> `CONTRIBUTING.md`
- `CONTRIBUTING.md` -> `docs/developer-change-governance.md`
- `CONTRIBUTING.md` -> plan / proof / zone docs
- `git diff --check`

证明：

- 开发者入口可达；
- 入口没有断链或结构污染。

### B. Zone Clarity

- human spot-check on `CONTRIBUTING.md`
- human spot-check on `docs/developer-change-governance.md`
- canary contributor journey

证明：

- 开发者可以区分：
  - 允许直接开发的区域
  - 受控区域
  - 冻结区域

### C. Process Enforceability

- PR template coverage check
- developer entry gate

证明：

- 规则不仅可读，而且在提交流程中可见。

### D. Functional Non-Regression

- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`

证明：

- 开发者入口治理没有改变系统行为。

## Proof Standard

与收敛计划一致，所有“入口已可用”或“不会导致功能退化”的结论都必须以：

1. **Command**
2. **Output**
3. **Claim**

形式记录。

例：

- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-developer-entry-gate.ps1 -WriteArtifacts`
- Output: `gate_result = PASS`, `contributing_exists = true`, `root_link_present = true`
- Claim: “开发者入口主链路已存在且可验证”

## Stability Contract

本计划把“开发者入口稳定”定义成三层：

### E1: Documented

- 规则写出来了，但还没有模板和 gate

### E2: Enforced

- 有 `CONTRIBUTING.md`
- 有 PR template
- 有 developer entry gate

### E3: Release-Safe Contributor UX

- E2 成立
- canary contributor journey 通过
- runtime proof bundle 无回退

只有达到 E3，才允许宣称“开发者入口已经正确落地，且不会诱导功能退化”。

## Acceptance Criteria

1. 存在正式的 `CONTRIBUTING.md`。
2. root README 明确暴露开发者入口。
3. `CONTRIBUTING.md` 清楚描述默认安全工作面与高风险冻结区。
4. 至少存在一张 zone decision table 和一张 proof matrix。
5. PR template 要求声明 touched zones 与验证结果。
6. developer entry gate PASS。
7. canary contributor journey 通过。
8. runtime / install / router 关键 gate 结果不弱于基线。

## Explicit Non-Goals

- 不在本计划中直接重写 router / install / protocol。
- 不把所有治理文档重新洗牌。
- 不把“欢迎贡献”误写成“所有区域都允许自由编辑”。
- 不为了降低贡献摩擦而移除高风险变更的 proof 要求。

## Recommended Immediate Sequence

1. 先冻结当前开发者入口基线。
2. 创建 `CONTRIBUTING.md` 并接到 root README。
3. 把 zone / proof 规则压缩成贡献者视角的入口文档。
4. 接入 PR template 和 developer entry gate。
5. 做一次 canary contributor journey。
6. 最后和 runtime proof bundle 一起出 closure report。

## Success Signal

当这份计划完成后，这个仓库的开发者入口应该达到：

- 新开发者不会一进来就碰高风险控制面；
- 普通贡献者知道自己优先在哪些目录工作；
- 维护者不需要反复口头解释“这个地方别乱改”；
- 开发规则不是抽象原则，而是入口、模板、gate、journey proof 一体化的工程化系统；
- 这套入口增强不会对现有功能造成退化，且能被重复验证。
