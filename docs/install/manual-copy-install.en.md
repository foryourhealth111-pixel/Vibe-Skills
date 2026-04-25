# Manual Copy Install (Offline / No-Admin)

If you do not want to run the install scripts, this path solves only one thing: copying the repo files into the target host root.

The current public host surface includes:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

## Core Files To Copy

Copy these into the target root:

- `skills/`
- `commands/`
- `config/upstream-lock.json`
- `skills/vibe/`

## Default Host Roots

- `codex` -> default `CODEX_HOME` to the real `~/.codex`; if you want the current Codex to discover `$vibe` after the copy, do not default to `~/.vibeskills/targets/codex`
- `claude-code` -> default `CLAUDE_HOME` to the real `~/.claude`
- `cursor` -> default `CURSOR_HOME` to the real `~/.cursor`
- `windsurf` -> `WINDSURF_HOME` or the real host root `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` or the real host root `~/.openclaw`
- `opencode` -> `OPENCODE_HOME` or the real host root `~/.config/opencode`

If the target is `windsurf`, also note:

- if you need exact parity with the current scripted result, prefer rerunning `install.* --host windsurf`
- the current public contract uses `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json` as the host sidecars instead of `mcp_config.json` / `global_workflows/`

If the target is `opencode`, switch to the OpenCode preview payload:

- `skills/`
- `.vibeskills/host-settings.json`
- `.vibeskills/host-closure.json`
- `.vibeskills/install-ledger.json`
- `.vibeskills/bin/*-specialist-wrapper.*`
- `opencode.json.example`

Then use [`opencode-path.en.md`](./opencode-path.en.md) for the preview-adapter follow-up steps.

## What You Still Need To Do Yourself

### Codex

- maintain `~/.codex/settings.json`
- manual copy does not complete host-side provider, plugin, or MCP authorization
- the public manual path does not currently guide built-in online enhancement configuration

### Claude Code

- maintain `~/.claude/settings.json`
- manual copy does not complete Claude-side provider, plugin, or MCP authorization
- the public manual path does not currently guide built-in online enhancement configuration

### Cursor

- maintain `~/.cursor/settings.json`
- add local provider / MCP configuration as needed

### Windsurf

- confirm `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json` under `WINDSURF_HOME` or the real host root `~/.codeium/windsurf`
- finish host-local configuration inside Windsurf itself

### OpenClaw

- confirm the runtime-core payload under `OPENCLAW_HOME` or the real host root `~/.openclaw`
- use the attach / copy / bundle guidance when you want parity with the scripted path
- finish host-local configuration inside OpenClaw itself

### OpenCode

- confirm the preview payload under `OPENCODE_HOME` or the real host root `~/.config/opencode`
- the real `~/.config/opencode/opencode.json` remains host-managed
- keep the real `opencode.json`, provider credentials, plugin installation, and MCP trust host-managed
- use `./.opencode` when you want a project-local isolated target

## What This Path Does Not Complete Automatically

- hook installation
- provider credential wiring
- automatic takeover of host-local configuration

Across the current public surface, none of the six hosts should be described as “hooks installed automatically.”
