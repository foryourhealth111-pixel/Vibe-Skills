# Quick Start

[中文](./quick-start.md)

If this is your first time in the repository, you do not need to read every document first.

Think of VibeSkills as a **Super Skill Harness** for AI agents:

> You bring the goal. `vibe` manages the work rhythm: clarify the requirement, split the work into stages, call the right expert Skills, push toward testing and verification, and preserve the useful context.

It is not a long tool menu that leaves the user to choose every step. It is a plug-in workflow package that helps Skills-capable agents start faster, stay more disciplined, and handle work across phases.

## 1. What problem does it solve?

VibeSkills focuses on five practical problems:

| Problem | What VibeSkills does |
|:---|:---|
| Too many Skills, unclear which one to call | The harness orchestrates expert Skills by task and phase |
| Agents skip requirements, planning, or testing | `vibe` moves work through governed stages |
| Users keep saying "plan first" or "verify it" | You provide the goal; the harness absorbs more of the control burden |
| Long work loses context across sessions | Requirements, plans, decisions, and evidence are stored in structured places |
| New domain Skills are hard to integrate | The Skills bundle is the core package, so future domain Skills can plug into the same workflow |

If you remember one line:

> **VibeSkills packages expert Skills, automatic orchestration, verification, and cross-session memory into one portable Super Skill that is easy to install and easy to start using.**

## 2. Start fast

Open the install entry:

- [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md)

Choose three things on that page:

1. Host: `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, or `opencode`
2. Action: choose `install` for a first install, or `update` if VibeSkills is already installed
3. Version: use `full` for the normal experience, or `minimal` only if you want the smaller framework foundation

Then copy the matching prompt into the AI app where you want VibeSkills installed, and let it run the install and checks.

After install, invoke it through your host's Skills entry:

| Host | Common invocation |
|:---|:---|
| Codex | Append `$vibe` to your request |
| Claude Code | Append `/vibe` to your request |
| OpenCode | Use `/vibe` or the host-supported Skills invocation |
| Cursor / Windsurf / OpenClaw | Follow the host's Skills entry documentation |

For updates, keep:

- `vibe-upgrade`

## 3. Current public entries

The current public, host-visible entries are only:

- `vibe`
- `vibe-upgrade`

`vibe` is the main entry. It stops at requirement, plan, and execution boundaries, then continues only after explicit confirmation.

`vibe-upgrade` is the governed upgrade entry for the current host installation.

Older stage-specific and legacy CLI entries are retired from the public host-visible surface and should not be advertised or installed.

If you want a stronger execution lane, use only the public lightweight overrides:

- `--l`
- `--xl`

Older stage IDs may still exist in runtime metadata for compatibility and continuity, but they are not commands or skills that users should invoke.

## 4. What to read next

Pick by intent:

| Goal | Read |
|:---|:---|
| Full project introduction | [`../README.md`](../README.md) |
| Install or update | [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md) |
| Direct command reference | [`install/recommended-full-path.en.md`](./install/recommended-full-path.en.md) |
| Unsure about host roots | [`cold-start-install-paths.en.md`](./cold-start-install-paths.en.md) |
| Using OpenCode | [`install/opencode-path.en.md`](./install/opencode-path.en.md) |
| Using OpenClaw | [`install/openclaw-path.en.md`](./install/openclaw-path.en.md) |
| Manual/offline install | [`install/manual-copy-install.en.md`](./install/manual-copy-install.en.md) |
| Custom Skills onboarding | [`install/custom-workflow-onboarding.en.md`](./install/custom-workflow-onboarding.en.md) |
| Why the project exists | [`manifesto.en.md`](./manifesto.en.md) |

## 5. Common confusion

- `$vibe` or `/vibe` only enters the governed runtime. It is not proof that MCP is fully configured.
- Install reports should separate `installed locally`, `vibe host-ready`, `mcp native auto-provision attempted`, per-MCP `host-visible readiness`, and `online-ready`.
- VibeSkills is a Skills-format runtime, not a standalone CLI you run directly in a terminal.
- `full` is the recommended default for normal users; `minimal` is for users who deliberately want the smaller governance framework.

## Recommended reading order

For the shortest path:

1. [`../README.md`](../README.md)
2. [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md)
3. Try `vibe` on a small task

Start with something simple, for example:

> Clarify this requirement and turn it into a plan `$vibe`

The difference becomes clear quickly: the user does not have to act as the dispatcher, and the agent gets a steadier way to move work through the harness.
