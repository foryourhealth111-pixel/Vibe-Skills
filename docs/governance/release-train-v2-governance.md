# Release Train v2 Governance

## Purpose

Wave81 defines **release train v2** so that governed releases are cut from runtime truth, scorecard evidence, replay evidence, rollback evidence, and operator readiness together.

Release train v2 exists to ensure that promotion claims never outrun governance evidence.

## Release Evidence Stack

Release train v2 requires the following evidence stack:

1. existing version / packaging / runtime freshness gates
2. promotion board v2 snapshot
3. cross-plane replay evidence
4. rollback drill evidence
5. operator readiness from the ops cockpit
6. release notes that record governance impact and stop-ship decisions

## Stop-Ship Rules

Release train v2 is stop-ship when any of the following is true:

- promotion board evidence is missing or stale;
- replay evidence is incomplete for a widened plane;
- rollback drill evidence is absent for a promoted candidate;
- operator readiness is claimed without cockpit evidence;
- release notes omit governance impact.

## Train Stages

| Stage | Required outcome |
|---|---|
| `board_snapshot` | promotion board v2 reflects the intended release scope |
| `gate_bundle` | required Wave64-82 governance gates have been run |
| `operator_handoff` | cockpit, rollback, and replay evidence are reviewable |
| `release_note_cut` | release note and README guidance reflect the final stop-ship bundle |

## Required Wave64-82 Gate Bundle

Release train v2 should be able to point to the following governance bundle when relevant:

- `vibe-connector-scorecard-gate.ps1`
- `vibe-connector-action-ledger-gate.ps1`
- `vibe-prompt-intelligence-productization-gate.ps1`
- `vibe-cross-plane-task-contract-gate.ps1`
- `vibe-cross-plane-replay-gate.ps1`
- `vibe-promotion-scorecard-gate.ps1`
- `vibe-ops-cockpit-gate.ps1`
- `vibe-rollback-drill-gate.ps1`
- `vibe-release-train-v2-gate.ps1`
- `vibe-wave64-82-closure-gate.ps1`

Validation is performed by `scripts/verify/vibe-release-train-v2-gate.ps1`.
