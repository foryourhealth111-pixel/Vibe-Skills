# Installation and Custom Integration Index

This directory contains the public install, upgrade, and custom-integration docs.

## Quick Navigation

### Fresh Install

- [`prompts/full-version-install.en.md`](./prompts/full-version-install.en.md): full-version install prompt
- [`prompts/framework-only-install.en.md`](./prompts/framework-only-install.en.md): framework-version install prompt

### Upgrade Existing Install

- [`prompts/full-version-update.en.md`](./prompts/full-version-update.en.md): full-version upgrade prompt
- [`prompts/framework-only-update.en.md`](./prompts/framework-only-update.en.md): framework-version upgrade prompt

### Reference Docs

- [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md): default entrypoint with host/version selection and links to prompt files
- [`recommended-full-path.en.md`](./recommended-full-path.en.md): advanced host, lane, and command reference
- [`manual-copy-install.en.md`](./manual-copy-install.en.md): manual copy path for offline or no-admin environments
- [`installation-rules.en.md`](./installation-rules.en.md): truth-first rules every install assistant must follow
- [`configuration-guide.en.md`](./configuration-guide.en.md): local configuration guidance

## Public Versions

The public install surface still exposes two user-facing versions:

- `Full Version + Customizable Governance`
- `Framework Only + Customizable Governance`

Their actual script-level profile mapping is:

- `Full Version + Customizable Governance` -> `full`
- `Framework Only + Customizable Governance` -> `minimal`

Keep the public wording user-friendly, then map to the real profile at execution time.

## Publicly Supported Hosts

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`

Within that scope:

- `codex`: governed and currently the strongest path
- `claude-code`: supported install-and-use path
- `cursor`: supported install-and-use path
- `windsurf`: supported install-and-use path with runtime-adapter integration
- `openclaw`: preview / runtime-core-preview / runtime-core path

Other hosts should not currently be described as supported installation targets.

## Recommended Reading Order

If you are a regular user:

1. [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
2. the matching prompt file
3. [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md)
4. [`custom-skill-governance-rules.en.md`](./custom-skill-governance-rules.en.md)

If you are an advanced user:

1. [`recommended-full-path.en.md`](./recommended-full-path.en.md)
2. [`manual-copy-install.en.md`](./manual-copy-install.en.md)
3. [`host-plugin-policy.en.md`](./host-plugin-policy.en.md)

## Custom Extension Docs

- [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md): how to bring a new workflow into governance and routing
- [`custom-skill-governance-rules.en.md`](./custom-skill-governance-rules.en.md): governance rules for custom skills and workflows
