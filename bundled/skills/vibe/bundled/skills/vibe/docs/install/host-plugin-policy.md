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
- `opencode`

其他代理当前不应被描述成“已有支持的安装路径”。

## 总体原则

- 先把仓库分发内容安装好
- 再按真实需求补宿主侧配置
- 没有被仓库稳定、公开、可验证接管的能力，不要写成默认安装要求
- OpenClaw 默认目标根目录必须写清：`OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`
- OpenClaw 更细的安装路径说明放在宿主专页
- OpenCode 默认目标根目录必须写清：`OPENCODE_HOME` 或 `~/.vibeskills/targets/opencode`
- OpenCode 必须写清它走 direct install/check，不接管真实 `opencode.json`
- 如需查看更细的宿主契约和 proof 信息，继续看宿主专页或 `dist/*` / `adapters/*`

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

- 提供支持的安装与使用路径
- 默认目标根目录是 `WINDSURF_HOME` 或 `~/.vibeskills/targets/windsurf`
- 当前仓库只负责共享安装内容，以及按需物化 `mcp_config.json` 和 `global_workflows/`
- Windsurf 宿主本地设置仍按 Windsurf 自身方式管理

## OpenClaw

- 提供支持的安装与使用路径
- 默认目标根目录是 `OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`
- 更细的 attach / copy / bundle 路径放在 [`openclaw-path.md`](./openclaw-path.md)
- 宿主侧本地配置仍按 OpenClaw 自身方式管理

## OpenCode

- 提供支持的安装与使用路径
- 默认目标根目录是 `OPENCODE_HOME` 或 `~/.vibeskills/targets/opencode`
- direct install/check 会写入 skills、command/agent wrappers 与 `opencode.json.example`
- 真实 `opencode.json`、provider 凭据、plugin 安装与 MCP 信任仍按宿主自身方式管理

## 推荐的社区表述

- 当前版本支持 `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode`
- `codex` 是默认推荐路径
- `claude-code` / `cursor` 提供支持的安装与使用路径
- `windsurf` 提供支持的安装与使用路径
- `openclaw` 提供支持的安装与使用路径，默认目标根目录是 `OPENCLAW_HOME` 或 `~/.vibeskills/targets/openclaw`
- `opencode` 提供支持的安装与使用路径，默认目标根目录是 `OPENCODE_HOME` 或 `~/.vibeskills/targets/opencode`
- `opencode` 走 direct install/check，且不接管真实 `opencode.json`
- hooks 在当前公开支持面里统一冻结；这不是用户安装失败
- provider 的 `url` / `apikey` / `model` 由用户在本地配置，不要要求用户贴到聊天里
