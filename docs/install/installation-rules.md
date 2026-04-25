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

补充约束：

- Linux / macOS 的 shell 入口现在按 **macOS 自带 Bash 3.2 可运行** 这一基线维护，不能再偷偷引入 `mapfile` 这类 Bash 4+ 专属能力
- 这些 shell 入口在进入 adapter / doctor / bootstrap Python helper 之前，会先检查 **Python 3.10+**
- 如果用户在 macOS 的 `zsh` 里运行命令，真正决定成败的不是 `zsh` 本身，而是被调用到的 `bash` / `python3` 可执行文件版本

## 规则 6：公开版本名必须映射到真实 profile

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

不要再把框架版本伪装成 `framework-only`，因为当前脚本真实接受的是 `minimal` / `full`。

## 规则 6.5：把 bootstrap 先决条件和可选外部 runtime 区分清楚

- `install.sh` / `check.sh` / `scripts/bootstrap/one-shot-setup.sh` 的基础 Python 门槛是仓库自身入口要求，当前按 **Python 3.10+** 处理
- `ruc-nlpir` 这类外部 upstream/runtime 需要单独 venv，它不是公开安装器本体的同义词
- 不要把 “外部 runtime 可能偏好 3.11” 说成 “整个仓库安装器硬要求 3.11”

## 规则 7：Codex 按默认推荐路径描述

如果用户选择 `codex`：

- 运行 `--host codex`
- 在 Linux / macOS 上默认使用 `CODEX_HOME="$HOME/.codex"`，在 Windows 上默认把 `CODEX_HOME` 设为真实宿主根目录 `%USERPROFILE%\\.codex`
- 明确说明这是当前最完整的 governed 路径；如果目标是安装后就能被当前 Codex 直接发现 `$vibe`，默认必须落到真实 `~/.codex`
- `~/.vibeskills/targets/codex` 只能在用户显式要求隔离安装，或 Codex 已经明确指向该目录时使用
- hook 当前因兼容性问题被冻结；这不是安装失败
- 暂时不要在公开安装流程里引导用户配置内置在线增强能力的 provider、凭据、URL 或模型
- 不能把宿主基础在线能力偷换成“治理 AI online readiness 已完成”

## 规则 8：Claude Code 要按“支持的安装与使用路径”口径描述

如果用户选择 `claude-code`：

- 运行 `--host claude-code`
- 明确说明当前提供支持的安装与使用路径
- 在 Linux / macOS 上默认使用 `CLAUDE_HOME="$HOME/.claude"`，在 Windows 上默认把 `CLAUDE_HOME` 设为真实宿主根目录 `%USERPROFILE%\\.claude`
- 明确说明安装器会在保留现有 `~/.claude/settings.json` 内容的前提下，补入受约束的 `vibeskills` 节点
- 不要宣传成 official runtime、Codex 满血等价或跨平台 proof 已闭环
- 引导用户继续把 `env`、plugin enablement、MCP 注册和 provider credentials 放在 Claude 宿主侧本地维护

## 规则 9：Cursor 也按“支持的安装与使用路径”口径描述

如果用户选择 `cursor`：

- 运行 `--host cursor`
- 明确说明当前提供支持的安装与使用路径
- 在 Linux / macOS 上默认使用 `CURSOR_HOME="$HOME/.cursor"`，在 Windows 上默认把 `CURSOR_HOME` 设为真实宿主根目录 `%USERPROFILE%\\.cursor`
- 当前不接管 Cursor 的真实 settings 与宿主原生扩展面
- 引导用户自己检查和维护 `~/.cursor/settings.json`

## 规则 10：Windsurf 按“支持的安装与使用路径”口径描述

如果用户选择 `windsurf`：

- 运行 `--host windsurf`
- 明确说明当前提供支持的安装与使用路径
- 默认目标根目录是 `WINDSURF_HOME`，否则是实际宿主根目录 `~/.codeium/windsurf`
- 当前仓库只负责共享安装内容，以及 `.vibeskills/host-settings.json` / `.vibeskills/host-closure.json` 这类 sidecar 状态
- Windsurf 宿主本地设置仍由用户在宿主侧完成

## 规则 11：OpenClaw 按“支持的安装与使用路径”口径描述

如果用户选择 `openclaw`：

- 运行 `--host openclaw`
- 明确说明当前提供支持的安装与使用路径
- 默认目标根目录是 `OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw`
- 如果用户需要 attach / copy / bundle 等更细路径，继续看 [`openclaw-path.md`](./openclaw-path.md)
- 宿主侧本地配置仍按 OpenClaw 方式完成

## 规则 12：OpenCode 按“支持的安装与使用路径”口径描述

如果用户选择 `opencode`：

- 运行 `--host opencode`
- 明确说明当前提供支持的安装与使用路径
- 默认目标根目录是 `OPENCODE_HOME`，否则是实际宿主根目录 `~/.config/opencode`
- 真实宿主配置目录就是 `~/.config/opencode`
- direct install/check 会写入 skills、`.vibeskills/*` sidecar 与 `opencode.json.example`
- 真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任仍由宿主侧本地完成

## 规则 13：暂不公开引导内置在线增强配置

公开安装、更新、手动复制和提示词安装都暂时不向用户说明内置在线增强能力的配置细节。安装助手必须遵守：

- 不向用户推荐这条路径的 provider、凭据、URL 或模型配置
- 不把这条路径的缺失描述成基础安装失败
- 不把宿主基础在线能力偷换成在线增强能力已就绪
- 如果相关能力没有通过公开路径配置好，只能把 `online-ready` 分开报告为未就绪或未验证


## 规则 14：不要要求用户把密钥贴到聊天里

对六个支持宿主，都不要要求用户把密钥、URL 或 model 直接粘贴到聊天里。公开安装当前也不要引导用户为内置在线增强能力补这些配置。

## 规则 15：MCP 默认必须以宿主原生 MCP 配置面为完成目标

对六个支持宿主，都必须优先把 MCP 自动接入到宿主当前真实使用的 **宿主原生 MCP 配置面**。

明确禁止把以下内容当作 MCP 完成证据：

- `$vibe` / `/vibe` / `skills/vibe` 的可发现性
- `mcp/servers.template.json`
- plugin manifest
- `*.json.example`
- `.vibeskills/*` sidecar
- 仅仅“命令已经在 PATH 上”

如果原生自动注册失败，或当前宿主没有稳定、官方可支持的自动注册接口，必须明确报告“尚未进入宿主原生 MCP 配置面 / not host-visible”，不能伪装成 ready。

## 规则 16：区分“本地安装完成”“vibe host-ready”和“在线能力就绪”

如果本地 provider 字段没有配置好，就不能把环境描述成“online ready”。

同时也不能把 `$vibe` 可调用偷换成 “MCP 已安装完成”。

## 规则 17：输出安装或更新结果时必须说清楚

结果摘要至少应包含：

- 目标宿主
- 公开版本
- 实际映射的 profile
- 实际执行的命令
- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- 每个 MCP 的 `host-visible readiness`
- `online-ready`
- 已完成的部分
- 仍需用户手动处理的部分

## 规则 18：框架版本不是开箱即用全量体验

如果用户选择 `仅核心框架 + 可自定义添加治理` / `minimal`，必须额外提醒：

- 这表示先安装治理框架底座
- 不等于默认 workflow core 已齐备
- 如果后续要接入自己的 workflow，请继续走 [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
