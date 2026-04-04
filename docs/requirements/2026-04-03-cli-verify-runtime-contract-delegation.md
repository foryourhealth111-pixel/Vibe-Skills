# 2026-04-03 CLI Verify Runtime Contract Delegation

## Goal

Make the CLI `verify` surface consume the installed-runtime coherence gate from the effective runtime contract instead of hardcoding a second gate path owner in `main.py`.

## Scope

In scope:
- `apps/vgo-cli/src/vgo_cli/main.py`
- `apps/vgo-cli/src/vgo_cli/commands.py`
- `apps/vgo-cli/src/vgo_cli/repo.py`
- focused integration and unit tests for CLI verify dispatch

Out of scope:
- changing shell `check` behavior
- changing runtime command entrypoints
- changing coherence gate semantics or verification-core behavior

## Acceptance Criteria

1. The CLI `verify` command no longer hardcodes `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1` in `main.py`.
2. PowerShell verify dispatch resolves the coherence gate from the effective installed-runtime contract.
3. Shell verify dispatch remains `check.sh` and existing CLI behavior does not regress.
4. Focused tests lock the ownership boundary and command behavior.
