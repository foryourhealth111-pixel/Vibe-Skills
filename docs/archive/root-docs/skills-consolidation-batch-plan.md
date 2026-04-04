# Skills Consolidation Batch Plan

## Execution Order

This batch plan follows low-risk to high-risk migration order.

## Batch A: Duplicate Fast-Wins

- Status:
  - Completed (hard migration validated on 2026-02-24, including bundled overlap cleanup)
- Goal:
  - Remove obvious duplicates with canonical aliases already defined.
- Scope:
  - `code-review1..4 -> code-review`
  - `xlsx1 -> xlsx`
  - `vibe/bundled/*` overlap aliases already mapped
- Acceptance:
  - Duplicate-name groups reduced from 19 to <= 12
  - No regression in `vibe-routing-smoke.ps1`
  - `vibe-pack-routing-smoke.ps1` still passes

## Batch B: Orchestration/Core Quality Packs

- Status:
  - Completed (Soft Migration Expansion, validated on 2026-02-24)
- Goal:
  - Normalize high-frequency workflow skills into pack-first access.
- Scope:
  - `orchestration-core`
  - `code-quality`
- Acceptance:
  - Routes for planning/coding/review/debug resolve through pack overlay at high confidence
  - Legacy matrix fallback rate remains low and explainable

## Batch C: Data/ML and Research Packs

- Status:
  - Completed (hard candidate-pruning validated on 2026-02-24)
- Goal:
  - Consolidate related ML, analytics, and research workflows.
- Scope:
  - `data-ml`
  - `research-design`
  - `ai-llm`
- Acceptance:
  - Pack candidate lists pruned to top stable skills
  - No grade-boundary violations

## Batch D: Bio/Docs/Integration Packs

- Status:
  - Completed (hard candidate-pruning validated on 2026-02-24)
- Goal:
  - Consolidate domain packs with external-tool dependencies.
- Scope:
  - `bio-science`
  - `docs-media`
  - `integration-devops`
- Acceptance:
  - Tool availability checks remain lazy and stable
  - Fallback paths documented for unavailable external dependencies

## Batch E: Cleanup Window

- Status:
  - Completed (final hard cleanup executed and validated on 2026-02-24)
- Goal:
  - Remove deprecated aliases and archive superseded stubs after stability window.
- Scope:
  - generate removable alias whitelist with impact/risk tiers
  - aliases with near-zero usage
  - retired duplicate skill entries
- Acceptance:
  - Batch E audit report and whitelist file published
  - Duplicate groups reach 0
  - Public entry skill count reaches target
  - Final report published

## Per-Batch Checklist

- Pre-check:
  - snapshot current inventory
  - confirm rollback target
- Change:
  - update alias/pack configs
  - update docs if routing behavior changes
- Verify:
  - run `vibe-routing-smoke.ps1`
  - run `vibe-pack-routing-smoke.ps1`
- Report:
  - list changed files
  - summarize route impact and residual risks
