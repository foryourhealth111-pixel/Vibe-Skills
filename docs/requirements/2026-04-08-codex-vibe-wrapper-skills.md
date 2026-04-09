# Codex Vibe Wrapper Skills Requirement

## Goal
Make Codex full-profile installs expose a skill-first `vibe` family consisting of:

- `vibe`
- `vibe-what-do-i-want`
- `vibe-how-do-we-do`
- `vibe-do-it`

while preserving `vibe` as the only canonical governed runtime skill.

## Required Outcomes
- Codex full-profile install materializes the three wrapper skills into the host-visible skill surface under `skills/`.
- `vibe` remains the only runtime authority and keeps the canonical governed contract.
- Wrapper skills are thin entry-bias surfaces only and must delegate into canonical `vibe`.
- Codex check flows validate the skill surface first.
- Existing command files, if retained, are treated as compatibility shims rather than the primary Codex discovery surface.

## Constraints
- No second runtime authority may be introduced.
- No second requirement surface may be created by wrapper skills.
- No second plan surface may be created by wrapper skills.
- This implementation is scoped to `codex` with `full` profile only.
- `minimal` profile and other hosts remain unchanged in this turn.

## Acceptance Criteria
- Packaging manifests declare wrapper-skill projections for Codex full profile.
- The repo contains bundled wrapper skill sources for the three new entries.
- A fresh Codex full-profile install creates:
  - `skills/vibe/SKILL.md`
  - `skills/vibe-what-do-i-want/SKILL.md`
  - `skills/vibe-how-do-we-do/SKILL.md`
  - `skills/vibe-do-it/SKILL.md`
- Codex governed checks pass while validating those four skills.
- Real-host verification in `~/.codex` confirms host-visible wrapper skill entries.

## Non-Goals
- Do not redesign the canonical `vibe` runtime contract.
- Do not migrate all hosts to skill-first wrapper surfaces in this turn.
- Do not use wrapper-skill visibility as MCP completion evidence.
