# VCO Repo Non-Regression Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在严格保证核心功能、发布链路、安装链路、验证链路和可发现性不退化的前提下，把 `vibe` 仓库从“高噪声、高镜像压力、高文档负担、高路径耦合”的状态，收口为一个目录整洁、真源明确、日志规范、依赖清晰、长期维护成本显著下降的仓库。

**Architecture:** 本方案采用 `behavior-first cleanup` 路线：先冻结扩张、建立受保护能力基线、识别路径耦合、补兼容层和迁移层、对每一类资产做“保留 / 迁移 / 归档 / 生成 / 删除”判定，再以 regression proof 驱动清理。任何目录删除、镜像收缩、outputs 严格化、第三方外移，都必须先完成替代路径与验证证明，最后才允许 prune。

**Tech Stack:** Git, PowerShell governance and verify scripts, Markdown information architecture, JSON policies and manifests, canonical-first sync pipeline, fixture migration, archive/index conventions, release/install/runtime coherence gates.

---

## Mission

这次整改不是“把文件删掉”，而是做一件更难但更正确的事：

1. **让仓库更简洁**：长期存在的镜像、日志、时间绑定文档、第三方重资产显著减少。
2. **让仓库更清晰**：任何人或 AI 都能快速回答“哪里是真源、哪里是派生物、哪里是运行态、哪里是历史档案、哪里是仍受保护的兼容层”。
3. **让仓库更干净**：`git status` 不再长期被 scratch、runtime outputs、镜像漂移、历史报告污染。
4. **让调用关系更清楚**：脚本、配置、镜像、fixtures、release/install/runtime 之间的关系由契约定义，而不是靠目录偶然存在。
5. **让功能不退化**：用户可见行为、安装行为、发布行为、验证行为都必须保持；允许变化的是实现形态和维护表面，不允许变化的是能力边界和结果语义。

## Non-Negotiable Success Criteria

本计划把“不能功能退化”提升为第一性约束。整改完成时必须同时满足：

1. **Routing 不退化**：pack routing、legacy fallback、`confirm_required`、explicit skill override、关键 smoke matrix 语义保持。
2. **Sync / Packaging 不退化**：canonical -> bundled 的唯一真源关系保持；release mirror 继续可生成、可验证、可解释。
3. **Install / Runtime 不退化**：`install.ps1`, `install.sh`, `check.ps1`, `check.sh`, installed runtime freshness、release-install-runtime coherence 继续成立。
4. **Verification 不退化**：当前有长期价值的 baseline 不能因 outputs 收口而丢失；必须进入 fixture / ledger / canonical doc 再允许删除旧路径。
5. **Discoverability 不退化**：active docs 虽然减少，但主入口必须更强，不得出现“信息更少但更难找”的假清洁。
6. **Rollback 能力不退化**：任何大规模 move/delete/prune 必须存在 manifest、preview、rollback path，而不是靠散落 backup。

## Protected Capability Matrix

### Tier P0: Must Remain Behaviorally Equivalent

- `scripts/router/resolve-pack-route.ps1`
- `config/pack-manifest.json`
- `config/router-thresholds.json`
- `config/skill-routing-rules.json`
- `confirm_required` white-box flow
- `sync-bundled-vibe.ps1`
- `install.ps1`, `install.sh`
- `check.ps1`, `check.sh`
- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`

### Tier P1: May Change Shape, Must Keep Outcome

- `nested_bundled` compatibility path
- tracked `outputs/**` historical carry-over
- `docs/plans/`, `docs/releases/` historical materials
- `references/**` family layout
- `scripts/**` and `config/**` index / taxonomy surfaces
- `third_party/**` local storage form

### Tier P2: May Be Removed After Proof

- mirror-only redundant copies
- duplicate historical reports
- stale dated plans not serving current execution
- runtime-generated outputs that have no canonical baseline role
- non-essential file-level backups

## Change Classification Rules

### Class A: Safe Immediate Cleanup

满足以下条件时，可直接清理：

- 仅属于 local operator state / scratch；
- 不被任何 manifest / doc / gate / script 引用；
- 不承担 runtime、fixture、release、install、audit 角色。

典型对象：

- `.serena/`
- `.tmp/`
- `task_plan.md`
- `findings.md`
- `progress.md`

### Class B: Migrate Then Prune

满足以下任一条件时，必须先迁移再删除：

- 仍出现在 policy / governance / manifest / gate / release SOP 中；
- 有已知脚本硬编码引用；
- 承担 baseline、fixture、evidence、receipt、compatibility 角色。

典型对象：

- `nested_bundled`
- tracked `outputs/**`
- `third_party/system-prompts-mirror`
- `docs/releases/*`
- `docs/plans/*`

### Class C: Contract Rewrite Required

满足以下条件时，必须先改契约、再做迁移：

- `config/version-governance.json`
- `docs/version-packaging-governance.md`
- `docs/repo-cleanliness-governance.md`
- `docs/governance/output-artifact-boundary-governance.md`
- topology-aware gates
- release/install/runtime contracts

## Recommended Strategy

采用 **Balanced Simplification, Non-Regression First**。

这不是保守修补，也不是激进拆仓，而是：

- 保留核心能力；
- 显著压缩长期治理对象数量；
- 任何结构删减都必须先做 compatibility migration；
- 用 proof 驱动 prune，而不是用主观判断驱动 prune。

## Canonical Doc Spine

整改过程中，以下文档被视为 topic-level canonical contract：

- repo cleanliness: `docs/repo-cleanliness-governance.md`
- version / packaging / mirror topology: `docs/version-packaging-governance.md`
- outputs boundary: `docs/governance/output-artifact-boundary-governance.md`
- docs IA: `docs/docs-information-architecture.md`
- active cleanup execution plan: `docs/plans/2026-03-11-vco-repo-simplification-remediation-plan.md`

以下材料视为 subordinate documents，不再作为并列规范源：

- `references/mirror-topology.md`
- `references/fixtures/README.md`
- `docs/releases/README.md`
- 历史 dated plans / reports / closure docs

## End-State Topology

### Canonical Source of Truth

- 根文件：`README.md`, `SKILL.md`, `check.ps1`, `check.sh`, `install.ps1`, `install.sh`, `.gitignore`, `.gitattributes`
- 核心治理目录：
  - `config/`
  - `scripts/`
  - `protocols/`
  - `docs/`
  - `references/`

### Distribution Layer

- 保留：`bundled/skills/vibe/`
- 角色：唯一 repo 内长期受控镜像
- 规则：只能 `canonical -> bundled`

### Compatibility Layer

- `nested_bundled` 不再作为长期常驻 mirror workset
- 如果仍有 install / release / compatibility 消费者，改为：
  - install-time generated
  - release-time generated
  - preview artifact
  - optional compatibility package

### Runtime Layer

- `outputs/`
- `.serena/`
- `.tmp/`
- `task_plan.md`, `findings.md`, `progress.md`

规则：

- 默认 untracked
- 可再生
- 不承担长期 canonical role

### Archive Layer

- `docs/archive/`
- `references/archive/`（如确有必要）

### Stable Current-State Layer

- `docs/README.md`
- `docs/status/current-state.md`
- `docs/status/roadmap.md`
- `docs/plans/README.md`
- `docs/releases/README.md`
- `references/index.md`
- `config/index.md`
- `scripts/README.md`

## Log, Evidence, and Backup Policy

### Long-Term Kept Classes

1. **Machine ledger**
   - 例如 `references/release-ledger.jsonl`
2. **Human summary**
   - 例如 `docs/status/current-state.md`
3. **Governed baseline fixtures**
   - 例如 `references/fixtures/**`

### Runtime-Only Classes

- `outputs/verify/**`
- `outputs/dashboard/**`
- `outputs/learn/**`
- `outputs/retro/**`
- `outputs/governance/**`

### Explicitly Prohibited Patterns

- 同一事件长期保留多份 `json + md + closure report + dated summary`
- 把 `outputs/**` 当作长期 canonical truth-source
- 在 repo 中散落 `backup/`, `old/`, `copy/`, `final_v2/`, `tmp_fix/`

### Backup Policy

- 默认不做文件级备份
- 优先使用：
  - git history
  - git branch
  - git tag
  - preview receipt
  - migration manifest
- 只有在不可逆 rewrite / move / prune 前，才允许一次性结构化 backup
- 所有 backup 必须具备：
  - manifest
  - retention deadline
  - owner
  - explicit delete step

## Alpha to Omega Program

### Phase α: Program Charter and Freeze

**Objective:** 把整改工程从“继续扩张治理面”切换为“先保功能，再清理”。

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Create: `docs/status/current-state.md`
- Create: `docs/status/roadmap.md`

**Actions:**

1. 宣告 cleanup-first freeze。
2. 暂停新增 overlay、wave、bulk docs、bulk vendoring。
3. 在入口文档中明确：当前优先级是 simplification with zero functional regression。

**Verification:**

- 入口文档能够明确说明当前仓库正在执行 non-regression cleanup program。

**Rollback:**

- 仅文档改动，可直接 git revert。

### Phase β: Protected Capability Baseline

**Objective:** 列出所有必须保持不变的行为、脚本、命令、门禁和用户路径。

**Files:**
- Create: `docs/status/protected-capability-baseline.md`
- Modify: `scripts/verify/README.md`
- Modify: `scripts/governance/README.md`

**Actions:**

1. 为 routing / sync / install / runtime / release / outputs / research 外部语料分别列 protected paths。
2. 标注每项的 consumer、proof command、rollback anchor。
3. 区分：
   - exact behavior preserve
   - preserve via replacement
   - deletable after proof

**Verification:**

- 每个潜在清理对象都能追溯到某个 capability tier。

**Rollback:**

- baseline 文档可回滚，不影响功能。

### Phase γ: Path Dependency Census

**Objective:** 找出所有对 `nested_bundled`、`outputs/**`、`third_party/**`、dated docs 的硬依赖。

**Files:**
- Create: `docs/status/path-dependency-census.md`
- Modify: `scripts/governance/export-repo-cleanliness-inventory.ps1`

**Actions:**

1. 枚举 hardcoded path 依赖。
2. 标出 path kind：
   - mirror compatibility
   - runtime evidence
   - baseline fixture
   - external source corpus
   - human navigation only
3. 给每个依赖指定迁移方案。

**Verification:**

- 不再存在“准备删除时才发现有脚本依赖”的盲区。

### Phase δ: Regression Harness Definition

**Objective:** 用少数高价值命令定义功能不退化的 proof bundle。

**Files:**
- Create: `docs/status/non-regression-proof-bundle.md`
- Modify: `scripts/verify/gate-family-index.md`

**Proof bundle must include:**

- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-mirror-edit-hygiene-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`
- `vibe-output-artifact-boundary-gate.ps1`

**Verification:**

- 所有后续 prune 都必须引用这个 bundle 中至少一个 proof。

### Phase ε: Cleanliness Re-Baseline by Plane

**Objective:** 重新建立“脏项按 plane 分类”的基线，而不是只盯单一 dirty count。

**Files:**
- Modify: `config/repo-cleanliness-policy.json`
- Modify: `scripts/governance/export-repo-cleanliness-inventory.ps1`
- Modify: `scripts/verify/vibe-repo-cleanliness-gate.ps1`
- Create: `docs/status/repo-cleanliness-baseline.md`

**Actions:**

1. 区分 local noise、runtime outputs、governed workset、mirror pressure、archive candidates。
2. 给每类 dirty path 指定 owner 和处理方式。
3. 把“本地卫生已收口”和“canonical backlog 未收口”区分报告。

**Verification:**

- cleanliness gate 的 PASS/FAIL 语义更精确，不再把真实 backlog 误判为本地脏。

### Phase ζ: Execution Context Hardening

**Objective:** 防止清理期间因错误 repo root / mirror root 执行脚本而产生假阳性。

**Files:**
- Modify: `scripts/common/vibe-governance-helpers.ps1`
- Modify: topology-aware gates

**Actions:**

1. 明确 outer git root 约束。
2. 防止从 mirror root 运行 topology scripts。
3. 对 preview / generated compatibility path 做上下文识别。

**Verification:**

- 所有 topology-aware gates 在错误上下文中 fail closed。

### Phase η: Nested Compatibility Migration Design

**Objective:** 把 `nested_bundled` 从“长期 tracked mirror”改造成“兼容层”。

**Files:**
- Modify: `config/version-governance.json`
- Modify: `docs/version-packaging-governance.md`
- Modify: `references/mirror-topology.md`
- Modify: `scripts/governance/sync-bundled-vibe.ps1`

**Actions:**

1. 从契约层引入 compatibility mode 概念。
2. 把 `require_nested_bundled_root = true` 改为可迁移状态：
   - transitional required
   - generated-if-needed
   - disabled-after-proof
3. 明确 nested 不再是 repo 常驻真源对象。

**Verification:**

- 契约允许 nested 被生成而非长期常驻。

### Phase θ: Nested Compatibility Implementation

**Objective:** 在不降 install/runtime/release 功能的前提下，把 nested 变成 generated artifact。

**Files:**
- Modify: `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- Modify: `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`
- Modify: `install.ps1`
- Modify: `install.sh`
- Modify: `check.ps1`
- Modify: `check.sh`

**Actions:**

1. 让 installed runtime gate 支持“nested generated or not required”。
2. 如 legacy consumer 仍需要 nested layout，则由 install/release 生成。
3. repo 本体不再要求长期保留 nested root。

**Verification:**

- install/check/runtime freshness 语义与当前一致。
- release/install/runtime coherence 保持。

**Rollback:**

- 若任一关键 gate 失败，可临时保留 nested tracked root，直到 compatibility path 通过 proof。

### Phase ι: Outputs Baseline Migration Completion

**Objective:** 把所有仍有长期价值的 tracked outputs 迁移到 fixtures / ledgers。

**Files:**
- Modify: `config/outputs-boundary-policy.json`
- Modify: `references/fixtures/migration-map.json`
- Modify: `references/fixtures/README.md`
- Modify: `docs/governance/output-artifact-boundary-governance.md`

**Actions:**

1. 逐条核对 tracked outputs 是否具备长期回归价值。
2. 有价值的迁入 `references/fixtures/**`。
3. 仅属于运行证据的移出 tracked set。
4. 删除不再需要的双副本 `json + md` 组合。

**Verification:**

- fixture hash 与旧 baseline 对齐。
- boundary gate 通过。

### Phase κ: Outputs Strict Mode

**Objective:** 从 stage2 mirrored 升级到 strict mode。

**Files:**
- Modify: `config/outputs-boundary-policy.json`
- Modify: `docs/governance/output-artifact-boundary-governance.md`
- Modify: `scripts/verify/vibe-output-artifact-boundary-gate.ps1`

**Actions:**

1. 把 `strict_requires_zero_tracked_outputs` 切到 `true`。
2. 确保 `git ls-files outputs` 归零。
3. 让 outputs 彻底回归 runtime-only。

**Verification:**

- strict mode 打绿。

### Phase λ: Docs Spine Normalization

**Objective:** 减少 docs 规范源数量，强化入口骨架。

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/docs-information-architecture.md`
- Modify: `docs/plans/README.md`
- Modify: `docs/releases/README.md`

**Actions:**

1. 让 `docs/README.md` 只承担 spine 入口，不再复制大列表。
2. 修复主索引中的格式问题和过长聚合段。
3. 明确 topic canonical docs 与 subordinate docs。

**Verification:**

- 主入口可信、短、稳定。
- 不再需要从多个索引猜哪个文档才是现行规范。

### Phase μ: Archive Migration

**Objective:** 把历史计划、closure report、dated release notes 从 active 面剥离。

**Files:**
- Create: `docs/archive/README.md`
- Move: historical plans / reports / old release notes -> `docs/archive/`
- Modify: `docs/plans/README.md`
- Modify: `docs/releases/README.md`

**Actions:**

1. 只保留 current active plan、current state、roadmap、latest release summary。
2. 历史材料移入 archive，并提供索引。
3. 禁止在 root docs 中继续堆叠 dated status docs。

**Verification:**

- active docs 数量显著下降。
- dated docs 不再与当前正文混堆。

### Phase ν: Reference Asset Taxonomy

**Objective:** 把 `references/**` 整理为少量稳定 family。

**Files:**
- Modify: `references/index.md`
- Create: `references/contracts/README.md`
- Create: `references/matrices/README.md`
- Create: `references/ledgers/README.md`
- Create: `references/taxonomy/README.md`

**Actions:**

1. 将 reference assets 分为 contracts / matrices / ledgers / fixtures / taxonomy。
2. 合并重复 ledger 和一次性 batch 产物。
3. 把 mirror-topology 等 subordinate reference 标明从属关系。

**Verification:**

- `references/index.md` 足以回答“这类参考资产去哪找”。

### Phase ξ: Scripts and Config Surface Consolidation

**Objective:** 让 `scripts/` 和 `config/` 从“文件堆”变成“可发现的面”。

**Files:**
- Modify: `scripts/README.md`
- Modify: `scripts/governance/README.md`
- Modify: `scripts/verify/README.md`
- Modify: `config/index.md`

**Actions:**

1. 给 `common`, `router`, `governance`, `verify` 建立清晰边界。
2. 给 `config/` 标注：
   - routing core
   - topology / packaging
   - cleanliness / outputs
   - release / runtime
   - historical boards
3. archive 或合并已无运行价值的 board/status json。

**Verification:**

- 新人能先读 index，再读单文件，而不是先全量扫描。

### Phase ο: Third-Party Dependency Decoupling

**Objective:** 识别真正需要的第三方元数据和真正可以外移的镜像负担。

**Files:**
- Modify: `third_party/README.md`
- Modify: research scripts referencing `third_party/**`
- Modify: `config/upstream-corpus-manifest.json`
- Modify: upstream audit docs and indexes

**Actions:**

1. 识别仍依赖本地 `third_party` 的脚本。
2. 改为：
   - parameterized `-SourceRoot`
   - manifest-driven source resolution
   - optional external checkout
   - release-time or audit-time fetch
3. 仅在主仓保留 provenance、license、manifest、operator notes。

**Verification:**

- research / external corpus / audit flows 不因本地镜像外移而失效。

### Phase π: Log and Release Record Normalization

**Objective:** 把长期日志收敛到 machine ledger + human summary。

**Files:**
- Modify: `references/release-ledger.jsonl`
- Create: `references/ledgers/cleanup-ledger.md`
- Modify: `docs/status/current-state.md`
- Archive: duplicated closure reports and redundant release notes

**Actions:**

1. 统一命名和 retention 规则。
2. 把“事件型长期记录”压缩到 ledger。
3. 把阶段状态压缩到 current-state。
4. 不再为每个 batch 单独留下长期正文。

**Verification:**

- tracked logs 数量下降。
- 日志类型不再重复。

### Phase ρ: Backup and Rollback Discipline

**Objective:** 用结构化 rollback 替代散落备份。

**Files:**
- Create: `docs/status/migration-manifests.md`
- Modify: governance operator docs

**Actions:**

1. 为每个大迁移定义 manifest。
2. 定义 preview -> apply -> verify -> prune -> rollback 五段式。
3. 禁止无 owner、无过期时间的 backup 常驻。

**Verification:**

- 所有高风险迁移都可解释、可回退。

### Phase σ: Release / Install / Check Hardening

**Objective:** 在完成主要结构迁移后，重新校准 release/install/check 契约。

**Files:**
- Modify: `docs/runtime-freshness-install-sop.md`
- Modify: `docs/version-packaging-governance.md`
- Modify: install/check scripts

**Actions:**

1. 让 release/install/check 文档与实际结构一致。
2. 明确 compatibility layer 的生成位置。
3. 保持 shell degraded behavior 语义。

**Verification:**

- 从 canonical 到 installed runtime 的链路继续完整。

### Phase τ: Minimum Critical Gate Re-Green

**Objective:** 用最小关键 gate bundle 重新定义 closure。

**Required gates:**

- `vibe-repo-cleanliness-gate.ps1`
- `vibe-output-artifact-boundary-gate.ps1`
- `vibe-mirror-edit-hygiene-gate.ps1`
- `vibe-version-packaging-gate.ps1`
- `vibe-installed-runtime-freshness-gate.ps1`
- `vibe-release-install-runtime-coherence-gate.ps1`
- `vibe-pack-routing-smoke.ps1`
- `vibe-router-contract-gate.ps1`

**Actions:**

1. 先打绿 hygiene / outputs / mirror。
2. 再打绿 routing / packaging / install / runtime。
3. specialized gates 后置，不再让 closure 依赖海量报告。

**Verification:**

- 关键功能和关键清洁边界均有 machine proof。

### Phase υ: Operator Dry Run

**Objective:** 让真实操作者按新结构完成一次完整演练。

**Files:**
- Create: `docs/status/operator-dry-run.md`

**Actions:**

1. 从 canonical root 运行一次标准 operator path：
   - sync
   - routing smoke
   - packaging gate
   - install
   - runtime freshness
   - coherence
2. 记录 friction points。

**Verification:**

- 新结构可操作，不只是文档上成立。

### Phase φ: Safe Prune Window

**Objective:** 只在 proof 完成后，删除冗余常驻对象。

**Prune candidates:**

- nested tracked mirror root
- remaining tracked outputs
- duplicated dated plans/reports
- redundant release-note copies
- obsolete backup directories
- externalized third_party heavy content

**Rule:**

- no proof, no prune

### Phase χ: Closure Audit

**Objective:** 证明“仓库已变简洁、清晰、干净，且功能未退化”。

**Files:**
- Create: `docs/status/closure-audit.md`

**Audit questions:**

1. 真源是否唯一？
2. 兼容层是否被显式标记而不是暗藏？
3. runtime 是否退出长期资产职责？
4. docs 是否明显收口？
5. 日志是否规范且低冗余？
6. 关键 proof bundle 是否全绿？

### Phase ψ: Handover and Steady-State Docs

**Objective:** 把新结构交给未来维护者，而不是只对本次整改团队有效。

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/status/current-state.md`
- Modify: `docs/status/roadmap.md`

**Actions:**

1. 记录当前 steady state。
2. 记录后续新增内容必须走的入口。
3. 明确 future changes 的 admission rules。

### Phase ω: Steady-State Governance

**Objective:** 防止清理后的仓库再次滑回旧模式。

**Long-term guardrails:**

1. 新 mirror 必须先论证，不得默认常驻 tracked。
2. 新 outputs 不得进入 git，除非先声明 fixture role。
3. 新 dated docs 必须先判断是否应写进 archive、ledger、current-state。
4. 新 third-party intake 必须先过 manifest / source registry / consumer proof。
5. 新 cleanup 需求优先通过 canonical docs spine 和 existing indices 消化，不先写新的治理文档。

## Definition of Done

整改完成时，必须同时满足：

1. `nested_bundled` 不再是 repo 常驻 mirror workset，且 install/runtime/release 功能未退化。
2. `outputs/**` 完全回到 runtime-only，长期 baseline 已迁入 fixtures / ledgers。
3. active docs 显著少于当前状态，且主入口更强。
4. 长期 tracked logs 只保留少量 ledger 和 current-state。
5. `third_party/**` 不再是主仓巨大认知面，但 research / audit / corpus flows 继续可用。
6. `docs/README.md`, `docs/status/current-state.md`, `references/index.md`, `config/index.md`, `scripts/README.md` 构成稳定入口骨架。
7. 关键 proof bundle 全绿。
8. 未来维护者无需阅读大量 dated plan/report 才能理解当前仓库状态。

## Immediate Next Actions

1. 采用本计划作为唯一 active cleanup execution plan。
2. 冻结新增 overlay / wave / bulk docs / bulk vendoring。
3. 先执行 `β -> γ -> δ`：
   - protected capability baseline
   - path dependency census
   - non-regression proof bundle
4. 在 `β -> δ` 未完成之前，禁止删除：
   - `nested_bundled`
   - tracked outputs baseline
   - `third_party` heavy source roots
   - active release/install/runtime docs
5. 在 non-regression baseline 建好之后，再进入 `ε -> θ` 做第一批结构迁移。

## Final Recommendation

本工程的最佳执行口径不是“先删掉多余结构，再修功能”，而是：

**先把功能的边界画准，先把替代路径做好，先把 proof 建起来，然后再做清理。**

只有这样，仓库才能同时达到你的两个目标：

- **更简洁、更清晰、更干净**
- **严格不发生功能退化**
