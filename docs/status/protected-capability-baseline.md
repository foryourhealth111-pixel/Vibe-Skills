# Protected Capability Baseline

Updated: 2026-04-01

## Positioning

This page is a closure-phase guardrail matrix.

It does not act as a live PASS table, and it is not the full long-term governance contract. Its purpose is narrower:

1. define which surfaces are protected during cleanup;
2. bind each protected surface to a proof command or bounded audit path;
3. make it explicit that anything outside this table is not automatically protected at P0.

The durable governance details remain in root `docs/*-governance.md` documents. This page only states the minimum "do not silently break this" boundary for the active closure program.

## Guardrail Rule

The cleanup program is allowed to simplify structure. It is not allowed to silently change the protected surfaces listed below without rerunning the corresponding proof.

## P0: Must Remain Behaviorally Equivalent

| Domain | Preserve Mode | Key Surfaces | Proof Command | Rollback Anchor |
| --- | --- | --- | --- | --- |
| Pack routing | exact behavior preserve | `scripts/router/resolve-pack-route.ps1`, `config/pack-manifest.json`, `config/router-thresholds.json`, `config/skill-alias-map.json` | `powershell -NoProfile -File scripts/verify/vibe-pack-routing-smoke.ps1` | restore router/config edits |
| Router compatibility boundary | candidate-audit behavior preserve; no runtime authority | router output shape + current routing debt policy | `powershell -NoProfile -File scripts/verify/vibe-current-routing-debt-gate.ps1` | remove any route-to-binding authority or retired field reintroduction |
| Packaging contract | exact behavior preserve | `config/version-governance.json`, runtime packaging configs, `scripts/verify/vibe-version-packaging-gate.ps1` | `powershell -NoProfile -File scripts/verify/vibe-version-packaging-gate.ps1` | keep canonical-only repo truth and generated compatibility contract |
| Compatibility hygiene | exact behavior preserve | no repo-tracked bundled mirror reintroduction | `powershell -NoProfile -File scripts/verify/vibe-mirror-edit-hygiene-gate.ps1` | reject recreated mirror-first edits |
| Install flow | exact behavior preserve | `install.ps1`, `install.sh` | `powershell -NoProfile -File scripts/verify/vibe-installed-runtime-freshness-gate.ps1` | restore install behavior or re-enable transitional compatibility |
| Check flow | exact behavior preserve | `check.ps1`, `check.sh` | `powershell -NoProfile -File scripts/verify/vibe-release-install-runtime-coherence-gate.ps1` | restore check behavior or gate wiring |
| Installed runtime coherence | exact behavior preserve | runtime receipt, freshness gate, coherence gate | `powershell -NoProfile -File scripts/verify/vibe-release-install-runtime-coherence-gate.ps1` | restore receipt contract / target layout |
| Execution context lock | exact behavior preserve | `scripts/common/vibe-governance-helpers.ps1`, topology-aware gates | targeted verify gate + `powershell -NoProfile -File scripts/governance/phase-end-cleanup.ps1 -WriteArtifacts -IncludeMirrorGates` | restore context guardrails |

## P1: May Change Shape, Must Keep Outcome

| Domain | Allowed Structural Change | Current Protected Outcome | Proof Command |
| --- | --- | --- | --- |
| generated compatibility path | may remain absent in repo and be materialized only during install/runtime | legacy compatibility path remains covered by the named packaging / runtime / coherence gates | `vibe-version-packaging-gate.ps1`, `vibe-installed-runtime-freshness-gate.ps1`, `vibe-release-install-runtime-coherence-gate.ps1`, `vibe-nested-bundled-parity-gate.ps1` |
| tracked outputs | may migrate into fixtures / ledgers | long-term regression baselines are preserved | `vibe-output-artifact-boundary-gate.ps1` |
| docs spine | may be shortened aggressively | canonical index surfaces remain readable and status-vs-contract boundaries remain discoverable | manual index audit against `docs/README.md`, `docs/status/README.md`, `references/index.md`, `config/index.md`, `scripts/README.md` |
| historical plans / reports | may move to archive | current state and current roadmap remain discoverable | manual doc review |
| third-party roots | may be externalized or parameterized | manifest-backed research / audit / corpus flows remain executable through their governed entrypoints | `scripts/research/extract-prompt-signals.ps1`, `scripts/research/generate-vco-suggestions.ps1`, plus affected proof bundle |

## P2: Deletable Only After Proof

- direct nested tracked mirror residency
- remaining tracked `outputs/**`
- duplicate dated closure reports and duplicated release summaries
- redundant long-lived backup folders
- heavy local third-party mirrors that no longer serve default flows

## Decision Rule

If a candidate path cannot be mapped to one of the rows above, it is not ready for prune.

If a new surface must be protected, add it here together with a proof path before using "no regression" language for that surface.

## Cross-Document Boundary

- proof contract lives in [`non-regression-proof-bundle.md`](non-regression-proof-bundle.md)
- blocker map lives in [`path-dependency-census.md`](path-dependency-census.md)
- sequencing map lives in [`roadmap.md`](roadmap.md)
- long-term governance details live in root `docs/*-governance.md`
