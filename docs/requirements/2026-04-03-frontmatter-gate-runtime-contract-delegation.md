# 2026-04-03 Frontmatter Gate Runtime Contract Delegation

## Goal

Make the BOM/frontmatter verification gate consume installed-runtime closure paths from effective runtime config instead of hardcoding a second installed-runtime semantic owner.

## Scope

In scope:
- `scripts/verify/vibe-bom-frontmatter-gate.ps1`
- focused integration and runtime-neutral tests

Out of scope:
- changing BOM/frontmatter detection policy
- changing CLI verify entrypoints
- changing release-cut gate orchestration

## Acceptance Criteria

1. The frontmatter gate no longer hardcodes the installed-runtime freshness gate path inline.
2. Runtime closure checks in the frontmatter gate use effective installed-runtime config from governance context.
3. Existing canonical, bundled, nested, and installed scope behavior remains unchanged.
4. Focused tests lock the new boundary and catch regressions.
