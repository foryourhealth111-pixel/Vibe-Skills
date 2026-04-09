# Release Evidence Bundle v3 Governance

## Purpose

Wave96 defines the third-generation release evidence bundle so release train decisions can cite a compact, machine-readable evidence index. In short: this is the governed `bundle v3` contract for release evidence.
Bundle v3 joins version governance, git head, board posture, dashboard refs, verify outputs, and ledger refs in one place.

## Governance Scope

- The bundle must be generated from governed sources and use stable evidence refs.
- The bundle is not allowed to infer missing evidence as passing evidence.
- Version, updated date, git head, and evidence refs are mandatory top-level fields.

## Required Invariants

- `bundle_version = v3` remains fixed.
- `evidence_refs` must point to governed docs, configs, and verify artifacts.
- `git_head` and release ledger linkage must remain visible.
- The bundle cannot replace release notes; it complements them.

## Non-Goals

- No manual-only checklist may masquerade as the bundle.
- No hidden pass status may be inserted when evidence files are absent.

Validation is performed by `scripts/verify/vibe-release-evidence-bundle-gate.ps1`.
