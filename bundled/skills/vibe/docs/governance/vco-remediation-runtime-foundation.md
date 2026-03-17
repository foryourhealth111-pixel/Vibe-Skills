# VCO Remediation Runtime Foundation

Date: 2026-03-17

This governance note records the first executable baseline of the remediation master program.

## What is now materially present

- a frozen runtime input packet emitted before requirement and plan generation
- proof-class registry separating structure, fixture, runtime, and field proof
- truthful cleanup modes distinguishing `receipt_only`, `bounded_cleanup_executed`, `destructive_cleanup_applied`, and `cleanup_degraded`
- a shadow plan-derived execution manifest emitted alongside the current benchmark executor
- a bounded messy-task corpus, path ecology board, and authoritative promotion board

## What remains intentionally deferred

- plan-derived execution is still shadow-only
- messy-task corpus is defined but not yet deeply replayed as a field-proof source
- replacement-lane governance is recognized but not yet operationalized as an authority-switch path

## Why this matters

The remediation cycle now produces explicit runtime truth artifacts instead of relying on prose-only intent:

1. the router truth is frozen into a runtime packet before requirement freezing
2. execution receipts declare proof class explicitly
3. cleanup receipts no longer imply material cleanup when only a receipt was written
4. the plan-derived executor can now be measured without prematurely replacing the benchmark harness
