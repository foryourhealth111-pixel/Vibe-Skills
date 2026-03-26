# Cold-Start Install Paths

This document answers the only cold-start questions that matter right now: which hosts are supported, and what the shortest truth-first install path looks like for each.

## One-Line Conclusion

The current public surface supports five hosts:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`

Within that scope:

- `codex`: governed path
- `claude-code`: preview guidance
- `cursor`: preview guidance
- `windsurf`: preview runtime-core
- `openclaw`: `preview` / `runtime-core-preview` / `runtime-core`

Other hosts should not currently be described as supported installation targets.

## Codex

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex --profile full
bash ./check.sh --host codex --profile full --deep
```

What you get:

- governed runtime payload
- local settings / MCP guidance
- deep health check

What you do not get:

- automatic hooks
- automatic governance-AI online readiness

## Claude Code

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code --profile full
bash ./check.sh --host claude-code --profile full --deep
```

What you get:

- preview-guidance payload
- preview health check

What you do not get:

- full closure
- overwrite of the real `~/.claude/settings.json`
- automatic hooks

## Cursor

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --profile full
bash ./check.sh --host cursor --profile full --deep
```

What you get:

- preview-guidance payload
- preview health check

What you do not get:

- full closure
- overwrite of the real `~/.cursor/settings.json`
- Cursor host-native provider / MCP / hook closure

## Windsurf

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host windsurf --profile full
bash ./check.sh --host windsurf --profile full --deep
```

What you get:

- shared runtime payload
- a runtime-core preview install under `~/.codeium/windsurf`
- optional `mcp_config.json` materialization
- optional `global_workflows/` materialization

What you do not get:

- full closure
- automatic takeover of host-local configuration

## OpenClaw

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

What you get:

- shared runtime payload
- an OpenClaw runtime-core preview install path, with default target root from `OPENCLAW_HOME` or `~/.openclaw`
- explicit attach / copy / bundle path semantics:
  - attach: connect and validate an existing `OPENCLAW_HOME` (or `~/.openclaw`) target root
  - copy: use install/check entrypoints to copy runtime-core payload into the target root
  - bundle: consume runtime-core distribution manifests from `dist/host-openclaw/manifest.json` and `dist/manifests/vibeskills-openclaw.json`
- explicit host-managed boundaries
- a runtime-core-focused install, validation, and distribution path

What you do not get:

- full closure
- automatic takeover of OpenClaw-local configuration

## Boundaries That Must Hold During Cold Start

- `HostId` / `--host` decides host semantics
- hooks remain frozen across the current public surface; that is not an install failure
- if local provider fields are not configured, the environment must not be described as online-ready
- do not ask users to paste secrets into chat
