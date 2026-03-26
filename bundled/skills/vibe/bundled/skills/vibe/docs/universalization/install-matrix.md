# Install Matrix (No-Regression, No-Overclaim)

> Status baseline: 2026-03-21
> Scope: installation and bootstrap entrypoints by lane, without changing official runtime ownership.

## Purpose

This document answers a single question:

Which lane can the repo install today, and at what truth level?

It does **not** promise that all host dependencies can be installed in one shot.

## Lane Install Closure

| Lane | Install Entry | Check Entry | Closure Level | Notes |
| --- | --- | --- | --- | --- |
| `official-runtime` | `install.ps1`, `install.sh` | `check.ps1`, `check.sh` | governed | Tier-1 reference lane |
| `host-codex` | `install.* --host codex` | `check.* --host codex` | governed-with-constraints | strongest current lane |
| `host-claude-code` | `install.* --host claude-code` | `check.* --host claude-code` | preview-scaffold | writes truthful scaffold only |
| `host-cursor` | `install.* --host cursor` | `check.* --host cursor` | preview-scaffold | exposes preview guidance and truthful readiness checks only |
| `host-windsurf` | `install.* --host windsurf` | `check.* --host windsurf` | runtime-core-preview | documented host root with shared runtime-core payload only |
| `host-openclaw` | `install.* --host openclaw` | `check.* --host openclaw` | runtime-core-preview | documented host root with shared runtime-core payload only |
| `generic` | `install.* --host generic` | `check.* --host generic` | runtime-core-only | neutral target root only |
| `host-opencode` | `install.* --host opencode` | `check.* --host opencode` | runtime-core-only | neutral target root only |
| `core` | none | none | none | contracts only |

## Host-Managed Boundaries

Even when the repo can install something, these surfaces may still remain host-managed:

- plugin provisioning inside the host runtime
- credentials / API keys and provider permissions
- MCP server connectivity and external trust boundaries
- final host-native settings semantics for preview lanes

## Reading The Matrix Correctly

- `governed-with-constraints` means real repo-backed install/check exists, but some host surfaces are still outside repo control.
- `preview-scaffold` means the repo can scaffold and verify a preview surface, but not claim full host closure.
- `runtime-core-preview` means the repo can install shared runtime-core payload into a documented host root, but still cannot claim host-native settings, login, plugin, or credential closure.
- `runtime-core-only` means the repo can install canonical runtime-core payload into a neutral target root, not a host-native home.

## Required Truth References

- `docs/universalization/host-capability-matrix.md`
- `docs/universalization/official-runtime-baseline.md`
