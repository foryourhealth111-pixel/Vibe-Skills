# Platform Install Matrix (Truth-First)

> Status baseline: 2026-03-13  
> Scope: platform differences for install/check surfaces. This is not a parity claim.

## Purpose

This matrix prevents the repo from collapsing two statements into one:

- "install works"
- "install is fully authoritative and parity-proved"

The platform truth is defined by:

- `docs/universalization/platform-support-matrix.md`

This document only maps that truth into the install entrypoints.

## Platform x Official Install Surfaces

| Platform | Primary Install | Primary Check | Support Rating (Truth) | Notes |
| --- | --- | --- | --- | --- |
| Windows | `install.ps1` | `check.ps1` | `full-authoritative` | current reference closure lane |
| Linux + `pwsh` | `install.sh` | `check.sh` (+ PowerShell follow-up) | `supported-with-constraints` | proof is frozen, but release truth remains below formal promotion |
| Linux without `pwsh` | `install.sh` | `check.sh` (degraded) | `degraded-but-supported` | must not be marketed as full |
| macOS + `pwsh` | shell path inferred | partial | `not-yet-proven` | must be measured and recorded |
| macOS without `pwsh` | shell path inferred | partial | `not-yet-proven` | must be measured and recorded |

## PowerShell Host Policy Boundary

`pwsh` is the preferred PowerShell host for the documented install/check surface. Linux and macOS require PowerShell 7 before PowerShell-native governed verification, doctor, freshness, or parity gates can be claimed. Without `pwsh`, shell install and runtime-neutral checks may still run, but closeout wording must remain degraded and must not claim full governed-runtime readiness.

## Lane Applicability

- `official-runtime` and `host-codex` inherit this platform matrix directly.
- `host-claude-code` uses shared entrypoints as a `managed-with-constraints` lane: it can write and verify a bounded Claude managed surface, but does not claim official-runtime closure.
- `host-cursor` and `host-opencode` use shared entrypoints as preview-scaffold lanes, but do not claim governed install closure.
- `host-windsurf` and `host-openclaw` use shared entrypoints as `runtime-core-preview` lanes, with truthful runtime-core-only boundaries on host-native surfaces.
- `core` remains contract-only and does not claim a host-native install lane.
