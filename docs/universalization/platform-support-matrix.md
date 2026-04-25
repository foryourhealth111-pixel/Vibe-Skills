# Platform Support Matrix

> Status baseline: 2026-03-13  
> Scope: current official runtime truth, not future marketing claims.

## Purpose

This document makes platform truth explicit for the universalization program.

It separates:

- host support
- platform support
- authoritative closure path
- honest degraded path

This document does **not** claim that all hosts and all platforms already have identical closure strength.

## Rating Vocabulary

| Status | Meaning |
| --- | --- |
| `full-authoritative` | official install + check + governance gates have a documented and intended closure path |
| `supported-with-constraints` | usable path exists, but some authoritative gates or lifecycle surfaces still depend on extra prerequisites |
| `degraded-but-supported` | installation and main runtime can work, but key governance / doctor / parity surfaces are intentionally skipped with warnings |
| `not-yet-proven` | repo contains signals suggesting support, but no formal proof contract exists yet |

## Current Truth Summary

As of the current repository baseline:

- Windows is the clearest official runtime path because the repo's primary governance, doctor, freshness, and coherence gates are PowerShell-first. The preferred PowerShell host is PowerShell 7 / `pwsh`; Windows PowerShell is only a Windows fallback path.
- Linux is now a promoted official runtime path when `pwsh` is available, backed by a frozen fresh-machine proof bundle and synchronized replay/docs state.
- Linux without `pwsh` is an honest degraded path, not a false "full support" path.
- macOS is logically close to the Linux shell path, but it is not yet separately frozen as a formal proof lane. macOS also needs `pwsh` before PowerShell-native governed verification can be treated as available.

Linux promotion is governed by:

- `docs/universalization/linux-full-authoritative-contract.md`
- `docs/universalization/platform-promotion-criteria.md`
- `docs/status/linux-pwsh-fresh-machine-evidence-ledger-2026-03-13.md`

Those layers are now satisfied together for `codex/linux` when `pwsh` is present.

## PowerShell 7 Boundary

The platform contract now separates content installation from full governed-runtime verification:

- shell entrypoints can still install shipped content where supported
- runtime-neutral checks can still run where Python and shell prerequisites are present
- PowerShell-native governance, doctor, freshness, and parity gates require PowerShell 7 / `pwsh`
- Linux/macOS without `pwsh` must not be reported as full governed-runtime readiness
- Windows may fall back to Windows PowerShell only when `pwsh` is unavailable, and that fallback must be visible in the closeout wording

## Platform Matrix

| Platform | Install Surface | Check Surface | Governance / Doctor Surface | Current Rating | Notes |
| --- | --- | --- | --- | --- | --- |
| Windows | `install.ps1`, `one-shot-setup.ps1` | `check.ps1` | strongest current path for PowerShell-first gates | `full-authoritative` | this is the current reference closure lane |
| Linux + `pwsh` | `install.sh`, `one-shot-setup.sh` | `check.sh` plus PowerShell-capable follow-up | strongest Linux path when `pwsh` is provisioned | `supported-with-constraints` | fresh-machine proof is frozen, but formal promotion is still intentionally withheld |
| Linux without `pwsh` | `install.sh`, `one-shot-setup.sh` | `check.sh` | PowerShell authority gates may be skipped with warnings | `degraded-but-supported` | usable, but not equal to official Windows closure |
| macOS + `pwsh` | shell path inferred from bash tooling | partial | likely similar to Linux + `pwsh`, but not frozen | `not-yet-proven` | must not be marketed as full until proved |
| macOS without `pwsh` | shell path inferred from bash tooling | partial | likely degraded like Linux without `pwsh` | `not-yet-proven` | must first be measured and recorded |

## Host vs Platform

Universalization must never collapse these two axes into one statement.

Examples:

- "Codex supported" is incomplete without saying whether the support claim is Windows-only, Linux-with-pwsh, or degraded.
- "Linux supported" is incomplete without saying whether the lane is official runtime, host adapter preview, or heuristic-only.
- "OpenCode preview install exists" is incomplete without saying which platform replay evidence has actually been frozen.

The correct statement pattern is:

`<host> on <platform> => <status>`

## Required Truths to Freeze Next

The migration plan must freeze the following:

1. Which PowerShell gates are authoritative and must be preserved.
2. Which bash surfaces are first-class versus convenience wrappers.
3. Which platform differences are expected and acceptable.
4. Which missing prerequisites force support labeling down from `full-authoritative`.

## Non-Regression Rule

Universalization work is not allowed to weaken the current Windows official lane in order to make the matrix look cleaner.

The order is:

1. document truth
2. freeze support contract
3. close high-value parity gaps
4. only then promote support language
