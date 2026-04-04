# Path Dependency Census

Updated: 2026-04-04

## Positioning

This page is the live blocker map for the active architecture-closure program.

It answers one question only:

Which dependency clusters still make blanket delete / move / archive / over-claim unsafe right now?

## Blocker Summary

The repository currently has six blocker clusters that still constrain safe closure language or blanket structural cleanup:

1. optional nested compatibility topology
2. governed `outputs/**` evidence surfaces
3. protected third-party source roots
4. live docs / proof / status handoff spine
5. retained compatibility payload and shim surfaces
6. dated history surfaces that still sit near active entry points

## Dependency Table

| Dependency Cluster | Current Consumers | Risk | Current Constraint | Safe Migration Direction |
| --- | --- | --- | --- | --- |
| `bundled/skills/vibe/bundled/skills/vibe` | `config/version-governance.json`, `scripts/common/vibe-governance-helpers.ps1`, `scripts/verify/vibe-nested-bundled-parity-gate.ps1`, mirror topology docs | high | runtime contract allows absence, but topology-safe absence semantics still matter | keep the optional topology contract, materialize only on demand if legacy compatibility actually needs it |
| tracked `outputs/**` | `config/outputs-boundary-policy.json`, `references/fixtures/migration-map.json`, `scripts/verify/vibe-output-artifact-boundary-gate.ps1` | high | policy still keeps the legacy migration label `stage2_mirrored`, but tracked `outputs/**` are already required to be zero and fixture mirrors remain the canonical retained surface | keep the compatibility label stable while documenting strict-zero enforcement truthfully |
| `third_party/system-prompts-mirror` | research scripts, docs examples | high | scripts still default to a fixed local mirror path | make source roots manifest-driven and parameterizable |
| `third_party/vco-ecosystem-mirror` | `config/upstream-corpus-manifest.json`, registry / curation metadata, mirror-path references, some research flows | medium-high | the local mirror is still treated as the default evidence source | preserve provenance and manifest, allow external checkout / audit-time fetch |
| live docs / proof / status spine | `docs/status/*`, `docs/proof/*`, `docs/plans/README.md`, `docs/README.md`, `scripts/README.md`, `scripts/verify/gate-family-index.md`, `config/index.md`, `references/index.md` | medium | the scoped live spine is now refreshed; the remaining constraint is keeping proof, status, and residual-boundary language aligned so historical pages do not retake authority | keep a short canonical handoff spine: root requirement -> root plan -> proof -> current-state -> closure-audit |
| dated plan / report surfaces | `docs/plans/**`, `docs/releases/**`, older status / closure pages | medium | historical material still sits close to active navigation surfaces | keep active state in `docs/status/` and `docs/proof/`, and progressively demote history to archive-style access patterns |

## Notable Hard References

### Optional Nested Compatibility Topology

Observed hard references include:

- `config/version-governance.json`
- `scripts/common/vibe-governance-helpers.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-nested-bundled-parity-gate.ps1`
- `config/repo-cleanliness-policy.json`
- `config/execution-context-status.json`

The physical payload can stay absent, but the optional topology contract still makes blanket wording or deletion unsafe.

### Outputs Boundary

Observed hard references include:

- `config/outputs-boundary-policy.json`
- `references/fixtures/migration-map.json`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `references/fixtures/README.md`
- `docs/governance/output-artifact-boundary-governance.md`

This is why `outputs/**` cannot be described as fully closed or freely deletable yet.

### Third-Party Source Roots

Observed hard references include:

- `scripts/research/extract-prompt-signals.ps1`
- `scripts/research/generate-vco-suggestions.ps1`
- `config/upstream-corpus-manifest.json`
- `config/candidate-curation-policy.json`
- `config/tool-registry.json` mirror-path metadata
- docs and verify README examples that still point to local mirrors

This is why third-party shrinkage still has to be parameterized rather than asserted by deletion.

## Current Migration Order

The order below is the current safe sequencing recommendation after the 2026-04-04 architecture closure proof wave.

1. keep the owner -> consumer proof, live status pages, and residual-risk language mutually aligned
2. continue shrinking compatibility payload and shim surfaces only where live callers prove it is safe
3. parameterize third-party source roots
4. make the outputs strict-mode decision explicitly
5. open archive / prune windows only after a later follow-up proof wave is green

## Cross-Document Boundary

- active sequencing lives in [`roadmap.md`](roadmap.md)
- active root requirement lives in [`../requirements/2026-04-04-remaining-architecture-closure.md`](../requirements/2026-04-04-remaining-architecture-closure.md)
- active root plan lives in [`../plans/2026-04-04-remaining-architecture-closure-plan.md`](../plans/2026-04-04-remaining-architecture-closure-plan.md)
- architecture sign-off proof lives in [`../proof/2026-04-04-owner-consumer-consistency-proof.md`](../proof/2026-04-04-owner-consumer-consistency-proof.md)
- live runtime summary lives in [`current-state.md`](current-state.md)
- closure receipt lives in [`closure-audit.md`](closure-audit.md)
