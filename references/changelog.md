# VCO Changelog

## v3.0.1 (2026-04-09)

- Restored install-time generated nested compatibility materialization so managed installs keep the nested `bundled/skills/vibe` surface without deleting the source tree when the source already resolves to that nested root.
- Hardened `scripts/governance/release-cut.ps1` by restoring bundled-sync preview/apply flow, appending release-ledger rows safely when the existing file has no trailing newline, and only passing `-WriteArtifacts` to gates that actually declare it.
- Reintroduced the historical governance boards, manifests, and release-train documents required by the extended Wave40-63, Wave64-82, Wave83-100, and Wave121-140 gates, and aligned capability/role-pack gates with canonical skill IDs so the full governed release train passes again.
- Detailed release notes: `docs/releases/v3.0.1.md`.

This file is the stable current changelog surface used by release governance.

Historical entries before `v2.3.53` now live in `references/archive/changelog/pre-v2.3.53.md`.

## v3.0.0 (2026-04-07)

- Promoted the unpublished `v2.3.56` architecture-closure baseline into the public major-release line instead of leaving that baseline as a local-only note.
- Hardened host-safe install and uninstall behavior while keeping supported hosts on a skill-first, sidecar-aware ownership model.
- Tightened governed execution proof through better child-lineage validation, specialist-promotion closure, runtime/MCP truth alignment, and native MCP-first readiness guidance.
- Synchronized the repository's governed release line and Python package metadata at `3.0.0` so package surfaces no longer advertise the old `0.1.0` scaffold placeholder.
- Detailed release notes: `docs/releases/v3.0.0.md`.

## v2.3.56 (2026-04-04)

- Completed the frozen `remaining-architecture-closure` program and moved the repository to a regression-backed low-coupling / high-cohesion baseline instead of leaving the closure work as an open-ended refactor stream.
- Added a dedicated owner-consumer architecture proof surface so contracts, runtime-core, verification-core, CLI, governance wrappers, packaging, and live status pages now point at one explicit sign-off source.
- Realigned the live status spine and closure language around the same 2026-04-04 truth: the scoped closure work is complete, residual fallbacks are explicit, and deferred cleanup tracks are no longer hidden inside the finished plan.
- Preserved compatibility honestly rather than over-pruning: retained shims, optional nested topology, release/operator fallbacks, outputs evidence, and protected third-party roots all stay bounded and non-authoritative.
- Detailed release notes: `docs/releases/v2.3.56.md`.


## v2.3.55 (2026-03-30)

- Promoted the unified owned-only uninstall surface and aligned supported hosts around explicit skill-only / sidecar-first activation, so install and uninstall touch only Vibe-managed content in the normal path.
- Fixed the OpenCode startup regression by preserving compatibility with pre-existing OpenCode config surfaces instead of writing managed state into locations that could stop the host from booting.
- Split built-in intent advice from optional vector diff embeddings under explicit `VCO_INTENT_ADVICE_*` and `VCO_VECTOR_DIFF_*` key families, without backfilling legacy `OPENAI_*` names.
- Hardened macOS shell bootstrap compatibility by removing Bash 4-only assumptions from active entrypoints and by enforcing a clear Python 3.10+ prerequisite before helper dispatch.
- Detailed release notes: `docs/releases/v2.3.55.md`.


## v2.3.54 (2026-03-30)

- Closed the release-surface truth gap by making `scripts/governance/release-cut.ps1` the authoritative path for version governance, changelog / ledger writes, release README updates, dist manifest `source_release` alignment, and bundled / nested bundled sync during release apply.
- Added a stable runtime-contract proof baseline through shared packet projection, contract references, schema/golden tests, and host/runtime projection coverage so later refactors can move with less hidden drift risk.
- Completed the currently targeted tracked outputs-boundary migration and install-time generated nested compatibility path while preserving installed-runtime behavior and parity gates.
- Added release-note quality enforcement and re-cut the governed release surface so `v2.3.54` accurately describes the code and verification state that now exists in the repository.
- Detailed release notes: `docs/releases/v2.3.54.md`.


## v2.3.53 (2026-03-30)

- Closed governed specialist dispatch with explicit custom-admission handling, and restored delegated-lane payload plus host-adapter metadata continuity across router admission, runtime packets, and specialist execution closure gates.
- Hardened Windows PowerShell host resolution for install, check, and bootstrap surfaces, and tightened managed-host install guarantees across the current preview / runtime-core adapter lanes.
- Tightened cleanup-truth wording and policy so public release claims and runtime cleanup semantics stay aligned with what the governed runtime can actually prove.
- Detailed release notes: `docs/releases/v2.3.53.md`.
