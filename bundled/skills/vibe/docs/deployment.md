# Deployment

## Profiles

- `minimal`: install only required bundled skills + rules + hooks
- `full`: install full vendored skill mirror + rules + hooks + MCP templates

## Windows

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\install.ps1 -Profile minimal
pwsh -File .\install.ps1 -Profile full -InstallExternal
pwsh -File .\install.ps1 -Profile full -StrictOffline
```

## Linux / macOS

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./install.sh --profile minimal
bash ./install.sh --profile full --install-external
bash ./install.sh --profile full --strict-offline
```

Recommended prerequisites:

- `git`
- `node` and `npm`
- `python3` or `python`
- `bash`
- `pwsh` if you want the authoritative PowerShell verification gates on Linux / macOS

## Recommended One-Shot Path

`pwsh -File .\scripts\bootstrap\one-shot-setup.ps1` on Windows and `bash ./scripts/bootstrap/one-shot-setup.sh` on Linux / macOS are the preferred operator paths when you want a single bootstrap command that:

- installs the governed runtime payload into the target Codex root
- attempts the explicitly auto-installable external CLI layer
- materializes the selected MCP profile into `~/.codex\mcp\servers.active.json`
- finishes with `check.ps1 -Deep`

This is intentionally not a fake “everything is auto-provisioned” path. The bootstrap still reports manual follow-up items for:

- host-managed Codex plugins
- user/provider API keys and secret material
- host-level MCP registration or permissions that cannot be safely mutated by a repo script

## Verification

```powershell
pwsh -File .\check.ps1 -Profile full
pwsh -File .\check.ps1 -Profile full -Deep
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -File .\scripts\verify\vibe-bootstrap-doctor-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex" -WriteArtifacts
# Windows PowerShell fallback:
powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep
```

```bash
bash ./check.sh --profile full
bash ./check.sh --profile full --deep
```

## External Tools

`-InstallExternal` optionally installs external tools/plugins when available:
- SuperClaude command set
- claude-flow (npm global)
- plugin entries in manifest (best-effort)

Installer behavior notes:
- Default install path now trusts vendored skills first (`bundled/skills`).
- `-StrictOffline` enforces routed-skill closure + lock/hash consistency.
- `-AllowExternalSkillFallback` can temporarily allow non-vendored fallback sources; avoid it for reproducible team baselines.
- `check.ps1 -Deep` now runs the bootstrap doctor gate so operators get a classified readiness result instead of only a shallow integrity check.

## MCP Materialization

If you need to materialize the active MCP profile without re-running the full bootstrap, use:

```powershell
pwsh -File .\scripts\setup\materialize-codex-mcp-profile.ps1 -TargetRoot "$env:USERPROFILE\.codex" -Force
```

On Linux / macOS, the one-shot shell bootstrap materializes the active profile automatically. If you want the authoritative standalone materialization script outside the bootstrap flow, install `pwsh` and run the same command there.

This writes the selected profile into `~/.codex\mcp\servers.active.json`. It does not silently mutate global host registration or provision plugin-backed MCP surfaces.

## Safe Update Flow

This flow has two separate scopes:

1. repo maintenance sync
2. installed runtime upgrade

Pulling the repo does **not** upgrade `${TARGET_ROOT}/skills/vibe` by itself.

### Repo maintenance sync

1. Pull latest `vco-skills-codex`
2. Run `scripts/bootstrap/sync-local-compat.ps1`
3. Run `scripts/verify/vibe-generate-skills-lock.ps1`
4. Review diff
5. Run `check.ps1 -Deep` and `scripts/verify/vibe-offline-skills-gate.ps1`
6. Commit + push

### Installed runtime upgrade

After the repo tree is updated, re-materialize the governed runtime for the same target root before trusting any freshness output:

- Windows:
  - `pwsh -File .\install.ps1 -TargetRoot "$env:USERPROFILE\.codex"`
  - or `pwsh -File .\scripts\bootstrap\one-shot-setup.ps1`
- Linux / macOS:
  - `bash ./install.sh --target-root "$HOME/.codex"`
  - or `bash ./scripts/bootstrap/one-shot-setup.sh`

Then re-run the deep check for that target root.
