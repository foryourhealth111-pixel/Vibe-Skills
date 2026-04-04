# 2026-04-03 Bootstrap Host Catalog Dedupe

## Goal

Reduce host-selection duplication in the active one-shot bootstrap entrypoints so shell and PowerShell derive the supported-host list and prompt surface from a shared registry/helper contract instead of hard-coding the same host catalog in multiple places.

## Scope

In scope:
- `scripts/bootstrap/one-shot-setup.sh`
- `scripts/bootstrap/one-shot-setup.ps1`
- shared registry/helper surfaces used only to drive bootstrap host selection and non-interactive error messaging
- focused tests that prove the bootstrap host catalog comes from shared registry/helper logic

Out of scope:
- changing which hosts are supported
- changing install/check/bootstrap semantics beyond host prompt/message dedupe
- changing adapter registry contract for install/check/runtime execution behavior
- docs refresh outside the frozen requirement/plan pair for this phase

## Acceptance Criteria

1. Shell bootstrap no longer hard-codes the supported host list in both the prompt and the non-interactive missing-host error path.
2. PowerShell bootstrap no longer hard-codes the supported host list in both the prompt and the non-interactive missing-host error path.
3. Supported hosts and prompt choices remain functionally identical to the current behavior: `codex`, `claude-code`, `cursor`, `windsurf`, `openclaw`, `opencode`.
4. Interactive selection still accepts the same intended user inputs, including `claude` as an alias for `claude-code`.
5. Existing bootstrap target-root guard behavior and current install/check/runtime behavior remain unchanged.
6. Verification includes focused bootstrap tests plus a full regression sweep before completion language is used.

## Product Acceptance Checks

1. Non-interactive bootstrap without `--host` / `-HostId` still fails explicitly and lists the same supported hosts.
2. Interactive bootstrap still presents the same host choices in the same order.
3. Full test suite remains green after the cutover.
