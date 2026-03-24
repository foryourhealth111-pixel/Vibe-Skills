# Deployment

## Profiles

- `minimal`: install required runtime payload only
- `full`: install the full vendored mirror and host-specific extras for the selected supported host

## Supported Hosts

暂时只支持：

- `codex`
- `claude-code`
- `cursor`

`TargetRoot` 是文件路径。
`HostId` / `--host` 才是宿主选择。

## Recommended Commands

### Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId codex
pwsh -File .\check.ps1 -HostId codex -Profile full -Deep
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId claude-code
pwsh -File .\check.ps1 -HostId claude-code -Profile full -Deep
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId cursor -TargetRoot "$env:USERPROFILE\.cursor"
pwsh -File .\check.ps1 -HostId cursor -TargetRoot "$env:USERPROFILE\.cursor" -Profile full -Deep
```

### Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex
bash ./check.sh --host codex --profile full --deep
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code
bash ./check.sh --host claude-code --profile full --deep
bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --target-root "${HOME}/.cursor"
bash ./check.sh --host cursor --target-root "${HOME}/.cursor" --profile full --deep
```

## Truth Boundaries

- `codex` 是当前最完整的 repo-governed 路径
- `claude-code` 是 preview guidance，不是 full closure
- `cursor` 是 preview guidance，不是 full closure
- hook 当前因兼容性问题被冻结，`codex` / `claude-code` / `cursor` 都不提供 hook 安装
- `claude-code` 不再写 `settings.vibe.preview.json`
- provider 的 `url` / `apikey` / `model` 仍然是本地用户侧配置
- 安装提示必须告诉用户去本地 settings 或本地环境变量里配置，不要让用户把密钥贴到聊天里
