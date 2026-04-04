# 2026-04-03 CLI Repo Adapter Registry Retirement Plan

## Goal

Remove dead adapter-registry helpers from `vgo_cli.repo` so the CLI repo module reflects the intended architecture: governance and repo-root utilities only, with host registry truth delegated elsewhere.

## Internal Grade

XL, executed serially for this microphase because the repo module is imported by CLI gate logic and the cleanup must be proven non-regressive.

## Frozen Scope

- Remove unused adapter-registry helpers from `apps/vgo-cli/src/vgo_cli/repo.py`.
- Add or update focused tests that prove the repo module no longer owns adapter-registry loading.
- Run focused verification and then full regression.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Delete the retired adapter-registry helpers from `vgo_cli.repo`.
3. Add/update focused architecture tests to lock the new module boundary.
4. Run focused CLI tests.
5. Run the full regression suite and `git diff --check`.

## Verification Commands

- `python3 -m py_compile apps/vgo-cli/src/vgo_cli/repo.py`
- `python3 -m pytest tests/unit/test_vgo_cli_repo.py tests/integration/test_cli_main_infra_separation.py tests/integration/test_cli_host_registry_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
