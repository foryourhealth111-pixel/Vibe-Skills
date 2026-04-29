# AIOS Core Hard Removal Design

Date: 2026-04-29

## Decision

Remove `aios-core` from the live Vibe-Skills routing surface.

This is a hard removal, not a role-consolidation pass. The pack and its twelve thin AIOS role skills should no longer be selectable, routable, visible in the bundled skill lock, or presented as a Vibe runtime expert team.

## Current State

`config/pack-manifest.json` currently defines:

| Surface | Current value |
| --- | --- |
| Pack | `aios-core` |
| `skill_candidates` | 12 AIOS role skills |
| `route_authority_candidates` | `aios-master` |
| `stage_assistant_candidates` | 11 AIOS role skills |
| Defaults | all task types route to `aios-master` |

The twelve bundled skill directories are:

- `bundled/skills/aios-analyst`
- `bundled/skills/aios-architect`
- `bundled/skills/aios-data-engineer`
- `bundled/skills/aios-dev`
- `bundled/skills/aios-devops`
- `bundled/skills/aios-master`
- `bundled/skills/aios-pm`
- `bundled/skills/aios-po`
- `bundled/skills/aios-qa`
- `bundled/skills/aios-sm`
- `bundled/skills/aios-squad-creator`
- `bundled/skills/aios-ux-design-expert`

Each directory only contains `SKILL.md`. No scripts, templates, references, examples, or assets were found.

Each `SKILL.md` is an activator wrapper that points to `.aios-core/development/agents/*.md` or `.codex/agents/*.md`. Those source paths do not exist in this checkout, so the skills are not self-contained.

## Goals

- Remove the `aios-core` pack from live routing.
- Physically delete the twelve bundled `aios-*` skill directories.
- Remove AIOS role keys from keyword and routing-rule configs.
- Remove AIOS capability-catalog references.
- Refresh `config/skills-lock.json`.
- Keep Vibe's public six-stage runtime unchanged.
- Keep the simplified skill usage model intact:

```text
candidate -> selected -> used / unused
```

## Non-Goals

- Do not import or vendor SynkraAI AIOS upstream assets.
- Do not replace AIOS with another role-team framework.
- Do not create `aios-master` as a rewritten self-contained skill.
- Do not introduce a new primary/secondary/assistant skill concept.
- Do not change canonical `$vibe` launch, requirement freeze, plan freeze, execution, or cleanup behavior.

## Routing Migration

Existing prompts that route to `aios-core` should stop selecting AIOS.

Representative prompts:

| Prompt class | Current route | Target route |
| --- | --- | --- |
| `create PRD and user story backlog with quality gate` | `aios-core / aios-master` | no AIOS route; route to an existing planning or quality owner, or require confirmation if ambiguous |
| `输出用户故事和产品需求文档` | `aios-core / aios-master` | no AIOS route; route to an existing planning owner, or require confirmation if ambiguous |
| `product owner style backlog prioritization and acceptance criteria` | `aios-core / aios-master` or AIOS role metadata | no AIOS route; no AIOS role metadata |

The migration should prefer existing non-AIOS surfaces:

- general governed task planning remains under canonical `vibe` / orchestration surfaces
- code quality, test strategy, and quality-gate review remain under `code-quality`
- product/requirement drafting should use existing planning flows or confirmation rather than an AIOS role team

If no existing pack owns a prompt cleanly, the router should fall back to confirmation instead of preserving AIOS as a catch-all.

## Files To Change

Expected implementation files:

- `config/pack-manifest.json`
- `config/skill-keyword-index.json`
- `config/skill-routing-rules.json`
- `config/capability-catalog.json`
- `config/skills-lock.json`
- `scripts/verify/vibe-pack-regression-matrix.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-routing-stability-gate.ps1`
- `scripts/verify/vibe-openspec-governance-gate.ps1`
- `tests/runtime_neutral/test_router_bridge.py`
- route replay fixtures under `tests/replay/route/`
- new focused runtime-neutral test for AIOS hard removal
- new governance note under `docs/governance/`

Expected deleted directories:

- `bundled/skills/aios-analyst`
- `bundled/skills/aios-architect`
- `bundled/skills/aios-data-engineer`
- `bundled/skills/aios-dev`
- `bundled/skills/aios-devops`
- `bundled/skills/aios-master`
- `bundled/skills/aios-pm`
- `bundled/skills/aios-po`
- `bundled/skills/aios-qa`
- `bundled/skills/aios-sm`
- `bundled/skills/aios-squad-creator`
- `bundled/skills/aios-ux-design-expert`

## Verification Design

Add focused tests that prove:

- `config/pack-manifest.json` has no `aios-core` pack.
- no `aios-*` skill directory remains under `bundled/skills`.
- no `aios-*` skill remains in `config/skills-lock.json`.
- route results for PRD/backlog/user-story/quality-gate prompts do not select `aios-core` or any `aios-*` skill.
- route ranked metadata does not include AIOS role skills as `stage_assistant`.

Update existing gates that currently expect AIOS:

- `vibe-pack-regression-matrix.ps1`
- `vibe-pack-routing-smoke.ps1`
- `vibe-routing-stability-gate.ps1`
- `vibe-openspec-governance-gate.ps1`
- replay fixtures that record `aios-core / aios-master`

Final verification should include:

```powershell
python -m pytest tests/runtime_neutral/test_aios_core_hard_removal.py -q
python -m pytest tests/runtime_neutral/test_router_bridge.py -q
.\scripts\verify\vibe-pack-regression-matrix.ps1
.\scripts\verify\vibe-pack-routing-smoke.ps1
.\scripts\verify\vibe-routing-stability-gate.ps1
.\scripts\verify\vibe-openspec-governance-gate.ps1
.\scripts\verify\vibe-generate-skills-lock.ps1
.\scripts\verify\vibe-offline-skills-gate.ps1
.\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```

## Governance Record

The implementation should create `docs/governance/aios-core-hard-removal-2026-04-29.md` documenting:

- why AIOS was removed
- deleted skill directories
- removed routing surfaces
- replacement routing behavior
- verification commands and outcomes

## Risks

Some existing tests and replay fixtures intentionally expect `aios-core / aios-master`. These expectations must be changed to assert the absence of AIOS, not silently removed.

Some broad product-management prompts may become `confirm_required`. That is acceptable because preserving AIOS as a catch-all would reintroduce the same role-team complexity this removal is meant to eliminate.

## Success Criteria

- No live routing config contains an `aios-core` pack.
- No bundled `aios-*` skill directory remains.
- No route probe selects `aios-core` or an `aios-*` skill.
- No AIOS role appears as a stage assistant.
- Required route and offline skill gates pass.
- The work is committed in focused commits, with lock refresh separated if it only changes generated metadata.
