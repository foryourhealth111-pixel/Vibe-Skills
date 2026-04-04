# Linux + pwsh Fresh-Machine Evidence Ledger 2026-03-13

## Purpose

This ledger tracks the frozen Linux + `pwsh` fresh-machine evidence that now backs the pre-promotion proof bundle for `codex/linux`.

It remains explicit about the boundary between the proof-complete `Linux + pwsh` candidate lane and the still-degraded `Linux without pwsh` lane.

## Required Runs

| Run ID | Environment | Status | Required Commands | Notes |
| --- | --- | --- | --- | --- |
| `linux-pwsh-run-01` | WSL Ubuntu 24.04 | frozen | `bash ./scripts/bootstrap/one-shot-setup.sh`; `bash ./check.sh --profile full --deep`; PowerShell bootstrap-doctor follow-up; runtime-neutral coherence follow-up | `references/proof-bundles/linux-full-authoritative-candidate/linux-pwsh-run-01-wsl/` with `Result: 61 passed, 0 failed, 0 warnings` and readiness `manual_actions_pending` |
| `linux-pwsh-run-02` | Docker Ubuntu 24.04 | frozen | same as run 01 plus container provisioning | `references/proof-bundles/linux-full-authoritative-candidate/linux-pwsh-run-02-docker/` with `Result: 61 passed, 0 failed, 0 warnings` and readiness `manual_actions_pending` |

## Minimum Artifact Expectations

Each frozen run captures:

- host environment summary
- whether `pwsh` was preinstalled or provisioned
- exact command lines
- pass/fail summary
- generated receipts under `installed-runtime-outputs/`
- operation record plus manifest-required logs as the live proof surface
- duplicated `repo-outputs-verify/` copies are not part of the current minimum retained bundle
- operator notes for any manual remediation

## Current Result

Two independent fresh-machine Linux proof runs are now frozen into the repository.

That means Linux is no longer blocked on missing proof capture.
The frozen evidence is ready for a future promotion decision, but current release truth still keeps `codex/linux` at `supported-with-constraints` when `pwsh` is available.
