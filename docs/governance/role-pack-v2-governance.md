# Role Pack v2 Governance

## Purpose

Wave89 upgrades role-pack governance with a scorecard and catalog format that can absorb value from `agent-squad` and `awesome-claude-code-subagents` without importing a second orchestrator.
Role pack v2 focuses on role clarity, handoff readiness, and bounded ownership under the Codex Native Team runtime.

## Governance Scope

- Role packs remain subordinate to VCO and cannot become a new orchestration runtime.
- Every role card must declare boundaries, expected inputs, expected outputs, and overlap-risk notes.
- The scorecard must explicitly penalize duplicated ownership or hidden supervisor behavior.

## Required Invariants

- `second_orchestrator_forbidden = true` stays fixed.
- `codex_native_team_runtime_only = true` remains the only execution topology assumption.
- Role pack evidence can support planning and handoff quality, not route authority.
- Every promoted role pack must preserve explicit done definitions and reviewer ownership.

## Non-Goals

- No second supervisor hierarchy is introduced.
- No pack may silently claim merge, release, or router ownership.

Validation is performed by `scripts/verify/vibe-role-pack-v2-gate.ps1`.
