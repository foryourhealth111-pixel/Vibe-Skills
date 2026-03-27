# 手动复制安装（离线 / 无管理员权限）

如果你不想跑安装脚本，只想手动放文件，这条路径只解决“把仓库文件复制到目标宿主根目录”。

当前公开支持六个宿主：

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

## 基本复制内容

复制到目标根目录：

- `skills/`
- `commands/`
- `config/upstream-lock.json`
- `skills/vibe/`

## 宿主根目录提示

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` 或 `~/.openclaw`
- `opencode` -> `OPENCODE_HOME` 或 `~/.config/opencode`

如果目标是 `windsurf`，还要额外注意：

- 如需对齐脚本安装结果，把 `commands/` 同步到 `global_workflows/`
- 如目标目录缺少 `mcp_config.json`，可由 `mcp/servers.template.json` 复制得到

如果目标是 `opencode`，请改用 OpenCode 预览载荷：

- `skills/`
- `commands/*.md`
- `command/*.md`
- `agents/*.md`
- `agent/*.md`
- `opencode.json.example`

并结合 [`opencode-path.md`](./opencode-path.md) 处理 preview adapter 的后续步骤。

## 复制后仍需你自己完成的部分

### Codex

- 维护 `~/.codex/settings.json`
- 如需 AI 治理 advice 的常见 OpenAI-compatible 在线路径，优先配置：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`

### Claude Code

- 维护 `~/.claude/settings.json`
- 如需 AI 治理 advice 的常见 OpenAI-compatible 在线路径，优先补：
  - `OPENAI_API_KEY`
  - 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`

### Cursor

- 维护 `~/.cursor/settings.json`
- 视需要补本地 provider / MCP 配置

### Windsurf

- 确认 `~/.codeium/windsurf` 下的 `mcp_config.json` 与 `global_workflows/`
- 宿主侧本地配置仍需在 Windsurf 内完成

### OpenClaw

- 确认 `OPENCLAW_HOME` 或 `~/.openclaw` 下的 runtime-core payload
- 如需与脚本安装结果对齐，优先使用 attach / copy / bundle 三路径说明
- 宿主侧本地配置仍需在 OpenClaw 内完成

### OpenCode

- 确认 `OPENCODE_HOME` 或 `~/.config/opencode` 下的 preview payload
- 真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任仍需宿主侧本地完成
- 如需项目内隔离安装结果，对齐 `./.opencode`

## 这条路径不会自动完成什么

- hook 安装
- provider 凭据写入
- 宿主侧本地配置的自动代管

当前公开支持面里，六个宿主都不应被描述成“已自动安装 hook”。
