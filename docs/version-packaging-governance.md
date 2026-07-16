# VCO Version / Packaging Governance

This document defines the canonical governance contract after tracked `bundled/skills/vibe` retirement:

- canonical-only repo topology for `vibe`
- generated runtime payload + generated compatibility surface
- release / install / runtime freshness boundaries
- execution-context lock for governance scripts

## Mirror Topology Contract

The canonical repo root is the only repo truth surface for `vibe`. `mirror_topology.targets` remains machine-readable, but it now describes only the repo-resident canonical target.

| Target ID | Path | Role | Required | Presence Policy | Sync Rule |
| --- | --- | --- | --- | --- | --- |
| `canonical` | `.` | canonical | yes | `required` | never synced from any mirror |

Core rules:

1. `canonical` is the only authoritative target.
2. `bundled/skills/vibe` is no longer a tracked repo mirror.
3. Install-time compatibility surfaces are generated from the installed canonical payload, not copied from a repo mirror.
4. `allow_installed_only` remains the only approved exception set for installed-runtime-only files.
5. Installed runtime stays outside repo parity, but it must obey the runtime freshness contract.

## Execution-Context Lock

The execution-context lock protects governance and verify scripts from running inside derived or compatibility roots and producing false passes.

Lock behavior:

- the resolved repo root must be the outer git root
- the executing script path must not live under any non-canonical derived target
- topology resolution must land on the outer canonical root

Shared entrypoint:

- `scripts/common/vibe-governance-helpers.ps1`
- `Get-VgoGovernanceContext -ScriptPath $PSCommandPath -EnforceExecutionContext`

## Packaging Scope

Repo parity and installed-runtime parity use the packaging contract from `config/version-governance.json`:

- runtime payload files: `SKILL.md`, `check.ps1`, `check.sh`, `install.ps1`, `install.sh`
- runtime payload directories: `config`, `protocols`, `references`, `docs`, `scripts`, `mcp`
- normalized JSON ignore keys: `updated`, `generated_at`
- installed-only allowlist: `docs/CODEX_ECOSYSTEM_MAINTENANCE_PRINCIPLES.md`

`mcp` is part of the governed payload because the install scripts copy `mcp/` into the target runtime and `check.ps1` / `check.sh` validate `mcp/servers.template.json`.

## Gate Stack

### Repo / Packaging Gates

- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-version-consistency-gate.ps1`

### Runtime / Coherence Gates

- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

## Release / Install / Runtime Boundaries

release only governs repo parity.

That means:

- release metadata and release-cut gates validate canonical repo state
- install copies the governed payload into `<skills-dir>/vibe` and writes an install receipt with the owned file hashes
- install-time compatibility flows may generate `${TARGET_ROOT}/skills/vibe/bundled/skills/vibe` even though no repo-level mirror exists
- runtime freshness validates the receipt-owned installed files without requiring a full repository mirror
- routine `check.ps1` / `check.sh` validate the same receipt contract on every supported shell

## Runtime Freshness Contract

`runtime.installed_runtime` defines the runtime contract:

- `target_relpath`
- `receipt_relpath`
- `post_install_gate`
- `coherence_gate`
- `receipt_contract_version`

The installer owns the receipt. The installed runtime freshness gate verifies its file inventory and hashes. The coherence gate validates that release, install, runtime documentation, and scripts stay aligned.

`require_nested_bundled_root = false` means installed-runtime freshness does not fail only because a nested compatibility surface is absent. If a nested layout is materialized for compatibility, install-time generation must keep it derived from the installed canonical payload and governed by the same parity and hygiene rules.

## Recommended Operational Flow

1. Edit canonical files only.
2. Cut or verify release metadata.
3. Install into the target runtime.
4. Run runtime freshness and coherence checks.
5. Use compatibility-only mirror tooling only for legacy fixture maintenance, not for repo truth.

Example sequence:

```powershell
pwsh -NoProfile -File .\scripts\verify\vibe-version-packaging-gate.ps1 -WriteArtifacts
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"
pwsh -NoProfile -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex" -WriteArtifacts
```

For the detailed operator SOP, see `docs/runtime-freshness-install-sop.md`.

## Related Governance

- docs/runtime-freshness-install-sop.md: operator-facing install / runtime freshness playbook.
- docs/promotion-board-governance.md: Wave39 uses version / parity / coherence gates as promotion and release evidence inputs.
- docs/plans/2026-03-07-vco-deep-value-extraction-drift-closure-plan.md: Wave31-39 execution plan and closure criteria.
