# 2026-04-04 Verification Runtime Entrypoint Contract Delegation

## Goal

Make verification-side PowerShell gates consume the governed runtime entrypoint from the effective installed-runtime contract instead of hardcoding direct calls to `scripts/runtime/invoke-vibe-runtime.ps1` in multiple gate surfaces.

## Scope

In scope:
- `scripts/common/vibe-governance-helpers.ps1`
- bounded verification gates that already use `Get-VgoGovernanceContext`
- focused integration and runtime-neutral tests for helper resolution and gate ownership

Out of scope:
- changing governed runtime stage behavior
- changing runtime-neutral Python tests that intentionally exercise the canonical runtime script path directly
- changing release-cut orchestration in this microphase

## Acceptance Criteria

1. The selected verification gates no longer hardcode `scripts/runtime/invoke-vibe-runtime.ps1` inline for runtime invocation.
2. Those gates resolve the entrypoint from the effective installed-runtime config through a shared PowerShell helper.
3. The helper respects governance overrides for `runtime_entrypoint` and preserves default behavior when no override is present.
4. Focused tests lock both the ownership boundary and the override behavior.
