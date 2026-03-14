# Platform Parity Contract

## Principle

Platform parity is not assumed from the presence of shell scripts.

A platform only earns a stronger support label when the repository can show:

1. install path
2. check path
3. doctor/gate path
4. degrade contract
5. measured evidence

## Current Rules

- Windows remains the authoritative official-runtime reference lane.
- Linux + `pwsh` is the strongest current Linux path, but it remains `supported-with-constraints` until promotion truth is deliberately reopened and synchronized.
- Linux without `pwsh` is degraded, not secretly full.
- macOS remains `not-yet-proven` until a separate evidence lane exists.

## Required Parity Evidence

For each `<host, platform>` pair the project must eventually record:

- install entry points
- health check entry points
- required external prerequisites
- gated vs skipped governance surfaces
- final support label

## Anti-Overclaim Rule

The repository must never upgrade wording from:

- `supported-with-constraints`

to:

- `full-authoritative`

without corresponding gate and replay evidence.

## Linux Proof Linkage

For Linux, promotion evidence is a bundled contract rather than a generic "measured once" claim.

Linux promotion must simultaneously satisfy:

- contract truth
- replay synchronization
- fresh-machine evidence
- public wording synchronization

The canonical references are:

- `docs/universalization/platform-promotion-criteria.md`
- `docs/universalization/linux-full-authoritative-contract.md`
