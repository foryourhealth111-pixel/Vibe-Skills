# One-Shot Setup

`vco-skills-codex` 现在提供一个面向支持宿主的单命令 bootstrap 入口，用来把 **仓库可自动化的部分** 一次性落地，并在最后给出一份深度 readiness 报告。

这份文档当前只覆盖 `codex` 和 `claude-code` 的 one-shot bootstrap。

如果你的目标宿主是 `opencode`，请改走 direct install/check 路径：

- [`install/opencode-path.md`](./install/opencode-path.md)

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

## 谁应该把 one-shot 当成标准推荐安装入口

如果你属于下面这些人，one-shot 就是默认入口：

- 想先把仓库负责的面尽量一次装好的人
- 想先拿到 deep doctor 结果，再决定要不要继续增强的人
- 想先验证这套治理面是否值得纳入团队标准的负责人

如果你只是想快速 smoke test，先走 `minimum viable`。
如果你要做团队级、可审计、可回滚交付，就继续升级到 `enterprise-governed` 路径。

入口说明见：

- [`cold-start-install-paths.md`](./cold-start-install-paths.md)
- [`install/recommended-full-path.md`](./install/recommended-full-path.md)

## Full-Feature Prerequisites

- `git`
- `node` and `npm`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux / macOS: `bash`
- Recommended on Linux / macOS for authoritative gate parity: `pwsh` (PowerShell 7)

Linux / macOS without `pwsh` still gets the full shipped content and the active MCP profile, but the PowerShell-native doctor gates degrade to explicit warnings instead of silent success.

当前 one-shot 会把三类默认面分开表达：

- `scrapling`：属于 `full` profile 的默认本地 runtime / MCP 面，在可用 Python 打包环境下会尝试自动安装
- `Cognee`：属于默认长程图记忆增强面，只负责 governed long-term graph memory，不取代 `state_store`
- `Composio / Activepieces`：属于默认可见但 setup-required 的外部操作接入面，不会被伪装成自动就绪

默认行为：

1. 安装 `full` profile 到 `~/.codex`
2. 尝试安装可脚本安装的外部 CLI
3. 物化启用中的 MCP profile 到 `~/.codex\mcp\servers.active.json`
4. 运行 `check.ps1 -Deep`
5. 生成 doctor artifacts 到 `outputs/verify/`

当前额外边界：

- hook 由于兼容性问题已冻结
- `codex` / `claude-code` / `windsurf` 当前都不会由 one-shot 安装 hook
- `claude-code` 当前也不再写 `settings.vibe.preview.json`
- `windsurf` 当前只能按 preview runtime-core 描述，不代表宿主登录、账号、provider 或插件闭环

## Operator Notes

- When external CLI installation is enabled, the slowest step is usually the `npm` install for `claude-flow`; several minutes is expected on some machines.
- `npm` deprecation warnings during that step are advisory unless the install command exits non-zero.
- If the target `settings.json` already contains `OPENAI_API_KEY` and `VCO_RUCNLPIR_MODEL`, the bootstrap reuses those values and reports them explicitly instead of warning that the built-in governance path is incomplete.

## What It Can Finish Automatically

- vendored / bundled skills
- rules / agent templates
- shipped MCP templates and selected MCP active profile
- runtime freshness / coherence verification
- 可脚本安装的部分外部 CLI，例如 `claude-flow`

## What It Cannot Finish Automatically

标准推荐安装现在默认包含 `scrapling` 这条本地能力面，但它不会把 `Cognee`、`Composio`、`Activepieces` 混成同一类“缺失项”：

- `Cognee` 是默认 enhancement lane，用于受治理的 long-term graph memory
- `Composio / Activepieces` 是 prewired external action surfaces，仍然必须 setup 后才能使用
- 它们默认不会被算成 `core_install_incomplete`

以下部分不会被 repo 静默“装完”，而是会在 doctor 报告里明确标成待处理：

- Codex 本地设置补充项
- 用户 API keys / provider secrets
- host 级 MCP 注册与平台侧权限

这不是缺陷掩盖，而是平台边界的显式化。目标不是伪造“全部 ready”，而是让用户一次执行后清楚知道：

- 哪些部分已经 ready
- 哪些部分是 optional gap
- 哪些部分还需要人工一步

所以，one-shot 是 **标准推荐安装的闭环器**，不是“整个生态所有增强面的自动安装器”。

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

在当前默认层次里，建议把 follow-up 顺序理解成：

1. 先补 provider secrets
2. 先确认 `scrapling` 可调用，把它视作 default full-profile scraping surface
3. 把 `Cognee` 放在长程增强面，不让它接管 `state_store`
4. 再补官方支持的 MCP surfaces
5. `Composio / Activepieces` 仅在你确实需要外部操作能力时再做 setup，并保持 confirm-gated

6. 如果 `OPENAI_API_KEY` 仍是 `placeholder` 或 `missing`，先在本地配置 key，不要在聊天里粘贴。
7. 如果 `VCO_RUCNLPIR_MODEL` 仍是 `placeholder` 或 `missing`，补上治理层实际要调用的模型名。
8. 如果是 Claude Code，打开 `~/.claude/settings.json`，只补充缺失的 `env` 字段；当前版本不会再生成 `settings.vibe.preview.json`。
9. 如果 `manual_action_required` 的 MCP server 是 `stdio` 模式，先安装对应命令行依赖，再在 host 中注册。

当前 `full` profile 最重要的人工补齐项是：

- plugin-backed MCP surfaces: `github`、`context7`、`serena`
- 你实际要在线使用的 provider secrets，尤其是 `OPENAI_API_KEY`
- 内置治理 advice 要使用的模型名，即 `VCO_RUCNLPIR_MODEL`

但默认策略不是“让用户自己折腾 hook 面”。当前 hook 由于兼容性问题被冻结，不在安装支持范围内。

推荐：

- 第一次安装：先跑 one-shot + deep doctor，允许 `manual_actions_pending`
- Codex：优先补本地配置、官方 MCP 和确有价值的 CLI 依赖
- Claude Code：优先按本地文件增量补 `settings.json`，不要覆盖原文件

如果你还想进一步增强，推荐顺序是：

1. provider secrets
2. plugin-backed MCP surfaces
3. Claude Code 本地 `settings.json` 增量配置
4. 可选 CLI / 工具链增强
5. 可选 CLI / 工具链增强

更细的宿主边界说明见：[`docs/install/recommended-full-path.md`](./install/recommended-full-path.md)
