# Per-Skill Index Rollout Report

Date: 2026-02-24  
Scope: `$vibe` pack router + per-skill keyword index refinement

## 1. Goal

Introduce a per-skill keyword layer (especially Chinese business phrases) to reduce same-pack skill jitter while preserving the existing soft-migration architecture.

## 2. What Changed

- Added `config/skill-keyword-index.json`
  - Includes high-frequency skill mappings and bilingual keywords.
  - Adds common Chinese business phrases for practical routing.
- Updated `scripts/router/resolve-pack-route.ps1`
  - Added pack-level `skill_keyword_signal` into pack scoring.
  - Added keyword-ranked candidate selection inside each pack.
  - Preserved explicit skill priority (`RequestedSkill`) as strongest signal.
- Updated `config/router-thresholds.json`
  - Added `weights.skill_keyword_signal`.
- Updated `config/pack-manifest.json`
  - Expanded bilingual triggers for frequently ambiguous domains.
- Added verification script:
  - `scripts/verify/vibe-skill-index-routing-audit.ps1`

## 3. Validation Results

### Per-skill routing audit

- Script: `vibe-skill-index-routing-audit.ps1`
- Assertions: `93`
- Passed: `93`
- Failed: `0`

### Existing regression suite

- `vibe-routing-smoke.ps1`: `38/38`
- `vibe-pack-routing-smoke.ps1`: `104/104`
- `vibe-soft-migration-practice.ps1`: `11/11`
- `vibe-pack-regression-matrix.ps1`: `24/24`
- `vibe-keyword-precision-audit.ps1`: `1402/1402`

## 4. Compatibility

- Soft migration behavior remains intact.
- Alias resolution remains unchanged.
- Legacy fallback remains available for low-confidence prompts.
- Main and bundled config copies are synchronized.

## 5. Conclusion

Per-skill index routing is now active and validated for bilingual practical prompts, with no regression in the existing verification matrix.
