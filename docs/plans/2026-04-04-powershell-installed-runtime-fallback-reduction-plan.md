# 2026-04-04 PowerShell Installed Runtime Fallback Reduction Plan

## Goal

Narrow the remaining PowerShell-side installed-runtime fallback so the helper layer behaves as a consumer of the contract rather than a second semantic owner.

## Internal Grade

XL microphase, executed serially at the root lane because the write scope is small but cross-layer verification is required.

## Frozen Scope

- reduce `Get-VgoInstalledRuntimeFallbackDefaults` to an explicitly emergency compatibility surface
- update `Get-VgoRuntimeEntrypointPath` to prefer effective runtime config before any fallback default
- update focused tests to assert the new ownership boundary and preserved fallback semantics
- run PowerShell parse checks, focused pytest, direct helper validation if needed, full regression, and cleanup
