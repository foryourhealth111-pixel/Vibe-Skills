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

## 当前推荐版本

- 当前对外推荐版本：[`v2.3.40`](./docs/releases/v2.3.40.md)
- 面向普通用户的一键安装发布文案：[`docs/install/one-click-install-release-copy.md`](./docs/install/one-click-install-release-copy.md)
- 面向操作者的标准推荐安装路径：[`docs/install/recommended-full-path.md`](./docs/install/recommended-full-path.md)

## 先来用

如果你是：

- 重度使用大模型做开发、研究、分析、自动化的人
- 想让 AI 从“偶尔能做”变成“稳定可用”的团队负责人
- 正在被 skills 太多、太乱、太难组合困扰的用户

你可以直接从这里开始。

### 安装指南

#### 标准推荐安装，先记这一条

对大多数用户来说，**标准推荐安装** 就是默认入口。

它的含义不是“第一次就把所有增强面全部装满”，而是：

- 先把 repo-governed surfaces 尽量闭环
- 允许结果诚实落在 `manual_actions_pending`
- 再按真实缺口逐层增强，而不是第一天就把宿主插件、MCP、密钥全部堆上去

最适合这条路的人：

- 想稳定把 VibeSkills 用起来的重度 AI 用户
- 想先验证这套治理面是否值得团队推广的负责人
- 不想第一天就背负大量宿主冲突和排障成本的人

先看这两份入口文档：

- [`docs/install/recommended-full-path.md`](./docs/install/recommended-full-path.md)
- [`docs/cold-start-install-paths.md`](./docs/cold-start-install-paths.md)

#### 这里说的“满血版”是什么

在当前默认推荐链路里，这个“满血版”会把三层语义明确拆开：

- `scrapling`：默认本地 runtime / MCP 面，属于 `full` profile 的开箱链路
- `Cognee`：默认长程图记忆增强面，不取代 `state_store` 的 session truth 身份
- `Composio / Activepieces`：默认预接线的外部操作能力接入面，但必须 setup 后才能使用

这里的“满血版”不是“仓库 clone 下来就算完成”，而是：

- 仓库内随附的 skills、governance 配置、脚本和镜像内容都已经落到本地
- 当前 MCP profile 已经物化为 active 配置
- 安装后已经跑过 deep health check
- 仍然需要宿主侧手工 provision 的插件、MCP、密钥被明确列出来，而不是被静默跳过

#### 我们承诺的“满血版”，不是伪 fully ready

VibeSkills 的“满血版”承诺是治理完成，不是神奇自动化。

这意味着：

- 仓库负责交付的 payload、脚本、镜像、profile 和 doctor gates，会尽可能一次性安装、同步并验证完成
- 宿主机自己必须负责的 host plugins、外部 MCP、provider secrets，会被明确暴露为前置条件或后续动作
- 如果这些宿主侧条件还没补齐，最终状态应该是 `manual_actions_pending`，而不是假装一切都 ready

我们不把“没有报错”包装成“全生态已经就绪”。
我们把“哪些已经闭环、哪些仍需人工补齐”讲清楚，这才是一个可治理、可交付、可长期维护的满血版。

#### 满血安装前置条件

- `git`
- `node` 和 `npm`
- `python3` 或 `python`
- Windows：`powershell` 或 `pwsh`
- Linux / macOS：`bash`
- 推荐 Linux / macOS 额外安装：`pwsh`（PowerShell 7），这样可以进入当前最强的受治理验证路径

如果 Linux 具备 `pwsh`，当前可以进入 Linux 最强验证路径，但对外口径仍然只是 `supported-with-constraints`，而不是 `full-authoritative`。
如果 Linux / macOS 没有 `pwsh`，依然可以安装完整仓库内容并物化 MCP active profile，但 PowerShell 侧 doctor gates 会退化为 shell warning。

#### Operator Notes

- 启用外部 CLI 安装时，最慢的步骤通常是 `claude-flow` 的 `npm` 安装；跑几分钟属于正常预期。
- `npm` 在这个阶段出现的 deprecated warnings 属于 advisory signal，只有当命令 `exit non-zero` 时才算安装失败。
- 如果目标 `settings.json` 已经写入 `OPENAI_API_KEY` 或 `ARK_API_KEY`，bootstrap 会复用现有值，而不再误报 “not provided”。

#### Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1
```

#### Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
```

可选示例：

```bash
# 安装到自定义 Codex 根目录
bash ./scripts/bootstrap/one-shot-setup.sh --target-root "$HOME/.codex"

# 安装时强制执行 offline closure gate
bash ./scripts/bootstrap/one-shot-setup.sh --strict-offline
```

这两个 one-shot bootstrap 都会完成同一套治理安装动作：

- 安装 shipped runtime payload 到 `~/.codex`
- 在支持的平台上安装可自动安装的外部 CLI，其中标准推荐安装会尝试把 `scrapling` 收敛进默认链路
- 在支持的平台上安装可自动安装的外部 CLI
- 根据选定 profile 物化 `mcp/servers.active.json`
- 运行 deep readiness check

#### 标准推荐安装，完成到什么程度才算合理

对多数用户，标准推荐安装完成的合理定义是：

- one-shot bootstrap 跑通
- deep doctor 跑通
- shipped payload、bundled mirrors、active MCP profile、doctor / coherence 路径已经闭环
- 剩余缺口被明确列出，而不是被静默吞掉

因此：

- `fully_ready` 是最好结果
- `manual_actions_pending` 对标准推荐安装来说也是**正常且可接受**的结果
- 真正不应接受的是 `core_install_incomplete`

#### 重新执行 deep doctor

Windows：

```powershell
pwsh -File .\check.ps1 -Profile full -Deep
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep
```

Linux / macOS：

```bash
bash ./check.sh --profile full --deep
```

升级提示：

- 仅仅拉取仓库并不会自动刷新 `${TARGET_ROOT}/skills/vibe`
- 仓库版本升级后，请先对同一个 target root 重新执行 `install.ps1` / `install.sh` 或对应 one-shot bootstrap，再去判断 freshness 失败是不是单纯的 receipt 问题

#### 想进入真正的满血 MCP 体验，还需要手工补齐这些项

这里还要额外看清三类对象：

- `scrapling`：已经进入标准推荐安装的默认本地能力面
- `Cognee`：应该被看作默认长程图记忆 enhancement lane，而不是第二个 session truth
- `Composio / Activepieces`：属于预接线但仍需 setup 的 external action surfaces

这些部分不会被仓库伪装成“自动完成”，必须在宿主环境里自己 provision：

- 宿主插件面：当前 doctor / manifest 仍会跟踪 `superpowers`、`everything-claude-code`、`claude-code-settings`、`hookify`、`ralph-loop`
- plugin-backed MCP surfaces：`github`、`context7`、`serena`
- 需要在线能力时的 provider secrets：`OPENAI_API_KEY`，以及你实际使用的其他 provider keys

但默认策略不是“第一次就把这 5 个宿主插件全装上”。

我建议：

- 第一次安装：先不把这 5 个插件都当成前置必装项，先跑 one-shot + deep doctor
- 作者级 / 参考 Windows Codex 环境：优先补 `superpowers`、`hookify`
- `everything-claude-code`、`claude-code-settings`、`ralph-loop`：只有在 doctor 仍然指向明确缺口时再补

完整决策与安装说明见：

- [`docs/install/host-plugin-policy.md`](./docs/install/host-plugin-policy.md)

如果这些还没有 provision，doctor 的正确结果应该是 `manual_actions_pending`，而不是虚假的“everything ready”。

#### 如果你想进一步增强，按这条顺序加

建议把顺序理解成：

1. 先补 provider secrets
2. 先确认 `scrapling` 可调用，把它当作默认 full-profile scraping surface
3. 把 `Cognee` 放在长程增强面，不让它接管 `state_store`
4. 再补默认推荐的宿主插件和 plugin-backed MCP surfaces
5. `Composio / Activepieces` 仅在你确实需要外部操作能力时再做 setup，并保持 confirm-gated
6. 最后再补其余宿主插件与可选 CLI 增强

不要一开始把所有增强面都堆上去。更稳的顺序是：

1. 先补 provider secrets
   例如 `OPENAI_API_KEY`，先把在线能力跑通。
2. 再补默认推荐的宿主插件
   优先 `superpowers`、`hookify`。
3. 再补 plugin-backed MCP surfaces
   例如 `github`、`context7`、`serena`。
4. 只有 doctor 仍然指向明确缺口时，再补其余宿主插件
   例如 `everything-claude-code`、`claude-code-settings`、`ralph-loop`。
5. 最后再补可选 CLI / 工具链增强
   例如 `claude-flow`、`xan`、`ivy`。

增强路线详见：

- [`docs/install/recommended-full-path.md`](./docs/install/recommended-full-path.md)
- [`docs/install/host-plugin-policy.md`](./docs/install/host-plugin-policy.md)

#### 不知道该走哪条安装路径

如果你是第一次接触这个仓库，不要直接猜。

先看这份冷启动演练文档：

- [`docs/cold-start-install-paths.md`](./docs/cold-start-install-paths.md)：最小可用 / 推荐满血 / 企业治理 三条安装路径、适用人群、命令、验收方式与 stop rules
- [`docs/install/full-featured-install-prompts.md`](./docs/install/full-featured-install-prompts.md)：可直接复制给 AI 助手的一键安装提示词，覆盖 Windows / Linux

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

## 贡献入口

如果你准备参与开发，不要直接猜哪些文件能改。

先从这里进入：

- [`CONTRIBUTING.md`](./CONTRIBUTING.md)：贡献流程、禁止随意修改的区域、proof 预期
- [`docs/developer-change-governance.md`](./docs/developer-change-governance.md)：开发者变更治理规则
- [`references/contributor-zone-decision-table.md`](./references/contributor-zone-decision-table.md)：可改区 / 受保护区决策表
- [`references/change-proof-matrix.md`](./references/change-proof-matrix.md)：不同类型改动需要补哪些验证证据

默认的 contributor-safe 变更面是增量治理层，例如：

- `docs/**`
- `references/**`（fixture 除外）
- `scripts/governance/**`
- `scripts/verify/**`
- `templates/**`

不要在没有完成分区判断与验证设计前，随意修改这些高风险面：

- `install.*`
- `check.*`
- `protocols/**`
- `scripts/router/**`
- `bundled/**`
- 已跟踪的 `outputs/**`
- `third_party/**`
- `vendor/**`

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
