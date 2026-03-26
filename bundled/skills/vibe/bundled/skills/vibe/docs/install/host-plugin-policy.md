# 宿主插件与宿主配置策略

这份文档只回答三件事：

- 哪些宿主在当前公开支持面内
- 仓库当前自动处理什么
- 哪些能力仍必须由宿主侧本地完成

## 当前公开支持面

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`

其他代理当前不应被描述成“已有官方安装闭环”。

## 总体原则

- 先把 repo-governed payload 安装好
- 再按真实需求补宿主侧配置
- 没有被仓库稳定、公开、可验证接管的能力，不要写成默认安装要求
- OpenClaw 口径必须写清：`preview` / `runtime-core-preview` / `runtime-core`
- OpenClaw 默认根目录必须写清：`OPENCLAW_HOME` 或 `~/.openclaw`
- OpenClaw 安装路径必须写清：attach / copy / bundle 三路径

## Codex

- 当前最完整路径
- 围绕本地 settings、MCP 和可选 CLI 做建议
- hook 当前冻结；这不是安装失败

## Claude Code

- 提供支持的安装与使用路径
- 不靠“补一堆宿主插件”来完成接入
- 不覆盖真实 `~/.claude/settings.json`
- hook 当前冻结；这不是安装失败

## Cursor

- 提供支持的安装与使用路径
- 不覆盖真实 `~/.cursor/settings.json`
- Cursor 宿主原生插件、设置与扩展面仍按 Cursor 自身方式管理
- hook 当前冻结；这不是安装失败

## Windsurf

- 提供支持的安装与使用路径，且已接入 runtime adapter
- 默认根目录是 `~/.codeium/windsurf`
- repo 当前只负责 shared runtime payload，以及按需物化 `mcp_config.json` 和 `global_workflows/`
- Windsurf 宿主本地设置仍按 Windsurf 自身方式管理

## OpenClaw

- 提供支持的安装与使用路径，但当前只到 `preview`（`runtime-core-preview`）
- install/check 走 `runtime-core` 模式，默认目标根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`
- attach / copy / bundle 三路径都围绕 runtime-core payload 的安装、校验与分发
- 宿主侧本地配置仍按 OpenClaw 自身方式管理

## 推荐的社区表述

- 当前版本支持 `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`
- `codex` 走 governed 路径
- `claude-code` / `cursor` 提供支持的安装与使用路径
- `windsurf` 提供支持的安装与使用路径，且已接入 runtime adapter
- `openclaw` 按 `preview` / `runtime-core-preview` / `runtime-core` 描述
- `openclaw` 默认根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`，并明确 attach / copy / bundle 三路径
- hooks 在当前公开支持面里统一冻结；这不是用户安装失败
- provider 的 `url` / `apikey` / `model` 由用户在本地配置，不要要求用户贴到聊天里
