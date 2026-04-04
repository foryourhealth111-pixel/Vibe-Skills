# Claude Code Linux Evidence Ledger 2026-03-31

## Purpose

This ledger freezes the Linux evidence that supports moving `claude-code/linux` from `not-yet-proven` to `supported-with-constraints`.

It does not claim official-runtime parity with Codex.
It does not promote Windows or macOS.

## Frozen Evidence

Primary proof bundle:

- `references/proof-bundles/claude-code-managed-closure-candidate/linux-managed-run-01-local-host/operation-record.md`
- `references/proof-bundles/claude-code-managed-closure-candidate/linux-managed-run-01-local-host/installed-runtime-outputs/runtime-freshness-receipt.json`

Retained live proof is intentionally minimal: the operation record summarizes install/check/bootstrap/coherence/CLI-smoke results, and the runtime-freshness receipt keeps the machine-readable receipt contract.

Supporting command-surface audit:

- `docs/audits/2026-03-30-cross-host-startup-regression-audit.md`

## Measured Result

- `install.sh --host claude-code` passed on a clean Linux target root
- `check.sh --host claude-code --deep` passed with `67 passed, 0 failed, 1 warnings`
- the warning is the expected deep-doctor skip for adapter mode `preview-guidance`
- the dedicated bootstrap doctor gate returned `manual_actions_pending`, which is expected for a host-managed lane with plugin, MCP, and credential surfaces outside repo ownership
- the runtime coherence gate passed
- the real local Claude CLI binary was present and returned `2.1.81 (Claude Code)`
- `CLAUDE_HOME=<target-root> claude agents` succeeded, which is a command-level smoke result against the managed target root

## Why This Is Sufficient

`claude-code/linux` does not target `full-authoritative`.
Its declared platform promotion target is `supported-with-constraints`.

For this lane, the repository owns only a bounded managed closure:

- `settings.json` managed `vibeskills` node
- managed Claude `PreToolUse` hook entry
- managed `hooks/write-guard.js`
- `.vibeskills` sidecar state

The frozen evidence now proves those owned Linux surfaces can be installed, checked, and tolerated by a real local Claude CLI command surface.

## What Still Remains Out Of Scope

- Windows proof
- macOS proof
- official-runtime ownership
- whole-host guarantees across every Claude startup or login path

## Docker Note

A follow-up Docker fresh-machine attempt was explored on the same host and failed because Docker Hub egress was blocked by the environment:

- with the preexisting Docker daemon proxy, pulls failed because the configured local proxy endpoint was unavailable
- after temporarily removing that daemon proxy, direct Docker Hub access still timed out

That blocker is environmental, not a repository implementation failure, so it does not negate the frozen local Linux managed-closure evidence above
