# Deployment

## Profiles

- `minimal`: governance foundation install
- `full`: full install with optional workflow extras

## Supported Hosts

- `codex`
- `claude-code`
- `cursor`
- `windsurf`

`TargetRoot` is only the filesystem path.
`HostId` / `--host` decides host semantics.

## Recommended Commands

### Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId codex -Profile full
pwsh -File .\check.ps1 -HostId codex -Profile full -Deep
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId claude-code -Profile full
pwsh -File .\check.ps1 -HostId claude-code -Profile full -Deep
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId cursor -Profile full
pwsh -File .\check.ps1 -HostId cursor -Profile full -Deep
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId windsurf -Profile full
pwsh -File .\check.ps1 -HostId windsurf -Profile full -Deep
```

### Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex --profile full
bash ./check.sh --host codex --profile full --deep
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code --profile full
bash ./check.sh --host claude-code --profile full --deep
bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --profile full
bash ./check.sh --host cursor --profile full --deep
bash ./scripts/bootstrap/one-shot-setup.sh --host windsurf --profile full
bash ./check.sh --host windsurf --profile full --deep
```

## Truth Boundaries

- `codex` is the strongest governed path today
- `claude-code` has a supported install-and-use path and does not overwrite the real host settings
- `cursor` has a supported install-and-use path and does not overwrite the real host settings
- `windsurf` has a supported install-and-use path with runtime-adapter integration
- hooks remain frozen on the current public surface
- `windsurf` defaults to `~/.codeium/windsurf` and only gets shared runtime payload plus optional `mcp_config.json` / `global_workflows/` materialization
- provider `url` / `apikey` / `model` values remain local user configuration
