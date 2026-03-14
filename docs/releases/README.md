# Releases

- Up: [`../README.md`](../README.md)

## What Lives Here

This directory stores governed VCO release notes and the minimum runtime-facing navigation needed to cut or verify a release.

## Start Here

### Current Release Surface

- [`v2.3.40.md`](v2.3.40.md): cross-shell install-check closure, upgrade hint hardening, and conservative Linux truth sync

### Release Runtime / Proof Handoff

- [`../runtime-freshness-install-sop.md`](../runtime-freshness-install-sop.md): install, freshness, and coherence SOP
- [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md): gate family navigation and typical run order
- [`../../scripts/verify/README.md`](../../scripts/verify/README.md): verify surface entrypoint
- [`../status/non-regression-proof-bundle.md`](../status/non-regression-proof-bundle.md): minimum closure proof contract

## Recent Governed Releases

- [`v2.3.40.md`](v2.3.40.md) - 2026-03-14 - cross-shell receipt normalization / upgrade hint closure / Linux truth sync
- [`v2.3.39.md`](v2.3.39.md) - 2026-03-14 - Linux regression closure / router contract hardening / freshness recursion fix
- [`v2.3.38.md`](v2.3.38.md) - 2026-03-14 - config path de-leak / tokenized runtime roots / smoke installed-runtime refresh
- [`v2.3.37.md`](v2.3.37.md) - 2026-03-13 - scrapling default full-lane promotion / doctor surface split / install-surface version closure
- [`v2.3.36.md`](v2.3.36.md) - 2026-03-13 - install-surface messaging hardening / host-plugin policy / version alignment
- [`v2.3.34.md`](v2.3.34.md) - 2026-03-13 - full-feature framing correction / cold-start onboarding / readiness boundary disclosure
- [`v2.3.33.md`](v2.3.33.md) - 2026-03-13 - provider seeding fix / slow-install expectation hardening / bundled config sync repair
- [`v2.3.32.md`](v2.3.32.md) - 2026-03-13 - dual-platform one-shot setup / Linux shell bootstrap / install boundary disclosure
- [`v2.3.31.md`](v2.3.31.md) - 2026-03-13 - post-upstream governance closure / disclosure parity / runtime alignment

Older release notes remain in this directory as historical version records, but they are not part of the active release surface.

## Historical Packetization

- [`wave15-18-release-packet.md`](wave15-18-release-packet.md) - historical packetization artifact, not the current release-note format

## Release Operator Entry

Canonical release cut command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\governance\release-cut.ps1 -RunGates
```

## Stop-Ship Families

Exact script names live in the gate-family index. At the README level, releases should be understood through families rather than giant flat lists:

- topology and integrity: version consistency, version packaging, config parity, nested bundled parity, mirror edit hygiene, BOM/frontmatter integrity
- runtime and install coherence: installed runtime freshness, release/install/runtime coherence
- cleanliness and readiness: repo cleanliness, wave board readiness, capability dedup, adaptive routing readiness, upstream value ops

## Extended Release Trains

Use the gate-family index for the exact scripts. The extended trains stay grouped here by governed concern:

- Wave64-82 extensions: memory runtime, browser / desktop / document / connector scorecards, cross-plane replay, ops cockpit, rollback drill, release-train closure
- Wave83-100 extensions: gate reliability, eval quality, candidate / role / subagent / discovery governance, capability lifecycle, sandbox simulation, release evidence bundle, bounded rollout, upstream re-audit closure

## Rules

- `docs/releases/README.md` is the release-surface navigator, not the flat home for every gate script.
- Keep current release surface, proof handoff, and historical packetization separated instead of flattening them into one list.
- Exact gate names, ordering, and family ownership are defined by [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md).
- Release notes stay one-file-per-version using the `v<version>.md` pattern.
- Historical release packets must stay distinct from the current governed release surface.
