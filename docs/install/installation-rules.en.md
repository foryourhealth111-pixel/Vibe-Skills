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

## Rule 6: Map public version names to real script profiles

- `Full Version + Customizable Governance` -> `full`
- `Framework Only + Customizable Governance` -> `minimal`

Do not keep pretending the framework version is `framework-only`; the current scripts actually accept `minimal` / `full`.

## Rule 7: Describe Codex as the default recommended path

If the user chooses `codex`:

- run `--host codex`
- describe it as the default recommended path today
- explain that hook installation is currently frozen because of compatibility issues; that is not an install failure
- if the common OpenAI-compatible governance-advice path is needed, point the user to local configuration for:
  - `OPENAI_API_KEY`
  - optional `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`
- the built-in AI governance layer now supports OpenAI-compatible integration only
- never imply that baseline host online access automatically means governance-AI online readiness

## Rule 8: Describe Claude Code as a supported install-and-use path

If the user chooses `claude-code`:

- run `--host claude-code`
- state clearly that it has a supported install-and-use path
- explain that hooks remain frozen; this is not an install failure
- do not claim the installer writes extra Claude Code host settings files
- guide the user to maintain `~/.claude/settings.json` locally

## Rule 9: Describe Cursor as a supported install-and-use path too

If the user chooses `cursor`:

- run `--host cursor`
- state clearly that it has a supported install-and-use path
- do not claim the repo takes over Cursor settings or Cursor-native extension surfaces
- guide the user to maintain `~/.cursor/settings.json` locally

## Rule 10: Describe Windsurf as a supported install-and-use path

If the user chooses `windsurf`:

- run `--host windsurf`
- state clearly that it has a supported install-and-use path
- the default host root is `~/.codeium/windsurf`
- the repo currently owns only shared install content plus optional materialization of `mcp_config.json` and `global_workflows/`
- make it clear that Windsurf-local settings still need to be managed on the Windsurf side

## Rule 11: Describe OpenClaw as a supported install-and-use path

If the user chooses `openclaw`:

- run `--host openclaw`
- state clearly that it has a supported install-and-use path
- the default target root is `OPENCLAW_HOME` or `~/.openclaw`
- if the user needs attach / copy / bundle details, point them to [`openclaw-path.en.md`](./openclaw-path.en.md)
- leave host-local configuration on the OpenClaw side

## Rule 12: Describe OpenCode as a supported install-and-use path

If the user chooses `opencode`:

- run `--host opencode`
- state clearly that it has a supported install-and-use path
- the default target root is `OPENCODE_HOME`, otherwise `~/.config/opencode`
- direct install/check writes skills, command/agent wrappers, and `opencode.json.example`
- do not claim ownership of the real `opencode.json`
- keep provider credentials, plugin installation, and MCP trust on the host-managed side

## Rule 13: Prefer the real recommended key names for AI-governance online config

When explaining AI-governance advice connectivity, prefer:

- OpenAI-compatible:
  - `OPENAI_API_KEY`
  - optional `OPENAI_BASE_URL` / `OPENAI_API_BASE`
  - `VCO_RUCNLPIR_MODEL`


## Rule 14: Never ask users to paste secrets into chat

For all six supported hosts, do not ask users to paste keys, URLs, or model names into chat. Point them to local settings or local environment variables instead.

## Rule 15: Distinguish local install from online readiness

If local provider fields are not configured, the environment must not be described as online-ready.

## Rule 16: The result summary must stay explicit

The install or upgrade summary should include at least:

- target host
- public version
- actual mapped profile
- commands actually executed
- completed parts
- manual follow-up still required

## Rule 17: The framework version is not the full out-of-box experience

If the user chooses `Framework Only + Customizable Governance` / `minimal`, explicitly remind them:

- this installs the governance foundation first
- it does not mean the default workflow core is already complete
- if they want to add their own workflows later, continue with [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md)
