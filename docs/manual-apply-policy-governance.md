# Manual Apply Policy Governance

## Purpose

Wave97 codifies how governance proposals may be written back into board or config state, keeping the repo in advice-first, rollback-first posture.
The policy exists to prevent suggestion engines, gates, or helper scripts from silently applying stage or threshold changes.

## Governance Scope

- Config and board writes require explicit manual flags and named operator acknowledgement.
- Default behavior stays `report_only` whenever an apply flag is absent.
- No manual-apply path may bypass promotion-board rules, release-train rules, or rollback limits.

## Required Invariants

- `apply_requires_explicit_flag = true` remains fixed.
- `default_action = report_only` remains fixed.
- `forbid_auto_promote = true` and `forbid_auto_threshold_mutation = true` remain fixed.
- Board writes and config writes must be separated from verify-only artifact generation.

## Non-Goals

- No auto-promotion hook is introduced.
- No silent threshold mutation is allowed through telemetry or gates.

Validation is performed by `scripts/verify/vibe-manual-apply-policy-gate.ps1`.
