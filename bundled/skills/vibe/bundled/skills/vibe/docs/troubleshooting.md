# Troubleshooting

## Missing skill after install
- Run `check.ps1`
- Confirm target path is `~/.codex/skills`
- Re-run `install.ps1 -Profile full -StrictOffline`
- Run `scripts/verify/vibe-offline-skills-gate.ps1` and fix lock mismatch if any

## MCP unavailable
- Verify server entries in `mcp/servers.template.json`
- Check environment variables and local binaries

## Upstream update broke behavior
- Do not hot-replace bundled content from upstream
- Use manual merge workflow and update `config/upstream-lock.json`

## Plugin install failures
- Installer is best-effort by design
- See `config/plugins-manifest.codex.json` and install manually
