# Connector Action Ledger Governance

## Purpose

Wave74 formalizes a **connector action ledger** so that connector execution is no longer described only by scattered docs or provider-specific logs.

The ledger is the canonical operator-facing record for:

- what connector capability was requested;
- which provider surface handled it;
- whether confirmation was required;
- how the action can be replayed;
- how the operator should roll it back.

## Why A Dedicated Ledger Exists

Connector admission governs *whether* a provider may participate.
Connector scorecards govern *how healthy* the plane is.
The action ledger governs *what actually happened when a connector action was executed*.

Without a ledger, the connector plane cannot satisfy Wave76-82 requirements for replay, rollback, and release evidence.

## Required Ledger Fields

Every governed connector action row must expose the following minimum fields:

- `action_id`
- `provider_id`
- `capability_id`
- `risk_class`
- `confirm_mode`
- `requested_by`
- `execution_owner`
- `rollback_command`
- `replay_handle`
- `evidence_refs`

If any of these fields are absent, the action may remain documented, but it is **not promotion-grade evidence**.

## Governance Rules

1. `control_plane_owner` remains `vco` even when a provider executes the action.
2. `confirm_mode = required` is mandatory for all write-capable or externally visible actions.
3. `rollback_command` must be specific enough for an operator to execute without inventing missing steps.
4. `replay_handle` must be stable enough to support cross-plane replay governance.
5. `evidence_refs` must point to governance docs, gate artifacts, or operator evidence — not only to provider dashboards.

## Risk Classes

| Risk class | Meaning | Minimum posture |
|---|---|---|
| `read_only` | safe inspection or retrieval | replayable, no silent escalation |
| `confirm_write` | write action allowed only behind human confirmation | `confirm_mode = required`, rollback required |
| `deny` | action class is catalogued but not execution-eligible | must never appear as an executed action row |

## Lifecycle

The connector action ledger participates in the following lifecycle:

1. admission identifies the provider surface;
2. scorecard evaluates provider readiness;
3. action ledger records concrete governed actions;
4. cross-plane replay links connector actions to task-level replay evidence;
5. promotion board consumes the resulting evidence summary.

## Outputs

The canonical contract for this ledger lives in `references/connector-action-ledger.md`.
Validation is performed by `scripts/verify/vibe-connector-action-ledger-gate.ps1`.
