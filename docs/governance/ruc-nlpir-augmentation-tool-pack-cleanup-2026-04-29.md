# RUC-NLPIR Augmentation Tool Pack Cleanup

Date: 2026-04-29

## Decision

`ruc-nlpir-augmentation` is now an explicit two-tool pack:

| Tool | Ownership |
| --- | --- |
| `flashrag-evidence` | Local repo/config/governance evidence lookup with file and line anchors |
| `webthinker-deep-research` | Auditable multi-hop web research with `report.md`, `sources.json`, and `trace.jsonl` |

The pack no longer exposes DeepAgent as a skill, helper, stage assistant, overlay, runtime repo, capability, or upstream reimport handle.

## Before / After

| Surface | Before | After |
| --- | --- | --- |
| `skill_candidates` | 4 | 2 |
| `route_authority_candidates` | 2 | 2 |
| `stage_assistant_candidates` | 2 | 0 |
| `defaults_by_task` | planning/review/debug -> `flashrag-evidence`; research -> `webthinker-deep-research` | research -> `webthinker-deep-research` |
| Bundled DeepAgent skills | `deepagent-toolchain-plan`, `deepagent-memory-fold` | none |
| RUC-NLPIR runtime repos | FlashRAG, WebThinker, DeepAgent | FlashRAG, WebThinker |

## Trigger Boundary

`flashrag-evidence` is selected only for explicit local evidence lookup, such as repo/config evidence, route rule evidence, `SKILL.md` source-of-truth lookup, or file-and-line citation requests.

`webthinker-deep-research` is selected only for explicit auditable web research, such as deep research, multi-hop browsing, `trace.jsonl`, `sources.json`, or web evidence-chain requests.

DeepAgent prompts such as toolchain planning, skill-chain planning, memory folding, and context compression do not route to this pack.

## Verification

Protected by:

- `tests/runtime_neutral/test_ruc_nlpir_augmentation_cleanup.py`
- `tests/runtime_neutral/test_router_bridge.py`
- `scripts/verify/vibe-pack-regression-matrix.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-routing-stability-gate.ps1`
- `scripts/verify/vibe-offline-skills-gate.ps1`
- `scripts/verify/vibe-config-parity-gate.ps1`
- `scripts/verify/vibe-capability-catalog-gate.ps1`

## Non-Changes

This cleanup does not change Vibe's six-stage runtime and does not introduce a replacement helper, assistant, or consultation role.
