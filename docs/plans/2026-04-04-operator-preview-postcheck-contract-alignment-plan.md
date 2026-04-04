# 2026-04-04 Operator Preview Postcheck Contract Alignment Plan

## Goal

Close the remaining semantic gap inside the operator preview contract by giving `postcheck_gates` a real consumer in `release-cut` while keeping apply-time gate execution stable.

## Internal Grade

M cut executed inside the governed XL root wave because the change is narrow, local to one operator, and easily verifiable.

## Frozen Scope

- add a postcheck gate resolver in `release-cut.ps1`
- keep `apply_gates` as the source for `-RunGates` execution
- use `postcheck_gates` for preview `verify_after_apply`
- keep compatibility fallback to the apply gate list when `postcheck_gates` is missing
- add focused integration and runtime-neutral tests
