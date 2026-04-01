# Host Plugin and Host Configuration Policy

This document answers only three questions:

- which hosts are on the current public support surface
- what the repo currently handles automatically
- what still must be completed locally by the host side

## Current Public Surface

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

Other agents should not currently be described as having a supported install path.

## Global Principle

- install the repo-distributed content first
- add host-local configuration only as needed
- if a capability is not stably, publicly, and verifiably owned by the repo, do not write it as a default install requirement
- for OpenClaw, make the default root explicit: `OPENCLAW_HOME` or `~/.openclaw`
- keep deeper OpenClaw path details in the dedicated host guide
- for OpenCode, make the default root explicit: `OPENCODE_HOME` or `~/.config/opencode`
- for OpenCode, make it explicit that direct install/check does not take ownership of the real `opencode.json`
- for deeper host contracts and proof details, point readers to the host guides or `dist/*` / `adapters/*`

## Codex

- currently the strongest path
- guidance stays centered on local settings, MCP, and optional CLI enhancements
- hooks remain frozen; that is not an install failure

## Claude Code

- supported install-and-use path
- not integrated by “adding a pile of host plugins”
- preserves the real `~/.claude/settings.json` while merging a bounded managed `vibeskills` settings surface
- plugin enablement, MCP registration, credentials, and broader Claude behavior remain host-managed

## Cursor

- supported install-and-use path
- does not overwrite the real `~/.cursor/settings.json`
- Cursor-native plugins, settings, and extension surfaces remain managed on the Cursor side
- hooks remain frozen; that is not an install failure

## Windsurf

- supported install-and-use path
- default root is `~/.codeium/windsurf`
- the repo currently owns only shared install content plus sidecar state such as `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- Windsurf-native local settings remain managed on the Windsurf side

## OpenClaw

- supported install-and-use path
- default target root is `OPENCLAW_HOME` or `~/.openclaw`
- deeper attach / copy / bundle guidance lives in [`openclaw-path.en.md`](./openclaw-path.en.md)
- OpenClaw-local configuration remains managed on the OpenClaw side

## OpenCode

- supported install-and-use path
- default target root is `OPENCODE_HOME` or `~/.config/opencode`
- direct install/check writes skills, `.vibeskills/*` sidecars, and `opencode.json.example`
- the real `opencode.json`, provider credentials, plugin installation, and MCP trust remain managed on the OpenCode side

## Recommended Community Wording

- the current version supports `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, and `opencode`
- `codex` is the default recommended path
- `claude-code` and `cursor` have a supported install-and-use path
- `windsurf` has a supported install-and-use path
- `openclaw` has a supported install-and-use path, with default root from `OPENCLAW_HOME` or `~/.openclaw`
- `opencode` has a supported install-and-use path, with default root from `OPENCODE_HOME` or `~/.config/opencode`
- `opencode` uses direct install/check and does not take ownership of the real `opencode.json`
- hooks are not one-size-fits-all across the current public surface: Codex/Cursor keep hooks frozen, and Claude now also avoids repo-managed hook installation because of compatibility risk
- provider `url` / `apikey` / `model` values stay local and should not be pasted into chat
