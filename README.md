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

- `bundled/skills/*`：Codex 兼容技能镜像。
- `bundled/superpowers-skills/*`：规划、调试、代码评审等工作流增强技能。
- 可选外部增强（按需安装）：`SuperClaude_Framework` 命令集、`claude-flow`。

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
| `scripts/router/resolve-pack-route.ps1` | 路由核心执行器 |
| `scripts/verify/*.ps1` | 回归矩阵、审计、稳定性门禁 |
| `docs/skills-overlap-matrix.md` | 技能重叠分类与路由建议 |
| `bundled/skills/vibe/config/*` | 与主配置镜像同步的 bundled 配置 |

## 搭建与安装流程

### 前置要求

- Windows PowerShell 7+（或兼容 PowerShell）
- `git`
- 可选：`npm`（安装外部增强时使用）

### 快速安装（Codex 本地）

```powershell
pwsh -File .\install.ps1 -Profile full
pwsh -File .\check.ps1 -Profile full
```

### 安装可选外部增强

```powershell
pwsh -File .\install.ps1 -Profile full -InstallExternal
```

说明：当前安装器为 Codex-only 主模式。`plugins-manifest.codex.json` 中的插件安装命令不会被自动执行，会输出手动安装提示，避免跨运行时误装。

### 指定安装目录

```powershell
pwsh -File .\install.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex"
```

## 日常使用

### 1. 路由验证（建议每次改配置后执行）

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-pack-regression-matrix.ps1
pwsh -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -WriteArtifacts
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

### 2. 生态同步（从本地兼容源更新 bundled）

```powershell
pwsh -File .\scripts\bootstrap\sync-local-compat.ps1
```

## 使用到的上游项目与方法论

| 项目 / 来源 | 用途 |
|---|---|
| `SynkraAI/aios-core` | 引入 Agentic Agile 角色化协作（PM/PO/QA/DevOps 等） |
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
- 外部语料（如 `system-prompts-and-models-of-ai-tools`）默认作为“研究输入”处理，不应将原始语料直接并入核心编排协议。
- 若你在 `third_party/` 本地镜像外部仓库并进行再分发，请自行确保满足对应上游许可证义务。

## 当前版本更新重点

- 完成 AIOS-Core Pack 级集成与默认任务技能映射。
- 完成路由规则层升级（`skill-routing-rules` + `defaults_by_task`）。
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
