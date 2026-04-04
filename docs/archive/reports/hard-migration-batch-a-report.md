# Hard Migration Report - Batch A

Date: 2026-02-24

## Scope

Deleted duplicate top-level skill directories after soft-migration validation.

Removed:
- `skills/code-review1`
- `skills/code-review2`
- `skills/code-review3`
- `skills/code-review4`
- `skills/xlsx1`

Kept canonical:
- `skills/code-review`
- `skills/xlsx`

Compatibility:
- legacy names retained in `config/skill-alias-map.json`
- pack routing fallback chain unchanged

## Duplicate Inventory Delta

Before (top-level):
- skill count: 228
- duplicate groups: 2
- duplicate names:
  - `code-review` (5 directories)
  - `xlsx` (2 directories)

After (top-level):
- skill count: 223
- duplicate groups: 0

## Validation

Executed:
- `scripts/verify/vibe-routing-smoke.ps1`
- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-soft-migration-practice.ps1`
- `scripts/verify/vibe-pack-regression-matrix.ps1`

Expected acceptance:
- all assertions pass
- no critical misroute
- deterministic route behavior for repeated input
