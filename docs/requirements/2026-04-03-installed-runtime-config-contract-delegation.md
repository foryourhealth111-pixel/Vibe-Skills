# 2026-04-03 Installed Runtime Config Contract Delegation

## Goal

Move installed-runtime default configuration and governance merge semantics into the contracts package so CLI and verification-core consume one contract-owned installed-runtime configuration surface.

## Scope

In scope:
- `packages/contracts/src/vgo_contracts/installed_runtime_contract.py`
- `packages/contracts/src/vgo_contracts/__init__.py`
- `packages/verification-core/src/vgo_verify/policies.py`
- `apps/vgo-cli/src/vgo_cli/repo.py`
- focused unit and integration tests for the new ownership boundary

Out of scope:
- changing installed-runtime governance schema
- changing PowerShell helper ownership in this microphase
- changing gate behavior or install UX
- changing runtime-neutral verification entrypoints

## Acceptance Criteria

1. Installed-runtime defaults live in contracts, including frontmatter gate defaults used by CLI.
2. Installed-runtime governance merge semantics live in contracts.
3. CLI repo helpers no longer hardcode installed-runtime defaults inline.
4. Verification-core policies no longer own the installed-runtime merge algorithm inline.
5. Existing merged config behavior remains unchanged.
6. Focused tests lock the new dependency direction and config owner.
