# 2026-04-04 Mirror-Topology Contract Delegation Plan

## Goal

Remove repeated Python-side mirror-topology and legacy `source_of_truth` resolution logic by centralizing it in the contracts package and making installer-core plus verification-core consume that shared contract surface.

## Internal Grade

XL microphase executed serially at the root lane, with bounded parallel read-only analysis and implementation review where file ownership is disjoint.

## Frozen Scope

- add a shared mirror-topology resolver module under `packages/contracts/src/vgo_contracts/`
- export canonical target and generated nested compatibility helpers from the contracts layer
- refactor installer-core materialization and uninstall support to consume the shared helper
- refactor verification-core policy topology loading to consume the shared helper
- add focused unit/integration/runtime-neutral tests for the shared boundary
- run focused verification, full regression, and phase cleanup hygiene

## Verification

- `python3 -m py_compile` on touched Python tests and modules
- focused `pytest` for contracts / installer-core / verification-core cutover tests
- full `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
