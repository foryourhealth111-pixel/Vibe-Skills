# VCO Version & Packaging Governance

## Goal

Prevent version confusion between:
- canonical source files in repo root
- bundled mirror in `bundled/skills/vibe`
- installed runtime copy in `${TARGET_ROOT}/skills/vibe`

## Source of Truth

Use `config/version-governance.json` as the machine-readable contract:
- release metadata (`version`, `updated`)
- version marker targets (`SKILL.md` + bundled mirror)
- changelog path and release ledger path
- canonical root and bundled root
- mirror scope (files + directories)
- bundled-only whitelist
- normalized JSON ignore keys for parity checks

## Packaging Rules

1. Canonical source is repo root (`.`).
2. Bundled mirror is `bundled/skills/vibe`.
3. Bundled must mirror the configured file/dir set.
4. JSON parity ignores `updated` and `generated_at` keys only.
5. Any bundled-only file must be explicitly listed in `allow_bundled_only`.

## Tooling

### Sync bundled mirror

```powershell
& ".\scripts\governance\sync-bundled-vibe.ps1"
```

Optional prune:

```powershell
& ".\scripts\governance\sync-bundled-vibe.ps1" -PruneBundledExtras
```

### Run version/packaging gate

```powershell
& ".\scripts\verify\vibe-version-packaging-gate.ps1" -WriteArtifacts
```

Artifacts:
- `outputs/verify/vibe-version-packaging-gate.json`
- `outputs/verify/vibe-version-packaging-gate.md`

### Run version consistency gate

```powershell
& ".\scripts\verify\vibe-version-consistency-gate.ps1" -WriteArtifacts
```

Artifacts:
- `outputs/verify/vibe-version-consistency-gate.json`
- `outputs/verify/vibe-version-consistency-gate.md`

### Cut a release (single command)

```powershell
& ".\scripts\governance\release-cut.ps1" -Version "2.3.25" -Updated "2026-02-28" -RunGates
```

This command updates:
- `config/version-governance.json`
- maintenance markers in `SKILL.md` and `bundled/skills/vibe/SKILL.md`
- changelog header (`references/changelog.md`)
- release ledger (`references/release-ledger.jsonl`)
- release note skeleton (`docs/releases/v<version>.md`)
- bundled mirror sync (`sync-bundled-vibe`)

## Install-time Safety

`install.ps1` / `install.sh` first copy bundled, then force-copy canonical mirror scope to target `skills/vibe`.

This guarantees deployed runtime files match canonical source even if bundled drift appears.

## Recommended Release Flow

1. Edit canonical files in repo root.
2. Run sync:
   - `scripts/governance/sync-bundled-vibe.ps1 -PruneBundledExtras`
3. Run gates:
   - `scripts/verify/vibe-version-consistency-gate.ps1`
   - `scripts/verify/vibe-version-packaging-gate.ps1`
   - existing routing/config gates
4. Commit and push.
