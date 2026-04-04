# 2026-04-03 CLI Verify Runtime Contract Delegation Plan

## Goal

Remove the remaining CLI verify gate-path duplication so the outer CLI surface delegates installed-runtime verification entrypoints to the existing runtime contract owner.

## Internal Grade

XL wave, executed serially for this microphase because the change touches a user-facing CLI surface and must preserve both shell and PowerShell behavior.

## Frozen Scope

- Add a `verify_command` path that resolves the effective installed-runtime config before dispatching PowerShell verification.
- Keep shell verify behavior unchanged.
- Move the parser binding away from inline hardcoded gate paths in `main.py`.
- Add focused unit and integration tests.
- Run focused verification first, then the full regression wave and hygiene gate.
