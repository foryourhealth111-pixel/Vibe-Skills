# VCO Status

`docs/status/` is the runtime-entry surface inside `docs/`.

It answers three questions:

1. what is true about the repository right now
2. what closure batch or migration wave is currently active
3. which capabilities are not allowed to regress during convergence

## Start Here

### Runtime Summary

- [`current-state.md`](current-state.md): the single live status entry; keep only artifact-backed summary, blockers, and operator handoff
- [`roadmap.md`](roadmap.md): current batch order, exit conditions, and next-wave sequencing

### Batch Receipts

- [`operator-dry-run.md`](operator-dry-run.md): latest operator replay for the active wrapper or closure batch
- [`closure-audit.md`](closure-audit.md): current closure-batch completion surface, remaining gaps, no-overclaim notes, and report-only completion-honesty language

### Guardrails / Proof / Transitional Baselines

- [`protected-capability-baseline.md`](protected-capability-baseline.md): defines which surfaces must be proven before they are changed during closure work
- [`non-regression-proof-bundle.md`](non-regression-proof-bundle.md): current cleanup and no-regression proof contract
- [`stage-bound-specialist-dispatch-closure-2026-03-28.md`](stage-bound-specialist-dispatch-closure-2026-03-28.md): closure proof for phase-bound specialist dispatch, `L` serial specialist steps, and `XL` bounded specialist lanes under root/child governance
- [`platform-promotion-baseline-2026-03-13.md`](platform-promotion-baseline-2026-03-13.md): current platform-promotion truth snapshot
- [`linux-pwsh-fresh-machine-evidence-ledger-2026-03-13.md`](linux-pwsh-fresh-machine-evidence-ledger-2026-03-13.md): Linux fresh-machine evidence ledger for the promoted `Linux + pwsh` authoritative lane
- [`single-core-dual-adaptation-baseline-2026-03-14.md`](single-core-dual-adaptation-baseline-2026-03-14.md): first adapter-contract landing status for platform-neutral target roots, installed-runtime resolution, and shell spawning
- [`router-platform-truth-matrix-2026-03-15.md`](router-platform-truth-matrix-2026-03-15.md): router-specific platform truth matrix for the Linux host-neutrality and route-quality recovery wave
- [`path-dependency-census.md`](path-dependency-census.md): transitional blocker map for dependencies that still cannot be removed or relocated blindly
- [`repo-cleanliness-baseline.md`](repo-cleanliness-baseline.md): dated inventory baseline for delta measurement, not a live dashboard

## Cross-Layer Handoff

- [`../README.md`](../README.md): top-level docs entry
- [`../plans/README.md`](../plans/README.md): execution plans and historical batch context
- [`../../scripts/README.md`](../../scripts/README.md): operator script surface
- [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md): verify-family navigation and canonical run order
- [`../universalization/platform-promotion-criteria.md`](../universalization/platform-promotion-criteria.md): canonical promotion criteria
- [`../universalization/linux-full-authoritative-contract.md`](../universalization/linux-full-authoritative-contract.md): Linux promotion contract and stop rules

## Rules

- `current-state.md` is the only live summary page in `docs/status/`; any PASS / FAIL or numeric claim must point back to `outputs/verify/**` or an operator receipt
- `operator-dry-run.md` and `closure-audit.md` are batch receipts; keep only the latest trustworthy, reviewable version
- closure reporting must preserve honest objective / scope / completion wording; anti-drift report-only warnings correct language but do not silently become hard enforcement
- supporting baselines may act only as guardrails, proof contracts, or transitional blocker maps; when content becomes a stable long-term contract, move it back to root `docs/` or `references/`
- dated baselines such as `repo-cleanliness-baseline.md` must be clearly distinguished from current state; the latest gate receipt remains authoritative
- historical closure reports and batch reports stay under [`../plans/README.md`](../plans/README.md), not here
