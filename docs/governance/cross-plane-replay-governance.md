# Cross-Plane Replay Governance

## Purpose

Wave77 turns replay from a collection of plane-local traces into a **single cross-plane replay ledger**.

The replay ledger exists so operators can answer one question across planes:

> What was requested, what was confirmed, what executed, what evidence was captured, and how do we replay or roll back it now?

## Replay Chain

Every governed replay chain must preserve the same ordered checkpoints:

1. `request`
2. `confirm`
3. `execute`
4. `verify`
5. `rollback` (when needed)
6. `replay`

If any checkpoint is missing, the run may be useful for debugging, but it is not promotion-grade replay evidence.

## Required Fields

The replay ledger must be able to join back to the unified task contract and connector action ledger through:

- `replay_id`
- `task_id`
- `plane_id`
- `action_id`
- `confirm_token`
- `artifact_hash`
- `rollback_token`
- `outcome`
- `evidence_refs`

## Governance Rules

1. Replay evidence must be plane-agnostic at the ledger level.
2. `confirm_token` is required whenever `confirm_mode = required`.
3. `artifact_hash` must identify the evidence snapshot that was actually reviewed.
4. `rollback_token` must exist whenever a rollback path exists.
5. The replay ledger must remain operator-readable, not provider-dashboard-only.

## Consumers

Cross-plane replay evidence feeds directly into:

- promotion board v2;
- ops cockpit freshness / drift / replay panels;
- rollback drills;
- release train v2 evidence bundles;
- Wave64-82 closure decisions.

The authoritative schema lives in `references/cross-plane-replay-ledger.md`.
