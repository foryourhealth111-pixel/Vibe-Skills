# Install Path: Advanced Host / Lane Reference

> Most users should start with:
>
> - [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
> - [`manual-copy-install.en.md`](./manual-copy-install.en.md)

This document explains the current real support boundary and the concrete commands per host.

## Current Supported Surface

| Host | Mode | Default root | Current wording |
| --- | --- | --- | --- |
| `codex` | governed | `~/.codex` | strongest supported path today |
| `claude-code` | supported install-and-use path | `~/.claude` | keeps real host settings boundaries explicit |
| `cursor` | supported install-and-use path | `~/.cursor` | keeps real host settings boundaries explicit |
| `windsurf` | supported install-and-use path + runtime adapter | `~/.codeium/windsurf` | includes runtime-adapter integration while keeping real host settings boundaries explicit |
| `openclaw` | `preview` / `runtime-core-preview` / `runtime-core` | `OPENCLAW_HOME` or `~/.openclaw` | focused on runtime-core payload install, validation, and distribution |

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

## Boundaries That Must Stay Explicit

### Codex

- this is the governed path
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

- this host has a supported install-and-use path with runtime-adapter integration
- the default root is `~/.codeium/windsurf`
- the repo currently owns only shared runtime payload plus optional materialization of `mcp_config.json` and `global_workflows/`
- Windsurf-native local settings remain managed on the Windsurf side

### OpenClaw

- this host is described with the `preview` / `runtime-core-preview` / `runtime-core` wording
- the default target root is `OPENCLAW_HOME` or `~/.openclaw`
- attach / copy / bundle center on runtime-core payload install, validation, and distribution
- OpenClaw-local configuration remains managed on the OpenClaw side
