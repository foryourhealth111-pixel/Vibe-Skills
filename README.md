[English](./README.en.md)

# VibeSkills

> 终结 skills 混乱状态的 skills 基座。
> 让通用大模型从“会调用技能”，进化为“能稳定完成任务”。

VibeSkills 是一个面向通用大模型的开源 skills 生态。

它以 Vibe Code Orchestrator `VCO` 为控制面，不只是收集 skills，而是通过智能路由、框架治理、质量门禁、多技能组合与多智能体协作，把离散能力组织成一个更安全、更规范、更稳定、更可靠的执行外骨骼。

我们想做的，不是另一个 skills 仓库。
我们想做的是一个通用的智能大模型 skills 基座。

## 为什么要做 VibeSkills

今天的问题，不是没有 skills。

真正的问题是：

- skills 太离散，不知道该用哪个
- skills 太不透明，不知道是否安全、是否稳定、是否值得信任
- skills 很难组合，复杂任务经常只能靠手工 glue
- 自己写 skills 缺少规范，生态越长越乱
- 大模型即使很强，也缺少一个能够长期运行、持续治理的能力框架

VibeSkills 想改变的，不是某一个 skill 的表现。
我们想改变的是整个 skills 生态的使用方式。

## 我们的主张

未来不是更多 skills。
未来是对 skills 的治理能力。

VibeSkills 想成为一个通用的智能大模型 skills 基座：

- 让用户不必记忆 skills
- 让模型自己做更好的选择
- 让多个 skills 可以被智能组合
- 让复杂任务拥有清晰的边界、协议和质量门禁
- 让 agent 从单体执行进化到 team 协同

我们不是在做另一个 prompt 集合。
我们不是在做另一个工具清单。
我们是在为通用智能建立一层真正可治理、可组合、可演进的能力基础设施。

## 它和普通 skills / agent 框架有什么不同

很多 systems 停留在：

- 能不能接更多工具
- 能不能调用更多 skills
- 能不能把 prompt 写得更像 agent

VibeSkills 更关心的是：

- 能不能智能路由到正确的 skill 与执行流
- 能不能在执行前做治理，而不是在失败后补救
- 能不能把多个 skills 组合成稳定工作流
- 能不能在复杂任务中进行多智能体 team 协作
- 能不能在不同场景下保持一致的质量、边界与可靠性

不是“更多功能”。
而是“更可靠的执行系统”。

## 这套生态里有什么

这个仓库围绕 `VCO` 这一个控制面展开，核心包含：

- `VCO` 核心编排层：任务分级、路由、执行流控制
- Pack Router：按任务语义、规则和阈值选择最合适的 skills
- Governance Layers：质量债务、Prompt 资产、Memory、ML 生命周期、System Design、CUDA 等后置治理层
- Verification Gates：对路由稳定性、治理策略、离线闭包和回归矩阵做持续验证
- Bundled Skills Mirrors：为离线、兼容与可重复安装提供基线
- Optional Integrations：AIOS-Core、OpenSpec、GSD-Lite、prompts.chat、GitNexus、claude-flow、ralph-loop 等增强能力

VibeSkills 的目标不是把这些组件堆在一起。
而是让它们在一个统一治理面下协同工作。

## Manifesto

如果你想先理解这套生态的理念、反对什么、建设什么，以及我们对技术和开源做出的承诺，请先读：

- [`docs/manifesto.md`](./docs/manifesto.md)

## 先来用

如果你是：

- 重度使用大模型做开发、研究、分析、自动化的人
- 想让 AI 从“偶尔能做”变成“稳定可用”的团队负责人
- 正在被 skills 太多、太乱、太难组合困扰的用户

你可以直接从这里开始。

### 快速安装

```powershell
pwsh -File .\install.ps1 -Profile full -StrictOffline
pwsh -File .\check.ps1 -Profile full -Deep
```

### 路由与治理验证

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

### 继续深入

- [`SKILL.md`](./SKILL.md)：VCO 主协议与分级执行模型
- [`docs/README.md`](./docs/README.md)：治理正文、plans、releases 与 integration spine 总入口
- [`config/index.md`](./config/index.md)：machine-readable routing / cleanliness / packaging / rollout 配置入口
- [`references/index.md`](./references/index.md)：contracts / registries / matrices / ledgers / overlays 导航入口
- [`scripts/README.md`](./scripts/README.md)：router / governance / verify / overlay / setup surfaces 总入口

## 为什么值得 Star

如果你相信：

- 通用大模型需要一套真正可治理的 skills 基础设施
- AI 执行系统不能一直停留在零散脚本和 prompt glue code 阶段
- 开源社区应该共同定义下一代 skills 生态的标准、边界与协作方式

那么这个项目值得你关注。

Star 它，不只是收藏一个仓库。
而是加入一个方向：
把 skills 从零散插件，推进成通用智能的可靠基座。

## 欢迎加入

### 如果你是用户

- 来使用
- 来提 issue 和真实场景
- 来告诉我们哪里还不稳、哪里还不够智能
- 来推动这个系统更贴近真实工作流

### 如果你是开发者 / agent 框架玩家

- 基于真实用户需求贡献 skills、路由策略、治理规则与验证脚本
- 帮我们减少生态里的重复建设、隐式冲突与不可控执行
- 和我们一起把 skills 从“能用”推进到“可靠、规范、稳定、可组合”

## 项目入口

- [`docs/manifesto.md`](./docs/manifesto.md)：VibeSkills 对外宣言与技术承诺
- [`docs/ecosystem-absorption-dedup-governance.md`](./docs/ecosystem-absorption-dedup-governance.md)：VibeSkills 生态吸收、去冗余与分层治理总纲
- [`docs/observability-consistency-governance.md`](./docs/observability-consistency-governance.md)：可观测性、一致性与手动回退治理
- [`docs/memory-governance-integration.md`](./docs/memory-governance-integration.md)：记忆边界与角色分工
- [`docs/prompt-overlay-integration.md`](./docs/prompt-overlay-integration.md)：Prompt 资产增强层接入方式
- [`docs/data-scale-overlay-integration.md`](./docs/data-scale-overlay-integration.md)：大数据规模 overlay 的接入方式
- [`docs/system-design-overlay-integration.md`](./docs/system-design-overlay-integration.md)：系统设计覆盖增强层
- [`docs/pilot-scenarios-and-eval.md`](./docs/pilot-scenarios-and-eval.md)：试点场景与评估计划

## 许可证

- 本仓库根许可证为 [`Apache-2.0`](./LICENSE)
- 第三方边界与说明见 [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md)
- 仓库公告见 [`NOTICE`](./NOTICE)

## 一句话总结

VibeSkills 想做的，是让通用大模型第一次真正拥有一套可治理、可组合、可验证、可持续演进的 skills 基座。

如果你也相信这是下一代 AI 基础设施应该走的方向，欢迎来用，欢迎 Star，欢迎一起把它做出来。
