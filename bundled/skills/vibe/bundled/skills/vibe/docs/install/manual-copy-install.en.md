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

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `OPENCLAW_HOME` or `~/.openclaw`
- `opencode` -> `OPENCODE_HOME` or `~/.config/opencode`

If the target is `windsurf`, also note:

- mirror `commands/` into `global_workflows/` if you want parity with the scripted result
- copy `mcp/servers.template.json` to `mcp_config.json` when it is missing

If the target is `opencode`, switch to the OpenCode preview payload:

- `skills/`
- `commands/*.md`
- `command/*.md`
- `agents/*.md`
- `agent/*.md`
- `opencode.json.example`

Then use [`opencode-path.en.md`](./opencode-path.en.md) for the preview-adapter follow-up steps.

## What You Still Need To Do Yourself

### Codex

- maintain `~/.codex/settings.json`
- for the common OpenAI-compatible governance-advice path, prefer:
  - `OPENAI_API_KEY`
  - optional `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`

### Claude Code

- maintain `~/.claude/settings.json`
- for the common OpenAI-compatible governance-advice path, prefer:
  - `OPENAI_API_KEY`
  - optional `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`

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

### OpenCode

- confirm the preview payload under `OPENCODE_HOME` or `~/.config/opencode`
- keep the real `opencode.json`, provider credentials, plugin installation, and MCP trust host-managed
- use `./.opencode` when you want a project-local isolated target

## What This Path Does Not Complete Automatically

- hook installation
- provider credential wiring
- automatic takeover of host-local configuration

Across the current public surface, none of the six hosts should be described as “hooks installed automatically.”
