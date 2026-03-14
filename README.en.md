[中文](./README.md)

# VibeSkills

> The skills substrate that ends skill chaos.
> Turn general-purpose AI from “able to call skills” into “able to complete tasks reliably”.

VibeSkills is an open skills ecosystem for general-purpose AI models.

Powered by Vibe Code Orchestrator `VCO`, it does not just collect skills. It adds intelligent routing, framework-level governance, quality gates, multi-skill composition, and multi-agent coordination so scattered capabilities can be turned into a safer, more standardized, more stable, and more reliable execution exoskeleton.

We are not trying to build another skill repository.
We are trying to build a universal skills substrate for general-purpose AI.

## Why VibeSkills Exists

The problem today is not a lack of skills.

The real problems are:

- skills are fragmented and hard to discover
- skills are opaque and difficult to trust
- skills do not compose well in real workflows
- custom skills are often inconsistent and poorly governed
- even strong models still lack a long-running capability governance layer

VibeSkills is not about improving one isolated skill.
It is about changing how the entire skills ecosystem is used.

## What We Believe

The future is not more skills.
The future is skill governance.

VibeSkills aims to become a universal skills substrate for general-purpose AI:

- users should not have to memorize skills
- models should be able to choose better execution paths
- multiple skills should be composable by design
- complex tasks should have explicit boundaries, protocols, and quality gates
- agents should evolve from single executors into coordinated teams

This is not another prompt pack.
This is not another tool list.
This is an attempt to build a real capability infrastructure layer for general-purpose intelligence.

## How It Is Different

Many systems stop at:

- connecting more tools
- exposing more skills
- making prompts look more agentic

VibeSkills focuses on something else:

- routing to the right skill and execution flow
- governing before execution, not only after failure
- composing multiple skills into stable workflows
- coordinating multi-agent teams for larger tasks
- maintaining consistent quality, boundaries, and reliability across scenarios

Not “more features”.
But a more reliable execution system.

## What Lives In This Repository

This repository is organized around a single control plane, `VCO`, and includes:

- the `VCO` orchestration layer for task grading, routing, and execution control
- the Pack Router for mapping task semantics to the right skills
- governance layers for quality debt, prompt assets, memory, ML lifecycle, system design, CUDA, and more
- verification gates for routing stability, offline closure, governance policy, and regression control
- bundled skill mirrors for repeatable installation and compatibility
- optional integrations such as AIOS-Core, OpenSpec, GSD-Lite, prompts.chat, GitNexus, claude-flow, and ralph-loop

The point is not to pile components together.
The point is to make them work under one governed execution surface.

## Manifesto

If you want the full statement of what this ecosystem is trying to build, what it rejects, and what it publicly commits to, start here:

- [`docs/manifesto.en.md`](./docs/manifesto.en.md)

## Current Recommended Release

- Current outward-facing recommended version: [`v2.3.40`](./docs/releases/v2.3.40.md)
- Ordinary-user one-click release copy: [`docs/install/one-click-install-release-copy.en.md`](./docs/install/one-click-install-release-copy.en.md)
- Operator-grade install path: [`docs/install/recommended-full-path.en.md`](./docs/install/recommended-full-path.en.md)

## Start Here

If you are:

- a heavy AI user doing development, research, analysis, or automation
- a team lead who wants AI to become operationally reliable instead of occasionally impressive
- someone frustrated by too many scattered and hard-to-compose skills

You can start here.

### Install Guide

#### Ordinary-user fast path

If you want the simplest public-facing onboarding path for ordinary users, community posts, or "copy this into your AI assistant" onboarding, start here:

- [`docs/install/one-click-install-release-copy.en.md`](./docs/install/one-click-install-release-copy.en.md)

This is the current public install copy for `v2.3.40`.

#### Start with the standard recommended install

For most users, the **standard recommended install** is the default entry point.

It does not mean "install every enhancement on day one". It means:

- close the repo-governed surfaces first
- accept `manual_actions_pending` as an honest state when host-managed surfaces are still missing
- enhance the setup in layers instead of forcing every plugin, MCP surface, and secret into the first run

This is the right default for:

- heavy AI users who want a stable real setup
- team leads who want to evaluate the governed surface before broader rollout
- operators who want less first-day conflict and less first-day debugging

Start here:

- [`docs/install/recommended-full-path.en.md`](./docs/install/recommended-full-path.en.md)
- [`docs/cold-start-install-paths.en.md`](./docs/cold-start-install-paths.en.md)

#### What "full-featured" means here

A full-featured VibeSkills setup is not just "the repo cloned successfully".
It means all shipped skills and governance assets are installed locally, the active MCP profile is materialized, the runtime passes deep health checks, and the remaining host-managed surfaces are called out explicitly instead of being silently skipped.

In the current default recommendation, that now means three different layers are made explicit:

- `scrapling` is treated as a default local runtime surface for the full profile, and the installer attempts to provision it during the standard external CLI pass
- `Cognee` is treated as the default long-term enhancement lane for governed graph memory, not as a replacement for session truth
- `Composio` and `Activepieces` are treated as predeclared external action surfaces that ship with governance context, but still require setup before use

#### Our "full-featured" promise is governed, not magical

In VibeSkills, "full-featured" means repo-governed completion, not fake "everything is automatically ready".

That means:

- the payload, scripts, mirrors, profiles, and doctor gates shipped by this repo should install, sync, and verify in one governed path
- host-managed surfaces such as host plugins, external MCP services, and provider secrets are still real operator responsibilities
- if those host-side prerequisites are not provisioned yet, the correct end state is `manual_actions_pending`, not a dishonest "all ready"

We do not blur "no install error" into "the whole ecosystem is now operational".
We make the closure boundary explicit so operators know what is already governed and what still needs manual provisioning.

#### Full-feature prerequisites

- `git`
- `node` and `npm`
- `python3` or `python`
- Windows: `powershell` or `pwsh`
- Linux/macOS: `bash`
- Recommended on Linux/macOS for the strongest governed verification path: `pwsh` (PowerShell 7)

With `pwsh`, Linux gets the strongest currently supported path, but it still ships as `supported-with-constraints` rather than `full-authoritative`.
Without `pwsh`, Linux/macOS still gets the full shipped content and the MCP active profile, but the PowerShell doctor gates are downgraded to shell-safe warnings.

Operator notes:

- The one-shot bootstrap can be slow when external CLI installation is enabled, especially during `npm` installation of `claude-flow`. Several minutes is normal.
- `npm` deprecation warnings during external CLI installation are advisory unless the command exits non-zero.
- If the target `settings.json` already contains `OPENAI_API_KEY` or `ARK_API_KEY`, the bootstrap now keeps those values and reports that they were reused instead of emitting a misleading "not provided" warning.

#### Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1
```

#### Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
```

Optional examples:

```bash
# install to a custom Codex root
bash ./scripts/bootstrap/one-shot-setup.sh --target-root "$HOME/.codex"

# enforce the offline closure gate during install
bash ./scripts/bootstrap/one-shot-setup.sh --strict-offline
```

Both one-shot bootstraps do the same governed work:

- install the shipped runtime payload under `~/.codex`
- install automatable external CLIs where supported, including the default `scrapling` surface in the full lane when Python packaging is available
- materialize `mcp/servers.active.json` from the selected profile
- run the deep readiness check

#### What counts as complete for the standard recommended install

For most users, the standard recommended install is complete when:

- the one-shot bootstrap succeeds
- the deep doctor succeeds
- shipped payload, bundled mirrors, active MCP profile, and runtime coherence are closed on the repo-owned side
- remaining gaps are listed clearly instead of being hidden

So:

- `fully_ready` is ideal
- `manual_actions_pending` is still a valid and acceptable result for this path
- `core_install_incomplete` is the real blocking failure

#### Re-run the deep doctor

Windows:

```powershell
pwsh -File .\check.ps1 -Profile full -Deep
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep
```

Linux / macOS:

```bash
bash ./check.sh --profile full --deep
```

Upgrade note:

- pulling the repo does not refresh `${TARGET_ROOT}/skills/vibe`
- after a repo upgrade, re-run `install.ps1` / `install.sh` or the matching one-shot bootstrap for the same target root before treating freshness failures as receipt-only issues

#### Manual follow-up required for a true full MCP experience

These surfaces are intentionally not faked by the repo and must be provisioned on the host:

- Host plugin surfaces still tracked by the current doctor / manifest: `superpowers`, `everything-claude-code`, `claude-code-settings`, `hookify`, `ralph-loop`
- Plugin-backed MCP surfaces: `github`, `context7`, `serena`
- External action integrations that are now shipped as governed prewired surfaces, but remain setup-required: `Composio`, `Activepieces`
- Provider secrets when you want online execution: `OPENAI_API_KEY` and any optional provider keys you actually use

But the default policy is not "install all five host plugins on day one".

Recommended policy:

- first install: do not treat all five as up-front prerequisites; run one-shot + deep doctor first
- author/reference Windows Codex lane: provision `superpowers` and `hookify` first
- `everything-claude-code`, `claude-code-settings`, and `ralph-loop`: add them only when doctor still points to a concrete remaining gap

Full decision rules and install guidance:

- [`docs/install/host-plugin-policy.en.md`](./docs/install/host-plugin-policy.en.md)

If those are not provisioned yet, the doctor should end in `manual_actions_pending`, not in a false "everything is ready" state.

#### If you want to enhance the setup further

A lower-risk order is:

1. add provider secrets first
2. add the recommended host plugins next
   Prioritize `superpowers` and `hookify`.
3. verify the default local and enhancement surfaces
   Confirm `scrapling` is callable and treat `Cognee` as the governed long-term graph-memory lane instead of introducing a second session-truth system.
4. add plugin-backed MCP surfaces
   For example `github`, `context7`, and `serena`.
5. wire external action integrations only when you actually need them
   `Composio` and `Activepieces` are intentionally predeclared but not auto-enabled; they stay confirm-gated and setup-required.
6. only add the remaining host plugins when doctor still points to a concrete gap
   For example `everything-claude-code`, `claude-code-settings`, and `ralph-loop`.
7. add optional CLI / toolchain enhancements last
   For example `claude-flow`, `xan`, and `ivy`.

See:

- [`docs/install/recommended-full-path.en.md`](./docs/install/recommended-full-path.en.md)
- [`docs/install/host-plugin-policy.en.md`](./docs/install/host-plugin-policy.en.md)

#### Not sure which install path to choose

If this is your first time with the repo, do not guess.

Start with:

- [`docs/cold-start-install-paths.en.md`](./docs/cold-start-install-paths.en.md): three onboarding paths for `minimum viable`, `recommended full-featured`, and `enterprise-governed` installs, including who each path is for, commands, acceptance criteria, and stop rules
- [`docs/install/full-featured-install-prompts.en.md`](./docs/install/full-featured-install-prompts.en.md): copy-paste install prompts for AI assistants, covering Windows and Linux

### Routing and Governance Checks

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

### Deep Dive

- [`SKILL.md`](./SKILL.md): the main VCO protocol and execution model
- [`docs/README.md`](./docs/README.md): governance docs, plans, releases, and integration spine
- [`docs/one-shot-setup.md`](./docs/one-shot-setup.md): the exact one-shot bootstrap path and readiness-state model
- [`config/index.md`](./config/index.md): machine-readable routing, cleanliness, packaging, and rollout config
- [`references/index.md`](./references/index.md): contracts, registries, matrices, ledgers, and overlays
- [`scripts/README.md`](./scripts/README.md): router, governance, verify, overlay, and setup surfaces

## Why Star This Project

If you believe that:

- general-purpose AI needs a real governed skills infrastructure
- AI execution systems cannot remain at the stage of scattered scripts and prompt glue code
- open source should define the next generation of standards, boundaries, and collaboration models for skills ecosystems

then this project is worth watching.

Starring it is not just bookmarking a repository.
It is joining a direction:
turning skills from scattered plugins into reliable infrastructure for general-purpose intelligence.

## Join Us

### If you are a user

- use it
- file issues and real-world scenarios
- tell us where it is still unstable or not intelligent enough
- help us shape the system around real workflows

### If you are a developer or agent framework builder

- contribute skills, routing strategies, governance rules, and verification scripts grounded in real user demand
- help reduce duplication, hidden conflicts, and uncontrolled execution in the ecosystem
- help move skills from “usable” to “reliable, governed, stable, and composable”

## Key Entry Points

- [`docs/manifesto.en.md`](./docs/manifesto.en.md): the public manifesto and technical commitments of VibeSkills
- [`docs/ecosystem-absorption-dedup-governance.md`](./docs/ecosystem-absorption-dedup-governance.md): ecosystem absorption, deduplication, and layered governance
- [`docs/observability-consistency-governance.md`](./docs/observability-consistency-governance.md): observability, consistency, and manual rollback governance
- [`docs/memory-governance-integration.md`](./docs/memory-governance-integration.md): memory boundaries and role separation
- [`docs/prompt-overlay-integration.md`](./docs/prompt-overlay-integration.md): prompt asset overlay integration
- [`docs/data-scale-overlay-integration.md`](./docs/data-scale-overlay-integration.md): large-scale data overlay integration
- [`docs/system-design-overlay-integration.md`](./docs/system-design-overlay-integration.md): system design advisory integration
- [`docs/pilot-scenarios-and-eval.md`](./docs/pilot-scenarios-and-eval.md): pilot scenarios and evaluation plan

## License

- Root license: [`Apache-2.0`](./LICENSE)
- Third-party boundary: [`THIRD_PARTY_LICENSES.md`](./THIRD_PARTY_LICENSES.md)
- Repository notice: [`NOTICE`](./NOTICE)

## In One Sentence

VibeSkills aims to give general-purpose AI a skills substrate that is governable, composable, verifiable, and able to evolve over time.

If you believe this is the direction AI infrastructure should take, use it, star it, and help build it.
