# Data Scale Overlay Integration (xan x VCO)

## Purpose

Integrate `xan` as a data-volume-aware execution enhancement for tabular tasks without introducing a second router or changing existing pack scoring logic.

This overlay is designed to:
- Keep `/vibe` as the only routing entrypoint
- Use real file signals (size/rows/format) instead of relying only on user wording
- Recommend or switch `spreadsheet/xlsx/xan` in a controlled, mode-based way

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the control plane.
2. **Post-route decision layer**: overlay runs after pack and candidate selection.
3. **Scoped to tabular surface**: only applies to configured packs/skills (default `docs-media` + `spreadsheet/xlsx/excel-analysis/xan`).
4. **No model-flow takeover**: does not route ML tasks away from `data-ml`.

## Config

Primary policy file:
- `config/data-scale-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/data-scale-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `path_probe` (path extraction + optional workspace probe + sampling caps)
- `thresholds` (size/row thresholds, confidence thresholds)
- `recommendations` (default/large/workbook target skills)

## Runtime Behavior

Router file:
- `scripts/router/resolve-pack-route.ps1`

Output additions:
- `data_scale_advice`
- `data_scale_route_override`

Semantics:
- `shadow`: advisory only, never changes selected skill.
- `soft`: when recommendation conflicts with selected skill and confidence is sufficient, escalate to `confirm_required`.
- `strict`: if confidence is high enough, auto-override selected skill (within same pack candidates); otherwise require confirm.
- `off`: no overlay effect.

## Real Data Signal Strategy

1. Extract file paths from prompt (quoted + unquoted path patterns).
2. Resolve existing files from prompt paths.
3. Analyze primary file (largest by size):
   - extension and format class (`workbook` vs `csv-like`)
   - file size
   - lightweight sampled row/column estimate for uncompressed CSV-like files
4. Derive scale class (`small|medium|large`) and produce recommendation.

Defaults:
- workbook -> `xlsx` (or `excel-analysis` for pivot-like intent)
- large CSV-like -> `xan`
- small/medium CSV-like -> `spreadsheet` unless operation hints prefer `xan`

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-data-scale-overlay-gate.ps1
```

Run legacy-named packaging gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

## Failure Semantics

- missing policy -> bypass overlay advice
- no existing data file detected -> keep selected skill
- probe errors -> keep selected skill
- recommendation outside current pack candidates -> advisory only (no forced cross-pack switch)
