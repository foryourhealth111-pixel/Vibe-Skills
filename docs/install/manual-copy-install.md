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

- `codex` -> 默认把 `CODEX_HOME` 指到真实 `~/.codex`；如果你希望复制后当前 Codex 直接发现 `$vibe`，不要默认落到 `~/.vibeskills/targets/codex`
- `claude-code` -> 默认把 `CLAUDE_HOME` 指到真实 `~/.claude`
- `cursor` -> 默认把 `CURSOR_HOME` 指到真实 `~/.cursor`
- `windsurf` -> `WINDSURF_HOME` 或真实宿主根目录 `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw`
- `opencode` -> `OPENCODE_HOME` 或真实宿主根目录 `~/.config/opencode`

如果目标是 `windsurf`，还要额外注意：

- 如需与当前脚本安装结果严格对齐，优先重新运行 `install.* --host windsurf`
- 当前公开合同下，宿主侧 sidecar 以 `.vibeskills/host-settings.json` 与 `.vibeskills/host-closure.json` 为准，而不是 `mcp_config.json` / `global_workflows/`

如果目标是 `opencode`，请改用 OpenCode 预览载荷：

- `skills/`
- `.vibeskills/host-settings.json`
- `.vibeskills/host-closure.json`
- `.vibeskills/install-ledger.json`
- `.vibeskills/bin/*-specialist-wrapper.*`
- `opencode.json.example`

并结合 [`opencode-path.md`](./opencode-path.md) 处理 preview adapter 的后续步骤。

## 复制后仍需你自己完成的部分

### Codex

- 维护 `~/.codex/settings.json`
- 手动复制不会自动完成宿主 provider、插件或 MCP 授权
- 公开手动安装暂时不引导配置内置在线增强能力

### Claude Code

- 维护 `~/.claude/settings.json`
- 手动复制不会自动完成 Claude 宿主侧 provider、插件或 MCP 授权
- 公开手动安装暂时不引导配置内置在线增强能力

### Cursor

- 维护 `~/.cursor/settings.json`
- 视需要补本地 provider / MCP 配置

### Windsurf

- 确认 `WINDSURF_HOME` 或真实宿主根目录 `~/.codeium/windsurf` 下的 `.vibeskills/host-settings.json` 与 `.vibeskills/host-closure.json`
- 宿主侧本地配置仍需在 Windsurf 内完成

### OpenClaw

- 确认 `OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw` 下的 runtime-core payload
- 如需与脚本安装结果对齐，优先使用 attach / copy / bundle 三路径说明
- 宿主侧本地配置仍需在 OpenClaw 内完成

### OpenCode

- 确认 `OPENCODE_HOME` 或真实宿主根目录 `~/.config/opencode` 下的 preview payload
- 真实 `~/.config/opencode/opencode.json` 仍由宿主侧维护
- 真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任仍需宿主侧本地完成
- 如需项目内隔离安装结果，对齐 `./.opencode`

## 这条路径不会自动完成什么

- hook 安装
- provider 凭据写入
- 宿主侧本地配置的自动代管

当前公开支持面里，六个宿主都不应被描述成“已自动安装 hook”。
