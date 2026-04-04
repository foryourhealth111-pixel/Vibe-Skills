# 2026-04-03 Installed Runtime Gate Path Contract Delegation

## Goal

Move installed-runtime compatibility gate path projections into contracts so CLI and verification-core stop hardcoding runtime-neutral freshness and frontmatter gate paths inline.

## Scope

In scope:
- `packages/contracts/src/vgo_contracts/installed_runtime_contract.py`
- `packages/contracts/src/vgo_contracts/__init__.py`
- `apps/vgo-cli/src/vgo_cli/install_gates.py`
- `packages/verification-core/src/vgo_verify/runtime_coherence_support.py`
- `packages/verification-core/src/vgo_verify/runtime_coherence_runtime.py`
- focused unit and integration tests

Out of scope:
- changing installed-runtime governance schema
- changing PowerShell gate behavior
- changing runtime-neutral script entrypoints themselves

## Acceptance Criteria

1. Contracts own the runtime-neutral freshness gate compatibility path projection.
2. CLI install gates no longer hardcode `scripts/verify/runtime_neutral/freshness_gate.py`.
3. Verification coherence runtime no longer hardcodes the frontmatter gate path.
4. Existing install and coherence behavior remains unchanged.
5. Focused tests lock the new ownership boundary.
