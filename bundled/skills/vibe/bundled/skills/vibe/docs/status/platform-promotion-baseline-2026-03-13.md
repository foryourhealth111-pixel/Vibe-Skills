# Platform Promotion Baseline 2026-03-13

## Purpose

This status page records the current platform-promotion truth for the repository.

It is not a marketing summary.
It is an operator-facing baseline for future promotion work.
It is a status snapshot, not a promotion approval.

Canonical promotion criteria remain:

- `docs/universalization/platform-promotion-criteria.md`
- `docs/universalization/linux-full-authoritative-contract.md`

## Baseline Decision

- `codex/windows` remains a `full-authoritative` lane.
- `codex/linux` remains `supported-with-constraints` while being backed by a frozen Linux proof bundle.
- `codex/linux without pwsh` remains an honest degraded lane.
- `codex/macos` remains `not-yet-proven`.

## Current Promotion State

| Lane | Current Status | Promotion State | Reason |
| --- | --- | --- | --- |
| `codex/windows` | `full-authoritative` | frozen baseline | current reference closure lane |
| `codex/linux` | `supported-with-constraints` | proof frozen, promotion withheld | fresh-machine bundle is frozen, but release truth intentionally stays below formal promotion |
| `codex/linux without pwsh` | `degraded-but-supported` | not promotable in this wave | degraded contract must remain explicit |
| `codex/macos` | `not-yet-proven` | out of scope | no frozen proof lane yet |

## Promotion Closure Evidence

Linux promotion is now closed by the following synchronized evidence:

1. replay fixture synchronization
2. adapter / manifest / public wording sync
3. promotion gate pass after the status change
4. degraded honesty for `without_pwsh`

## Current Guardrail

Any future change that weakens the `codex/linux` proof bundle, drops `codex/linux` from the replay allowlist, or erases the `without_pwsh` degraded contract is overclaim and must fail review.
