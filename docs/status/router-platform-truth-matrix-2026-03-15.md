# Router Platform Truth Matrix 2026-03-15

## Purpose

This status page freezes the router-specific truth that the current recovery program is allowed to change.

It is not a release note.
It is not a promotion approval.
It is the operator-facing truth matrix for the Linux router host-neutrality and route quality recovery wave.

Primary execution sources:

- [Linux Router Host-Neutrality And Route Quality Recovery Requirement](../requirements/2026-03-15-linux-router-host-neutrality-and-route-quality-recovery.md)
- Supporting execution-plan leaves for this historical recovery wave are no longer kept on the public docs surface.

## Frozen Facts At Wave Start

1. The canonical router authority surface is still [resolve-pack-route.ps1](../../scripts/router/resolve-pack-route.ps1).
2. Windows PowerShell remains the strongest measured lane.
3. Linux with `pwsh` is usable but still not marketed as `full-authoritative`.
4. Linux without `pwsh` remains degraded because there is no equally authoritative non-PowerShell route adapter yet.
5. Route quality issues and platform issues are coupled because common prompts can still over-fall into `confirm_required`, especially on planning-heavy paths.

## Current Router Truth Matrix

| Host / Platform lane | Install or check status | Router authority status | Current truth label | Notes |
| --- | --- | --- | --- | --- |
| `official-runtime/windows` | green baseline | canonical PowerShell authority | `full-authoritative` | protected reference lane |
| `official-runtime/linux + pwsh` | usable with proof history | canonical PowerShell authority | `supported-with-constraints` | strongest Linux lane currently frozen |
| `official-runtime/linux without pwsh` | shell install and check can degrade honestly | no equal non-PowerShell authority yet | `degraded-but-supported` | this is the main recovery target |
| `official-runtime/macos + pwsh` | partial / inferred | not frozen | `not-yet-proven` | outside this wave |
| `official-runtime/macos without pwsh` | partial / inferred | not frozen | `not-yet-proven` | outside this wave |

## What This Wave Is Allowed To Promote

This wave may change only the following truths:

1. `official-runtime/linux without pwsh` may move upward only if a real host-neutral route adapter is implemented and proven.
2. Route quality truth may improve only if replay and gate coverage prove lower false `confirm_required` rates for common prompts.
3. Planning and migration routing truth may improve only if ranking fixtures show better pack selection without Windows regression.

This wave may not change:

1. Windows as the protected canonical reference lane.
2. macOS truth labels.
3. release wording beyond what proof artifacts can support.

## Required Closure Before Truth Changes

The following must be green before any truth update is claimed:

1. router contract compatibility
2. routing stability
3. Linux no-`pwsh` router proof
4. common prompt route quality proof
5. planning or migration ranking proof
6. release-truth consistency proof

## Stop Rules

Stop promotion immediately if any of the following occurs:

1. Windows route contract regresses.
2. Linux no-`pwsh` adapter returns placeholder or non-canonical JSON.
3. Common prompt auto-routing improves only by breaking planning or governance guardrails.
4. Docs or status are updated ahead of proof.
