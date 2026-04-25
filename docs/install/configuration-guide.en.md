# Post-Install Configuration Boundaries

This document explains what VibeSkills owns after install and what remains owned by the host or the user.

The public install flow does not currently expose user-facing configuration for built-in online enhancement features. Install assistants should not ask users for providers, credentials, URLs, or model names, and those values should not be treated as prerequisites for a successful base install.

## Separate These States

| State | Meaning |
|:---|:---|
| `installed locally` | Files were written into the target host root |
| `vibe host-ready` | The host can discover the `vibe` / `vibe-upgrade` entries |
| `online-ready` | Extra online capabilities are actually available when required |

`installed locally` does not imply `online-ready`.

`$vibe` or `/vibe` only means the governed runtime entry is available. It is not MCP completion and not proof that providers, plugins, credentials, or host-native MCP surfaces are fully configured.

## What Install Reports Should Say

Do not collapse the result into one vague success line. Report these separately:

- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`
- host-side manual follow-up

If a capability has not been configured through the public install path, report it as not ready or not verified.

## What Public Install Should Not Ask For

The public install flow does not currently guide users through built-in online enhancement configuration. Install assistants should not:

- ask users to paste secrets into chat
- ask users for provider URLs
- ask users for model names
- describe missing local online configuration as a base install failure
- turn basic host readiness into an online enhancement readiness claim

## Host Ownership Boundaries

### Codex

- target root: default `CODEX_HOME` to the real `~/.codex` when the goal is for the current Codex to discover `$vibe`
- use `~/.vibeskills/targets/codex` only for explicit isolation
- host login state, providers, plugins, and MCP trust remain Codex-side concerns

### Claude Code

- default `CLAUDE_HOME` to the real `~/.claude`
- the installer only merges the bounded VibeSkills settings surface
- broader Claude settings, plugins, credentials, and MCP registration remain host-managed

### Cursor

- default `CURSOR_HOME` to the real `~/.cursor`
- the repo does not take over Cursor's real settings or extension surface
- Cursor-native settings and extensions remain managed through Cursor

### Windsurf

- target root: `WINDSURF_HOME` or the real host root `~/.codeium/windsurf`
- repo-side files to inspect: `<target-root>/.vibeskills/host-settings.json` and `<target-root>/.vibeskills/host-closure.json`
- those files prove repo-owned sidecar state only, not host-side login, provider, or plugin readiness

### OpenClaw

- target root: `OPENCLAW_HOME` or the real host root `~/.openclaw`
- the repo owns only the runtime-core payload and sidecar state
- host-local configuration remains an OpenClaw-side concern

### OpenCode

- target root: `OPENCODE_HOME` or the real host root `~/.config/opencode`
- the real host config directory remains `~/.config/opencode`
- `<target-root>/opencode.json.example` is only a reference scaffold, not the live host config
- the real `opencode.json`, provider credentials, plugin installation, and MCP trust remain host-managed

## Uninstall

When you need to reverse an install, use the repo-root uninstall entrypoint:

- Windows: `uninstall.ps1 -HostId <host>`
- Linux / macOS: `uninstall.sh --host <host>`

The uninstallers honor the ledger-first, owned-only contract described in [`docs/uninstall-governance.md`](../uninstall-governance.md): they only delete Vibe-managed surfaces recorded in the install ledger, closure manifest, or documented legacy payloads, and remove only the managed `vibeskills` nodes from shared config files.
