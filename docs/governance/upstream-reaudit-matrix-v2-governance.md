# Upstream Re-Audit Matrix v2 Governance

## Purpose

Wave99 upgrades the upstream value ledger into a decision-oriented re-audit matrix that shows remaining value, migration ceiling, and explicit non-go absorption boundaries.
Wave121 extends the matrix from the original mirror-focused set to **19 canonical upstream sources**, including memory / browser / desktop sources that were already absorbed elsewhere but not yet ledger-aligned.

## Governance Scope

- Every upstream row must declare current status, absorbability class, recommended migration, promotion ceiling, remaining value class, and explicit no-go text.
- The matrix stays subordinate to single-control-plane governance and cannot itself widen runtime ownership.
- The matrix must use canonical slugs only; display names are routed through `config/upstream-source-aliases.json`.
- Wave94 skill harvest, lifecycle policy, and later promotion planning consume this matrix as evidence inputs.

## Required Invariants

- `explicit_no_go` and `promotion_ceiling` are mandatory per row.
- `remaining_value_class` can be multi-valued so residual value is not flattened into one bucket.
- `re_audit_priority` keeps later stage planning bounded.
- A re-audit row may recommend hold, ceiling, or partial absorption, but never auto-promotion.
- `mem0`, `browser-use`, and `agent-s` can appear in the matrix without ever becoming default runtime owners.

## Non-Goals

- No upstream project becomes a default runtime owner through the matrix.
- No lane or status may be widened without explicit board review.
- No alias may replace the canonical slug inside the matrix.

Validation is performed by `scripts/verify/vibe-upstream-reaudit-matrix-gate.ps1`, but the validation contract is evidence-oriented and must tolerate human-readable heading/casing differences so long as the matrix schema and governance meaning remain intact.
