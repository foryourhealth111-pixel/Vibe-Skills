# Candidate Quality Board Governance

## Purpose

Wave88 aggregates candidate-evaluation evidence from Waves84-87 into a single evidence-only board.
This board summarizes quality buckets, reviewers, next actions, and no-go notes for candidate tracks without replacing promotion board v2 or the ops cockpit.

## Governance Scope

- Candidate quality board v1 is evidence-only and advice-first.
- Board entries must point back to scorecards, evaluation scenarios, and verify artifacts.
- The board cannot write stages, widen rollout, or override promotion board v2 decisions.

## Required Invariants

- `board_policy.mode = advice_first` stays fixed.
- Every candidate row must include `scorecard_bucket`, `required_gates`, `reviewer`, and `no_go_boundary`.
- The board must refer to `references/plane-scorecards.md` and existing verify outputs as its evidence source.
- No candidate row may claim promotion or release readiness directly.

## Non-Goals

- No duplicate promotion board is created.
- No ops cockpit panel is replaced by this board.

Validation is performed by `scripts/verify/vibe-candidate-quality-board-gate.ps1`.
