# Distribution Lanes (Truth Contract)

> Status baseline: 2026-03-13  
> Scope: distribution descriptors and capability promises, not runtime takeover.

## Purpose

Universalization introduces a **distribution surface** (`dist/**`) without changing runtime ownership.

The dist surface exists to prevent two common failure modes:

- A single "mega pack" that mixes official runtime, preview adapters, and future core into one marketing blob.
- Silent overclaim (platform/host parity implied by bundling rather than proved by gates).

## Canonical Rule

The official runtime ownership remains:

- `install.ps1`, `install.sh`
- `check.ps1`, `check.sh`
- `scripts/router/resolve-pack-route.ps1`
- `config/version-governance.json`

Dist manifests may point to these assets, but must not replace them.

## Lane Vocabulary

Each lane has a machine-readable manifest:

- `dist/core/manifest.json`
- `dist/official-runtime/manifest.json`
- `dist/host-codex/manifest.json`
- `dist/host-claude-code/manifest.json`
- `dist/host-opencode/manifest.json`

## Lane Definitions (Conservative)

| Lane | Meaning | Install/Check Closure | Allowed Claim Level |
| --- | --- | --- | --- |
| `official-runtime` | The current Tier-1 official runtime (canonical repo lane). | Yes, via existing entrypoints. | bounded by existing gates + baseline docs |
| `core` | Universal contracts and schemas only. | No closure promised. | contract-only, no runtime claims |
| `host-codex` | Codex adapter lane (current practical reference). | Uses official runtime entrypoints. | supported-with-constraints only |
| `host-claude-code` | Claude Code adapter preview. | No governed closure claimed yet. | preview only |
| `host-opencode` | OpenCode future target. | No governed closure claimed yet. | not-yet-proven only |

## Truth Sources

Distribution promises must remain consistent with:

- Platform truth: `docs/universalization/platform-support-matrix.md`
- Host truth: `docs/universalization/host-capability-matrix.md`
- Official runtime baseline: `docs/universalization/official-runtime-baseline.md`

If a manifest conflicts with these docs, the manifest is wrong.

## Non-Goals

Dist manifests must not claim:

- one-shot installation of all host dependencies
- automatic host plugin provisioning
- automatic credential provisioning
- cross-platform "full parity" before a proof bundle exists

## Verification Gate

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify\vibe-dist-manifest-gate.ps1 -WriteArtifacts
```

This gate checks:

- the dist manifests exist and are structurally complete
- the manifests do not overclaim relative to platform/host truth docs
- the docs referenced by manifests exist and contain the required lane vocabulary

