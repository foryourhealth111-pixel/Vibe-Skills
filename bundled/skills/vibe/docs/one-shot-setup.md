# One-Shot Setup

`vco-skills-codex` 现在提供一个面向 Codex 运行时的单命令 bootstrap 入口，用来把 **仓库可自动化的部分** 一次性落地，并在最后给出一份深度 readiness 报告。

如果你还不知道自己应该走哪种安装方式，先看：

- [`cold-start-install-paths.md`](./cold-start-install-paths.md)
- [`cold-start-install-paths.en.md`](./cold-start-install-paths.en.md)

## One Command

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
```

## Full-Feature Prerequisites

- `git`
- `node` and `npm`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux / macOS: `bash`
- Recommended on Linux / macOS for authoritative gate parity: `pwsh` (PowerShell 7)

Linux / macOS without `pwsh` still gets the full shipped content and the active MCP profile, but the PowerShell-native doctor gates degrade to explicit warnings instead of silent success.

默认行为：

1. 安装 `full` profile 到 `~/.codex`
2. 尝试安装可脚本安装的外部 CLI
3. 物化启用中的 MCP profile 到 `~/.codex\mcp\servers.active.json`
4. 运行 `check.ps1 -Deep`
5. 生成 doctor artifacts 到 `outputs/verify/`

## Operator Notes

- When external CLI installation is enabled, the slowest step is usually the `npm` install for `claude-flow`; several minutes is expected on some machines.
- `npm` deprecation warnings during that step are advisory unless the install command exits non-zero.
- If the target `settings.json` already contains `OPENAI_API_KEY` or `ARK_API_KEY`, the bootstrap reuses those values and reports that explicitly instead of warning that the provider key is missing.

## What It Can Finish Automatically

- vendored / bundled skills
- rules / hooks / agent templates
- shipped MCP templates and selected MCP active profile
- runtime freshness / coherence verification
- 可脚本安装的部分外部 CLI，例如 `claude-flow`

## What It Cannot Finish Automatically

以下部分不会被 repo 静默“装完”，而是会在 doctor 报告里明确标成待处理：

- Codex host plugins
- 用户 API keys / provider secrets
- host 级 MCP 注册与平台侧权限

这不是缺陷掩盖，而是平台边界的显式化。目标不是伪造“全部 ready”，而是让用户一次执行后清楚知道：

- 哪些部分已经 ready
- 哪些部分是 optional gap
- 哪些部分还需要人工一步

## Deep Check

你可以随时重跑：

```powershell
pwsh -File .\check.ps1 -Profile full -Deep
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep
```

```bash
bash ./check.sh --profile full --deep
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

1. 如果 `OPENAI_API_KEY` 仍是 `placeholder` 或 `missing`，先配置 key。
2. 如果 `platform_plugin_required` 仍存在，按 doctor 报告中列出的插件逐项 provision。
3. 如果 `manual_action_required` 的 MCP server 是 `stdio` 模式，先安装对应命令行依赖，再在 host 中注册。

当前 `full` profile 最重要的人工补齐项是：

- host plugin surfaces still tracked by doctor / manifest: `superpowers`、`everything-claude-code`、`claude-code-settings`、`hookify`、`ralph-loop`
- plugin-backed MCP surfaces: `github`、`context7`、`serena`
- 你实际要在线使用的 provider secrets，尤其是 `OPENAI_API_KEY`

但默认策略不是“第一次就把 5 个 host plugin 全部装上”。

推荐：

- 第一次安装：先跑 one-shot + deep doctor，允许 `manual_actions_pending`
- Windows / Codex 参考 lane：优先补 `superpowers` 和 `hookify`
- `everything-claude-code`、`claude-code-settings`、`ralph-loop`：只在 doctor 仍指向明确缺口时再补

完整决策与安装说明见：[`docs/install/host-plugin-policy.md`](./install/host-plugin-policy.md)
