# Connector Scorecard Governance

## Scope

Wave73 moves the connector plane from admission-only governance to **scorecard-governed promotion**.

`connector admission` answers whether a source may exist inside VCO governance.
`connector scorecard` answers whether a governed connector surface is healthy enough to remain in `shadow`, enter `soft_candidate`, or be considered for `strict_candidate` review.

The scorecard is advisory-first:

- it does **not** select a provider at runtime;
- it does **not** auto-promote a connector surface;
- it does **not** override `confirm_required` or any control-plane boundary.

## Scorecard Objective

The connector scorecard exists to compress provider quality into a small set of operator-readable signals before promotion board review.

The scorecard must answer five questions:

1. Is the provider surface fresh enough to trust as a governed candidate?
2. Are high-risk actions classified and confirmation-disciplined?
3. Can connector actions be replayed and audited through a canonical ledger?
4. Is rollback defined before any stage increase is discussed?
5. Does the connector layer remain a child of `vco`, not a second orchestrator?

## Scorecard Dimensions

| Dimension | Required evidence | What a healthy result means |
|---|---|---|
| `provider_freshness` | documented review date, provider owner, schema surface snapshot | the provider has a named owner and a recent governance review |
| `capability_fit` | capability classes mapped to safe / confirm / deny buckets | only scoped, VCO-native connector capabilities are admitted |
| `confirm_discipline` | write actions mapped to `confirm_required` and `risk_class` | no write-capable connector action can bypass confirmation |
| `replay_coverage` | action ledger rows include replay handle and evidence refs | operator can reconstruct the executed action path |
| `rollback_ready` | rollback command, fallback stage, operator owner | connector plane can be reverted to `shadow` without improvisation |
| `owner_boundary` | explicit statement that `control_plane_owner = vco` | connector tooling never becomes a second router or execution owner |

## Score Bands

| Score band | Stage guidance | Interpretation |
|---|---|---|
| `0-2` | `shadow_only` | admission exists, but score evidence is too thin for rollout talk |
| `3-4` | `candidate_shadow` | enough evidence to stay governed, not enough to widen usage |
| `5-7` | `soft_candidate` | replay, rollback, and confirm discipline are present for operator review |
| `8-10` | `strict_candidate_review` | scorecard is strong enough to enter strict review, not auto-promotion |

`strict_candidate_review` still requires human approval, gate evidence, and rollback drills.

## Promotion Rules

The connector plane can only be proposed to board review when all of the following are true:

- `confirm_discipline` is green for every write-capable action class;
- `connector-action-ledger` contains canonical rows for replay, rollback, and evidence capture;
- the promotion board entry binds the connector scorecard to explicit gates;
- rollback remains capped at `max_safe_auto_write_stage = soft`.

The following are always stop conditions:

- a connector action can write without confirmation;
- replay metadata is missing for a promoted candidate;
- provider freshness is unknown;
- the connector layer claims route ownership, execution ownership, or memory truth ownership.

## Evidence Stack

This scorecard is grounded by the following assets:

- `docs/governance/connector-action-ledger-governance.md`
- `references/connector-action-ledger.md`
- `references/plane-scorecards.md`
- `config/promotion-board.json`
- `scripts/verify/vibe-connector-scorecard-gate.ps1`

## Non-Goals

This governance asset does not:

- define connector install flows;
- allow provider-defined promotion logic;
- introduce provider-specific release channels;
- replace the existing `connector admission` governance layer.
