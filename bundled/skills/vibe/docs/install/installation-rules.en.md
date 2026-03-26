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

## Rule 7: Describe Codex as the governed path

If the user chooses `codex`:

- run `--host codex`
- describe it as the strongest governed path today
- explain that hook installation is currently frozen because of compatibility issues; that is not an install failure
- if base online provider access is needed, point the user to local `OPENAI_*` configuration
- if the governance AI online layer is needed, point the user to local `VCO_AI_PROVIDER_*` configuration
- never imply that `OPENAI_*` alone means governance-AI online readiness

## Rule 8: Describe Claude Code as a supported install-and-use path

If the user chooses `claude-code`:

- run `--host claude-code`
- state clearly that it has a supported install-and-use path
- explain that hooks remain frozen; this is not an install failure
- do not claim the installer writes `settings.vibe.preview.json`
- guide the user to maintain `~/.claude/settings.json` locally

## Rule 9: Describe Cursor as a supported install-and-use path too

If the user chooses `cursor`:

- run `--host cursor`
- state clearly that it has a supported install-and-use path
- do not claim the repo takes over Cursor settings or Cursor-native extension surfaces
- guide the user to maintain `~/.cursor/settings.json` locally

## Rule 10: Describe Windsurf as a supported install-and-use path with runtime-adapter integration

If the user chooses `windsurf`:

- run `--host windsurf`
- state clearly that it has a supported install-and-use path with runtime-adapter integration
- the default host root is `~/.codeium/windsurf`
- the repo currently owns only shared runtime payload plus optional materialization of `mcp_config.json` and `global_workflows/`
- make it clear that Windsurf-local settings still need to be managed on the Windsurf side

## Rule 11: Never ask users to paste secrets into chat

For all five supported hosts, do not ask users to paste keys, URLs, or model names into chat. Point them to local settings or local environment variables instead.

## Rule 12: Describe OpenClaw as preview / runtime-core-preview / runtime-core

If the user chooses `openclaw`:

- run `--host openclaw`
- describe it as a `preview` host with `runtime-core-preview` closure level and `runtime-core` install/check mode
- the default target root is `OPENCLAW_HOME` or `~/.openclaw`
- make the three paths explicit:
  - attach: connect and validate an existing `OPENCLAW_HOME` (or `~/.openclaw`) root
  - copy: copy the runtime-core payload into the target root through the install/check entrypoints
  - bundle: consume `dist/host-openclaw/manifest.json` and `dist/manifests/vibeskills-openclaw.json`
- keep the wording focused on runtime-core payload installation, validation, and distribution
- leave host-local configuration on the OpenClaw side

## Rule 13: Distinguish local install from online readiness

If local provider fields are not configured, the environment must not be described as online-ready.

## Rule 14: The result summary must stay explicit

The install or upgrade summary should include at least:

- target host
- public version
- actual mapped profile
- commands actually executed
- completed parts
- manual follow-up still required

## Rule 15: The framework version is not the full out-of-box experience

If the user chooses `Framework Only + Customizable Governance` / `minimal`, explicitly remind them:

- this installs the governance foundation first
- it does not mean the default workflow core is already complete
- if they want to add their own workflows later, continue with [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md)
