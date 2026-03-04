# Keyword Precision Audit Report

Date: 2026-02-24  
Scope: `$vibe` soft migration keywords (accuracy, interference, bilingual hit)

## 1. Objective

Validate that migrated skills route with:

- accurate keyword targeting
- controlled cross-pack interference
- stable bilingual behavior (English + Chinese)

## 2. Implemented Changes

- Router matching upgrade in `scripts/router/resolve-pack-route.ps1`:
  - Added `Test-KeywordHit`
  - English keywords use token-boundary matching
  - Chinese keywords use substring matching
- Expanded bilingual trigger lexicon in `config/pack-manifest.json` for all 8 packs.
- Added keyword audit script: `scripts/verify/vibe-keyword-precision-audit.ps1`.
- Updated regression baseline in `scripts/verify/vibe-pack-regression-matrix.ps1`.

## 3. Audit Method

The keyword audit script performs three layers:

1. Pack keyword completeness:
   - each pack must contain at least one English trigger and one Chinese trigger
2. Pack-level bilingual routing:
   - EN/ZH prompt probes for each pack
   - expected top pack must match
   - top1-top2 score gap must pass interference guard (`>= 0.03`)
3. Skill-level full sweep:
   - all candidate skills tested in EN and ZH prompts with explicit requested skill
   - expected pack and selected skill must match
   - route mode must remain `pack_overlay` for explicit skill targeting

## 4. Results

- `vibe-keyword-precision-audit.ps1`
  - skill candidates checked: `223`
  - total assertions: `1402`
  - passed: `1402`
  - failed: `0`

Also revalidated core suites after keyword changes:

- `vibe-routing-smoke.ps1`: `38/38`
- `vibe-pack-routing-smoke.ps1`: `98/98`
- `vibe-soft-migration-practice.ps1`: `11/11`
- `vibe-pack-regression-matrix.ps1`: `24/24`

## 5. Notes on Fallback vs Overlay

For some generic prompts, route mode may still be `legacy_fallback` because confidence is intentionally threshold-gated.  
This behavior is expected and acts as safety. In these cases, pack ranking remains correct (top pack preserved), and explicit skill requests still route stably via `pack_overlay`.

## 6. Conclusion

Keyword migration quality is currently stable for soft migration:

- bilingual hit behavior validated
- no critical cross-pack interference found under current probe set
- full candidate skill targeting sweep passes end-to-end
