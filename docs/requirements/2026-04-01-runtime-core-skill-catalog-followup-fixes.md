# Runtime-Core / Skill-Catalog Follow-up Fixes

Date: 2026-04-01
Runtime: `vibe`
Status: `frozen`
Topic: `runtime-core-skill-catalog-followup-fixes`

## Goal

Fix the two remaining boundary defects in the runtime-core / skill-catalog
split:

1. `skill-catalog` must not participate in installed runtime freshness truth.
2. Catalog manifest consumers must honor the indirection declared by
   `config/runtime-core-packaging.json` instead of hardcoding a single path.

## Constraints

- Keep the same git repository and the same public install profiles:
  `minimal` and `full`.
- Preserve the separate catalog profile gate.
- Avoid widening the change beyond runtime packaging truth and catalog manifest
  resolution.

## Acceptance Criteria

- `config/skill-catalog-*.json` is no longer part of runtime payload mirroring.
- `config/skill-catalog-*.json` is no longer part of
  `runtime.installed_runtime.required_runtime_markers`.
- Python installer, PowerShell installer, and the catalog verification gate all
  resolve the catalog packaging manifest through the runtime-core manifest
  contract.
- Tests cover both boundaries and fail if either regression returns.

## Non-Goals

- No rework of catalog profile contents.
- No change to the public `minimal` / `full` profile mapping.
- No new fetch-on-demand or multi-repo packaging behavior.
