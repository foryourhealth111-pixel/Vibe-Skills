# Quick Start

[English](./quick-start.en.md)

第一次来到这个仓库，不需要先读完所有文档。

你可以先把 VibeSkills 理解成一个给 AI Agent 用的 **Super Skill Harness**：

> 你给目标，`vibe` 接管推进节奏：先弄清需求，再拆阶段，自动调用合适的专家 Skills，推动测试和验证，并把关键上下文留下来。

它不是一串让用户自己挑的工具菜单。它更像一个即插即用的工作流包，让支持 Skills 的 AI Agent 更容易开始、更少失控、更适合做跨阶段任务。

## 1. 三分钟知道它解决什么

VibeSkills 重点解决五件事：

| 你遇到的问题 | VibeSkills 做什么 |
|:---|:---|
| Skills 太多，不知道该叫哪个 | harness 按任务和阶段自动编排专家 Skills |
| AI 容易跳过需求、计划或测试 | `vibe` 把任务推进成受管阶段 |
| 用户总要手动提醒“先规划”“去验证” | 用户只给目标，流程控制交给 harness |
| 长任务换会话后上下文丢失 | 需求、计划、决策和证据会结构化保存 |
| 新领域 Skills 接入成本高 | Skills 包是核心封装，未来任意领域 Skills 都可以接入同一套流程 |

如果你只记一句话：

> **VibeSkills 的核心创新，是把“专家 Skills + 自动编排 + 测试验证 + 跨会话记忆”封装成一个通用、好安装、好上手的 Super Skill。**

## 2. 最快开始使用

打开安装入口：

- [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)

按页面选择三件事：

1. 选择宿主：`codex`、`claude-code`、`cursor`、`windsurf`、`openclaw` 或 `opencode`
2. 选择动作：第一次安装选 `install`，已经装过选 `update`
3. 选择版本：普通用户推荐 `full`，只想先装轻量框架时选 `minimal`

然后把对应提示词复制到你要安装 VibeSkills 的 AI 客户端里，让它执行安装和检查。

安装完成后，从宿主的 Skills 入口调用：

| 宿主 | 常见调用方式 |
|:---|:---|
| Codex | 在请求里附上 `$vibe` |
| Claude Code | 在请求里附上 `/vibe` |
| OpenCode | 使用 `/vibe` 或宿主支持的 Skills 调用方式 |
| Cursor / Windsurf / OpenClaw | 参考对应宿主的 Skills 入口说明 |

更新时保留：

- `vibe-upgrade`

## 3. 当前公开入口

当前公开、宿主可见的入口只有：

- `vibe`
- `vibe-upgrade`

`vibe` 是主入口。它会在需求、计划和执行边界停下来，等到明确确认后再继续推进。

`vibe-upgrade` 是受管升级入口，用来更新当前宿主安装。

旧阶段专用入口和旧 CLI 入口已经退出公开的宿主可见入口，不应再宣传或安装。

如果你想提高执行强度，只使用公开的轻量覆盖：

- `--l`
- `--xl`

旧的阶段 ID 可能仍保留在运行时元数据里，用于兼容和连续性；但它们不是用户应该调用的 commands / skills。

## 4. 什么时候继续看更多文档

按你的目的选，不用从头读：

| 你想做什么 | 看这里 |
|:---|:---|
| 想看项目完整介绍 | [`../README.zh.md`](../README.zh.md) |
| 想安装或更新 | [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md) |
| 想看完整命令参考 | [`install/recommended-full-path.md`](./install/recommended-full-path.md) |
| 不确定宿主根目录 | [`cold-start-install-paths.md`](./cold-start-install-paths.md) |
| 使用 OpenCode | [`install/opencode-path.md`](./install/opencode-path.md) |
| 使用 OpenClaw | [`install/openclaw-path.md`](./install/openclaw-path.md) |
| 想手动/离线安装 | [`install/manual-copy-install.md`](./install/manual-copy-install.md) |
| 想接入自定义 Skills | [`install/custom-workflow-onboarding.md`](./install/custom-workflow-onboarding.md) |
| 想理解项目为什么存在 | [`manifesto.md`](./manifesto.md) |

## 5. 几个容易混淆的点

- `$vibe` 或 `/vibe` 只表示进入 governed runtime，不等于 MCP 已经完成配置。
- 安装报告应该分开说明 `installed locally`、`vibe host-ready`、`mcp native auto-provision attempted`、每个 MCP 的 `host-visible readiness` 和 `online-ready`。
- VibeSkills 是 Skills 格式运行时，不是让你在终端里直接运行的独立 CLI。
- `full` 是普通用户默认推荐版本；`minimal` 适合明确只想要轻量治理框架的人。

## 推荐阅读顺序

如果你只想走最短路径：

1. [`../README.zh.md`](../README.zh.md)
2. [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)
3. 用一个小任务试试 `vibe`

从一个简单请求开始就好，比如：

> 帮我把这个需求先澄清并拆成计划 `$vibe`

你会更快感受到它和普通 Skills 列表的区别：用户不用一直做调度员，AI 会在 harness 下更有节奏地推进任务。
