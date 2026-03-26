# 安装路径：高级 host / lane 参考

> 普通用户优先看：
>
> - [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
> - [`manual-copy-install.md`](./manual-copy-install.md)

这份文档只解释当前真实支持边界，以及五个宿主对应的安装命令。

## 当前支持面

| 宿主 | 模式 | 默认根目录 | 当前口径 |
| --- | --- | --- | --- |
| `codex` | governed | `~/.codex` | 当前最完整路径 |
| `claude-code` | 支持的安装与使用路径 | `~/.claude` | 保持真实宿主设置边界 |
| `cursor` | 支持的安装与使用路径 | `~/.cursor` | 保持真实宿主设置边界 |
| `windsurf` | 支持的安装与使用路径 + runtime adapter | `~/.codeium/windsurf` | 已接入 runtime adapter，保持真实宿主设置边界 |
| `openclaw` | `preview` / `runtime-core-preview` / `runtime-core` | `OPENCLAW_HOME` 或 `~/.openclaw` | 聚焦 runtime-core payload 的安装、校验与分发 |

`TargetRoot` 只是路径。
`HostId` / `--host` 才决定宿主语义。

## 推荐命令

默认全量安装：

### Codex

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId codex -Profile full
pwsh -File .\check.ps1 -HostId codex -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex --profile full
bash ./check.sh --host codex --profile full --deep
```

### Claude Code

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId claude-code -Profile full
pwsh -File .\check.ps1 -HostId claude-code -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code --profile full
bash ./check.sh --host claude-code --profile full --deep
```

### Cursor

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId cursor -Profile full
pwsh -File .\check.ps1 -HostId cursor -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --profile full
bash ./check.sh --host cursor --profile full --deep
```

### Windsurf

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId windsurf -Profile full
pwsh -File .\check.ps1 -HostId windsurf -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host windsurf --profile full
bash ./check.sh --host windsurf --profile full --deep
```

### OpenClaw

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId openclaw -Profile full
pwsh -File .\check.ps1 -HostId openclaw -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

如果你要装“仅核心框架 + 可自定义添加治理”，把上面的 `full` 改成 `minimal`。

## 更新方式

如果本地还保留仓库，先更新仓库再重跑同一组命令：

```bash
git pull origin main
```

如果你跟随 tag 发布版本而不是 `main`，则：

```bash
git fetch --tags --force
git checkout vX.Y.Z
```

## 必须保持真实的边界

### Codex

- 这是 governed 路径
- hook 当前冻结；这不是安装失败
- `OPENAI_*` 只代表 Codex 基础在线 provider
- `VCO_AI_PROVIDER_*` 才是治理 AI 在线层的可选增强项

### Claude Code

- 当前提供支持的安装与使用路径
- 不覆盖真实 `~/.claude/settings.json`
- hook 当前冻结；这不是安装失败

### Cursor

- 当前提供支持的安装与使用路径
- 不覆盖真实 `~/.cursor/settings.json`
- Cursor 的宿主原生设置与扩展面仍按 Cursor 自身方式管理

### Windsurf

- 当前提供支持的安装与使用路径，且已接入 runtime adapter
- 默认根目录是 `~/.codeium/windsurf`
- repo 当前只负责 shared runtime payload，以及按需物化 `mcp_config.json` 与 `global_workflows/`
- Windsurf 宿主自身的本地设置仍按 Windsurf 自身方式管理

### OpenClaw

- 当前按 `preview` / `runtime-core-preview` / `runtime-core` 路径描述
- 默认目标根目录是 `OPENCLAW_HOME` 或 `~/.openclaw`
- attach / copy / bundle 三路径围绕 runtime-core payload 的安装、校验与分发
- OpenClaw 宿主自身的本地配置仍按 OpenClaw 自身方式管理
