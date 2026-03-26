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

## 规则 7：Codex 要按 governed 口径描述

如果用户选择 `codex`：

- 运行 `--host codex`
- 明确说明这是当前最完整的 governed 路径
- hook 当前因兼容性问题被冻结；这不是安装失败
- 如需 Codex 基础在线 provider，去本地 `~/.codex/settings.json` 的 `env` 或本地环境变量配置 `OPENAI_*`
- 如需治理 AI 在线层，再按需补 `VCO_AI_PROVIDER_*`
- 不能把 `OPENAI_*` 已配置偷换成“治理 AI online readiness 已完成”

## 规则 8：Claude Code 要按“支持的安装与使用路径”口径描述

如果用户选择 `claude-code`：

- 运行 `--host claude-code`
- 明确说明当前提供支持的安装与使用路径
- hook 当前冻结；这不是安装失败
- 不再写 `settings.vibe.preview.json`
- 引导用户自己补 `~/.claude/settings.json` 的 `env`

## 规则 9：Cursor 也按“支持的安装与使用路径”口径描述

如果用户选择 `cursor`：

- 运行 `--host cursor`
- 明确说明当前提供支持的安装与使用路径
- 当前不接管 Cursor 的真实 settings 与宿主原生扩展面
- 引导用户自己检查和维护 `~/.cursor/settings.json`

## 规则 10：Windsurf 要按“支持的安装与使用路径，且已接入 runtime adapter”口径描述

如果用户选择 `windsurf`：

- 运行 `--host windsurf`
- 明确说明当前提供支持的安装与使用路径，且已接入 runtime adapter
- 默认宿主根目录是 `~/.codeium/windsurf`
- repo 当前只负责 shared runtime payload，以及按需物化 `mcp_config.json` 与 `global_workflows/`
- Windsurf 宿主本地设置仍由用户在宿主侧完成

## 规则 11：OpenClaw 必须按 preview / runtime-core-preview / runtime-core 口径描述

如果用户选择 `openclaw`：

- 运行 `--host openclaw`
- 明确说明这是 `preview` 宿主，closure level 是 `runtime-core-preview`，install/check mode 是 `runtime-core`
- 默认目标根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`
- 明确三条路径：
  - attach：接入并校验已有 `OPENCLAW_HOME`（或 `~/.openclaw`）目录
  - copy：通过 install/check 入口复制 runtime-core payload 到目标根目录
  - bundle：按 `dist/host-openclaw/manifest.json` 与 `dist/manifests/vibeskills-openclaw.json` 消费分发清单
- 聚焦 runtime-core payload 的安装、检查与分发结果
- 宿主侧本地配置仍按 OpenClaw 方式完成

## 规则 12：不要要求用户把密钥贴到聊天里

对五个支持宿主，都不要要求用户把密钥、URL 或 model 直接粘贴到聊天里；只引导用户去本地 settings 或本地环境变量配置。

## 规则 13：区分“本地安装完成”和“在线能力就绪”

如果本地 provider 字段没有配置好，就不能把环境描述成“online ready”。

## 规则 14：输出安装或更新结果时必须说清楚

结果摘要至少应包含：

- 目标宿主
- 公开版本
- 实际映射的 profile
- 实际执行的命令
- 已完成的部分
- 仍需用户手动处理的部分

## 规则 15：框架版本不是开箱即用全量体验

如果用户选择 `仅核心框架 + 可自定义添加治理` / `minimal`，必须额外提醒：

- 这表示先安装治理框架底座
- 不等于默认 workflow core 已齐备
- 如果后续要接入自己的 workflow，请继续走 [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
