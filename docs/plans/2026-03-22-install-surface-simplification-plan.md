# 2026-03-22 Install Surface Simplification Plan

## Goal

Make installation easier to understand for users and safer across multiple agents by exposing only two primary install paths and adding host selection to bootstrap when no host is explicitly supplied.

## Grade

- Internal grade: M

## Work Batches

### Batch 1: Governance freeze
- Create requirement doc
- Create execution plan

### Batch 2: Bootstrap host selection
- Update `scripts/bootstrap/one-shot-setup.sh`
- Update `scripts/bootstrap/one-shot-setup.ps1`
- Preserve explicit host arguments
- Require explicit host in non-interactive mode if not inferable from environment
- Add clearer reminders for non-Codex provider inputs

### Batch 3: User-facing install surface reduction
- Rewrite `docs/install/one-click-install-release-copy.md`
- Rewrite `docs/install/one-click-install-release-copy.en.md`
- Add `docs/install/manual-copy-install.md`
- Add `docs/install/manual-copy-install.en.md`
- Update `README.md` install section
- Update `README.en.md` install section

### Batch 4: Verification
- shell syntax checks
- PowerShell parse checks
- targeted interactive bootstrap verification for Bash and PowerShell
- targeted non-interactive failure verification when host is omitted
- doc link consistency spot-check

### Batch 5: Phase cleanup
- remove temporary test roots
- audit for temporary files created during verification
- preserve final evidence in command history and cleanup summary

## Rollback Rules

- If interactive selection breaks explicit host usage, revert the prompt path and keep docs-only simplification.
- If PowerShell interactive detection is unreliable, keep Bash interactive prompting and require explicit `-HostId` on PowerShell as fallback.
- If docs and script behavior diverge, script truth wins and docs must be corrected before completion.
