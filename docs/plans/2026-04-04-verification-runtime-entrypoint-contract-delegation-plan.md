# 2026-04-04 Verification Runtime Entrypoint Contract Delegation Plan

## Goal

Remove repeated governed runtime entrypoint ownership from verification gates by routing those invocations through one PowerShell helper backed by the installed-runtime contract.

## Internal Grade

XL wave, executed serially for this microphase because the change touches multiple verification gates and a cross-language runtime contract bridge.

## Frozen Scope

- Add one helper in `vibe-governance-helpers.ps1` to resolve the effective runtime entrypoint path.
- Cut over the current bounded set of verification gates that already load governance context.
- Keep required file checks and runtime smoke semantics unchanged.
- Add a textual ownership lock and one runtime-neutral behavior test for override resolution.
- Run focused verification first, then the full regression wave and hygiene gate.
