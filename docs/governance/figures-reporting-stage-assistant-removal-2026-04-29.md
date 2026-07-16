# Figures And Reporting Stage Assistant Removal

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

Date: 2026-04-29

## Scope

This pass cleans only:

- `science-figures-visualization`
- `science-reporting`

It preserves the public six-stage Vibe runtime and follows the simplified routing contract:

```text
candidate -> selected -> used / unused
```

## Before And After

| Pack | Before | After |
| --- | --- | --- |
| `science-figures-visualization` | 5 candidates, 2 route owners, 3 stage assistants | 2 direct candidates, 2 route owners, 0 stage assistants |
| `science-reporting` | 5 candidates, 2 route owners, 3 stage assistants | 2 direct candidates, 2 route owners, 0 stage assistants |

## Direct Owners

| Pack | Skill | Direct ownership |
| --- | --- | --- |
| `science-figures-visualization` | `scientific-visualization` | Publication/result/model-evaluation figures and data visualization. |
| `science-figures-visualization` | `scientific-schematics` | Scientific diagrams, flowcharts, mechanism schematics, graphical abstracts. |
| `science-reporting` | `scientific-reporting` | Scientific and technical reports with HTML/PDF, appendices, and reproducibility sections. |
| `science-reporting` | `scientific-writing` | Scientific prose and manuscript-body writing. |

## Moved Out Of Pack Candidate Surfaces

| Skill | Previous pack surface | Decision |
| --- | --- | --- |
| `matplotlib` | `science-figures-visualization` stage assistant | Removed from routed candidate surface; used as implementation library under `scientific-visualization` when needed. |
| `seaborn` | `science-figures-visualization` stage assistant | Removed from routed candidate surface; used as implementation library under `scientific-visualization` when needed. |
| `plotly` | `science-figures-visualization` stage assistant | Removed from routed candidate surface; used as implementation library under `scientific-visualization` when needed. |
| `scientific-visualization` | `science-reporting` stage assistant | Owned by `science-figures-visualization`; report tasks should route figure work as a separate selected slice. |
| `scientific-schematics` | `science-reporting` stage assistant | Owned by `science-figures-visualization`; diagram work should route as a separate selected slice. |
| `markdown-mermaid-writing` | `science-reporting` stage assistant | Removed from reporting helper surface; Mermaid/flowchart requests route to `scientific-schematics`. |

## Deletion Position

No bundled skill directory is physically deleted in this pass.

## Verification

```powershell
python -m pytest tests/runtime_neutral/test_figures_reporting_stage_assistant_removal.py -q
python -m pytest tests/runtime_neutral/test_bundled_stage_assistant_freeze.py tests/runtime_neutral/test_router_bridge.py tests/runtime_neutral/test_docs_research_publishing_boundary_routing.py -q
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
