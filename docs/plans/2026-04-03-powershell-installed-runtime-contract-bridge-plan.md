# 2026-04-03 PowerShell Installed Runtime Contract Bridge Plan

## Goal

Remove the remaining PowerShell-side installed-runtime default owner so wrappers and baseline gates consume a contract-owned compatibility surface.

## Internal Grade

XL wave, executed serially for this microphase because the change crosses Python bridge code, PowerShell helper code, and verification boundaries.

## Frozen Scope

- Add a JSON-emitting installed-runtime contract bridge in `scripts/common/runtime_contracts.py`.
- Refactor `Get-VgoInstalledRuntimeConfig` to load defaults from the bridge.
- Refactor the official runtime baseline gate to use effective runtime gate paths from runtime config.
- Add focused tests for the new bridge and the PowerShell ownership boundary.
- Run focused verification and then full-suite regression for the new wave.
