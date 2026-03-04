# VCO Skills Codex Ecosystem

面向 Codex 运行时的 Vibe Code Orchestrator（VCO）生态仓库。这个仓库不是“单一技能包”，而是一个可安装、可验证、可演进的路由与执行体系，覆盖从任务分级、技能路由到质量门禁的完整链路。

## 目标与定位

本仓库解决三个核心问题：

1. 如何在 Codex 中稳定路由到正确的技能与执行流。
2. 如何在多来源技能生态里保持可重复安装与可控升级。
3. 如何通过可执行门禁持续控制误路由和质量波动。

## 生态组成

### 1. VCO 核心编排层

- `SKILL.md` 定义了 VCO v2.3 的分级执行模型（M/L/XL）。
- `scripts/router/resolve-pack-route.ps1` 负责 Pack 路由决策。
- `config/*` 提供路由参数、候选技能、别名和规则配置。

### 2. AIOS-Core 集成层

已将 `SynkraAI/aios-core` 的工作方法纳入 VCO 生态，以 Pack 方式并入路由系统：

- Pack: `aios-core`
- 任务默认技能（`defaults_by_task`）：
  - `planning -> aios-pm`
  - `coding -> aios-dev`
  - `review -> aios-qa`
  - `debug -> aios-devops`
  - `research -> aios-analyst`
- 适合 PRD、Backlog、PO/PM 协作、QA Gate、DevOps 排障等 Agentic Agile 流程。

### 3. 兼容与增强层

- `bundled/skills/*`：全量 vendored 技能镜像（离线开箱基线，当前 239 skills）。
- `bundled/superpowers-skills/*`：规划、调试、代码评审等工作流增强技能。
- `config/skills-lock.json`：vendored 技能锁文件（目录哈希 + `SKILL.md` 哈希），用于离线一致性门禁。
- 可选外部增强（按需安装）：`SuperClaude_Framework` 命令集、`claude-flow`。
- `ralph-loop` 采用双引擎接入：
  - `compat`（默认）：本地状态循环，手动 `--next`，稳定低依赖
  - `open`（可选）：委托 `open-ralph-wiggum` 自动循环后端（`--engine open`）

### 4. OpenSpec 治理层（零冲突接入）

OpenSpec 以“后置治理”方式接入，不参与现有 Pack 路由打分，确保路由分配稳定：

- 治理策略：`config/openspec-policy.json`
- 路由输出附加治理建议（不改变 selected pack/skill）：`scripts/router/resolve-pack-route.ps1`
- 治理执行器（M 级 Lite 卡片、L/XL Full 产物检查）：`scripts/governance/invoke-openspec-governance.ps1`
- 渐进切换脚本（默认仅 L/XL planning 触发 confirm）：`scripts/governance/set-openspec-rollout.ps1`
- 单命令软发布脚本（先验后切，失败时仅输出手动回退命令，需用户确认后执行）：`scripts/governance/publish-openspec-soft-rollout.ps1`
- 设计说明：`docs/openspec-vco-integration.md`

当前默认策略：`soft-lxl-planning`（`mode=soft`，`soft_confirm_scope={grades:[L,XL], task_types:[planning]}`）。

### 5. GSD-Lite 规划增强层（零双轨接入）

GSD 仅以“协议钩子层”接入，不引入第二编排器、不引入第二命令面：

- 覆盖范围：仅 `L/XL + planning`（可配置）
- 接入方式：`protocols/think.md` preflight hook + `protocols/team.md` wave contract hook
- 路由边界：不参与 Pack 打分，不改变 selected pack/skill
- 配置文件：`config/gsd-overlay.json`
- 模式切换：`scripts/governance/set-gsd-overlay-rollout.ps1`
- 设计说明：`docs/gsd-vco-overlay-integration.md`

### 6. prompts.chat Prompt 资产增强层（零冲突接入）

prompts.chat 仅作为 Prompt 资产层接入，不引入第二路由器：

- 覆盖范围：`planning/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `prompt_overlay_advice`
- 路由边界：不替换 Pack 选择，仅在 prompt/doc 语义冲突时提升为 `confirm_required`
- 配置文件：`config/prompt-overlay.json`
- 设计说明：`docs/prompt-overlay-integration.md`

### 7. Memory Governance 增强层（零冲突接入）

Memory governance 以“后置建议层”接入，不改变现有 Pack 路由决策：

- 覆盖范围：`M/L/XL + planning/coding/review/debug/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `memory_governance_advice`
- 路由边界：不替换 Pack 选择，不引入第二控制面
- 配置文件：`config/memory-governance.json`
- 设计说明：`docs/memory-governance-integration.md`

核心边界：
- `state_store` 只做会话状态
- `Serena` 只做显式项目决策
- `ruflo` 只做短期会话向量缓存
- `Cognee` 只做长期图记忆与关系检索
- `episodic-memory` 在 VCO 治理路径中停用

### 8. Data Scale Overlay（xan 大 CSV 增强，零冲突接入）

Data scale overlay 仅作为“后置数据探针层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `docs-media + coding/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `data_scale_advice`
- 决策依据：真实文件信号（路径存在性、大小、格式、采样估计行数），不是仅靠用户说“大/小”
- 路由边界：保持 pack 不变；仅在同 pack 候选内做 mode-gated skill 选择增强（`spreadsheet/xlsx/xan`）
- 配置文件：`config/data-scale-overlay.json`
- 设计说明：`docs/data-scale-overlay-integration.md`

### 9. Quality Debt Overlay（fuck-u-code 增强，零冲突接入）

Quality debt overlay 仅作为“后置质量债务建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `code-quality + coding/review`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `quality_debt_advice`
- 决策依据：风险关键词 + 抑制关键词 + 侧重 facet（maintainability/test/security）
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段也仅提升 advice 为 `confirm_required`
- 外部工具：`fuck-u-code` 可选接入，缺失时仅返回 `tool_unavailable`，不阻断主流程
- 配置文件：`config/quality-debt-overlay.json`
- 设计说明：`docs/quality-debt-overlay-integration.md`

### 10. Framework Interop Overlay（ivy 跨框架互操作增强，零冲突接入）

Framework interop overlay 仅作为“后置跨框架迁移建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `data-ml/ai-llm + L/XL + coding/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `framework_interop_advice`
- 决策依据：跨框架迁移信号 + 框架实体识别 + 抑制关键词降噪
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段仅将建议提升为 `confirm_required`
- 外部工具：`ivy` 可选接入，缺失时仅返回 `tool_unavailable`，不阻断主流程
- 配置文件：`config/framework-interop-overlay.json`
- 设计说明：`docs/framework-interop-overlay-integration.md`

### 11. ML Lifecycle Overlay（Made-With-ML 生命周期治理增强，零冲突接入）

ML lifecycle overlay 仅作为“后置生命周期治理建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `data-ml/ai-llm + planning/coding/review/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `ml_lifecycle_advice`
- 决策依据：生命周期阶段信号（develop/evaluate/deploy/iterate）+ 证据工件覆盖率（run/eval/baseline/tests/monitoring）
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段仅将建议提升为 `confirm_required`
- 外部工具：`mlflow` 可选接入，缺失时仅返回 `tool_unavailable`，不阻断主流程
- 配置文件：`config/ml-lifecycle-overlay.json`
- 设计说明：`docs/ml-lifecycle-overlay-integration.md`

### 12. Python Clean Code Overlay（clean-code-python 增强，零冲突接入）

Python clean-code overlay 仅作为“后置 Python 质量建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `coding/review/debug`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `python_clean_code_advice`
- 决策依据：`.py/.pyi` 文件信号 + Python 语义 + clean-code 原则/反模式 + 抑制关键词
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段仅将建议提升为 `confirm_required`
- 外部工具：无强依赖，缺少外部工具不影响主流程
- 配置文件：`config/python-clean-code-overlay.json`
- 设计说明：`docs/python-clean-code-overlay-integration.md`

### 13. System Design Overlay（system-design-primer 架构覆盖增强，零冲突接入）

System design overlay 仅作为“后置架构覆盖建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `L/XL + planning/research/review`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `system_design_advice`
- 决策依据：架构语义信号 + 架构覆盖维度评分（requirements/NFR/capacity/cache/partition/recovery/observability/cost）+ 抑制关键词
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段仅将建议提升为 `confirm_required`
- 外部工具：无强依赖，缺少外部工具不影响主流程
- 配置文件：`config/system-design-overlay.json`
- 设计说明：`docs/system-design-overlay-integration.md`

### 14. CUDA Kernel Overlay（LeetCUDA CUDA内核优化增强，零冲突接入）

CUDA kernel overlay 仅作为“后置 CUDA 内核优化建议层”接入，不替代 Pack 路由、不引入第二编排器：

- 覆盖范围：默认 `M/L/XL + coding/debug/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 输出 `cuda_kernel_advice`
- 决策依据：CUDA语义信号 + 文件/环境信号（`.cu/.ptx/nvcc/nvidia-smi`）+ 优化覆盖维度评分（memory/tensor-core/occupancy/profiling/correctness/fallback）
- 路由边界：保持 `selected pack/skill` 不变，strict 阶段仅将建议提升为 `confirm_required`
- 外部工具：无强依赖，缺少 CUDA 环境或工具不影响主流程
- 许可证边界：`LeetCUDA` 为 GPL-3.0，上游仅作为方法论参考，不 vendoring 源码
- 配置文件：`config/cuda-kernel-overlay.json`
- 设计说明：`docs/cuda-kernel-overlay-integration.md`

### 15. Observability & Consistency Governance（严格、轻量、低上下文压力）

Observability governance 以“后置遥测层”接入，不影响既有路由分配：

- 覆盖范围：`M/L/XL + planning/coding/review/debug/research`（可配置）
- 接入方式：`resolve-pack-route.ps1` 写入隐私安全路由事件（JSONL）
- 数据策略：默认仅 `prompt_hash` + 结构化路由字段，不落地原始 prompt
- 学习策略：离线建议（manual apply），不自动改路由阈值
- 回退策略：发布失败时只告知并输出手动回退命令，必须用户确认后执行
- 配置文件：`config/observability-policy.json`
- 设计说明：`docs/observability-consistency-governance.md`

### 16. External Expert Prompt Overlays（agency-agents + GitNexus，advice-only）

这一层不是“路由 overlay”（不参与 Pack 打分，不改变 selected pack/skill），而是“交付视角 overlay”：

- 目标：把“部门专家视角”和“代码感知底座”以 **可注入 prompt 模板** 的形式接入 VCO，减少盲改、漏依赖与漏测。
- 使用方式：**自动建议 → 你确认 → 输出可注入的 prompt overlay**（advice-only，不强制执行）。
- 统一入口（建议最多选 2 个 overlay）：`scripts/overlay/suggest-vco-overlays.ps1`
  - GitNexus（底层证据）+ agency-testing（任意阶段可推荐）是最常见组合。
- 配置与模板：
  - 合并配置：`config/vco-overlays.json`
  - 部门专家：`config/agency-overlays.json` + `references/overlays/agency/*.md`
  - GitNexus：`config/gitnexus-overlays.json` + `references/overlays/gitnexus/*.md`
- 文档入口：
  - `docs/agency-agents-overlay.md`
  - `docs/gitnexus-overlay.md`
  - `docs/gitnexus-mcp-integration-draft.md`
  - `docs/gitnexus-execution-checklist.md`

治理边界（避免冲突）：

- advice-only：用户显式指令 > VCO 协议/质量闸门（P5/V2/V3）> overlay 建议
- GitNexus MCP 为可选增强；不可用/未索引时必须 fallback（`rg`/`git diff`/入口点追踪）

## 当前路由能力（Strict-Ready）

本版本已经包含稳定性收敛与规则化路由增强：

1. `pack-manifest.json` 支持 `defaults_by_task`。
2. `skill-routing-rules.json` 支持：
   - `task_allow`
   - `positive_keywords`
   - `negative_keywords`
   - `equivalent_group`
   - `canonical_for_task`
3. 路由器新增关键行为：
   - 先做 `task_allow` 硬过滤
   - 再做正负关键词打分
   - 低置信度不再“首候选兜底”，改为按 `defaults_by_task` 兜底
   - top1/top2 过近时进入 `confirm_required`
4. 已提供技能重叠画像文档：`docs/skills-overlap-matrix.md`。

## 仓库关键组件

| 路径 | 作用 |
|---|---|
| `config/pack-manifest.json` | Pack 定义、触发词、候选技能、`defaults_by_task` |
| `config/router-thresholds.json` | 路由权重、阈值、候选评分参数 |
| `config/skill-keyword-index.json` | 技能关键词索引（含中英） |
| `config/skill-routing-rules.json` | 任务硬过滤与正负关键词规则 |
| `config/openspec-policy.json` | OpenSpec 治理策略（mode/profile/升级触发） |
| `config/gsd-overlay.json` | GSD-Lite 规划增强策略（post-route hook） |
| `config/prompt-overlay.json` | prompts.chat Prompt 资产增强策略（post-route ambiguity guard） |
| `config/memory-governance.json` | Memory governance 策略（角色边界 + disabled memory） |
| `config/data-scale-overlay.json` | Data scale overlay 策略（真实文件探针 + spreadsheet/xlsx/xan 选择增强） |
| `config/quality-debt-overlay.json` | Quality debt overlay 策略（风险信号评分 + 可选外部分析器提示） |
| `config/framework-interop-overlay.json` | Framework interop overlay 策略（跨框架迁移信号评分 + Ivy advisory） |
| `config/ml-lifecycle-overlay.json` | ML lifecycle overlay 策略（生命周期阶段识别 + 证据工件完备度 advisory） |
| `config/python-clean-code-overlay.json` | Python clean-code overlay 策略（`.py` 自动触发 + 原则/反模式 advisory） |
| `config/system-design-overlay.json` | System design overlay 策略（架构语义 + 覆盖维度 advisory） |
| `config/cuda-kernel-overlay.json` | CUDA kernel overlay 策略（CUDA优化语义 + 文件/环境信号 + 证据完备度 advisory） |
| `config/observability-policy.json` | 可观测性策略（隐私安全遥测 + 分桶学习 + 手动应用） |
| `config/vco-overlays.json` | External expert prompt overlay 合并配置（GitNexus + agency-agents，自动建议 → 确认 → 注入） |
| `config/agency-overlays.json` | 部门专家 overlay 配置（关键词/阶段兜底；Testing 支持 any-stage 推荐） |
| `config/gitnexus-overlays.json` | GitNexus overlay 配置（foundation/impact/detect_changes/architecture-map） |
| `scripts/router/resolve-pack-route.ps1` | 路由核心执行器 |
| `scripts/governance/invoke-openspec-governance.ps1` | OpenSpec 后置治理执行器（零冲突） |
| `scripts/overlay/suggest-vco-overlays.ps1` | External expert overlay：统一建议入口（最多选 2 个） |
| `scripts/overlay/suggest-agency-overlays.ps1` | External expert overlay：只建议部门专家 |
| `scripts/overlay/suggest-gitnexus-overlays.ps1` | External expert overlay：只建议 GitNexus |
| `references/overlays/agency/` | 部门专家可注入 prompt 模板（精简版） |
| `references/overlays/gitnexus/` | GitNexus 可注入 prompt 模板（基底/影响面/变更感知/架构地图） |
| `scripts/governance/set-openspec-rollout.ps1` | OpenSpec 模式渐进切换（off/shadow/soft/strict） |
| `scripts/governance/publish-openspec-soft-rollout.ps1` | OpenSpec soft-lxl-planning 单命令发布（先验后切 + 后验门禁） |
| `scripts/governance/set-gsd-overlay-rollout.ps1` | GSD-Lite 模式切换（off/shadow/soft/strict） |
| `scripts/verify/*.ps1` | 回归矩阵、审计、稳定性门禁 |
| `scripts/learn/vibe-adaptive-train.ps1` | 基于遥测的离线阈值建议（手动审核应用） |
| `docs/skills-overlap-matrix.md` | 技能重叠分类与路由建议 |
| `docs/openspec-vco-integration.md` | OpenSpec 与 VCO 的分层集成说明 |
| `docs/gsd-vco-overlay-integration.md` | GSD-Lite 与 VCO 的非冗余接入说明 |
| `docs/prompt-overlay-integration.md` | prompts.chat 与 VCO 的非冗余接入说明 |
| `docs/memory-governance-integration.md` | Memory governance 与 VCO 的非冲突接入说明 |
| `docs/data-scale-overlay-integration.md` | Data scale overlay 与 VCO 的非冲突接入说明 |
| `docs/quality-debt-overlay-integration.md` | Quality debt overlay 与 VCO 的非冲突接入说明 |
| `docs/framework-interop-overlay-integration.md` | Framework interop overlay 与 VCO 的非冲突接入说明 |
| `docs/ml-lifecycle-overlay-integration.md` | ML lifecycle overlay 与 VCO 的非冲突接入说明 |
| `docs/python-clean-code-overlay-integration.md` | Python clean-code overlay 与 VCO 的非冲突接入说明 |
| `docs/system-design-overlay-integration.md` | System design overlay 与 VCO 的非冲突接入说明 |
| `docs/cuda-kernel-overlay-integration.md` | CUDA kernel overlay 与 VCO 的非冲突接入说明 |
| `docs/observability-consistency-governance.md` | 可观测性与一致性治理设计（低上下文压力 + 手动确认回退） |
| `bundled/skills/vibe/config/*` | 与主配置镜像同步的 bundled 配置 |

## 搭建与安装流程

### 前置要求

- Windows PowerShell 7+（或兼容 PowerShell）
- `git`
- 可选：`npm`（安装外部增强时使用）

### 快速安装（Codex 本地）

```powershell
pwsh -File .\install.ps1 -Profile full -StrictOffline
pwsh -File .\check.ps1 -Profile full -Deep
```

### 安装可选外部增强

```powershell
pwsh -File .\install.ps1 -Profile full -InstallExternal
```

说明：当前安装器为 Codex-only 主模式。`plugins-manifest.codex.json` 中的插件安装命令不会被自动执行，会输出手动安装提示，避免跨运行时误装。  
`-InstallExternal` 会尝试安装 `claude-flow` 与 `@th0rgal/ralph-wiggum`（open 引擎）。
`ivy` 作为可选 Python 依赖默认不自动安装，安装器仅做可用性提示（建议手动执行 `pip install ivy`）。
离线强一致安装建议使用 `-StrictOffline`；默认不再依赖仓库外技能目录。若必须临时放开外部兜底，可显式使用 `-AllowExternalSkillFallback`（不建议用于团队基线）。

### 强建议安装的 MCP（Full Profile）

为保证 `/vibe` 路由与增强能力稳定，建议在 `full` 配置下至少安装并启用以下 MCP 组合（与 `mcp/profiles/full.json` 对齐）：

| MCP | 作用 | 安装方式 |
|---|---|---|
| `github` | PR/Issue/代码检索与仓库操作 | 在 Codex MCP/插件管理中启用 GitHub 集成 |
| `context7` | 官方文档检索与代码示例查询 | 在 Codex MCP/插件管理中启用 Context7 集成 |
| `serena` | 项目决策型记忆（显式决策记录） | 在 Codex MCP/插件管理中启用 Serena 集成 |
| `claude-flow` | 本地 stdio MCP 扩展能力 | `npm install -g claude-flow` 或 `install.ps1 -InstallExternal` |

可选增强（不影响核心路由）：`prompts-chat`、`xan`、`ivy`、`fuck-u-code`。

### MCP 安装步骤（Windows）

1. 安装 VCO（离线强一致）：

```powershell
pwsh -File .\install.ps1 -Profile full -StrictOffline
```

2. 安装本地 `claude-flow`（二选一）：

```powershell
# 方式 A：让安装器处理外部依赖
pwsh -File .\install.ps1 -Profile full -InstallExternal

# 方式 B：手动安装
npm install -g claude-flow
```

3. 在 Codex MCP/插件管理中手动启用：`github`、`context7`、`serena`。

4. 使用仓库模板作为服务清单参考：`mcp/servers.template.json`；目标 profile 参考：`mcp/profiles/full.json`。

5. 运行健康检查：

```powershell
pwsh -File .\check.ps1 -Profile full -Deep
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
```

说明：`-StrictOffline` 只保证“技能与路由闭包”不回退；MCP 服务本身是否可用取决于本机是否完成对应 MCP 的安装与授权配置。

### 指定安装目录

```powershell
pwsh -File .\install.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex"
```

### 离线闭包门禁（推荐纳入 CI）

```powershell
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
```

## 日常使用

### 1. 路由验证（建议每次改配置后执行）

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-pack-regression-matrix.ps1
pwsh -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -WriteArtifacts
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
pwsh -File .\scripts\verify\vibe-openspec-governance-gate.ps1
pwsh -File .\scripts\verify\vibe-gsd-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-prompt-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-memory-governance-gate.ps1
pwsh -File .\scripts\verify\vibe-data-scale-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-quality-debt-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-framework-interop-gate.ps1
pwsh -File .\scripts\verify\vibe-ml-lifecycle-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-python-clean-code-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-system-design-overlay-gate.ps1
pwsh -File .\scripts\verify\vibe-cuda-kernel-overlay-gate.ps1
```

### 2. OpenSpec 软发布（先验后切，默认不回退）

```powershell
# 当前推荐：单命令发布到 soft-lxl-planning
# 内置流程：Precheck(Strict) -> Switch -> Postcheck(Strict + Governance Gate)
pwsh -File .\scripts\governance\publish-openspec-soft-rollout.ps1
```

默认语义：

- precheck 失败：直接终止，不切换，不回退
- postcheck 失败：默认保持当前状态并失败退出（不自动回退，避免掩盖问题）

仅在“特殊事故”场景下显式启用应急回退：

```powershell
pwsh -File .\scripts\governance\publish-openspec-soft-rollout.ps1 `
  -EnableEmergencyRollbackOnFailure `
  -RollbackStage shadow
```

手动阶段切换（不带门禁）仍可用：

```powershell
pwsh -File .\scripts\governance\set-openspec-rollout.ps1 -Stage soft-lxl-planning

pwsh -File .\scripts\governance\set-openspec-rollout.ps1 -Stage shadow
```

### 3. GSD-Lite Overlay 切换（协议增强，不改路由）

```powershell
# 仅记录建议，不影响执行
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage shadow

# 建议默认：仅 L/XL planning 进入 soft 确认策略
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage soft-lxl-planning

# 更严格：L/XL planning 都强制确认
pwsh -File .\scripts\governance\set-gsd-overlay-rollout.ps1 -Stage strict-lxl-planning
```

### 4. 生态同步（从本地兼容源更新 bundled）

```powershell
pwsh -File .\scripts\bootstrap\sync-local-compat.ps1
pwsh -File .\scripts\verify\vibe-generate-skills-lock.ps1
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
```

### 5. Ralph 双引擎用法（可选）

```powershell
# 默认 compat 引擎（本地状态循环）
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\\.codex\\skills\\ralph-loop\\scripts\\ralph-loop.ps1" `
  Build a todo API --max-iterations 10 --completion-promise DONE

# open 引擎（open-ralph-wiggum 自动循环后端）
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\\.codex\\skills\\ralph-loop\\scripts\\ralph-loop.ps1" `
  --engine open Build a todo API --max-iterations 10 --completion-promise DONE
```

边界约束：

- `ralph-loop` 与 XL team orchestration 互斥。
- `open` 引擎建议保持 no-commit 模式，循环结束后再走 VCO 质量门禁与人工提交。

## 使用到的上游项目与方法论

| 项目 / 来源 | 用途 |
|---|---|
| `SynkraAI/aios-core` | 引入 Agentic Agile 角色化协作（PM/PO/QA/DevOps 等） |
| `Th0rgal/open-ralph-wiggum` | 作为 `ralph-loop --engine open` 的可选自动循环后端（不替代 VCO 路由层） |
| `f/prompts.chat` | 提供 prompt 模板检索/改写/发布能力，作为 VCO prompt 资产增强层 |
| `medialab/xan` | 提供超大 CSV 低内存处理能力，作为 data-scale overlay 的可选执行后端 |
| `Done-0/fuck-u-code` | 提供离线质量债务分析思路，作为 quality-debt overlay 的可选分析后端 |
| `ivy-llc/ivy` | 提供跨框架互操作能力，作为 framework-interop overlay 的可选 advisory 后端 |
| `GokuMohandas/Made-With-ML` | 提供 ML 生命周期治理方法论，作为 ml-lifecycle overlay 的阶段/证据 advisory 语义来源 |
| `zedr/clean-code-python` | 提供 Python clean-code 原则体系，作为 python-clean-code-overlay 的原则/反模式 advisory 语义来源 |
| `donnemartin/system-design-primer` | 提供系统设计覆盖维度方法论，作为 system-design-overlay 的架构完整性 advisory 语义来源 |
| `xlite-dev/LeetCUDA` | 提供 CUDA kernel 优化方法论，作为 cuda-kernel-overlay 的 CUDA 优化证据/维度 advisory 语义来源 |
| `x1xhlol/system-prompts-and-models-of-ai-tools` | 作为外部语料镜像来源，提取路由信号与关键词候选，服务 VCO 路由优化 |
| `muratcankoylan/Agent-Skills-for-Context-Engineering` | 作为 Context Retro Advisor 的专家知识源，驱动 CER 复盘框架 |
| `SuperClaude_Framework`（可选） | 提供 `sc` 命令体系兼容能力 |
| `claude-flow`（可选） | 外部编排增强能力 |
| 本仓库 VCO 核心 | 分级执行、Pack 路由、规则门禁、验证体系 |

## 外部项目融合说明

### A. `system-prompts-and-models-of-ai-tools` 在 VCO 中的作用

这部分不是“直接抄系统提示词进 VCO”，而是作为外部语料输入到一条受控的数据化流程：

1. 语料镜像到 `third_party/system-prompts-mirror`
2. 通过 `scripts/research/extract-prompt-signals.ps1` 抽取 prompt/tool 信号
3. 通过 `scripts/research/generate-vco-suggestions.ps1` 生成候选路由关键词
4. 通过 `scripts/verify/vibe-external-corpus-gate.ps1` 做门禁对比后再决定是否采纳

对应文档与产物：

- 流程说明：`docs/external-corpus-integration.md`
- 信号抽取：`scripts/research/extract-prompt-signals.ps1`
- 候选生成：`scripts/research/generate-vco-suggestions.ps1`
- 安全门禁：`scripts/verify/vibe-external-corpus-gate.ps1`
- 产物目录：`outputs/external-corpus/`

核心原则：外部语料用于“路由信号工程”，不直接污染 `SKILL.md` 主编排协议。

### B. `Agent-Skills-for-Context-Engineering` 在 VCO 中的作用

这部分融合在 VCO 的 LEARN / retro 闭环，定位是 advisory-only（建议层），不自动改配置：

1. 在 `SKILL.md` 中作为 Context Retro Advisor 的指导知识源
2. 在 `protocols/retro.md` 中落地为可执行的复盘流程
3. 输出统一 CER（Context Evidence Report）结构，支撑跨迭代对比

对应文档与组件：

- 设计文档：`docs/context-retro-advisor-design.md`
- 执行协议：`protocols/retro.md`
- CER 模板与 Schema：`templates/cer-report.*`
- CER 对比工具：`scripts/verify/cer-compare.ps1`

核心价值：把“上下文工程经验”变成可量化、可对比、可复用的复盘资产，而不是一次性结论。

## 许可证与第三方边界

- 本仓库根许可证：`Apache-2.0`（见 `LICENSE`）。
- 仓库简版公告：`NOTICE`（仓库名/年份/作者规范化）。
- 第三方来源与边界清单：`THIRD_PARTY_LICENSES.md`。
- 第三方上游项目保留其各自许可证，不因本仓库发布而被重新授权。
- GitNexus 为可选工具增强，其上游许可证为 **PolyForm Noncommercial**；商用/对外服务前务必先做合规确认（见 `docs/gitnexus-mcp-integration-draft.md`）。
- 外部语料（如 `system-prompts-and-models-of-ai-tools`）默认作为“研究输入”处理，不应将原始语料直接并入核心编排协议。
- 若你在 `third_party/` 本地镜像外部仓库并进行再分发，请自行确保满足对应上游许可证义务。

## 当前版本更新重点

- 完成 AIOS-Core Pack 级集成与默认任务技能映射。
- 完成路由规则层升级（`skill-routing-rules` + `defaults_by_task`）。
- 新增 External Expert Prompt Overlays（agency-agents + GitNexus）：自动建议 → 你确认 → 输出可注入 overlay（advice-only，不改路由）。
- 新增 GitNexus MCP 接入草案与执行清单（Codex CLI `codex mcp add` + `gitnexus analyze` 索引闭环）。
- 完成 OpenSpec 治理层零冲突接入（后置治理，不参与 Pack 打分，不改 selected pack/skill）。
- 完成 GSD-Lite 规划增强层接入（协议钩子模式，不引入第二编排器/第二命令面）。
- 完成 prompts.chat Prompt 资产增强层接入（post-route advice，不替换 Pack 选择，仅处理 prompt/doc 冲突确认）。
- 完成 Memory Governance 增强层接入（post-route advice，不替换 Pack 选择，明确五层记忆边界并停用 episodic-memory）。
- 完成 Data Scale Overlay 接入（post-route data probe，不替换 Pack 选择，按真实文件规模/格式增强 `spreadsheet/xlsx/xan` 选择）。
- 完成 Quality Debt Overlay 接入（post-route risk advisory，不替换 Pack 选择，严格模式仅输出 confirm_required 建议）。
- 完成 Framework Interop Overlay 接入（post-route interop advisory，不替换 Pack 选择，跨框架迁移场景输出 `framework_interop_advice`）。
- 完成 ML Lifecycle Overlay 接入（post-route lifecycle advisory，不替换 Pack 选择，输出 `ml_lifecycle_advice` 以刻画阶段与证据完备度）。
- 完成 Python Clean Code Overlay 接入（post-route Python quality advisory，不替换 Pack 选择，输出 `python_clean_code_advice` 并支持 `.py` 文件自动触发）。
- 完成 System Design Overlay 接入（post-route architecture advisory，不替换 Pack 选择，输出 `system_design_advice` 以刻画架构覆盖完整度）。
- 完成 CUDA Kernel Overlay 接入（post-route CUDA advisory，不替换 Pack 选择，输出 `cuda_kernel_advice` 以刻画 CUDA 优化证据完备度）。
- 新增 OpenSpec 单命令 soft 发布脚本（`publish-openspec-soft-rollout.ps1`）：
  - 固定流程：`precheck -> switch -> postcheck`
  - 默认不自动回退，失败保持可见
  - 仅在显式应急开关下执行回退
- 新增 GSD-Lite 模式切换脚本（`set-gsd-overlay-rollout.ps1`）：
  - 支持 `off|shadow|soft-lxl-planning|strict-lxl-planning`
  - 默认推荐 `soft-lxl-planning`
- 完成 strict-ready 稳定性收敛：
  - 对高重叠组进行非粗暴精调（正负关键词 + 任务硬过滤 + 同义样本分组）。
  - 新增/扩展稳定性指标：`route_stability`、`top1_top2_gap`、`fallback_rate`、`misroute_rate`。

## 贡献与发布建议

1. 先改 `config/` 与 `scripts/router/`。
2. 运行全部 `scripts/verify/` 门禁。
3. 同步 `bundled/skills/vibe/config/` 镜像配置。
4. 更新 `docs/`（尤其是 overlap matrix 与验证产物）。
5. 再提交并发布。

---

如果你希望把该仓库作为“团队默认 VCO 基线”，建议将 `vibe-routing-stability-gate.ps1 -Strict` 纳入 CI 的必过步骤。
