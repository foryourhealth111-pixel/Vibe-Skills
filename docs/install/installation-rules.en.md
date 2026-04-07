# Installation Rules

This document defines the truth-first rules that install and upgrade assistants must follow on the public install surface.

## Rule 1: Confirm the host first

Do not start any install or upgrade command until the user explicitly confirms the target host.

The current public host surface is limited to:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

## Rule 2: Confirm the public version next

Do not start execution until the user explicitly confirms the public version.

The current public versions are:

- `Full Version + Customizable Governance`
- `Framework Only + Customizable Governance`

## Rule 3: Reject unsupported hosts clearly

If the user names a host outside the supported surface, say so directly and stop instead of pretending installation is complete.

## Rule 4: Reject unsupported version names clearly

If the user names a version outside the public version surface, say so directly and stop.

## Rule 5: Detect the operating system before choosing commands

- Linux / macOS use `bash`
- Windows use `pwsh`

Additional contract:

- the Linux / macOS shell entrypoints must stay runnable on the macOS system Bash 3.2 baseline; do not reintroduce Bash 4+ builtins such as `mapfile`
- those shell entrypoints now validate **Python 3.10+** before dispatching into adapter, doctor, or bootstrap helper scripts
- when a user launches from macOS `zsh`, the real compatibility boundary is the resolved `bash` and `python3` binaries, not `zsh` itself

## Rule 6: Map public version names to real script profiles

- `Full Version + Customizable Governance` -> `full`
- `Framework Only + Customizable Governance` -> `minimal`

Do not keep pretending the framework version is `framework-only`; the current scripts actually accept `minimal` / `full`.

## Rule 6.5: Separate bootstrap prerequisites from optional external runtimes

- the base prerequisite for `install.sh` / `check.sh` / `scripts/bootstrap/one-shot-setup.sh` is a repo-owned **Python 3.10+** floor
- external runtimes such as `ruc-nlpir` may still need their own isolated venv, but that is not the same thing as the bootstrap prerequisite floor
- do not describe an optional upstream/runtime preference for 3.11 as if the whole public installer were 3.11-only

## Rule 7: Describe Codex as the default recommended path

If the user chooses `codex`:

- run `--host codex`
- on Linux / macOS, default to `CODEX_HOME="$HOME/.codex"`; on Windows, default `CODEX_HOME` to the real host root `%USERPROFILE%\\.codex`
- describe it as the strongest governed path today; if the goal is to install and have the current Codex discover `$vibe` directly, the default target must be the real `~/.codex`
- only use `~/.vibeskills/targets/codex` when the user explicitly asks for an isolated target root, or Codex is already intentionally pointed there
- explain that hook installation is currently frozen because of compatibility issues; that is not an install failure
- if the common governance-advice path is needed, point the user to local configuration for:
  - `VCO_INTENT_ADVICE_API_KEY`
  - optional `VCO_INTENT_ADVICE_BASE_URL`
  - `VCO_INTENT_ADVICE_MODEL`
  - `VCO_VECTOR_DIFF_API_KEY` (optional vector diff embeddings that degrade gracefully)
- the built-in AI governance layer now reads the advice credentials strictly from `VCO_INTENT_ADVICE_*`
- never imply that baseline host online access automatically means governance-AI online readiness

## Rule 8: Describe Claude Code as a supported install-and-use path

If the user chooses `claude-code`:

- run `--host claude-code`
- state clearly that it has a supported install-and-use path
- on Linux / macOS, default to `CLAUDE_HOME="$HOME/.claude"`; on Windows, default `CLAUDE_HOME` to the real host root `%USERPROFILE%\\.claude`
- explain that the installer preserves existing `~/.claude/settings.json` content while adding a bounded managed `vibeskills` node
- do not claim official-runtime ownership, full Codex parity, or cross-platform proof that has not been frozen
- guide the user to keep `env`, plugin enablement, MCP registration, and provider credentials on the Claude host-managed side

## Rule 9: Describe Cursor as a supported install-and-use path too

If the user chooses `cursor`:

- run `--host cursor`
- state clearly that it has a supported install-and-use path
- on Linux / macOS, default to `CURSOR_HOME="$HOME/.cursor"`; on Windows, default `CURSOR_HOME` to the real host root `%USERPROFILE%\\.cursor`
- do not claim the repo takes over Cursor settings or Cursor-native extension surfaces
- guide the user to maintain `~/.cursor/settings.json` locally

## Rule 10: Describe Windsurf as a supported install-and-use path

If the user chooses `windsurf`:

- run `--host windsurf`
- state clearly that it has a supported install-and-use path
- the default target root is `WINDSURF_HOME`, otherwise the real host root `~/.codeium/windsurf`
- the repo currently owns only shared install content plus sidecar state such as `.vibeskills/host-settings.json` and `.vibeskills/host-closure.json`
- make it clear that Windsurf-local settings still need to be managed on the Windsurf side

## Rule 11: Describe OpenClaw as a supported install-and-use path

If the user chooses `openclaw`:

- run `--host openclaw`
- state clearly that it has a supported install-and-use path
- the default target root is `OPENCLAW_HOME` or the real host root `~/.openclaw`
- if the user needs attach / copy / bundle details, point them to [`openclaw-path.en.md`](./openclaw-path.en.md)
- leave host-local configuration on the OpenClaw side

## Rule 12: Describe OpenCode as a supported install-and-use path

If the user chooses `opencode`:

- run `--host opencode`
- state clearly that it has a supported install-and-use path
- the default target root is `OPENCODE_HOME`, otherwise the real host root `~/.config/opencode`
- the real host config directory is `~/.config/opencode`
- direct install/check writes skills, `.vibeskills/*` sidecars, and `opencode.json.example`
- do not claim ownership of the real `opencode.json`
- keep provider credentials, plugin installation, and MCP trust on the host-managed side

## Rule 13: Prefer the real recommended key names for AI-governance online config

When explaining AI-governance advice connectivity, prefer:

- `VCO_INTENT_ADVICE_API_KEY`
- optional `VCO_INTENT_ADVICE_BASE_URL`
- `VCO_INTENT_ADVICE_MODEL`
- mention `VCO_VECTOR_DIFF_*` if vector embeddings are configured, and note that missing vector diff keys do not block the advice path because it degrades gracefully


## Rule 14: Never ask users to paste secrets into chat

For all six supported hosts, do not ask users to paste keys, URLs, or model names into chat. Point them to local settings or local environment variables instead.

## Rule 15: MCP completion must target the host's native MCP surface

For all six supported hosts, MCP must be provisioned into the host's real **native MCP surface** first.

The following must not be treated as MCP completion evidence:

- `$vibe` / `/vibe` / `skills/vibe` discoverability
- `mcp/servers.template.json`
- plugin manifests
- `*.json.example`
- `.vibeskills/*` sidecars
- a command merely existing on PATH

If native auto-registration fails, or the current host does not expose a stable officially supportable auto-registration interface, report that the MCP is still `not host-visible` rather than pretending it is ready.

## Rule 16: Distinguish local install, `vibe host-ready`, and online readiness

If local provider fields are not configured, the environment must not be described as online-ready.

`$vibe` being callable must not be rewritten as if MCP were already complete.

## Rule 17: The result summary must stay explicit

The install or upgrade summary should include at least:

- target host
- public version
- actual mapped profile
- commands actually executed
- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`
- completed parts
- manual follow-up still required

## Rule 18: The framework version is not the full out-of-box experience

If the user chooses `Framework Only + Customizable Governance` / `minimal`, explicitly remind them:

- this installs the governance foundation first
- it does not mean the default workflow core is already complete
- if they want to add their own workflows later, continue with [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md)
