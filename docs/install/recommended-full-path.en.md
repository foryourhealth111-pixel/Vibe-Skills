# Multi-Host Install Command Reference

> Most users should start with:
>
> - [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
> - [`manual-copy-install.en.md`](./manual-copy-install.en.md)
> - [`openclaw-path.en.md`](./openclaw-path.en.md)
> - [`opencode-path.en.md`](./opencode-path.en.md)

This document summarizes the install commands and default target roots for the six supported hosts.

## Supported Hosts and Install Styles

| Host          | Install style          | Default target root                                  | Notes                                                                 |
| ------------- | ---------------------- | ---------------------------------------------------- | --------------------------------------------------------------------- |
| `codex`       | one-shot setup + check | `CODEX_HOME` or `~/.vibeskills/targets/codex`        | default recommended path                                              |
| `claude-code` | one-shot setup + check | `CLAUDE_HOME` or `~/.vibeskills/targets/claude-code` | supported install-and-use path                                        |
| `cursor`      | one-shot setup + check | `CURSOR_HOME` or `~/.vibeskills/targets/cursor`      | supported install-and-use path                                        |
| `windsurf`    | one-shot setup + check | `WINDSURF_HOME` or `~/.vibeskills/targets/windsurf`  | supported install-and-use path                                        |
| `openclaw`    | one-shot setup + check | `OPENCLAW_HOME` or `~/.vibeskills/targets/openclaw`  | host-specific details: [`openclaw-path.en.md`](./openclaw-path.en.md) |
| `opencode`    | direct install + check | `OPENCODE_HOME` or `~/.vibeskills/targets/opencode`  | host-specific details: [`opencode-path.en.md`](./opencode-path.en.md) |

`TargetRoot` is only a path.
`HostId` / `--host` decides host semantics.

## Recommended Commands

Default full install:

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

### OpenCode

```powershell
pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile full
pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile full
```

```bash
bash ./install.sh --host opencode --profile full
bash ./check.sh --host opencode --profile full
```

If you want the “Framework Only + Customizable Governance” variant, replace `full` with `minimal`.

## Upgrade Flow

If you still have a local checkout, update the repo first and then rerun the same commands:

```bash
git pull origin main
```

If you follow tagged releases instead of `main`, use:

```bash
git fetch --tags --force
git checkout vX.Y.Z
```

## What You Still Handle Locally After Install

### Codex

- hooks remain frozen; that is not an install failure
- `OPENAI_*` only covers Codex base online provider access
- `VCO_AI_PROVIDER_*` is the optional governance-AI online layer

### Claude Code

- this host has a supported install-and-use path
- it does not overwrite the real `~/.claude/settings.json`
- hooks remain frozen; that is not an install failure

### Cursor

- this host has a supported install-and-use path
- it does not overwrite the real `~/.cursor/settings.json`
- Cursor-native settings and extension surfaces remain managed on the Cursor side

### Windsurf

- the default target root is `WINDSURF_HOME` or `~/.vibeskills/targets/windsurf`
- the repo currently owns only shared runtime payload plus optional materialization of `mcp_config.json` and `global_workflows/`
- Windsurf-native local settings remain managed on the Windsurf side

### OpenClaw

- the default target root is `OPENCLAW_HOME` or `~/.vibeskills/targets/openclaw`
- the dedicated host guide expands attach / copy / bundle details
- OpenClaw-local configuration remains managed on the OpenClaw side

### OpenCode

- the default target root is `OPENCODE_HOME` or `~/.vibeskills/targets/opencode`
- direct install/check writes skills, command/agent wrappers, and `opencode.json.example`
- the real `opencode.json`, provider credentials, plugin installation, and MCP trust remain host-managed
- use `--target-root ./.opencode` when you want project-local isolation
