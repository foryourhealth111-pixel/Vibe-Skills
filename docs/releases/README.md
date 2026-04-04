# Releases

- Up: [`../README.md`](../README.md)

## What Lives Here

This directory stores governed VCO release notes and the minimum runtime-facing navigation needed to cut or verify a release.

## Start Here

### Current Release Surface

- [`v2.3.56.md`](v2.3.56.md): remaining-architecture-closure completion / owner-consumer proof / live status truth alignment / bounded fallback honesty / regression-backed baseline

### Release Runtime / Proof Handoff

- [`../runtime-freshness-install-sop.md`](../runtime-freshness-install-sop.md): install, freshness, and coherence SOP
- [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md): gate family navigation and typical run order
- [`../../scripts/verify/README.md`](../../scripts/verify/README.md): verify surface entrypoint
- [`../status/non-regression-proof-bundle.md`](../status/non-regression-proof-bundle.md): minimum closure proof contract
- `scripts/verify/vibe-release-truth-consistency-gate.ps1`: fallback and degraded-truth consistency proof for release and promotion surfaces

## Recent Governed Releases

- [`v2.3.56.md`](v2.3.56.md) - 2026-04-04 - remaining-architecture-closure completion / owner-consumer proof / live status truth alignment / bounded fallback honesty / regression-backed baseline
- [`v2.3.55.md`](v2.3.55.md) - 2026-03-30 - owned-only uninstall and skill-only host alignment / OpenCode startup safety / explicit intent-vs-vector AI config split / macOS bootstrap compatibility
- [`v2.3.54.md`](v2.3.54.md) - 2026-03-30 - release operator closure / runtime contract schema baseline / outputs-boundary migration / install-time generated nested compatibility / release truth hardening
- [`v2.3.53.md`](v2.3.53.md) - 2026-03-30 - governed specialist dispatch and custom admission closure / Windows PowerShell host resolution / managed host install guarantees / cleanup-truth tightening
- [`v2.3.52.md`](v2.3.52.md) - 2026-03-29 - stage-aware memory activation / governed memory backend adapters / explicit memory-scope boundaries
- [`v2.3.51.md`](v2.3.51.md) - 2026-03-28 - main-chain delivery acceptance / specialist dispatch governance closure / Windows specialist runtime handoff fix
- [`v2.3.50.md`](v2.3.50.md) - 2026-03-26 - router AI connectivity probe / host-adapter expansion / single-entry install surface / Windows PowerShell default verification guidance
- [`v2.3.49.md`](v2.3.49.md) - 2026-03-23 - shallow-worktree install/check hardening / installed-runtime adapter fallback / parent-path guard convergence
- [`v2.3.48.md`](v2.3.48.md) - 2026-03-23 - benchmark mode compatibility downgrade / governed proof alignment / adaptive-routing gate robustness
- [`v2.3.47.md`](v2.3.47.md) - 2026-03-15 - no-silent-fallback governance / degraded-truth hazard surfacing / release-truth consistency closure
- [`v2.3.46.md`](v2.3.46.md) - 2026-03-15 - Linux benchmark/governed-runtime Python host neutrality / proof-chain closure
- [`v2.3.45.md`](v2.3.45.md) - 2026-03-15 - benchmark_autonomous bridge durability / relative runtime summary paths / restored Python bridge proof
- [`v2.3.44.md`](v2.3.44.md) - 2026-03-15 - real bounded benchmark_autonomous executor / execution manifests / benchmark proof gate
- [`v2.3.43.md`](v2.3.43.md) - 2026-03-15 - governed runtime contract / six-stage vibe entry / runtime bridge tests / release-surface alignment
- [`v2.3.42.md`](v2.3.42.md) - 2026-03-14 - tracked Linux proof artifacts / manifest tracked-file gate / clean-clone release-truth closure
- [`v2.3.41.md`](v2.3.41.md) - 2026-03-14 - Linux target-root portability hardening / proof-gate execution-context lock / governed manifest alignment
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
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\governance\release-cut.ps1 -RunGates
```

On Windows, `powershell.exe` remains an acceptable fallback if `pwsh` is unavailable, but the governed cross-platform release command is `pwsh`.

## Stop-Ship Families

Exact script names live in the gate-family index. At the README level, releases should be understood through families rather than giant flat lists:

- topology and integrity: version consistency, version packaging, config parity, nested bundled parity, mirror edit hygiene, BOM/frontmatter integrity
- runtime and install coherence: installed runtime freshness, release/install/runtime coherence
- fallback truth honesty: no silent fallback contract, self-introduced fallback guard, release-truth consistency
- cleanliness and readiness: repo cleanliness, wave board readiness, capability dedup, adaptive routing readiness, upstream value ops

## Extended Release Trains

Use the gate-family index for the exact scripts. The extended trains stay grouped here by governed concern:

- Wave64-82 extensions: memory runtime, browser / desktop / document / connector scorecards, cross-plane replay, ops cockpit, rollback drill, release-train closure
- Exact gates include `vibe-wave64-82-closure-gate.ps1` and `vibe-release-train-v2-gate.ps1`.
- Wave83-100 extensions: gate reliability, eval quality, candidate / role / subagent / discovery governance, capability lifecycle, sandbox simulation, release evidence bundle, bounded rollout, upstream re-audit closure
- Wave83-100 Extended Gates: `vibe-release-evidence-bundle-gate.ps1`, `vibe-manual-apply-policy-gate.ps1`, `vibe-rollout-proposal-boundedness-gate.ps1`, `vibe-upstream-reaudit-matrix-gate.ps1`, `vibe-wave83-100-closure-gate.ps1`

## Rules

- `docs/releases/README.md` is the release-surface navigator, not the flat home for every gate script.
- Keep current release surface, proof handoff, and historical packetization separated instead of flattening them into one list.
- Exact gate names, ordering, and family ownership are defined by [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md).
- Degraded closure is never equivalent to authoritative success. If a release depends on fallback or degraded behavior, the release surface must say so explicitly and include fallback-truth consistency proof.
- Release notes stay one-file-per-version using the `v<version>.md` pattern.
- Historical release packets must stay distinct from the current governed release surface.
