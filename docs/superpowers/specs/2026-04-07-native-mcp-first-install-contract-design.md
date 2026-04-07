# Native MCP-First Install Contract Design

## Summary
Define a stricter installation-assistant contract for all six public hosts where MCP provisioning must target the host's real native MCP surface first, rather than stopping at `skills/vibe`, repo-owned templates, sidecars, manifests, or `$vibe` discoverability.

The design keeps base runtime installation, governed-runtime discoverability, MCP host visibility, and online governance readiness as separate truths. It does not require every MCP surface to succeed before VibeSkills can be used, but it does require the assistant to tell the truth about which layer is actually complete.

This design applies to the same six public hosts:

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

It keeps the same five MCP surfaces in scope:

- `github`
- `context7`
- `serena`
- `scrapling`
- `claude-flow`

## Problem
The current installation story still allows a misleading success shape:

- the runtime payload can be installed locally
- `$vibe` can be discoverable from the host root
- repo-owned MCP templates or manifests can exist
- required CLIs can be present on PATH

but the host may still not have those MCP servers registered in its real native MCP surface.

That creates two recurring failures in user understanding:

1. users may be told installation is complete when only the governed runtime is installed
2. users may infer that MCP is ready because `$vibe` works, a template exists, or a CLI command exists

The user wants a stronger contract:

- MCP should be installed into the corresponding host's native MCP surface whenever that surface is stably available
- `$vibe` should remain the governed runtime entry, not the proof that MCP is installed
- if native MCP auto-registration cannot be completed, the assistant must say so directly rather than reporting a soft success through templates, sidecars, or runtime mirrors

## Goals
- Make `native MCP first` the default installation contract for all six public hosts.
- Keep governed runtime installation and MCP native registration as separate reported outcomes.
- Prevent `$vibe`, `skills/vibe`, templates, manifests, examples, and sidecars from being reported as MCP completion evidence.
- Require the assistant to attempt native MCP registration first for every in-scope host and every in-scope MCP surface.
- Standardize reporting vocabulary so install prompts and install-path docs all describe the same truth model.
- Preserve the existing rule that users should not be asked to paste keys, URLs, or model IDs into chat.

## Non-Goals
- This design does not implement new host-native MCP registration APIs.
- This design does not promise that every host currently has a stable native MCP automation surface.
- This design does not turn every missing MCP into a hard blocker for base runtime installation.
- This design does not redesign `vibe` runtime authority, the canonical router, or the existing host list.
- This design does not change the existing AI-governance credential names or online-readiness probe contract.

## Scope Boundary
This design applies to:

- install prompt documents
- install/update wording
- recommended install path docs
- high-level README install semantics where runtime success and MCP success are currently adjacent

This design does not apply to:

- installer-core implementation in this turn
- check/bootstrap/doctor code in this turn
- non-public hosts

## Design Options Considered

### Option A: Codex-only native MCP-first wording
Restrict the stronger contract to `codex`, where the mismatch was observed.

Pros:

- smallest change
- directly addresses the reported pain

Cons:

- leaves the other five hosts under a weaker and inconsistent contract
- keeps cross-host install language fragmented
- preserves the possibility that other hosts continue to report payload or template success as if it were MCP success

### Option B: Cross-host native MCP-first wording
Apply one install-assistant contract across all six public hosts.

Pros:

- one consistent rule for users and assistants
- easier to reason about truthful reporting
- aligns with the user's requirement that MCP should go into the target host rather than stop at `$vibe`

Cons:

- requires broader doc updates
- will force some hosts to report more `pending` or `not host-visible` states than before

### Option C: Native MCP as a hard install blocker
Treat any failure to complete native MCP registration as a failed installation.

Pros:

- simplest completion rule
- strongest pressure toward full automation

Cons:

- conflicts with the requirement that base install success and MCP success remain separate
- too brittle for preview or runtime-core hosts where the host-native automation surface may still be incomplete

## Decision
Choose **Option B**.

The installation contract should become:

- base runtime install may succeed independently
- `vibe` host-ready may succeed independently
- MCP must still attempt native host registration first
- host-native MCP completion must be reported separately, not inferred from runtime payload or CLI presence
- if native MCP auto-registration is not stably available, the assistant must say that the MCP is not yet host-visible rather than reporting success through a fallback proxy

## Core Contract

### 1. Truth Layers Must Be Separate
Install surfaces must separate at least these outcomes:

- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP `host-visible readiness`
- `online-ready`

None of those may be used as shorthand for any other.

### 2. `$vibe` Is Runtime Entry, Not MCP Evidence
`$vibe`, `/vibe`, and `skills/vibe` remain the governed runtime entry story only.

They may prove:

- runtime payload exists
- governed runtime is discoverable
- host-specific skill entry is materially present

They must not be described as proving:

- MCP registration exists
- MCP is host-visible
- MCP is online-ready

### 3. Repo-Owned Artifacts Are Not Native MCP Completion
The assistant must not treat any of the following as host-native MCP completion evidence by themselves:

- `mcp/servers.template.json`
- profile JSON files
- plugin manifests
- example configs
- `.vibeskills/*` sidecar state
- runtime mirrors under `skills/vibe`
- a required executable merely existing on PATH

Those artifacts may support setup, but they are not completion proof.

### 4. Native MCP Must Be Attempted First
For every supported host, the assistant must attempt to place the five MCP surfaces into the host's real native MCP surface first.

The preferred completion target is:

- the MCP registry, config file, or native registration interface the host actually reads

The preferred completion target is not:

- a repo-owned template
- a repo-owned manifest
- a governed runtime skill entry
- a sidecar state file

### 5. No Soft-Landing Into Fake Success
If a host lacks a stable, officially supportable native MCP auto-registration interface, the assistant must still:

1. try the native path first
2. report the attempt truthfully
3. stop short of claiming MCP completion

In that case the assistant must not reinterpret a template, manifest, sidecar, or runtime mirror as a successful native MCP install.

## Host-Agnostic Reporting Vocabulary

### Required Status Families
Each MCP should be described using language equivalent to one of these states:

- `host_visible_ready`
- `attempted_not_host_visible`
- `native_registration_unavailable`
- `needs_local_login`
- `command_ready_but_not_host_visible`
- `not_attempted_due_to_host_constraint`

The exact label can vary slightly across docs, but the meaning must remain stable.

### Forbidden Completion Shortcuts
The install assistant must not say any variant of:

- "MCP installed" when only the command exists
- "MCP ready" when only a template or manifest exists
- "MCP complete" because `$vibe` is discoverable
- "host-ready" when the MCP is only repo-visible or CLI-visible

## Cross-Host Contract

### Shared Rule For All Six Hosts
All six hosts must use the same top-level wording:

- install VibeSkills into the real host root where applicable
- make `vibe` discoverable as a governed runtime entry
- attempt MCP registration in the host's real native MCP surface first
- if native MCP registration cannot be completed, report that gap directly

### `codex`
The assistant must describe Codex MCP completion in terms of Codex's real native MCP surface rather than in terms of `skills/vibe`, `settings.json` placeholders, or MCP templates.

Only host-visible registration in Codex's active MCP surface should count as MCP ready.

### `claude-code`
The assistant must describe Claude Code MCP completion in terms of Claude Code's real MCP/config surface, not merely managed settings merges or repo-owned runtime payload.

If only a bounded settings merge exists but native MCP completion is not proven, the report must still say native MCP is pending.

### `cursor`
Preview-guidance wording must not be used to imply native MCP completion.

If Cursor receives guidance, scaffolds, or repo-owned preview surfaces without host-visible MCP registration, the report must still say native MCP is not complete.

### `windsurf`
Runtime-core payload and `.vibeskills/*` sidecar state must remain explicitly separate from native MCP completion.

If only runtime-core installation succeeds, MCP readiness must still be reported independently.

### `openclaw`
Attach / copy / bundle paths solve runtime-core payload delivery only.

Those paths must not be described as MCP completion unless the resulting host-native MCP surface is actually populated and visible.

### `opencode`
Direct install/check and `opencode.json.example` must not be described as native MCP completion.

If the real host-managed config remains untouched and no native MCP registration occurs, the report must say so explicitly.

## Required Prompt-Level Rules
Every install prompt should explicitly state rules equivalent to these:

1. MCP must be automatically installed into the target host's native MCP surface first when that surface is stably available.
2. `$vibe` or `/vibe` only proves governed runtime entry, not MCP completion.
3. Runtime payload, templates, manifests, example configs, and sidecars are not valid evidence that MCP is installed into the host.
4. If native MCP auto-registration fails or is unavailable, the assistant must report that the host-native MCP integration is still incomplete.
5. The assistant must not downgrade the definition of "installed" just to avoid reporting a pending MCP state.

## Required Final Report Shape
The final install report should explicitly cover:

- target host
- public version
- real profile
- commands executed
- `installed locally`
- `vibe host-ready`
- `mcp native auto-provision attempted`
- per-MCP host-visible readiness
- `online-ready`
- manual follow-up

This ensures the user can tell whether:

- the runtime is installed
- the governed runtime is discoverable
- each MCP is truly visible through the host
- online governance is configured

## Documentation Surfaces To Update
At minimum, this contract should be reflected in:

- `docs/install/prompts/full-version-install.md`
- `docs/install/prompts/full-version-install.en.md`
- `docs/install/prompts/framework-only-install.md`
- `docs/install/prompts/framework-only-install.en.md`
- `docs/install/prompts/full-version-update.md`
- `docs/install/prompts/full-version-update.en.md`
- `docs/install/prompts/framework-only-update.md`
- `docs/install/prompts/framework-only-update.en.md`
- `docs/install/recommended-full-path.md`
- `docs/install/recommended-full-path.en.md`
- `README.md`
- `README.zh.md`

## Risks
- Some hosts will now report more pending MCP states than before, which may feel harsher in the short term.
- Existing language that centered success around `$vibe` or runtime payload presence will need careful editing to avoid regressions in clarity.
- If wording is updated without future installer changes, users may correctly discover that native MCP automation is still incomplete on some hosts.

These are acceptable tradeoffs because the goal is truthful contract language, not cosmetic success inflation.

## Rollout Guidance
- Update install prompts first so new assistant sessions stop claiming template or runtime-based MCP success.
- Update install-path docs next so manual and guided installs use the same truth model.
- Update README host/install wording last so top-level project framing matches the prompt contract.

## Acceptance Checks For This Design
This design is successful if the written contract makes the following impossible to state without contradiction:

- "`$vibe` works, therefore MCP is installed"
- "the CLI exists, therefore MCP is host-ready"
- "a template was written, therefore the host can use the MCP"
- "runtime payload installed" and "native MCP complete" expressed as one undifferentiated success

## Open Questions Deferred To Implementation
- Which hosts currently expose stable, automatable native MCP registration interfaces versus host-managed manual registration only?
- What exact host-native probes should be treated as canonical evidence for each host?
- Which shared verification surfaces should adopt the new vocabulary first?
