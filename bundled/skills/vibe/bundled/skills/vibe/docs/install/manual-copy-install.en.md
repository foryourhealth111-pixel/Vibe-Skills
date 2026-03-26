# Manual Copy Install (Offline / No-Admin)

If you do not want to run the install scripts, this path solves only one thing: copying the repo files into the target host root.

The current public host surface includes:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`

## Core Files To Copy

Copy these into the target root:

- `skills/`
- `commands/`
- `config/upstream-lock.json`
- `skills/vibe/`

## Default Host Roots

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` or `~/.openclaw`

If the target is `windsurf`, also note:

- mirror `commands/` into `global_workflows/` if you want parity with the scripted result
- copy `mcp/servers.template.json` to `mcp_config.json` when it is missing

## What You Still Need To Do Yourself

### Codex

- maintain `~/.codex/settings.json`
- configure `OPENAI_*` if needed
- add `VCO_AI_PROVIDER_*` if you also want the governance-AI online layer

### Claude Code

- maintain `~/.claude/settings.json`
- add `VCO_AI_PROVIDER_*` if needed

### Cursor

- maintain `~/.cursor/settings.json`
- add local provider / MCP configuration as needed

### Windsurf

- confirm `mcp_config.json` and `global_workflows/` under `~/.codeium/windsurf`
- finish host-local configuration inside Windsurf itself

### OpenClaw

- confirm the runtime-core payload under `OPENCLAW_HOME` or `~/.openclaw`
- use the attach / copy / bundle guidance when you want parity with the scripted path
- finish host-local configuration inside OpenClaw itself

## What This Path Does Not Complete Automatically

- hook installation
- provider credential wiring
- automatic takeover of host-local configuration

Across the current public surface, none of the five hosts should be described as “hooks installed automatically.”
