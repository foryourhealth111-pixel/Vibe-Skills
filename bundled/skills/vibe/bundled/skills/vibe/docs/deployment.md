# Deployment

## Profiles

- `minimal`: install only required bundled skills + rules + hooks
- `full`: install full vendored skill mirror + rules + hooks + MCP templates

## Windows

```powershell
pwsh -File .\install.ps1 -Profile minimal
pwsh -File .\install.ps1 -Profile full -InstallExternal
pwsh -File .\install.ps1 -Profile full -StrictOffline
```

## Verification

```powershell
pwsh -File .\check.ps1 -Profile full
pwsh -File .\check.ps1 -Profile full -Deep
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
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

## Safe Update Flow

1. Pull latest `vco-skills-codex`
2. Run `scripts/bootstrap/sync-local-compat.ps1`
3. Run `scripts/verify/vibe-generate-skills-lock.ps1`
4. Review diff
5. Run `check.ps1 -Deep` and `scripts/verify/vibe-offline-skills-gate.ps1`
6. Commit + push
