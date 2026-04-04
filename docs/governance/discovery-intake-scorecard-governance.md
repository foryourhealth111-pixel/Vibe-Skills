# Discovery Intake Scorecard Governance

## Purpose

Wave91 scores discovery intake candidates so upstream lists remain a governed discovery feed instead of silently expanding runtime surface area.
The scorecard ranks novelty, absorbability, overlap risk, and evaluation cost before any Stage B or Stage C productization consumes the source.

## Governance Scope

- Discovery intake is a material layer only; it cannot auto-install tools or change runtime routing.
- Every intake row must name its lane, likely owner, overlap risk, and next evaluation action.
- `tracked-corpus` sources remain non-runtime by default until lifecycle governance widens them deliberately.

## Required Invariants

- `discovery_feed_only = true` remains fixed.
- `runtime_install_forbidden = true` stays fixed for discovery-only rows.
- Each row must preserve explicit `next_eval` and `no_go_boundary` text.
- The scorecard must remain subordinate to upstream value ledger and capability lifecycle policy.

## Non-Goals

- No marketplace or runtime registry is created.
- No discovery row may skip dedup or absorbability review.

Validation is performed by `scripts/verify/vibe-discovery-intake-scorecard-gate.ps1`.
