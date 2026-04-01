# Multi-Host Install Command Reference

> Most users should start with:
>
> - [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
> - [`manual-copy-install.en.md`](./manual-copy-install.en.md)
> - [`openclaw-path.en.md`](./openclaw-path.en.md)
> - [`opencode-path.en.md`](./opencode-path.en.md)

This document summarizes the install commands and default roots for the six supported hosts.

Public Linux / macOS prerequisites:

- the shell entrypoints are maintained against the macOS system Bash 3.2 baseline
- `python3` / `python` must satisfy **Python 3.10+**
- launching from `zsh` is not the actual problem; the real compatibility boundary is the resolved `bash` / `python3` version

## Supported Hosts and Install Styles

| Host | Install style | Default root | Notes |
| --- | --- | --- | --- |
| `codex` | one-shot setup + check | `~/.codex` | default recommended path |
| `claude-code` | one-shot setup + check | `~/.claude` | supported install-and-use path |
| `cursor` | one-shot setup + check | `~/.cursor` | supported install-and-use path |
| `windsurf` | one-shot setup + check | `~/.codeium/windsurf` | supported install-and-use path |
| `openclaw` | one-shot setup + check | `OPENCLAW_HOME` or `~/.openclaw` | host-specific details: [`openclaw-path.en.md`](./openclaw-path.en.md) |
| `opencode` | direct install + check | `OPENCODE_HOME` or `~/.config/opencode` | host-specific details: [`opencode-path.en.md`](./opencode-path.en.md) |

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
- for the built-in governance-advice path, prefer:
  - `VCO_INTENT_ADVICE_API_KEY`
  - optional `VCO_INTENT_ADVICE_BASE_URL`
  - `VCO_INTENT_ADVICE_MODEL`
  - `VCO_VECTOR_DIFF_API_KEY` / `VCO_VECTOR_DIFF_BASE_URL` / `VCO_VECTOR_DIFF_MODEL` (optional embeddings that degrade gracefully)

### Claude Code

- this host has a supported install-and-use path
- it preserves the real `~/.claude/settings.json` while merging a bounded managed `vibeskills` settings surface
- broader Claude plugins, MCP registration, credentials, and host behavior still remain host-managed
- for the built-in governance-advice path, prefer `VCO_INTENT_ADVICE_API_KEY` + optional `VCO_INTENT_ADVICE_BASE_URL` + `VCO_INTENT_ADVICE_MODEL`; configure `VCO_VECTOR_DIFF_*` only when you also want vector-diff embeddings

### Cursor

- this host has a supported install-and-use path
- it does not overwrite the real `~/.cursor/settings.json`
- Cursor-native settings and extension surfaces remain managed on the Cursor side

### Windsurf

- the default root is `~/.codeium/windsurf`
- the repo currently owns only shared runtime payload plus sidecar state such as `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- Windsurf-native local settings remain managed on the Windsurf side

### OpenClaw

- the default target root is `OPENCLAW_HOME` or `~/.openclaw`
- the dedicated host guide expands attach / copy / bundle details
- OpenClaw-local configuration remains managed on the OpenClaw side

### OpenCode

- the default target root is `OPENCODE_HOME`, otherwise `~/.config/opencode`
- direct install/check writes skills, `.vibeskills/*` sidecars, and `opencode.json.example`
- the real `opencode.json`, provider credentials, plugin installation, and MCP trust remain host-managed
- use `--target-root ./.opencode` when you want project-local isolation
