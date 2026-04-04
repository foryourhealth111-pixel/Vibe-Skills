# Distribution Governance

## Purpose

This document defines how `vco-skills-codex` governs upstream sources, local retention, redistribution posture, and disclosure.

The goal is not to maximize how much upstream code is copied into the repo. The goal is to keep deployment simple **without** weakening license boundaries, provenance truth, or runtime stability.

## Phase Rule

Distribution governance is executed in two layers:

1. Governance-first: registries, disclosure, provenance policy, verify gates, and operator scaffolding.
2. Retention-first: only after the governance layer is green do we move any additional upstream material into repo-local surfaces.

Until the governance layer is green, the runtime surface stays frozen:

- do not change `SKILL.md`
- do not change router contracts
- do not change install/check semantics
- do not change bundled mirror behavior except through the canonical sync flow

## Canonical Truth Surfaces

The distribution layer has exactly three canonical truth surfaces:

- `config/upstream-lock.json`
  Distribution, installation, runtime-adjacent upstream references and governance metadata.
- `config/upstream-corpus-manifest.json`
  Corpus, watchlist, shadow-source, and value-extraction upstream registry.
- `THIRD_PARTY_LICENSES.md`
  Public disclosure view derived from the canonical registries.

Any upstream that appears in public disclosure must be traceable to at least one canonical registry entry.

## Distribution Tiers

The repo uses four distribution tiers:

| Tier | Meaning | Repo-local retention | Shipped by default |
| --- | --- | --- | --- |
| `distributed-local` | Canonical VCO-owned or locally rewritten assets that are part of normal distribution | allowed | yes |
| `repo-local-mirror-not-shipped` | Repo-local retained mirror or vendor asset kept for audit, comparison, or simplified local setup | allowed | no |
| `external-optional` | External dependency, service, or tool that may be used by operators but is not shipped as core content | not required | no |
| `reference-only` | Governance, methodology, or advisory source used to inform policy or documentation | not required | no |

Tier assignment is governance data, not runtime permission.

## Boundary Rules

### `third_party/**`

`third_party/**` is compliance-only.

It stores:

- license texts
- notice material
- attribution artifacts

It does **not** store active repo-local upstream working copies.

### `vendor/**`

`vendor/**` is the future repo-local upstream boundary.

It is split into:

- `vendor/upstreams/`
- `vendor/mirrors/`

Any real retained upstream asset under `vendor/**` must carry `ORIGIN.md`.

### `bundled/**`

`bundled/**` remains the packaged mirror surface for VCO-owned runtime assets and compat layers.

It is never the first edit surface for upstream governance.

## Required Metadata

Every entry in `config/upstream-lock.json` must declare, at minimum:

- canonical slug
- SPDX license identifier or `NOASSERTION`
- integration mode
- distribution tier
- redistribution posture
- disclosure required flag
- local retention allowed flag
- shipped by default flag

This metadata exists to make release and compliance decisions mechanical.

## Stop Rules

Stop the distribution-governance rollout if any of these become necessary:

- changing routing semantics to make a governance gate pass
- lowering verify standards to hide registry/disclosure drift
- moving live upstream code into `third_party/**`
- treating bundled mirrors as the canonical edit surface

## Required Gates

The minimum distribution-governance gate set is:

- `scripts/verify/vibe-upstream-corpus-manifest-gate.ps1`
- `scripts/verify/vibe-upstream-mirror-freshness-gate.ps1`
- `scripts/verify/vibe-third-party-disclosure-parity-gate.ps1`
- `scripts/verify/vibe-upstream-lock-coverage-gate.ps1`
- `scripts/verify/vibe-origin-provenance-gate.ps1`

These do not replace runtime or packaging gates. They supplement them.
