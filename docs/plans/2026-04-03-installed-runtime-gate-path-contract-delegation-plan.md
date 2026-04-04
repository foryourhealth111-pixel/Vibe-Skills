# 2026-04-03 Installed Runtime Gate Path Contract Delegation Plan

## Goal

Consolidate installed-runtime gate path projections in contracts so CLI and verification-core consume one contract-owned compatibility surface.

## Internal Grade

XL wave, executed serially for this microphase because the change touches contracts, CLI, and verification-core but should preserve behavior.

## Frozen Scope

- Add contract-owned installed-runtime compatibility gate path projection(s).
- Refactor CLI install gate helpers to consume the contract projection.
- Refactor verification coherence helpers to consume the contract projection and runtime-config frontmatter gate.
- Update focused tests.
- Run focused verification and diff hygiene; full regression will happen at wave boundary.
