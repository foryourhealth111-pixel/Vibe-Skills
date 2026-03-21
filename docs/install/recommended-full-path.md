# 安装路径：高级 host / lane 参考

> 大多数用户现在先看两条主路径：
> - [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
> - [`manual-copy-install.md`](./manual-copy-install.md)

这条路的默认答案仍然是：**先走 `codex` lane**。

因为当前只有它具备完整的 governed-with-constraints install/check/bootstrap。

## 现在的 lane 区分

- `codex`：正式推荐满血路径
- `claude-code`：preview scaffold 路径
- `generic` / `opencode`：runtime-core-only 路径

因此，推荐满血不再等于“所有 host 都走同一条脚本”，而是：

- 正式闭环需求走 `codex`
- 预览接入 Claude Code 走 `claude-code`
- 只要 canonical runtime-core 就走 `generic`

## 推荐命令

### Codex

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId codex
pwsh -File .\check.ps1 -HostId codex -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex
bash ./check.sh --host codex --profile full --deep
```

### Claude Code 预览

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId claude-code
pwsh -File .\check.ps1 -HostId claude-code -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code
bash ./check.sh --host claude-code --profile full --deep
```

### Generic Runtime-Core

```powershell
pwsh -File .\install.ps1 -HostId generic -Profile full
pwsh -File .\check.ps1 -HostId generic -Profile full
```

```bash
bash ./install.sh --host generic --profile full
bash ./check.sh --host generic --profile full
```

## 必须说清楚的边界

### Codex

- repo 会尽量完成 runtime、settings、MCP materialization 和 deep doctor
- 但插件 provision、provider secrets 仍有 host-managed 部分

### Claude Code

- repo 现在会 scaffold preview `settings.json` 和 hooks
- 但这不是 Claude Code full closure
- 用户仍需自己提供 URL、API key、model，并在宿主侧完成插件/MCP 接入

### Generic / OpenCode

- repo 只安装 runtime-core
- 默认写到中性目录，不写宿主专属状态
- 用户必须自己在目标 agent 中配置 URL、API key、model

## AI 治理层提示

对 `claude-code`、`generic`、`opencode` 这些非 governed Codex lane，AI 智能治理层必须提醒用户三件事：

- 你需要自己提供 `url`
- 你需要自己提供 `apikey`
- 你需要自己提供 `model`

如果这些值没有显式提供，不能把环境描述成“已完成 online readiness”。
