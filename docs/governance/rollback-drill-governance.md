# Rollback Drill Governance

## Purpose

Wave80 turns rollback from a documented promise into a **drillable operator routine**.

Every promoted candidate must prove that rollback is executable, not merely described.

## Drill Types

| Drill type | What is exercised |
|---|---|
| `plane rollback` | reverting a plane from `soft` or `strict_candidate_review` back to `shadow` |
| `kill switch drill` | proving the operator can stop a risky surface quickly |
| `freshness rollback` | recovering from install / runtime / parity regressions |
| `release abort` | stopping a release train before promotion evidence is overstated |

## Mandatory Evidence

Every rollback drill must capture:

- the `kill switch` or equivalent operator action;
- the expected fallback stage;
- the `operator SOP` or runbook reference;
- the resulting state after rollback;
- whether `max_safe_auto_write_stage = soft` remained intact.

## Governance Rules

1. No plane may claim promotion readiness without a rollback drill path.
2. Drills must be operator-reproducible, not author-memory-dependent.
3. If rollback evidence is stale, the plane must be treated as `shadow` for promotion purposes.
4. Release claims must defer to rollback evidence when the two disagree.

## Cadence

- before widening a `soft_candidate`
- before strict_candidate review
- before a release train includes a newly widened plane

Validation is performed by `scripts/verify/vibe-rollback-drill-gate.ps1`.
