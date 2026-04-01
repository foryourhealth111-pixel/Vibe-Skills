# Deployment

## Profiles

- `minimal`: governance foundation install
- `full`: full install with optional workflow extras

## Supported Hosts

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

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
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId openclaw -Profile full
pwsh -File .\check.ps1 -HostId openclaw -Profile full -Deep
pwsh -NoProfile -File .\install.ps1 -HostId opencode
pwsh -NoProfile -File .\check.ps1 -HostId opencode
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
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
bash ./install.sh --host opencode
bash ./check.sh --host opencode
```

## Truth Boundaries

- `codex` is the strongest governed path today
- `claude-code` has a supported install-and-use path and does not overwrite the real host settings
- `claude-code` merges a bounded managed `vibeskills` settings surface into the real host settings while leaving broader host behavior managed on the Claude side
- `cursor` has a supported install-and-use path and does not overwrite the real host settings
- `windsurf` has a supported install-and-use path with runtime-adapter integration
- `openclaw` is documented as `preview` / `runtime-core-preview` / `runtime-core`, with default target root from `OPENCLAW_HOME` or `~/.openclaw`
- `opencode` is documented as a preview-adapter path that uses direct install/check
- hooks are not uniform on the current public surface: Codex/Cursor remain frozen, and Claude also avoids repo-managed hook installation
- `windsurf` defaults to `~/.codeium/windsurf` and only gets shared runtime payload plus optional `mcp_config.json` / `global_workflows/` materialization
- `openclaw` keeps runtime-core payload install, validation, and distribution explicit through attach / copy / bundle
- `opencode` defaults to `OPENCODE_HOME`, otherwise `~/.config/opencode`, and keeps the real `opencode.json`, plugin install, and MCP trust host-managed
- provider `url` / `apikey` / `model` values remain local user configuration
