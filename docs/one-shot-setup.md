# One-Shot Setup

`vco-skills-codex` 现在提供一个 registry-driven 的单命令 bootstrap 入口，用来把 **仓库可自动化的部分** 一次性落地，并在最后给出一份深度 readiness 报告。

这份文档覆盖当前六个公开宿主，但要如实区分宿主模式：

- `codex`：`governed`
- `claude-code`、`cursor`、`opencode`：`preview-guidance`
- `windsurf`、`openclaw`：`runtime-core`

如果你的目标只是拿到更薄的预览安装路径，`opencode` 仍然可以直接走 `install.* + check.*`。但这不代表 one-shot 不能用于 `opencode`；它只是一个统一 wrapper，会按当前宿主的 `bootstrap_mode` 走对应分支。

如果你还不知道自己应该走哪种安装方式，先看：

- [`cold-start-install-paths.md`](./cold-start-install-paths.md)
- [`cold-start-install-paths.en.md`](./cold-start-install-paths.en.md)
- [`install/recommended-full-path.md`](./install/recommended-full-path.md)

## One Command

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
```

## 谁应该把 one-shot 当成标准推荐入口

如果你属于下面这些人，one-shot 就是更自然的入口：

- 想用一个统一 wrapper 覆盖当前公开宿主的人
- 想先把仓库负责的面尽量一次装好，再看 host-specific follow-up 的人
- 想先拿到 deep doctor 结果，再决定要不要继续增强的人
- 想先验证这套治理面是否值得纳入团队标准的负责人

如果你只是想走最薄的 preview 路径，尤其是 `opencode`，可以直接使用 `install.* + check.*`。

## Full-Feature Prerequisites

- `git`
- `node` and `npm`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux / macOS: `bash`
- Recommended on Linux / macOS for authoritative gate parity: `pwsh` (PowerShell 7)

Linux / macOS without `pwsh` still gets the shipped content and the runtime-neutral verification path where supported, but the PowerShell-native doctor gates degrade to explicit warnings instead of silent success.

## What one-shot actually does now

默认行为不再写死到 `~/.codex`，而是按当前宿主模式执行：

1. 按 `HostId` / `--host` 解析目标宿主与目标根目录
2. 安装对应 profile 的 payload 到目标根目录
3. 如果允许，尝试安装可脚本安装的外部 CLI
4. 按当前宿主的 `bootstrap_mode` 做 host-specific follow-up
5. 运行深度检查，并把 doctor artifacts 写到 `outputs/verify/`

### `governed`：当前是 `codex`

- 会尝试补齐内置 AI 治理 advice 的本地 settings
- 会物化启用中的 MCP profile 到 `<target-root>/mcp/servers.active.json`
- 会运行 `check.* --deep`

### `preview-guidance`：当前是 `claude-code`、`cursor`、`opencode`

- 不会伪装成 fully managed host takeover
- `claude-code` 当前会走受约束的 scaffold / write-guard path
- `cursor` 与 `opencode` 不会额外写入 host-specific scaffold
- 仍会运行 `check.* --deep`，但 provider settings 与 host-local config 继续保持 host-managed

### `runtime-core`：当前是 `windsurf`、`openclaw`

- repo 只负责 runtime-core payload 与 `.vibeskills/*` sidecar 状态
- 不物化 host settings，也不写入 provider secrets
- 仍会运行 `check.* --deep`

## What It Can Finish Automatically

- shipped skills / rules / templates
- shared runtime payload
- 当前宿主模式允许的 scaffold 或 sidecar 状态
- runtime freshness / coherence verification
- 可脚本安装的部分外部 CLI，例如 `claude-flow`

## What It Cannot Finish Automatically

以下部分不会被 repo 静默“装完”，而是会在 doctor 报告里明确标成待处理：

- 用户 API keys / provider secrets
- 大多数 host-native settings / plugin / MCP trust 决策
- 宿主登录态、账号状态与平台权限
- 不在当前宿主模式承诺范围内的 hook / host takeover 行为

这不是缺陷掩盖，而是平台边界的显式化。one-shot 的目标不是伪造“全部 ready”，而是让你一次执行后清楚知道：

- 哪些部分已经 ready
- 哪些部分是 optional enhancement
- 哪些部分仍需要人工一步

## Deep Check

你可以随时重跑：

```powershell
pwsh -File .\check.ps1 -Profile full -HostId <host> -Deep
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -HostId <host> -Deep
```

```bash
bash ./check.sh --profile full --host <host> --deep
```

深度检查会输出：

- settings / secret readiness
- plugin readiness classification
- external CLI availability
- MCP enabled server readiness
- overall `readiness_state`

## Readiness States

- `fully_ready`
  代表 repo 可自动化部分已完成，且没有剩余人工待办。
- `manual_actions_pending`
  代表核心安装已闭环，但仍有平台插件、密钥或外部服务接入需要人工一步完成。
- `core_install_incomplete`
  代表基础安装或运行时一致性本身有问题，需要先修复 install/runtime。

## Recommended Follow-up

推荐顺序：

1. 先确认目标宿主的本地 settings / provider 约束
2. 再补 `VCO_INTENT_ADVICE_*`，把 AI 治理主路径接通
3. 需要时再补 `VCO_VECTOR_DIFF_*`
4. 再补 plugin-backed MCP surfaces 或外部服务
5. 只在你确实需要时再做更重的 host-local enhancement

如果是 Claude Code，继续按本地 `~/.claude/settings.json` 的增量方式补全；如果是 Windsurf / OpenClaw / OpenCode，继续保持 host-managed 边界，不要把 one-shot 误解成全面接管宿主。
