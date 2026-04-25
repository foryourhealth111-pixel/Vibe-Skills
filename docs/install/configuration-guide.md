# 安装后配置边界

这份文档只说明安装完成后哪些内容由 VibeSkills 管，哪些内容仍由宿主或用户自己管。

当前公开安装流程暂时不开放内置在线增强能力的用户配置说明。安装助手不应要求用户提供 provider、凭据、URL 或模型名，也不应把这些内容作为完成安装的前置条件。

## 先分清三件事

| 状态 | 含义 |
|:---|:---|
| `installed locally` | 文件已经写入目标宿主根目录 |
| `vibe host-ready` | 宿主能发现 `vibe` / `vibe-upgrade` 入口 |
| `online-ready` | 需要额外在线能力真的可用时才可声明 |

`installed locally` 不等于 `online-ready`。

`$vibe` 或 `/vibe` 只说明 governed runtime 入口可用；它不等于 MCP 完成，也不能证明 provider、插件、凭据或宿主原生 MCP 面都已经配置好。

## 安装助手应该怎么报告

最终报告不要写成一句“全部成功”。至少分开说明：

- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- 每个 MCP 的 `host-visible readiness`
- `online-ready`
- 仍需用户手动处理的宿主侧事项

如果某个能力没有通过公开安装路径配置好，就如实写未就绪或未验证。

## 不要在公开安装里要求什么

公开安装暂时不引导用户配置内置在线增强能力。因此安装助手不应：

- 要求用户把密钥粘贴到聊天里
- 要求用户提供 provider URL
- 要求用户提供模型名
- 把缺少这些本地配置描述成安装失败
- 把宿主基础可用误写成在线增强能力已就绪

## 不同宿主通常由谁维护

### Codex

- 目标根目录：如果目标是安装后就让当前 Codex 直接发现 `$vibe`，默认把 `CODEX_HOME` 设为真实 `~/.codex`
- 只有显式隔离安装时才使用 `~/.vibeskills/targets/codex`
- 宿主登录态、provider、插件和 MCP 信任仍由 Codex 侧维护

### Claude Code

- 默认把 `CLAUDE_HOME` 设为真实 `~/.claude`
- 安装器只合并受控的 VibeSkills 设置面
- 更广的 Claude settings、插件、凭据和 MCP 注册仍由宿主侧维护

### Cursor

- 默认把 `CURSOR_HOME` 设为真实 `~/.cursor`
- 当前不接管 Cursor 的真实 settings 与扩展面
- Cursor 自身的设置和扩展仍按 Cursor 方式维护

### Windsurf

- 目标根目录：`WINDSURF_HOME` 或真实宿主根目录 `~/.codeium/windsurf`
- repo 侧可检查 `<target-root>/.vibeskills/host-settings.json` 与 `<target-root>/.vibeskills/host-closure.json`
- 这些文件只证明 repo 写入了 sidecar 状态，不代表宿主侧登录、provider 或插件能力已完成

### OpenClaw

- 目标根目录：`OPENCLAW_HOME` 或真实宿主根目录 `~/.openclaw`
- repo 侧只负责 runtime-core payload 和 sidecar 状态
- 宿主侧本地配置仍按 OpenClaw 方式完成

### OpenCode

- 目标根目录：`OPENCODE_HOME` 或真实宿主根目录 `~/.config/opencode`
- 真实宿主配置目录仍是 `~/.config/opencode`
- `<target-root>/opencode.json.example` 只是参考脚手架，不是 live host config
- 真实 `opencode.json`、provider 凭据、plugin 安装和 MCP 信任仍由 OpenCode 宿主侧维护

## 卸载

当你需要回滚当前安装时，使用仓库根目录下的卸载入口：

- Windows：`uninstall.ps1 -HostId <host>`
- Linux / macOS：`uninstall.sh --host <host>`

卸载遵守 [`../uninstall-governance.md`](../uninstall-governance.md) 的 ledger-first、owned-only 契约：只删除 install ledger、host closure 或保守 legacy 规则能够证明属于 Vibe 的内容；共享配置文件里只移除 `vibeskills` 受管节点。
