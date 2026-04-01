# Cold-Start Install Paths

This document answers the only cold-start questions that matter right now: which hosts are supported, and what the shortest truth-first install path looks like for each.

## One-Line Conclusion

The current public surface supports six hosts:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

Within that scope:

- `codex`: governed path
- `claude-code`: supported install-and-use path with bounded managed closure
- `cursor`: preview guidance
- `windsurf`: preview runtime-core
- `openclaw`: `preview` / `runtime-core-preview` / `runtime-core`
- `opencode`: preview adapter

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

- bounded managed `vibeskills` settings surface
- incremental merge and verification against the real `~/.claude/settings.json`
- supported-with-constraints health check

What you do not get:

- full closure
- overwrite of the real `~/.claude/settings.json`
- automatic takeover of broader Claude plugin / MCP / credential surfaces

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
- `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- a skills-only activation path that stays dormant until Vibe is explicitly invoked

What you do not get:

- full closure
- automatic takeover of host-local config files

## OpenClaw

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

What you get:

- shared runtime payload
- an OpenClaw runtime-core preview install path, with default target root from `OPENCLAW_HOME` or `~/.openclaw`
- `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- explicit attach / copy / bundle path semantics:
  - attach: connect and validate an existing `OPENCLAW_HOME` (or `~/.openclaw`) target root
  - copy: use install/check entrypoints to copy runtime-core payload into the target root
  - bundle: consume runtime-core distribution manifests from `dist/host-openclaw/manifest.json` and `dist/manifests/vibeskills-openclaw.json`
- explicit host-managed boundaries
- a runtime-core-focused install, validation, and distribution path

What you do not get:

- full closure
- automatic takeover of OpenClaw-local configuration

## OpenCode

```bash
bash ./install.sh --host opencode
bash ./check.sh --host opencode
```

What you get:

- runtime-core payload
- Vibe-Skills skill payload
- `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- `opencode.json.example`

What you do not get:

- one-shot bootstrap
- overwrite of the real `~/.config/opencode/opencode.json`
- automatic plugin installation
- automatic provider credential wiring
- automatic MCP trust decisions

Next actions:

- the default target root is `OPENCODE_HOME`, otherwise `~/.config/opencode`
- for project-local isolation, use `--target-root ./.opencode`
- read [`install/opencode-path.en.md`](./install/opencode-path.en.md)

## Boundaries That Must Hold During Cold Start

- `HostId` / `--host` decides host semantics
- hooks are not uniform across the current public surface: Codex/Cursor keep hooks frozen, and Claude also avoids repo-managed hook installation
- if local provider fields are not configured, the environment must not be described as online-ready
- do not ask users to paste secrets into chat
