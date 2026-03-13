# Hard Migration Report - Batch A2 (Bundled Overlap Cleanup)

Date: 2026-02-24

## Scope

Continue hard migration after soft-migration verification:

- Create full backup of current `skills` directory before deletion.
- Remove bundled duplicate directories that overlap with canonical skills.
- Keep canonical directories and alias mappings.
- Keep `bundled/skills/vibe` as the bundled entry package.

## Backup

- Backup file: `outputs/backups/skills-pre-hard-migration-20260224-224135.zip`
- Backup size: `4,542,860` bytes

## Removed Directories

From `skills/vibe/bundled/skills`:
- `cancel-ralph`
- `dialectic`
- `local-vco-roles`
- `ralph-loop`
- `spec-kit-vibe-compat`
- `superclaude-framework-compat`
- `tdd-guide`
- `think-harder`

From `skills/vibe/bundled/superpowers-skills`:
- `brainstorming`
- `receiving-code-review`
- `requesting-code-review`
- `subagent-driven-development`
- `systematic-debugging`
- `verification-before-completion`
- `writing-plans`

Total removed: `15` directories.

Post-cleanup state:
- `skills/vibe/bundled/skills`: only `vibe`
- `skills/vibe/bundled/superpowers-skills`: empty

## Installer Compatibility Changes

Updated installer scripts to avoid dependency on removed bundled duplicates:

- `skills/vibe/install.ps1`
- `skills/vibe/install.sh`

New behavior:
- Core compatibility skills are copied from canonical `skills/<name>` first, then bundled fallback (if present).
- Workflow skills are copied from canonical `superpowers/skills/<name>` first, then bundled fallback (if present).

This keeps install/check flows functional after bundled overlap cleanup.

## Validation

Install/check validation:
- `skills/vibe/install.ps1 -Profile full -TargetRoot outputs/tmp/vibe-install-test`
- `skills/vibe/check.ps1 -Profile full -TargetRoot outputs/tmp/vibe-install-test`
- Result: `21 passed, 0 failed, 0 warnings`

Routing and pack verification:
- `vibe-routing-smoke.ps1`: `38/38`
- `vibe-pack-routing-smoke.ps1`: `104/104`
- `vibe-skill-index-routing-audit.ps1`: `93/93`
- `vibe-keyword-precision-audit.ps1`: `1402/1402`
- `vibe-pack-regression-matrix.ps1`: `24/24`

Conclusion:
- No critical misroute introduced.
- Pack routing and per-skill routing remain stable.
- Hard migration cleanup completed with rollback backup in place.

