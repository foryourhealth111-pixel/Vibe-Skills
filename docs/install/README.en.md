# Install Docs Index

This folder contains the install, update, uninstall, and custom-integration docs.

Normal users have two paths:

- **Prompt-based install**: copy one prompt into the AI app and let it confirm host, version, install, and check.
- **Command install**: run install/check directly in a terminal when you already know the host root and command flow.

If you are unsure, start with prompt-based install:

1. Open [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md).
2. Choose host, action, and version.
3. Copy one prompt into the AI app you want to install VibeSkills into.

If you prefer direct commands, open [`recommended-full-path.en.md`](./recommended-full-path.en.md).

## Requirements

- Python 3.10+
- PowerShell 7 (`pwsh`) for the full governed verification path
- Git access to this repository

Linux and macOS can still use the `bash` install scripts. PowerShell 7 is recommended because several governed verification gates use the PowerShell command surface.

## Main Pages

| Need | Read |
|:---|:---|
| Public install/update entry | [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md) |
| Command install reference | [`recommended-full-path.en.md`](./recommended-full-path.en.md) |
| Host root decision help | [`../cold-start-install-paths.en.md`](../cold-start-install-paths.en.md) |
| Offline/manual install | [`manual-copy-install.en.md`](./manual-copy-install.en.md) |
| OpenClaw details | [`openclaw-path.en.md`](./openclaw-path.en.md) |
| OpenCode details | [`opencode-path.en.md`](./opencode-path.en.md) |
| Post-install configuration boundaries | [`configuration-guide.en.md`](./configuration-guide.en.md) |
| Custom Skill onboarding | [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md) |

Maintainer/reference pages:

- [`installation-rules.en.md`](./installation-rules.en.md): truth-first install assistant rules
- [`host-plugin-policy.en.md`](./host-plugin-policy.en.md): host/plugin boundary notes
- [`../one-shot-setup.md`](../one-shot-setup.md): one-shot setup behavior and MCP reporting contract

## Prompt Library

The public prompt set is intentionally small:

- [`prompts/full-version-install.en.md`](./prompts/full-version-install.en.md)
- [`prompts/framework-only-install.en.md`](./prompts/framework-only-install.en.md)
- [`prompts/full-version-update.en.md`](./prompts/full-version-update.en.md)
- [`prompts/framework-only-update.en.md`](./prompts/framework-only-update.en.md)

Other pages in this folder are reference docs, compatibility notes, or host-specific supplements. They are not separate public landing pages.

## Public Versions

| Public wording | Runtime profile |
|:---|:---|
| `Full Version + Customizable Governance` | `full` |
| `Framework Only + Customizable Governance` | `minimal` |

Use `full` for the normal VibeSkills experience. Use `minimal` only when you deliberately want the smaller framework foundation.

## Public Hosts

Current public host ids:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

The install modes are not identical across hosts. `codex` and `claude-code` are the clearest install-and-use paths; `cursor`, `windsurf`, `openclaw`, and `opencode` have host-specific or preview-oriented boundaries. Keep those boundaries visible in install reports.

## Truth Model For Install Reports

Do not collapse install state into one vague success line. Report these separately:

- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`

`$vibe` or `/vibe` proves the governed runtime entry only. It is not MCP completion and not proof that providers, credentials, plugins, or host-native MCP surfaces are fully configured.

The public install flow does not currently guide users through built-in online enhancement configuration. Install assistants should not ask users for providers, credentials, URLs, or model names; when that path is not configured through public docs, keep `online-ready` separate and report it as not ready or not verified.

## Uninstall

Use the repo-root uninstall entrypoint:

- Windows: `uninstall.ps1 -HostId <host>`
- Linux / macOS: `uninstall.sh --host <host>`

See [`../uninstall-governance.md`](../uninstall-governance.md) for the owned-only cleanup contract.
