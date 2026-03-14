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

## Lane Applicability

- `official-runtime` and `host-codex` inherit this platform matrix.
- `core`, `host-claude-code`, and `host-opencode` do not claim a governed install closure lane yet.
