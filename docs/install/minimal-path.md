# 安装路径：最小可用（truth-first / 可接受降级）

本路径的目标是：**尽快把仓库自己负责的最小闭环跑通**，并且如实暴露哪些能力仍然属于 **host-managed surfaces**（宿主侧手工 provision），而不是把“能跑”伪装成“满血等价”。

对应分发面：`dist/manifests/vibeskills-core.json` +（如果你在 Codex）`dist/manifests/vibeskills-codex.json`。

## 适合谁

- 第一次接触本仓库、只想验证 “repo-governed surfaces 是否闭环” 的用户
- 能接受最终状态落在 `manual_actions_pending`（例如缺 host plugins / MCP / provider secrets）
- 不准备在当前阶段补齐所有外部依赖的人

## 你不要期待什么（避免过度承诺）

- 不保证宿主侧插件已启用
- 不保证 plugin-backed MCP 已注册/授权
- 不保证任何 MCP 已进入对应宿主真实使用的 **宿主原生 MCP 配置面**
- 不保证 `VCO_INTENT_ADVICE_API_KEY` 等 VCO_* 凭据（含可选 `VCO_VECTOR_DIFF_*`）已准备好

`$vibe` 或 `/vibe` 只说明 governed runtime 入口可用，不等于 MCP 完成；repo template、manifest、sidecar、`*.json.example` 和 PATH 上已有命令也都不能单独算 host-visible MCP ready。

## Host / 平台先决判断

在 Linux / macOS 的 shell 路径上，先决条件补充如下：

- `bash` 入口按 **macOS 自带 Bash 3.2** 兼容维护
- `python3` / `python` 需要满足 **Python 3.10+**
- 如果你从 `zsh` 里启动，问题通常不是 `zsh`，而是实际解析到的 `bash` 或 `python3` 太老

### 最强参考 lane（Codex）

根据 `docs/universalization/host-capability-matrix.md`：Codex 当前是 `supported-with-constraints` 的参考 lane（仍有 host-managed surfaces）。

根据 `docs/universalization/platform-parity-contract.md`：

- Windows 是当前权威参考路径（authoritative lane）
- Linux **只有在安装了 `pwsh`** 并能跑 PowerShell gates 时，才接近权威路径；否则属于 **degraded**，不是“偷偷满血”
- macOS 仍是 `not-yet-proven`

### Claude Code / OpenCode / Generic Host

- Claude Code：此仓库当前是 `supported-with-constraints`（已经有受约束的 settings + hook 安装/检查闭环，但仍不是 Codex 官方 runtime，也不能宣传为满血等价）
- OpenCode：此仓库当前也是 `preview`，但有独立的 direct `install/check` 入口和专门安装说明
- Generic Host：`advisory-only`（只能消费契约与文档，不做运行时承诺）

如果你不是在 Codex 上运行，请把本路径理解为：**文档/契约消费 + 最小自检**，而不是“官方运行时安装”。

如果你的目标是 OpenCode，请直接看：

- [`opencode-path.md`](./opencode-path.md)

## 推荐命令（不接管主链）

### Windows（推荐：pwsh）

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -SkipExternalInstall
pwsh -File .\check.ps1
```

### Linux（bash 路径；无 pwsh 时属于 degraded）

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --skip-external-install
bash ./check.sh
```

> 提示：如果你希望 Linux 的 doctor/gate 更接近权威路径，请额外安装 `pwsh`，否则一些 PowerShell 治理 gate 可能只能跳过并输出明确 warning（这是预期的降级，而不是失败伪装）。

> macOS 提示：如果命令在进入安装逻辑前就报 Python 兼容性错误，请先确保 `python3 --version` 至少是 `3.10`。这和可选外部 runtime 的独立 venv 不是一回事。

## 验收标准（truth-first）

- 安装/检查命令退出码为 `0`
- 允许最终状态为 `manual_actions_pending`（缺宿主侧能力时应诚实落在这里）
- 不应出现 `core_install_incomplete`

## Stop Rules

如果你只是第一次体验仓库，到这里就可以停。

只有在你确认 “repo-governed surfaces 已闭环、剩余都是宿主侧手工 provision” 之后，才值得进入：

- `docs/install/recommended-full-path.md`
- `docs/install/enterprise-governed-path.md`
