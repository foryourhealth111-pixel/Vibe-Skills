# 安装规则说明

本文档定义安装助手在公开安装与升级流程里必须遵守的 truth-first 规则。

## 规则 1：先确认宿主

在用户明确回答目标宿主前，不要开始执行安装或更新命令。

当前公开支持的宿主只有：

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

## 规则 2：再确认版本

在用户明确回答公开版本前，不要开始执行安装或更新命令。

当前公开版本只有：

- `全量版本 + 可自定义添加治理`
- `仅核心框架 + 可自定义添加治理`

## 规则 3：拒绝未支持宿主

如果用户回答的宿主不在当前支持面内，必须直接说明当前版本暂不支持该宿主，不要伪装安装成功。

## 规则 4：拒绝未支持版本名

如果用户回答的版本名不在公开版本面内，必须直接说明当前公开安装说明暂不支持该版本名。

## 规则 5：先判定系统，再选命令

- Linux / macOS 使用 `bash`
- Windows 使用 `pwsh`

## 规则 6：公开版本名必须映射到真实 profile

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

不要再把框架版本伪装成 `framework-only`，因为当前脚本真实接受的是 `minimal` / `full`。

## 规则 7：Codex 按默认推荐路径描述

如果用户选择 `codex`：

- 运行 `--host codex`
- 明确说明这是当前默认推荐路径
- hook 当前因兼容性问题被冻结；这不是安装失败
- 如需 AI 治理 advice 的常见 OpenAI-compatible 在线路径，去本地 `~/.codex/settings.json` 的 `env` 或本地环境变量配置：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`
- 内置 AI 治理层当前只支持 OpenAI-compatible 接入
- 不能把宿主基础在线能力偷换成“治理 AI online readiness 已完成”

## 规则 8：Claude Code 要按“支持的安装与使用路径”口径描述

如果用户选择 `claude-code`：

- 运行 `--host claude-code`
- 明确说明当前提供支持的安装与使用路径
- hook 当前冻结；这不是安装失败
- 不要声称安装器会额外写入 Claude Code 的宿主 settings 文件
- 引导用户自己补 `~/.claude/settings.json` 的 `env`

## 规则 9：Cursor 也按“支持的安装与使用路径”口径描述

如果用户选择 `cursor`：

- 运行 `--host cursor`
- 明确说明当前提供支持的安装与使用路径
- 当前不接管 Cursor 的真实 settings 与宿主原生扩展面
- 引导用户自己检查和维护 `~/.cursor/settings.json`

## 规则 10：Windsurf 按“支持的安装与使用路径”口径描述

如果用户选择 `windsurf`：

- 运行 `--host windsurf`
- 明确说明当前提供支持的安装与使用路径
- 默认宿主根目录是 `~/.codeium/windsurf`
- 当前仓库只负责共享安装内容，以及按需物化 `mcp_config.json` 与 `global_workflows/`
- Windsurf 宿主本地设置仍由用户在宿主侧完成

## 规则 11：OpenClaw 按“支持的安装与使用路径”口径描述

如果用户选择 `openclaw`：

- 运行 `--host openclaw`
- 明确说明当前提供支持的安装与使用路径
- 默认目标根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`
- 如果用户需要 attach / copy / bundle 等更细路径，继续看 [`openclaw-path.md`](./openclaw-path.md)
- 宿主侧本地配置仍按 OpenClaw 方式完成

## 规则 12：OpenCode 按“支持的安装与使用路径”口径描述

如果用户选择 `opencode`：

- 运行 `--host opencode`
- 明确说明当前提供支持的安装与使用路径
- 默认目标根目录是 `OPENCODE_HOME`，否则是 `~/.config/opencode`
- direct install/check 会写入 skills、command/agent wrappers 与 `opencode.json.example`
- 真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任仍由宿主侧本地完成

## 规则 13：AI 治理在线配置要优先说真实推荐键名

如需解释 AI 治理 advice 的在线配置，优先使用：

- OpenAI-compatible：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`


## 规则 14：不要要求用户把密钥贴到聊天里

对六个支持宿主，都不要要求用户把密钥、URL 或 model 直接粘贴到聊天里；只引导用户去本地 settings 或本地环境变量配置。

## 规则 15：区分“本地安装完成”和“在线能力就绪”

如果本地 provider 字段没有配置好，就不能把环境描述成“online ready”。

## 规则 16：输出安装或更新结果时必须说清楚

结果摘要至少应包含：

- 目标宿主
- 公开版本
- 实际映射的 profile
- 实际执行的命令
- 已完成的部分
- 仍需用户手动处理的部分

## 规则 17：框架版本不是开箱即用全量体验

如果用户选择 `仅核心框架 + 可自定义添加治理` / `minimal`，必须额外提醒：

- 这表示先安装治理框架底座
- 不等于默认 workflow core 已齐备
- 如果后续要接入自己的 workflow，请继续走 [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
