# 2026-04-04 CLI Runtime Entrypoint Contract Delegation Plan

## Goal

Remove the remaining CLI runtime entrypoint duplication so the outer CLI surface delegates governed runtime entrypoint selection to the existing runtime contract owner.

## Internal Grade

XL wave, executed serially for this microphase because the change touches a user-facing CLI surface and the cross-language runtime contract bridge.

## Frozen Scope

- Extend the installed-runtime contract with a runtime entrypoint field.
- Keep shell runtime behavior unchanged.
- Move the parser binding away from the inline hardcoded runtime path in `main.py`.
- Keep Python and PowerShell fallback defaults aligned.
- Add focused unit and integration tests, then run full regression and hygiene gates.
