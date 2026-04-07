# Multi-Host Install Command Reference

> Most users should start with:
>
> - [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
> - [`manual-copy-install.en.md`](./manual-copy-install.en.md)
> - [`openclaw-path.en.md`](./openclaw-path.en.md)
> - [`opencode-path.en.md`](./opencode-path.en.md)

This document summarizes the install commands, default target roots, and current host-mode wording for the six public hosts.

## MCP Auto-Provision Contract

All six public hosts now follow one shared, non-blocking MCP contract:

- install or one-shot should attempt `github`, `context7`, `serena`, `scrapling`, and `claude-flow`
- the completion target for those MCPs must be the host's real **native MCP surface**
- `$vibe` or `/vibe` is governed runtime entry only and is not MCP completion
- repo templates, manifests, `*.json.example`, `.vibeskills/*` sidecars, and PATH-visible commands do not by themselves count as host-visible ready
- prefer host-native registration for `github`, `context7`, and `serena`
- prefer scripted CLI / stdio installation for `scrapling` and `claude-flow`
- if native auto-registration fails, or the current host does not expose a stable officially supportable auto-registration interface, the report must say that the MCP is still outside the host's native MCP surface rather than claiming success through `$vibe`, templates, or sidecars
- failure does not block the base install; failures are summarized only in the final report
- the final report separates `installed locally`, `vibe host-ready`, `mcp native auto-provision attempted`, per-MCP `host-visible readiness`, `manual follow-up`, and `online-ready`

Public Linux / macOS prerequisites:

- the shell entrypoints are maintained against the macOS system Bash 3.2 baseline
- `python3` / `python` must satisfy **Python 3.10+**
- launching from `zsh` is not the actual problem; the real compatibility boundary is the resolved `bash` / `python3` version

## Supported Hosts and Default Paths

| Host | Default command surface | Default root | Current wording |
| --- | --- | --- | --- |
| `codex` | one-shot setup + check | real `~/.codex` by default through `CODEX_HOME`; use `~/.vibeskills/targets/codex` only for explicit isolation | strongest governed lane |
| `claude-code` | one-shot setup + check | real `~/.claude` by default through `CLAUDE_HOME` | supported install/use path with bounded managed closure |
| `cursor` | one-shot setup + check | real `~/.cursor` by default through `CURSOR_HOME` | preview-guidance path |
| `windsurf` | one-shot setup + check | `WINDSURF_HOME` or the real host root `~/.codeium/windsurf` | runtime-core path |
| `openclaw` | one-shot setup + check | `OPENCLAW_HOME` or the real host root `~/.openclaw` | preview runtime-core adapter path |
| `opencode` | direct install + check (thinner) or one-shot wrapper | `OPENCODE_HOME` or the real host root `~/.config/opencode` | preview-guidance adapter path |

`TargetRoot` is only a path.
`HostId` / `--host` decides host semantics.

## Recommended Commands

Default full install:

### Codex

If the goal is to install and let the current Codex discover `$vibe` directly, the default target root must be the real host root `~/.codex`.
Switch to `~/.vibeskills/targets/codex` only when you explicitly want an isolated install, or the current Codex is already pointed there on purpose.

```powershell
$env:CODEX_HOME="$HOME\\.codex"
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId codex -Profile full
pwsh -File .\check.ps1 -HostId codex -Profile full -Deep
```

```bash
CODEX_HOME="$HOME/.codex" bash ./scripts/bootstrap/one-shot-setup.sh --host codex --profile full
CODEX_HOME="$HOME/.codex" bash ./check.sh --host codex --profile full --deep
```

### Claude Code

If the goal is to install into the real Claude host root, the default target should be `~/.claude`.

```powershell
$env:CLAUDE_HOME="$HOME\\.claude"
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId claude-code -Profile full
pwsh -File .\check.ps1 -HostId claude-code -Profile full -Deep
```

```bash
CLAUDE_HOME="$HOME/.claude" bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code --profile full
CLAUDE_HOME="$HOME/.claude" bash ./check.sh --host claude-code --profile full --deep
```

### Cursor

If the goal is to install into the real Cursor host root, the default target should be `~/.cursor`.

```powershell
$env:CURSOR_HOME="$HOME\\.cursor"
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId cursor -Profile full
pwsh -File .\check.ps1 -HostId cursor -Profile full -Deep
```

```bash
CURSOR_HOME="$HOME/.cursor" bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --profile full
CURSOR_HOME="$HOME/.cursor" bash ./check.sh --host cursor --profile full --deep
```

### Windsurf

The default target root is `~/.codeium/windsurf` unless you explicitly set `WINDSURF_HOME`.

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId windsurf -Profile full
pwsh -File .\check.ps1 -HostId windsurf -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host windsurf --profile full
bash ./check.sh --host windsurf --profile full --deep
```

### OpenClaw

The default target root is `~/.openclaw` unless you explicitly set `OPENCLAW_HOME`.

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId openclaw -Profile full
pwsh -File .\check.ps1 -HostId openclaw -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

### OpenCode

The thinner default path is:

The default target root is `~/.config/opencode` unless you explicitly set `OPENCODE_HOME`.

```powershell
pwsh -NoProfile -File .\install.ps1 -HostId opencode -Profile full
pwsh -NoProfile -File .\check.ps1 -HostId opencode -Profile full
```

```bash
bash ./install.sh --host opencode --profile full
bash ./check.sh --host opencode --profile full
```

If you prefer to keep the same bootstrap wrapper as other hosts, this is also valid:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -HostId opencode -Profile full
pwsh -File .\check.ps1 -HostId opencode -Profile full -Deep
```

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host opencode --profile full
bash ./check.sh --host opencode --profile full --deep
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
- add `VCO_VECTOR_DIFF_*` only when you also want vector diff embeddings

### Claude Code

- it preserves the real `~/.claude/settings.json` while merging a bounded managed `vibeskills` settings surface
- broader Claude plugins, MCP registration, credentials, and host behavior remain host-managed
- AI governance advice uses `VCO_INTENT_ADVICE_*`, with optional `VCO_VECTOR_DIFF_*`

### Cursor

- this host is currently a preview-guidance path
- it does not overwrite the real `~/.cursor/settings.json`
- Cursor-native settings and extension surfaces remain managed on the Cursor side

### Windsurf

- the default target root is `WINDSURF_HOME`, otherwise the real host root `~/.codeium/windsurf`
- the repo currently owns only shared runtime payload plus sidecar state such as `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- Windsurf-native local settings remain managed on the Windsurf side

### OpenClaw

- the default target root is `OPENCLAW_HOME` or the real host root `~/.openclaw`
- the dedicated host guide expands attach / copy / bundle details
- OpenClaw-local configuration remains managed on the OpenClaw side

### OpenCode

- the default target root is `OPENCODE_HOME`, otherwise the real host root `~/.config/opencode`
- the real host config directory `~/.config/opencode` remains host-managed
- both direct install/check and the one-shot wrapper keep host-managed boundaries intact
- the real `opencode.json`, provider credentials, plugin installation, and MCP trust remain host-managed
- use `--target-root ./.opencode` when you want project-local isolation
