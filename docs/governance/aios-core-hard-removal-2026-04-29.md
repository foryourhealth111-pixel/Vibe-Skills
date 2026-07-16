# AIOS Core Hard Removal

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

Date: 2026-04-29

## Decision

`aios-core` was removed from live Vibe-Skills routing.

This was a hard removal because the bundled AIOS skills were thin activator wrappers, not self-contained skills. They pointed to `.aios-core/development/agents/*.md` or `.codex/agents/*.md`, but those source paths are absent in this checkout.

## Deleted Skill Directories

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

## Routing Contract Change

| Surface | Before | After |
| --- | --- | --- |
| Pack | `aios-core` | removed |
| `skill_candidates` | 12 AIOS role skills | none |
| `route_authority_candidates` | `aios-master` | none |
| `stage_assistant_candidates` | 11 AIOS role skills | none |
| defaults | all task types to `aios-master` | none |
| upstream source aliases | `SynkraAI/aios-core`, `aios-core` | removed |
| upstream lock | `SynkraAI/aios-core` reference entry | removed |

PRD, backlog, user-story, product-owner, scrum-master, and quality-gate prompts no longer route to an AIOS role team.

If an existing non-AIOS pack clearly owns the prompt, that pack may be selected. If no pack owns it clearly, confirmation is preferred over reintroducing AIOS as a catch-all.

## Simplified Model Alignment

This removal keeps the public six-stage Vibe runtime unchanged. It only removes a noisy role-team pack from the skill routing surface.

AIOS no longer contributes primary, secondary, stage-assistant, role-team, or consultation-style routing surfaces. The remaining routing contract is the simplified `candidate -> selected -> used / unused` model.

## Verification Anchors

The implementation is protected by:

- `tests/runtime_neutral/test_aios_core_hard_removal.py`
- `tests/runtime_neutral/test_router_bridge.py`
- `scripts/verify/vibe-pack-regression-matrix.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-routing-stability-gate.ps1`
- `scripts/verify/vibe-openspec-governance-gate.ps1`
- `scripts/verify/vibe-router-contract-gate.ps1`
- `scripts/verify/vibe-offline-skills-gate.ps1`
- `scripts/verify/vibe-config-parity-gate.ps1 -WriteArtifacts`

Expected route behavior:

- `config/pack-manifest.json` has no `aios-core` pack.
- no `bundled/skills/aios-*` directory remains.
- `config/skills-lock.json` has no `aios-*` skill.
- product planning prompts do not select `aios-core` or any `aios-*` skill.
- ranked route metadata does not include AIOS skills as stage assistants.
- upstream source alias and lock metadata no longer expose an AIOS reimport handle.
