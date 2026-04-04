# Router Modularization Governance (Zero-Regression)

## Objective

Refactor `scripts/router/resolve-pack-route.ps1` into maintainable modules while keeping route behavior contract-stable.

## Current Topology

- Unified entrypoint remains: `scripts/router/resolve-pack-route.ps1`
- Function modules live in: `scripts/router/modules/*.ps1`
- Frozen contract baseline preserved for contract comparison:
  - `tests/replay/route/router-contract-gate-golden.json`

## Module Boundaries

- `00-core-utils.ps1`: normalization, keyword/scoring primitives, shared helpers
- `10-observability.ps1`: telemetry writer and overlay confirm detection
- `20-routing-rules.ps1`: candidate rule filtering and defaults-by-task helpers
- `30-39`: OpenSpec + all overlay advisory modules
- `40-cuda-kernel-overlay.ps1`: CUDA-specific advisory module
- `41-candidate-selection.ps1`: pack-candidate selection and fallback behavior
- `42-ai-rerank-overlay.ps1`: constrained Top-K rerank logic

## Zero-Regression Contract

A modular change is allowed only when all conditions hold:

1. The modular router matches the frozen contract baseline on the core routing matrix (core decision fields must match; additive advisory fields may differ).
2. Existing routing gates remain green.
3. Config parity gate remains 100%.
4. No automatic rollback behavior is introduced.

## Contract Gate

Primary gate:

```powershell
pwsh -File .\scripts\verify\vibe-router-contract-gate.ps1 -WriteArtifacts
```

The gate compares the current modular router against a frozen bilingual and cross-task contract fixture and fails on any **core routing contract** mismatch:

- `route_mode`
- `route_reason`
- `selected.pack_id`
- `selected.skill`
- `confidence`
- `top1_top2_gap`
- `candidate_signal`

Additive advisory payloads (e.g. post-route overlay advice blocks) are intentionally excluded from this gate to allow non-invasive enhancements without forcing legacy snapshot churn.

## Required Gate Chain

1. `vibe-pack-regression-matrix.ps1`
2. `vibe-router-contract-gate.ps1`
3. `vibe-routing-stability-gate.ps1 -Strict`
4. `vibe-config-parity-gate.ps1`
5. `vibe-observability-gate.ps1`
6. `vibe-ai-rerank-gate.ps1`

## CI Enforcement

GitHub workflow:

- `.github/workflows/vco-gates.yml`

includes the contract gate in the default pipeline.

## Operational Discipline

1. Any module change must keep function signatures stable unless explicitly versioned.
2. No strategy tuning (threshold/rule semantics) in pure modularization commits.
3. If a contract gate fails, stop and inspect diffs before proceeding.
4. Rollback remains manual-confirm only; no auto rollback execution.

## Install / Runtime Integrity

- Installer now syncs full router directory (`script + modules`) to target skill path.
- Health checks assert module directory and core module existence.

## Progressive Migration Guidance

1. Refresh `tests/replay/route/router-contract-gate-golden.json` only when a governed router contract change is intentionally approved.
2. If a planned strategy change is needed, do it in a separate commit after contract-stable modularization.
3. Use `check.ps1 -Deep` / `check.sh --deep` before release.
