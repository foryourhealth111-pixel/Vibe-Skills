# VCO v2.0 References Index

Navigation guide for all VCO (Vibe Code Orchestrator) documentation.

## Core Documents

| Document | Purpose |
|----------|---------|
| [tool-registry.md](tool-registry.md) | Capabilities, APIs, and state paths of all 6 integrated tools |
| [conflict-rules.md](conflict-rules.md) | 3 conflict avoidance rules (agent boundary, memory division, command priority) |
| [fallback-chains.md](fallback-chains.md) | Error recovery: M/L=2-level, XL=3-level degradation paths |
| [team-templates.md](team-templates.md) | 6 predefined team compositions for XL-grade tasks |
| [extending-vco.md](extending-vco.md) | Guide for adding new tools or adapting to tool updates |
| [changelog.md](changelog.md) | Version history |

## Protocol Specifications

| Protocol | Document | When Loaded |
|----------|----------|-------------|
| vibe-think | [protocols/think.md](../protocols/think.md) | Planning, design, research (L grade) |
| vibe-do | [protocols/do.md](../protocols/do.md) | Coding, debugging (L grade) |
| vibe-review | [protocols/review.md](../protocols/review.md) | Code review, security audit (M/L/XL) |
| vibe-team | [protocols/team.md](../protocols/team.md) | XL multi-agent coordination |
| vibe-retro | [protocols/retro.md](../protocols/retro.md) | Workflow review and improvement |

## Reading Order

1. Start with `tool-registry.md` to understand what each tool provides
2. Read `conflict-rules.md` to understand how tools coexist safely
3. Read `fallback-chains.md` to understand error recovery
4. Read the relevant protocol doc for your current task type
5. Consult `team-templates.md` when planning XL-grade team tasks
6. Consult `extending-vco.md` when adding new tools or handling updates
7. See `changelog.md` for version history
