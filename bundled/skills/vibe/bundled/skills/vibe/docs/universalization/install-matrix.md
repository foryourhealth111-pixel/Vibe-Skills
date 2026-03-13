# Install Matrix (No-Regression, No-Overclaim)

> Status baseline: 2026-03-13  
> Scope: installation and bootstrap entrypoints by lane, without changing official runtime ownership.

## Purpose

This document answers a single question:

Which distribution lane provides a governed install/check closure path today?

It intentionally does not promise that all host dependencies can be installed in one shot.

## Lane Install Closure

| Lane | Install Entry | Check Entry | Closure Level | Notes |
| --- | --- | --- | --- | --- |
| `official-runtime` | `install.ps1` (primary), `install.sh` (secondary) | `check.ps1` (primary), `check.sh` (secondary) | governed | Tier-1 reference lane |
| `host-codex` | same as `official-runtime` | same as `official-runtime` | governed-with-constraints | host plugins + credentials remain host-managed |
| `core` | none | none | none | contracts only, no runtime takeover |
| `host-claude-code` | none | none | none | preview configuration intent only |
| `host-opencode` | none | none | none | not-yet-proven target only |

## Host-Managed Boundaries (Always-On)

Even in the official runtime lane, these surfaces remain host-managed:

- plugin provisioning inside the host runtime
- credentials / API keys and provider permissions
- MCP server connectivity and external service trust boundaries

These are not bugs. They are truth boundaries.

## Required Truth References

- Platform status: `docs/universalization/platform-support-matrix.md`
- Host status: `docs/universalization/host-capability-matrix.md`
- Official runtime baseline: `docs/universalization/official-runtime-baseline.md`

