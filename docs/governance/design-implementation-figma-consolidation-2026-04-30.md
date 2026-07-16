# Design Implementation Figma Consolidation - 2026-04-30

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

## Purpose

This pass closes the remaining hard coverage gap in `design-implementation`.
The pack previously exposed both `figma-implement-design` and `figma` as direct route candidates, but only `figma-implement-design` had a keyword-index entry.

The cleanup keeps the route model simple:

```text
candidate skill -> selected skill -> used / unused
```

No stage assistants, advisory roles, or primary/secondary skill states are added.

## Before And After

| Surface | Before | After |
| --- | --- | --- |
| `skill_candidates` | `figma-implement-design`, `figma` | `figma-implement-design` |
| `route_authority_candidates` | `figma-implement-design`, `figma` | `figma-implement-design` |
| `stage_assistant_candidates` | absent/empty | empty |
| default `planning` | `figma-implement-design` | `figma-implement-design` |
| default `coding` | `figma-implement-design` | `figma-implement-design` |
| bundled `figma` directory | present | removed after reference migration |

## Ownership Decision

| User problem | Route owner | Rationale |
| --- | --- | --- |
| Implement a Figma design as code | `figma-implement-design` | Owns the full workflow: design context, screenshot, assets, translation to project conventions, and visual parity verification. |
| Configure or troubleshoot Figma MCP during design implementation | `figma-implement-design` | Setup guidance is part of the implementation workflow and should not create a separate route owner. |

The removed `figma` skill was a tool-style MCP reference. It did not own a distinct user problem once `figma-implement-design` existed.

## Migration

Useful references from `bundled/skills/figma/references/` were migrated to:

- `bundled/skills/figma-implement-design/references/figma-mcp-config.md`
- `bundled/skills/figma-implement-design/references/figma-tools-and-prompts.md`

The removed directory's icon assets were not migrated because `figma-implement-design` already contains equivalent assets.

## Regression Coverage

New regression tests in `tests/runtime_neutral/test_design_implementation_pack_consolidation.py` assert:

- `design-implementation` has exactly one route candidate: `figma-implement-design`.
- `figma` is absent from the keyword index, routing rules, skills lock, and bundled skill directories.
- Figma design implementation prompts still route to `design-implementation / figma-implement-design`.
- Figma MCP setup wording with an implementation context also routes to `figma-implement-design`.

## Verification

The focused verification command is:

```powershell
python -m pytest tests/runtime_neutral/test_design_implementation_pack_consolidation.py -q
```

Broader routing and offline gates should be run before completion:

```powershell
python -m pytest tests/runtime_neutral/test_docs_research_publishing_boundary_routing.py tests/runtime_neutral/test_research_design_pack_consolidation.py tests/runtime_neutral/test_global_pack_consolidation_audit.py -q
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
```
