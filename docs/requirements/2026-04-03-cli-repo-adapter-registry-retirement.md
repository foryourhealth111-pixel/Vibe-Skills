# 2026-04-03 CLI Repo Adapter Registry Retirement

## Goal

Retire the now-unused adapter-registry helpers from `apps/vgo-cli/src/vgo_cli/repo.py` so the CLI repo module owns only repo/governance concerns after the `vgo_cli.hosts` installer-core cutover.

## Scope

In scope:
- `apps/vgo-cli/src/vgo_cli/repo.py`
- focused tests that prove adapter-registry loading is no longer a responsibility of the CLI repo module

Out of scope:
- changing CLI command behavior
- changing installer-core adapter-registry APIs
- changing canonical repo-root semantics
- changing host resolution or target-root guard behavior

## Acceptance Criteria

1. `vgo_cli.repo` no longer defines adapter-registry path/loading helpers.
2. The repo module retains only repo/governance responsibilities used by CLI infrastructure.
3. CLI behavior remains unchanged because adapter-registry resolution already lives in installer-core-facing host code.
4. Focused tests lock the new boundary.
5. Verification includes focused CLI tests and a full regression sweep.
