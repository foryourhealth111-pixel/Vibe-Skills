# Cross-Plane Task Contract Governance

## Goal

Wave76 introduces a **unified task contract** for `browser`, `desktop`, `document`, and `connector` actions.
This is the single task contract for cross-plane execution inside VCO.

The task contract exists so that cross-plane work stops looking like four unrelated execution styles and starts looking like one governed envelope with plane-specific adapters.

## Control-Plane Boundary

The unified task contract must preserve the following invariants:

- `vco` remains the only control plane and no second orchestrator may appear;
- no plane may invent a silent write path;
- confirmation posture is represented explicitly as `confirm_mode`;
- rollback and replay are first-class contract fields, not afterthoughts.

## Canonical Task Envelope

Every cross-plane task envelope must define:

- `task_id`
- `plane_id`
- `intent`
- `capability_class`
- `risk_class`
- `confirm_mode`
- `input_artifacts`
- `expected_outputs`
- `rollback_plan`
- `replay_handle`
- `operator_owner`
- `evidence_refs`

The authoritative contract lives in `references/unified-task-contract.md`.

## Plane Bindings

| Plane | What the contract normalizes |
|---|---|
| `browser` | page/task intent, confirm posture, replay handle, rollback plan |
| `desktop` | operator-visible action intent, execution boundary, replay trace |
| `document` | document transform intent, output contract, rollback / rerun guidance |
| `connector` | provider-backed capability, confirm discipline, evidence refs |

## Governance Rules

1. `confirm_mode` must be explicit for every plane.
2. `rollback_plan` must describe how to return to the prior safe stage.
3. `replay_handle` must be stable enough for audit and drill use.
4. `evidence_refs` must point back to governance artifacts, not only transient logs.
5. Plane adapters may add fields, but may not remove the canonical envelope.

## Usage

The unified task contract is used by:

- cross-plane replay governance;
- promotion board v2 evidence review;
- rollback drill SOPs;
- release train v2 evidence bundling.
