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

## Start Here

If you are:

- a heavy AI user doing development, research, analysis, or automation
- a team lead who wants AI to become operationally reliable instead of occasionally impressive
- someone frustrated by too many scattered and hard-to-compose skills

You can start here.

### Quick Install

```powershell
pwsh -File .\install.ps1 -Profile full -StrictOffline
pwsh -File .\check.ps1 -Profile full -Deep
```

### Routing and Governance Checks

```powershell
pwsh -File .\scripts\verify\vibe-pack-routing-smoke.ps1
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

### Deep Dive

- [`SKILL.md`](./SKILL.md): the main VCO protocol and execution model
- [`docs/README.md`](./docs/README.md): governance docs, plans, releases, and integration spine
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
