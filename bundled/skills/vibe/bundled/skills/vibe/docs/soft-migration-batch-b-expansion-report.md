# Soft Migration Batch B Expansion Report

Date: 2026-02-24  
Scope: `$vibe` pack 路由扩容（保持 soft migration，不删除 canonical skill）

## 1. Change Summary

- Expanded `skills/vibe/config/pack-manifest.json` candidate coverage from partial set to near-full canonical set.
- Updated `skills/vibe/config/router-thresholds.json`:
  - `safety.max_skill_candidates_per_pack`: `7 -> 80`
- Synced runtime copies:
  - `skills/vibe/bundled/skills/vibe/config/pack-manifest.json`
  - `skills/vibe/bundled/skills/vibe/config/router-thresholds.json`

## 2. Current Pack Candidate Distribution

- `orchestration-core`: 27
- `code-quality`: 16
- `data-ml`: 52
- `bio-science`: 34
- `docs-media`: 22
- `integration-devops`: 14
- `ai-llm`: 13
- `research-design`: 45

Total candidate entries: 223  
Unique candidate entries: 223  
Cross-pack duplicate entries: 0

## 3. Coverage Check

Two measurement baselines were used:

- Directory baseline (excluding `vibe` and hidden dirs):
  - canonical directories: 224
  - covered by pack candidates: 222
  - coverage: `99.11%`
  - uncovered dirs: `learned`, `shared-templates` (resource-like dirs, not standard skill dirs)

- Skill baseline (requires `SKILL.md`):
  - valid skill dirs: 222
  - covered by pack candidates: 222
  - coverage: `100%`

## 4. Verification Results

All core verification scripts passed after expansion:

- `skills/vibe/scripts/verify/vibe-routing-smoke.ps1`  
  - assertions: 38  
  - passed: 38  
  - failed: 0

- `skills/vibe/scripts/verify/vibe-pack-routing-smoke.ps1`  
  - assertions: 98  
  - passed: 98  
  - failed: 0

- `skills/vibe/scripts/verify/vibe-soft-migration-practice.ps1`  
  - assertions: 11  
  - passed: 11  
  - failed: 0

- `skills/vibe/scripts/verify/vibe-pack-regression-matrix.ps1`  
  - assertions: 23  
  - passed: 23  
  - failed: 0

## 5. Risk and Gate to Hard Migration

Current state is suitable for continued soft migration observation:

- Pack overlay works with full candidate expansion.
- Legacy matrix fallback remains available and verified.
- Alias mapping remains intact and resolves correctly.

Recommended hard migration gate for next batch:

- Keep current config for observation window.
- Track misroute and fallback frequency in real tasks.
- Proceed to hard migration only after no key misroutes are observed in practice.
