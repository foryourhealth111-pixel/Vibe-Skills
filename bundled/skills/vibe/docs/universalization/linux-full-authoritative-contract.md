# Linux Full-Authoritative Promotion Boundary

> Status baseline: 2026-03-14  
> Scope: define the boundary between frozen Linux proof and any future promotion to `full-authoritative` when `pwsh` is available.

## Purpose

This document exists to prevent two opposite mistakes:

1. treating frozen fresh-machine proof as if formal promotion has already shipped
2. throwing away Linux proof simply because release truth remains conservative

Linux proof is real. Promotion is not yet claimed in current release truth.

## Current Truth

As of this baseline:

- Windows remains the proven `full-authoritative` lane.
- `Codex on Linux + pwsh` remains `supported-with-constraints`.
- `Codex on Linux without pwsh` remains `degraded-but-supported`.
- Fresh-machine Linux proof is frozen and kept ready for a future promotion decision.

## Promotion Target

Linux may move from `supported-with-constraints` to `full-authoritative` only when **all** of the following remain true at the same time:

1. the frozen fresh-machine Linux proof bundle is still complete
2. replay fixtures, adapter contracts, and public docs are synchronized in the same batch
3. the release note explicitly re-opens and ships the promotion claim
4. Windows remains green on the reference authority lane
5. Linux without `pwsh` still stays explicitly degraded rather than silently upgraded

## Required Entry Points

Future Linux promotion depends on these governed surfaces:

- `install.sh`
- `check.sh`
- `scripts/bootstrap/one-shot-setup.sh`
- `scripts/verify/runtime_neutral/freshness_gate.py`
- `scripts/verify/runtime_neutral/coherence_gate.py`
- `scripts/verify/runtime_neutral/bootstrap_doctor.py`

## Required Evidence

Any future promotion batch must preserve evidence for:

- runtime freshness
- release/install/runtime coherence
- bootstrap doctor parity
- honest degraded behavior when `pwsh` is absent
- Windows baseline preservation in the same batch

## Stop Rules

Promotion must stop and remain below `full-authoritative` if any of the following happens:

1. Windows baseline regresses
2. runtime-neutral receipts drift from the existing contract
3. Linux without `pwsh` becomes a silent skip instead of an explicit degraded result
4. public docs or adapter contracts claim promotion before release truth and replay fixtures are synchronized
5. proof bundle completeness drifts below the frozen evidence baseline

## Allowed Current Claim

The strongest truthful claim today is:

`Codex on Linux + pwsh` has frozen fresh-machine proof and is the strongest Linux lane currently available, but it still ships as `supported-with-constraints`. `Codex on Linux without pwsh` remains explicitly `degraded-but-supported`.
