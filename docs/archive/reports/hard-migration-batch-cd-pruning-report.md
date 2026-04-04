# Hard Migration Report - Batch C/D Candidate Pruning

Date: 2026-02-24

## Scope

Execute remaining hard migration work for Batch C/D at config level:

- Prune `skill_candidates` in the following packs:
  - `data-ml`
  - `research-design`
  - `ai-llm`
  - `bio-science`
  - `docs-media`
  - `integration-devops`
- Keep:
  - grade/task boundaries unchanged
  - alias map unchanged
  - fallback behavior unchanged

## Safety Snapshot

- Pre-change snapshot:
  - `outputs/backups/pack-manifest-pre-batch-cd-20260224-225014.json`

## Candidate Count Delta

| Pack | Before | After | Delta | Reduction |
|------|--------|-------|-------|-----------|
| data-ml | 52 | 25 | -27 | 51.92% |
| research-design | 45 | 25 | -20 | 44.44% |
| ai-llm | 13 | 11 | -2 | 15.38% |
| bio-science | 34 | 21 | -13 | 38.24% |
| docs-media | 22 | 16 | -6 | 27.27% |
| integration-devops | 14 | 12 | -2 | 14.29% |

Batch C/D total candidates:
- Before: `180`
- After: `110`
- Delta: `-70` (`38.89%` reduction)

Global candidates across all packs:
- Before: `223`
- After: `153`
- Delta: `-70`

## Validation

Executed after pruning:

- `scripts/verify/vibe-routing-smoke.ps1` -> `38/38`
- `scripts/verify/vibe-pack-routing-smoke.ps1` -> `104/104`
- `scripts/verify/vibe-skill-index-routing-audit.ps1` -> `93/93`
- `scripts/verify/vibe-keyword-precision-audit.ps1` -> `982/982`
- `scripts/verify/vibe-pack-regression-matrix.ps1` -> `24/24`

Key observation:
- No assertion failures.
- No critical misroute introduced.
- Determinism checks remain stable.

## Files Changed

- `skills/vibe/config/pack-manifest.json`
- `skills/vibe/bundled/skills/vibe/config/pack-manifest.json`

## Outcome

Batch C/D hard-migration candidate pruning completed and validated.
System remains in stable soft-fallback-capable mode while reducing candidate noise.

