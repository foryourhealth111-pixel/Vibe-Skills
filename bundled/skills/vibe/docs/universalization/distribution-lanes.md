# Distribution Lanes (Truth Contract)

> Status baseline: 2026-03-21
> Scope: distribution descriptors and capability promises, not runtime takeover.

## Purpose

Universalization introduces a **distribution surface** (`dist/**`) without changing runtime ownership.

The dist surface exists to prevent two failure modes:

- mixing official runtime, preview adapters, and neutral runtime-core into one fake "all hosts are equal" story
- silently overclaiming host or platform parity before replay-backed proof exists

## Canonical Rule

The canonical runtime ownership remains:

- `install.ps1`, `install.sh`
- `check.ps1`, `check.sh`
- `scripts/router/resolve-pack-route.ps1`
- `config/version-governance.json`

Dist manifests may point to these assets, but must not replace them.

## Lane Definitions

| Lane | Meaning | Install/Check Closure | Allowed Claim Level |
| --- | --- | --- | --- |
| `official-runtime` | Tier-1 official runtime in the canonical repo | yes | bounded by baseline docs + gates |
| `core` | universal contracts and schemas only | none | contract-only |
| `host-codex` | strongest host adapter lane | governed-with-constraints | supported-with-constraints |
| `host-claude-code` | preview host adapter lane | preview-scaffold via shared entrypoints | preview only |
| `host-cursor` | preview host adapter lane | preview-scaffold via shared entrypoints | preview only |
| `host-windsurf` | preview host adapter lane using documented Windsurf root | runtime-core-preview via shared entrypoints | preview only |
| `host-openclaw` | preview host adapter lane using documented OpenClaw root | runtime-core-preview via shared entrypoints | preview only |
| `host-opencode` | future host adapter lane | runtime-core-only via neutral target root | not-yet-proven only |
| `generic` | neutral contract consumer lane | runtime-core-only via neutral target root | advisory-only |

## Important Boundary

`runtime-core-only` means:

- the repo can install canonical skills, commands, locks, and mirrored `skills/vibe/**`
- the repo does **not** claim host-native settings, plugin, MCP, or credential closure
- target roots should remain neutral, not a fake `.codex` / `.claude` host home

`runtime-core-preview` means:

- the repo can install canonical runtime-core payload into a documented host root such as `~/.codeium/windsurf` or `~/.openclaw`
- the repo may materialize host-facing bridge files such as `mcp_config.json` or `global_workflows/`
- the repo still does **not** claim host-native settings, login, plugin, workspace, or credential closure

## Truth Sources

Distribution promises must remain consistent with:

- `docs/universalization/install-matrix.md`
- `docs/universalization/host-capability-matrix.md`
- `docs/universalization/official-runtime-baseline.md`

If a manifest conflicts with these docs, the manifest is wrong.

## Non-Goals

Dist manifests must not claim:

- one-shot installation of all host dependencies
- automatic host plugin provisioning
- automatic credential provisioning
- cross-platform full parity before a proof bundle exists

## Verification Gates

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vgo-adapter-closure-gate.ps1 -WriteArtifacts
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vgo-adapter-target-root-guard-gate.ps1 -WriteArtifacts
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-dist-manifest-gate.ps1 -WriteArtifacts
```
