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
| [../docs/skills-consolidation-roadmap.md](../docs/skills-consolidation-roadmap.md) | Consolidation phases, quality gates, rollback strategy |
| [../docs/skills-consolidation-batch-plan.md](../docs/skills-consolidation-batch-plan.md) | Batch-by-batch migration execution plan |
| [../docs/soft-migration-playbook.md](../docs/soft-migration-playbook.md) | Practical validation checklist for soft migration |
| [../docs/hard-migration-batch-a-report.md](../docs/hard-migration-batch-a-report.md) | Batch A hard migration execution and verification report |
| [../docs/context-retro-advisor-design.md](../docs/context-retro-advisor-design.md) | Retro-only integration design for Agent-Skills context expert guidance |
| [../docs/gsd-vco-overlay-integration.md](../docs/gsd-vco-overlay-integration.md) | GSD-Lite overlay design (post-route planning hook, non-redundant integration) |
| [../docs/memory-governance-integration.md](../docs/memory-governance-integration.md) | Memory governance design (state_store/Serena/ruflo/Cognee boundaries + episodic disablement) |
| [../docs/prompt-overlay-integration.md](../docs/prompt-overlay-integration.md) | prompts.chat prompt-asset overlay design (post-route ambiguity guard, non-redundant integration) |
| [../docs/data-scale-overlay-integration.md](../docs/data-scale-overlay-integration.md) | Data-scale overlay design (real file probe + spreadsheet/xlsx/xan adaptive selection) |
| [../docs/quality-debt-overlay-integration.md](../docs/quality-debt-overlay-integration.md) | Quality-debt overlay design (fuck-u-code inspired post-route advisory, no route mutation) |
| [../docs/framework-interop-overlay-integration.md](../docs/framework-interop-overlay-integration.md) | Framework-interop overlay design (ivy-inspired cross-framework advisory, no route mutation) |
| [../docs/ml-lifecycle-overlay-integration.md](../docs/ml-lifecycle-overlay-integration.md) | ML lifecycle overlay design (Made-With-ML inspired post-route stage/evidence advisory) |
| [../docs/python-clean-code-overlay-integration.md](../docs/python-clean-code-overlay-integration.md) | Python clean-code overlay design (clean-code-python inspired post-route advisory, no route mutation) |
| [../docs/system-design-overlay-integration.md](../docs/system-design-overlay-integration.md) | System-design overlay design (system-design-primer inspired architecture coverage advisory, no route mutation) |
| [../docs/cuda-kernel-overlay-integration.md](../docs/cuda-kernel-overlay-integration.md) | CUDA kernel overlay design (LeetCUDA inspired post-route kernel optimization advisory, no route mutation) |
| [../templates/cer-report.md.template](../templates/cer-report.md.template) | CER markdown template for human-readable retro reports |
| [../templates/cer-report.json.template](../templates/cer-report.json.template) | CER JSON template for machine analytics and comparison |
| [../templates/cer-report.schema.json](../templates/cer-report.schema.json) | CER JSON schema for validation gates |
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
