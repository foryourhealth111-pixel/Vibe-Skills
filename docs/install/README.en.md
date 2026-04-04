# Installation and Custom Integration Index

This directory contains the public install, upgrade, and custom-integration docs.

## Quick Navigation

### Public Install Entry

- [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md): the single public install entry; choose host, action, and version there, then copy the matching prompt

### Public Uninstall Entry

- [`../../uninstall.ps1`](../../uninstall.ps1) / [`../../uninstall.sh`](../../uninstall.sh): the symmetric uninstall entry after install; it mirrors `install.*` arguments and only removes Vibe-managed payloads recorded by the install ledger, host closure, or conservative legacy rules
- [`../uninstall-governance.md`](../uninstall-governance.md): the owned-only uninstall contract; shared JSON cleanup is limited to Vibe-managed nodes and does not roll back host-managed login state, provider credentials, or plugin state by default

### Reference Docs

- [`recommended-full-path.en.md`](./recommended-full-path.en.md): multi-host install command reference
- [`openclaw-path.en.md`](./openclaw-path.en.md): dedicated install-and-use guide for OpenClaw
- [`opencode-path.en.md`](./opencode-path.en.md): dedicated install-and-use guide for OpenCode
- [`manual-copy-install.en.md`](./manual-copy-install.en.md): manual copy path for offline or no-admin environments
- [`framework-only-path.en.md`](./framework-only-path.en.md): compatibility note for the older framework-only entry name
- [`full-featured-install-prompts.en.md`](./full-featured-install-prompts.en.md): compatibility note for the older Codex deep install prompt page
- [`installation-rules.en.md`](./installation-rules.en.md): truth-first rules every install assistant must follow
- [`configuration-guide.en.md`](./configuration-guide.en.md): local configuration guidance

## How to Read the Current Install Surface

The public install docs are now registry-driven:

- `HostId` / `--host` decides host semantics
- `install.*`, `check.*`, and `one-shot-setup.*` should follow [`../../config/adapter-registry.json`](../../config/adapter-registry.json)
- the current public hosts resolve into three install modes: `governed`, `preview-guidance`, and `runtime-core`
- `opencode` still keeps a thinner direct install/check path in the public docs, but that does not mean the registry-driven one-shot wrapper is unavailable

Notes:

- for normal users, the public install surface now keeps only [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md) as the primary entry
- the four retained install prompt docs still exist underneath that entry: full install, framework install, full upgrade, and framework upgrade
- other install-related pages now act only as compatibility notes, host-specific references, or command references instead of parallel public entrypoints
- the generic install prompts still support `openclaw` and `opencode`
- [`openclaw-path.en.md`](./openclaw-path.en.md) and [`opencode-path.en.md`](./opencode-path.en.md) are split out only to expand host-specific details, not because the generic install path cannot handle those hosts
- provider / MCP / host settings follow-up should be treated as optional enhancement guidance when the base install already works

## Public Versions

The public install surface still exposes two user-facing versions:

- `Full Version + Customizable Governance`
- `Framework Only + Customizable Governance`

Their actual script-level profile mapping is:

- `Full Version + Customizable Governance` -> `full`
- `Framework Only + Customizable Governance` -> `minimal`

Keep the public wording user-friendly, then map to the real profile at execution time.

## Publicly Supported Hosts

The public surface currently supports six hosts, but not under one identical mode:

- `codex`: the strongest governed lane and the default recommended path
- `claude-code`: a supported install-and-use path with bounded managed closure
- `cursor`: a preview-guidance path
- `windsurf`: a runtime-core path; the repo owns shared runtime payload plus `.vibeskills/*` sidecar state only
- `openclaw`: a preview runtime-core adapter path; the host guide expands the attach / copy / bundle details
- `opencode`: a preview-guidance adapter path; the public docs still keep direct install/check as the thinner default command surface

Other hosts should not currently be described as supported installation targets.

## Recommended Reading Order

If you are a regular user:

1. [`one-click-install-release-copy.en.md`](./one-click-install-release-copy.en.md)
2. [`../cold-start-install-paths.en.md`](../cold-start-install-paths.en.md)
3. choose the matching prompt or command path only from those entrypoints
4. [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md)
5. [`custom-skill-governance-rules.en.md`](./custom-skill-governance-rules.en.md)

If you are an advanced user:

1. [`recommended-full-path.en.md`](./recommended-full-path.en.md)
2. [`manual-copy-install.en.md`](./manual-copy-install.en.md)
3. [`host-plugin-policy.en.md`](./host-plugin-policy.en.md)
4. [`configuration-guide.en.md`](./configuration-guide.en.md)

## Custom Extension Docs

- [`custom-workflow-onboarding.en.md`](./custom-workflow-onboarding.en.md): how to bring a new workflow into governance and routing
- [`custom-skill-governance-rules.en.md`](./custom-skill-governance-rules.en.md): governance rules for custom skills and workflows
