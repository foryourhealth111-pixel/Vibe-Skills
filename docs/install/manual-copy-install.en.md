# Manual Copy Install (Offline / No-Admin / Other Agents)

This is the second main install path.

Use it when:

- you do not want AI to execute install commands for you
- the environment is offline
- you do not have admin rights
- your target host is not `codex`, `claude-code`, or `opencode`
- you only want to place the runtime-core first and wire the host yourself later

## What You Get

Manual copy install gives you **runtime-core**, not host-native closure.

That means you get:

- `skills/`
- `commands/`
- `config/upstream-lock.json`
- `config/skills-lock.json` if present
- the canonical `skills/vibe/` runtime mirror

It does **not** automatically give you:

- host plugin provisioning
- MCP registration
- provider credential wiring
- host-native settings closure

## Manual Copy Steps

Assume your target directory is: `<TARGET_ROOT>`

1. Create the target directory layout

```bash
mkdir -p <TARGET_ROOT>/skills <TARGET_ROOT>/commands <TARGET_ROOT>/config
```

2. Copy runtime-core skills

```bash
cp -R ./bundled/skills/. <TARGET_ROOT>/skills/
```

3. Copy commands

```bash
cp -R ./commands/. <TARGET_ROOT>/commands/
```

4. Copy lock files

```bash
cp ./config/upstream-lock.json <TARGET_ROOT>/config/upstream-lock.json
cp ./config/skills-lock.json <TARGET_ROOT>/config/skills-lock.json
```

If `skills-lock.json` is not present, skip it.

## The Most Important Rule For Other Agents

If you are not installing into `codex`, and especially if you are wiring another agent, you must provide these three values yourself:

- `url`
- `apikey`
- `model`

If those three values are not explicitly configured, the environment must not be described as online-ready.

## Short Prompt For Other Agents

You can place this in the target agent's system prompt or developer prompt:

```text
You are running with VibeSkills runtime-core.
Before claiming the environment is ready, check whether the user has explicitly provided:
- url
- apikey
- model
If any of them is missing, clearly remind the user to provide all three first.
Do not describe the environment as online-ready if they are missing.
```

## When Not To Use This Path

Prefer prompt-based install instead when:

- you are installing into `codex`
- you are installing into `claude-code`
- you want the script to run install + check for you
- you want AI to select the correct lane first

Main entry:

- [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
