# 2026-04-03 CLI Host Registry Delegation Plan

## Goal

Make `vgo_cli.hosts` a thin CLI-facing host facade by delegating registry truth to installer-core while retaining only command-surface semantics and user-facing error shaping.

## Internal Grade

XL, executed serially for this microphase because the host facade sits on install and uninstall entrypoints and any regression would affect the primary CLI path.

## Frozen Scope

- Refactor `apps/vgo-cli/src/vgo_cli/hosts.py` to delegate registry loading and adapter resolution to installer-core.
- Preserve CLI-only target-root guard behavior and message text.
- Update focused tests to prove the new boundary and keep behavior stable.
- Run focused verification, then full regression and diff hygiene.

## Implementation Steps

1. Freeze the microphase in a dedicated requirement/plan pair.
2. Replace repo-local registry loading in `vgo_cli.hosts` with installer-core delegation, adding only the minimal workspace-path bootstrap needed for CLI imports.
3. Keep local only the CLI-specific pieces: default target-root composition, path-signature matching, and `CliError` mapping.
4. Update the CLI host cutover test and add focused delegation coverage if needed.
5. Run focused unit/integration verification, then full regression and `git diff --check`.

## Verification Commands

- `python3 -m py_compile apps/vgo-cli/src/vgo_cli/hosts.py`
- `python3 -m pytest tests/unit/test_vgo_cli_infra_split.py tests/integration/test_cli_host_registry_cutover.py -q`
- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- `git diff --check`
