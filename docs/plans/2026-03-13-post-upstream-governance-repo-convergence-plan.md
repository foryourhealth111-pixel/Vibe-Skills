# Post-Upstream-Governance Repo Convergence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在上游治理完成后，把 `vco-skills-codex` 进一步收敛为一个“结构、合规、证据、入口、镜像、输出边界”都足够干净的仓库，并用可重复的验证链严格证明整个收敛过程没有造成功能退化、没有破坏现有打包/安装/路由/运行稳定性。

**Architecture:** 本计划采用 `evidence-first + canonical-first + no-runtime-regression + staged-closure` 架构。它以上游治理计划为前置约束，不再讨论“是否保留上游代码”，而是专注回答“治理之后如何把仓库真正收干净”。执行顺序是：先修信息面和证据面，再修输出物镜像一致性，再修 registry/disclosure 悬空项，最后用 proof bundle 和专项门禁证明 repo 已达到 `clean enough` 与 `release-safe`。

**Tech Stack:** Git, PowerShell governance/verify gates, Markdown governance docs, JSON policy/config manifests, fixture mirror governance, bundled mirror sync pipeline, runtime freshness and release coherence gates.

---

## Positioning

- **This plan is downstream of:** [2026-03-13-distribution-governance-plan.md](2026-03-13-distribution-governance-plan.md)
- **This plan does not replace:** [2026-03-08-repo-full-cleanup-master-plan.md](2026-03-08-repo-full-cleanup-master-plan.md)
- **This plan does:** 把“清扫总纲”和“分发治理总纲”连接起来，变成一份更近身、更可落地、更强调验证闭环的收敛计划。

换句话说：

- `distribution-governance-plan` 解决的是 upstream/source/distribution/provenance 的真相系统；
- `repo-full-cleanup-master-plan` 解决的是仓库长期整洁的 umbrella 方向；
- **本计划解决的是：如何在这两者约束下，把仓库推到“足够干净且可证明稳定”的完成态。**

## Current Verified Baseline

### 1. Local hygiene 通过，但仓库未 zero-dirty

根据 `vibe-repo-cleanliness-gate`：

- `gate_result = PASS`
- `local_noise_visible = 0`
- `runtime_generated_visible = 0`
- `other_dirty_visible = 0`
- `managed_workset_visible = 2`
- `repo_zero_dirty = false`

这说明当前仓库达到的是“本地噪声干净”，不是“仓库 fully clean”。

当前剩余 managed workset 就是：

- `docs/plans/README.md`
- `docs/plans/2026-03-13-distribution-governance-plan.md`

也就是说，当前 repo 的 dirty state 是受控的，但还没有真正归零。

### 2. Output artifact boundary 当前失败

`vibe-output-artifact-boundary-gate` 当前 `FAIL`，直接阻止“仓库已收敛”这一结论。失败原因非常集中，不是全线崩，而是 `fixture_hash_mismatches = 2`：

- `outputs/external-corpus/external-corpus-gate.md`
  vs `references/fixtures/external-corpus/external-corpus-gate.md`
- `outputs/external-corpus/vco-suggestions.md`
  vs `references/fixtures/external-corpus/vco-suggestions.md`

这说明：

- 输出物治理体系基本成立；
- mirrored fixture contract 已经存在；
- 但仍有 2 个 Markdown fixture 没和 tracked output 源保持一致。

仓库现在不是“乱”，而是卡在**最后一公里的 fixture mirror consistency**。

### 3. Main docs navigation 已出现结构性污染

`docs/README.md` 的 Start Here 区块当前存在串行污染，出现了字面量 `` `n- ``，把多个入口链接挤到了同一行。这是典型的“不是功能 bug，但会破坏仓库可读性和导航可信度”的脏点。

### 4. Upstream governance 仍有未闭环条目

即使只看治理，不看功能，也还有几个未闭合点：

- `config/upstream-corpus-manifest.json` 仍存在 `HEAD_FROM_UPSTREAM_LOCK`
- `THIRD_PARTY_LICENSES.md` 仍有至少 3 个对外披露但未 canonicalized 的来源
- 统一 `ORIGIN.md` 机制尚未落地

因此，仓库现在还不能声称：

- “上游真相完全闭合”
- “分发治理完全可执行”
- “release-ready clean”

## Cleanliness Levels

### Level A: Local Hygiene Clean

标准：

- `repo-cleanliness-gate` PASS
- 没有 local noise、runtime generated、uncategorized dirty

当前状态：**已达到**

### Level B: Clean Enough for Safe Iteration

标准：

- Level A 满足
- `git status --short` 只剩受控 workset
- `docs/README.md`、`docs/plans/README.md`、`references/index.md` 入口可信
- `output-artifact-boundary-gate` PASS
- 现有 mirror/package/runtime 关键门禁无回退

当前状态：**未达到**

### Level C: Release-Safe Converged

标准：

- Level B 满足
- proof bundle 全绿
- output/fixtures/mirror/runtime/registry/disclosure 全部闭合
- repo zero-dirty 或只剩明确计划中的单批次 workset
- upstream/distribution/provenance contracts 可对外说明

当前状态：**未达到**

## Design Principles

1. **Do not clean by hiding reality.**
   不允许通过扩大 `.gitignore`、关闭门禁、放宽 policy 来制造“看起来干净”。

2. **Fix contract mismatches before moving files.**
   先修 fixture、registry、导航、边界，再做任何目录重构。

3. **No runtime mutation in convergence batches 0-3.**
   前 4 个批次只处理文档、fixtures、registry、合规和索引，不动 router/install/sync/runtime 逻辑。

4. **Every convergence claim must be proven.**
   每一个“收敛完成”的声明都必须绑定门禁结果与 artifacts。

5. **A clean repo must also be readable.**
   “足够干净”不仅是 git zero-dirty，也包括入口文档、家族 README、plan index、reference index 能正常工作。

6. **A clean repo must also be governable.**
   若 registry、disclosure、provenance 未闭环，即使 `git status` 为空，也不能算治理完成。

7. **A clean repo must also be safely editable.**
   如果开发者不知道哪些区域禁止随意开发、哪些区域只能 canonical-first、哪些区域才是首选扩展面，那么仓库即使暂时干净，也会很快再次脏化。

## Convergence Scope

本计划只治理 canonical repo 内的以下面：

- `docs/`
- `references/`
- `config/`
- `scripts/verify/`
- `scripts/governance/`
- `third_party/`
- `outputs/**` 与 `references/fixtures/**` 的边界关系
- `docs/plans/` 索引与阶段计划入口
- 开发者 change-control zone 定义与公开入口

本计划明确**不**在第一轮收敛中处理：

- 新增 feature
- 新增 upstream retention 真实落库
- 路由策略重写
- runtime owner 切换
- 大规模 mirror 目录迁移

## Execution Plan

### Batch 0: Freeze the Current Evidence Line

**Objective**

把当前仓库状态固化为“收敛前基线”，避免后续清理把问题来源洗掉。

**Files**

- Create: `docs/status/repo-convergence-baseline-2026-03-13.md`
- Reference:
  - `outputs/verify/vibe-repo-cleanliness-gate.json`
  - `outputs/verify/vibe-output-artifact-boundary-gate.json`
  - `docs/README.md`
  - `config/upstream-corpus-manifest.json`
  - `THIRD_PARTY_LICENSES.md`

**Actions**

- 记录当前 PASS/FAIL gate snapshot
- 记录 docs navigation 污染点
- 记录 output mirror mismatch 精确列表
- 记录 upstream governance 未闭合项

**Why first**

如果不先冻结证据，后面的清理会让“为什么要改”失去锚点。

**Proof**

- 生成 baseline 文档
- 附上 gate artifact 路径和失败明细摘要

### Batch 1: Repair Information Architecture Surface

**Objective**

先修入口层，确保仓库“怎么看”是可信的。

**Files**

- Modify: `docs/README.md`
- Create: `docs/developer-change-governance.md`
- Modify: `docs/plans/README.md`
- Modify: `references/index.md`
- Modify: `scripts/verify/README.md`
- Optional: `scripts/governance/README.md`

**Actions**

- 修复 `docs/README.md` 中的串行污染
- 新增开发者边界治理文档，明确 frozen / guarded / preferred contribution zones
- 检查 Start Here 区块是否仍有单行挤压、断裂链接或无效说明
- 确保新的 plan 文档都能在 `docs/plans/README.md` 中被找到
- 检查 references 和 verify README 是否仍能形成 1-hop discoverability

**Exit criteria**

- 入口文档无结构性污染
- 开发者可以从主入口直接看到“哪些路径禁止随意开发”
- Start Here 区块可读、可点击、无拼接错误
- 根据信息架构，AI 与人都能快速定位仓库

**Proof**

- `git diff --check`
- 导航 spot-check 结果文档化

### Batch 2: Close Output/Fixture Mirror Drift

**Objective**

把当前唯一已知的 output artifact boundary failure 收掉。

**Files**

- Modify: `references/fixtures/external-corpus/external-corpus-gate.md`
- Modify: `references/fixtures/external-corpus/vco-suggestions.md`
- Or modify their tracked `outputs/external-corpus/*.md` sources
- Review: `config/output-artifact-boundary-policy.json` if required by actual mismatch cause

**Actions**

- 明确 source-of-truth 是 `outputs/...` 还是 `references/fixtures/...`
- 不允许“为了过 gate 而随便改任意一边”；必须保留 mirrored contract 语义
- 如果 mismatch 只是 fixture 未同步，做最小同步
- 如果 mismatch 暴露出 policy/contract 混乱，先补 contract 再同步

**Exit criteria**

- `fixture_hash_mismatches = 0`
- `vibe-output-artifact-boundary-gate` PASS

**Proof**

- 重新运行 `vibe-output-artifact-boundary-gate.ps1`
- 保存 PASS artifact
- 在 closure report 中记录“为什么两份 md 曾经漂移”

### Batch 3: Close Upstream Governance Residual Gaps

**Objective**

把上游治理尾巴收掉，否则仓库仍然不算治理上干净。

**Files**

- Modify: `config/upstream-corpus-manifest.json`
- Modify: `config/upstream-lock.json`
- Modify: `config/upstream-source-aliases.json`
- Modify: `THIRD_PARTY_LICENSES.md`
- Modify: `NOTICE`
- Create or modify: `docs/governance/upstream-distribution-governance.md`

**Actions**

- 替换 `HEAD_FROM_UPSTREAM_LOCK` 占位符为真实对齐值或正式的 machine-readable resolution 机制
- 处理 `SynkraAI/aios-core`
- 处理 `x1xhlol/system-prompts-and-models-of-ai-tools`
- 处理 `muratcankoylan/Agent-Skills-for-Context-Engineering`
- 明确这些来源是 canonicalized、external-only、reference-only 还是 exception-disclosed

**Exit criteria**

- registry/disclosure 中不存在悬空来源
- `THIRD_PARTY_LICENSES.md` 不再超出 canonical truth surface
- `upstream-corpus-manifest` 不再依赖临时占位字符串

**Proof**

- `vibe-upstream-corpus-manifest-gate.ps1`
- 必要时新增 disclosure parity gate 并跑通

### Batch 4: Introduce Provenance Skeleton Without Changing Runtime

**Objective**

先把 `ORIGIN.md` 机制和模板落地，为后续 repo-local retention 做准备，但不实际迁入更多上游代码。

**Files**

- Create: `templates/ORIGIN.md.tmpl`
- Create: `vendor/README.md`
- Create: `scripts/governance/new-origin-record.ps1`
- Modify: `third_party/README.md`
- Modify: `docs/repo-cleanliness-governance.md`

**Actions**

- 明确 `third_party/` 继续只是 compliance-only
- 引入未来 `vendor/upstreams/`、`vendor/mirrors/` 的目录契约
- 不添加任何真实 vendored upstream，只落脚手架

**Exit criteria**

- provenance 机制可执行
- 目录边界不再模糊
- 没有对现有 runtime/package/install 造成影响

**Proof**

- cleanliness gates 继续 PASS
- 新增 provenance skeleton 无边界越界

### Batch 5: Converge to Clean Enough

**Objective**

把仓库推进到 `clean enough for safe iteration`。

**Files**

- All files modified in batches 1-4
- Create: `docs/status/repo-convergence-closure-report.md`

**Actions**

- 确认工作树只剩本批次收口文档与相关最小修补
- 把 plan、baseline、closure report、gate artifact 串起来
- 明确哪些事项已完成，哪些是 deferred but governed

**Exit criteria**

- `repo-cleanliness-gate` PASS
- `output-artifact-boundary-gate` PASS
- docs navigation clean
- upstream residual gaps closed
- worktree 可以归零或只剩待提交的单批 closure workset

**Proof**

- closure report 引用所有关键 gate 结果
- 列出 exact command, exact output, exact claim

### Batch 6: Prove Release-Safe Stability

**Objective**

不是只证明“看起来干净”，而是证明“干净后的系统没有功能退化”。

**Proof bundle**

- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-router-contract-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-mirror-edit-hygiene-gate.ps1`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`
- `scripts/verify/vibe-repo-cleanliness-gate.ps1`
- `scripts/verify/vibe-upstream-corpus-manifest-gate.ps1`

**Actions**

- 收敛完成后全量复跑
- 比对基线与收敛后结果
- 对失败项做 stop-ship，不允许“带红过线”

**Exit criteria**

- 关键 gates 全绿
- 无新 failure
- 无比基线更差的结果

**Proof**

- 产出 closure report
- 产出 gate summary
- 明确记录 stability verdict: `stable`, `stable_with_deferred_nonruntime_backlog`, or `not_stable`

## Test Matrix

### A. Cleanliness and Boundary

- `vibe-repo-cleanliness-gate.ps1`
- `vibe-output-artifact-boundary-gate.ps1`

证明：

- 仓库没有隐藏本地噪声
- 输出物和 fixture 镜像关系已闭合

### B. Navigation and Information Architecture

- human spot-check on `docs/README.md`
- human spot-check on `docs/plans/README.md`
- human spot-check on `references/index.md`
- `git diff --check`

证明：

- 仓库入口层不再污染
- 没有因 Markdown 结构错误制造新的认知脏点

### C. Upstream Governance Closure

- `vibe-upstream-corpus-manifest-gate.ps1`
- optional new disclosure parity gate

证明：

- upstream 真相没有占位符和公开悬空项
- public disclosure 与 canonical registry 对齐

### D. Functional Non-Regression

- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`

证明：

- 文档、fixture、registry、provenance 收敛没有影响现有行为
- packaging/install/runtime freshness 仍然成立

## Proof Standard

本计划要求的“稳定性证明”不是口头证明，而是以下格式：

1. **Command**
   记录运行命令
2. **Output**
   记录 PASS/FAIL 结果和关键字段
3. **Claim**
   只基于输出作有限结论

例子：

- Command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-repo-cleanliness-gate.ps1 -WriteArtifacts`
- Output: `gate_result = PASS`, `repo_zero_dirty = false`, `managed_workset_visible = 2`
- Claim: “本地卫生已收口，但仓库尚未 fully clean”

只有当每个关键 claim 都能这样落地，才允许宣称“收敛完成”。

## Stability Contract

本计划定义三层稳定性：

### Stability S1: Non-runtime-safe

- 只要 routing/package/install/runtime 关键门禁有任何回退，就停在 S1，不允许继续宣称 clean enough。

### Stability S2: Clean-enough stable

满足以下条件才算 S2：

- cleanliness PASS
- output boundary PASS
- docs navigation clean
- upstream residual gaps closed
- runtime proof bundle 无退化

### Stability S3: Release-safe stable

满足以下条件才算 S3：

- S2 成立
- repo zero-dirty 或仅剩单批 closure workset
- closure report 完整
- 所有 deferred items 都被显式治理，不再是隐性脏项

## Acceptance Criteria

1. `docs/README.md` 不再有结构性拼接污染。
2. `vibe-output-artifact-boundary-gate` 由 FAIL 变 PASS。
3. `vibe-repo-cleanliness-gate` 继续 PASS，且不会因为清理动作引入 local noise/runtime noise。
4. upstream manifest/disclosure 不再存在 `HEAD_FROM_UPSTREAM_LOCK` 和公开悬空来源。
5. `ORIGIN.md` skeleton 与 vendor boundary 机制准备就绪，但未影响 runtime。
6. proof bundle 结果不弱于收敛前基线。
7. 有 closure report 明确记录：做了什么、验证了什么、为什么可以宣称稳定。
8. 已存在一份开发者可直接阅读的边界治理文档，明确仓库中禁止随意开发区域、受控开发区域与首选扩展区域。

## Explicit Non-Goals

- 不在本计划内直接引入大规模 repo-local upstream code。
- 不做 router 重构。
- 不做 install flow 改写。
- 不做 mirror topology 重写。
- 不靠“临时关闭 gate”达成收敛。

## Recommended Immediate Sequence

1. 先写 baseline 文档，把现有脏点和失败门禁冻结。
2. 立即修 `docs/README.md` 的入口污染。
3. 再修 2 个 external-corpus Markdown fixture mismatch。
4. 收口 upstream residual gaps。
5. 最后统一跑 proof bundle，并出 closure report。

## Success Signal

当这份计划被执行完成后，`vco-skills-codex` 应该达到的是：

- 不是“看起来干净”，而是“每个脏点都被解释、被修复、被验证”；
- 不是“临时绿了”，而是“关键门禁能重复跑、结果稳定、不退化”；
- 不是“只有作者知道怎么维护”，而是“任何新 AI/维护者都能通过入口文档与 gate 链复现同样判断”。
