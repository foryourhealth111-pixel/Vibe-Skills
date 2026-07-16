# Kernel-First Remediation Baseline

## Purpose

This note freezes the cleanup boundary before semantic authority is moved again.

## Live Authority Targets

- task understanding -> kernel
- skill selection -> kernel
- plan construction -> kernel
- execution truth -> kernel
- verification truth -> kernel
- wrapper role -> host launch and receipts only
- routing role -> candidate discovery and compatibility only

## Measured Hotspots

- `scripts/router/**`
- `packages/runtime-core/src/vgo_runtime/router_contract*.py`
- `packages/runtime-core/src/vgo_runtime/task_intent.py`
- `packages/runtime-core/src/vgo_runtime/planning.py`
- `packages/runtime-core/src/vgo_runtime/stage_machine.py`
- `packages/runtime-core/src/vgo_runtime/runtime_truth.py`
- `packages/runtime-core/src/vgo_runtime/kernel/**`
- `bundled/skills/**`
- `docs/governance/**`

## Exit Rule

No hotspot may retain live semantic authority unless the kernel boundary map still names it as current authority.
