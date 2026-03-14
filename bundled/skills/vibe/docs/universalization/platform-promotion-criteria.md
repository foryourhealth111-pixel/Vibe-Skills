# Platform Promotion Criteria

> Status baseline: 2026-03-13  
> Scope: promotion rules for platform labels, especially any attempt to move a lane to `full-authoritative`.

## Purpose

This document defines the minimum evidence required before any platform lane can be promoted.

It exists to stop two bad habits:

1. changing labels because the implementation looks close
2. treating wrapper availability as proof of platform closure

## Core Rule

A platform label may only be promoted when **contract**, **replay**, **fresh-machine evidence**, and **public wording** all agree.

No single layer is sufficient on its own.

## Required Evidence Classes

### 1. Contract evidence

The platform contract must exist and explicitly describe:

- install surface
- check surface
- doctor / governance surface
- degrade cases
- current status
- target promotion status

### 2. Replay evidence

The replay fixture must remain synchronized with the platform contract and the no-overclaim rules.

If the fixture still forbids a lane from being `full-authoritative`, the lane must not be promoted in docs or adapter contracts.

### 3. Fresh-machine evidence

Promotion to `full-authoritative` requires repeated fresh-machine runs for the target lane.

For Linux this means, at minimum:

1. one clean Linux workspace run with the required prerequisites
2. a second independent clean Linux workspace run
3. recorded command lines
4. recorded artifacts or receipts
5. recorded operator notes for any manual prerequisite

### 4. Public-truth evidence

The following must agree with the measured state before promotion:

- `docs/universalization/platform-support-matrix.md`
- `docs/universalization/platform-parity-contract.md`
- adapter platform contract JSON
- replay fixtures
- promotion gate output

## Linux-Specific Promotion Rule

`Codex on Linux` may only be promoted from `supported-with-constraints` to `full-authoritative` when all of the following are true:

1. the runtime-neutral authoritative core is implemented
2. Linux fresh-machine proof is frozen in the Linux proof bundle
3. the replay fixture explicitly allows `codex/linux` as `full-authoritative`
4. the Linux platform contract still declares `without_pwsh = degraded-but-supported`
5. the promotion gate passes without relying on warnings-only exceptions

## Honest Non-Promotion

A promotion wave is still considered successful if it concludes with:

- stronger evidence structure
- clearer blockers
- better gates
- unchanged support labels because proof is still incomplete

That outcome is preferred over a false promotion.

## Promotion Gate

The canonical gate for this policy is:

- `scripts/verify/vibe-platform-promotion-bundle.ps1`

For Linux-specific review, pair it with:

- `scripts/verify/vibe-linux-pwsh-proof-gate.ps1`

## Current Decision

As of this baseline:

- `codex/windows` remains a `full-authoritative` lane
- `codex/linux` remains `supported-with-constraints` in current release truth even though fresh-machine Linux proof has been frozen
- `codex/linux without pwsh` remains explicitly `degraded-but-supported`
- `codex/macos` remains `not-yet-proven`
