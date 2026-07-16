# Research Design High Prune

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

Date: 2026-04-30

## Summary

This pass applies the simplified Vibe-Skills routing model to `research-design`:

```text
candidate -> selected -> used / unused
```

No stage assistants, helper experts, advisory state, or primary/secondary hierarchy are introduced. The six-stage runtime is unchanged.

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 9 | 5 |
| `route_authority_candidates` | 9 | 5 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 4 |

## Retained Route Authorities

| Skill | Ownership |
| --- | --- |
| `designing-experiments` | Research design, experiment/quasi-experiment choice, and scientific failed-experiment recovery planning |
| `hypothesis-generation` | Testable hypotheses, predictions, mechanisms, validation experiments, and explicit HypoGeniC-style automated hypothesis requests |
| `performing-causal-analysis` | Existing-data causal effect estimation, DiD/ITS/synthetic-control analysis, robustness checks, and fitted causal interpretation |
| `research-grants` | Grant aims, significance, innovation, budget logic, and reviewer-facing proposal structure |
| `scientific-brainstorming` | Open-ended scientific ideation, mechanism exploration, research directions, and lightweight literature-matrix/A+B idea mapping |

## Deleted Or Absorbed

| Deleted skill | New owner | Rationale |
| --- | --- | --- |
| `experiment-failure-analysis` | `designing-experiments` | Failed scientific experiments are recovery-design decisions, not a separate top-level expert. Software/test failures remain outside this pack. |
| `hypogenic` | `hypothesis-generation` | HypoGeniC is a narrow tool/framework trigger; automated hypothesis generation is now handled inside the hypothesis owner. |
| `literature-matrix` | `scientific-brainstorming` | A+B paper-combination ideation is useful, but the large matrix workflow is too heavy as a default route owner. |
| `performing-regression-analysis` | `data-ml / scikit-learn` or `performing-causal-analysis` | Ordinary regression belongs to data modeling; causal regression/effect estimation remains with causal analysis. |

## Protected Route Boundaries

| Prompt type | Expected owner |
| --- | --- |
| Quasi-experiment design before modeling | `research-design / designing-experiments` |
| Scientific experiment failure recovery plan | `research-design / designing-experiments` |
| Existing panel data causal effect estimation | `research-design / performing-causal-analysis` |
| Plain or HypoGeniC-style hypothesis generation | `research-design / hypothesis-generation` |
| Literature matrix / A+B innovation ideation | `research-design / scientific-brainstorming` |
| Open-ended mechanism ideation | `research-design / scientific-brainstorming` |
| Ordinary regression coefficients and diagnostics | `data-ml / scikit-learn`, not `research-design` |
| LaTeX/PDF paper build | `scholarly-publishing-workflow / latex-submission-pipeline`, not `research-design` |

## Verification Targets

The cleanup is protected by:

```powershell
python -m pytest tests/runtime_neutral/test_research_design_pack_consolidation.py -q
.\scripts\verify\vibe-skill-index-routing-audit.ps1
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\probe-scientific-packs.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
.\scripts\verify\vibe-global-pack-consolidation-audit-gate.ps1 -WriteArtifacts -OutputDirectory outputs\skills-audit-latest
```

## Caveat

Historical governance documents may still mention the deleted skills as previous-state evidence. Live routing authority is defined by `config/pack-manifest.json`, `config/skill-keyword-index.json`, `config/skill-routing-rules.json`, and the refreshed `skills-lock.json`.
