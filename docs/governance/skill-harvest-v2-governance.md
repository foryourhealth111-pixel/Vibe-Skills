# Skill Harvest v2 Governance

## Purpose

Wave94 defines the second-generation harvest policy for upstream skill corpora such as `claude-skills`, `antigravity-awesome-skills`, and `awesome-claude-skills-composio`.
Harvest v2 exists to distill reusable value into governed skill cards, templates, and evaluation notes without wholesale importing upstream runtimes.

## Governance Scope

- Harvest stays selective, deduplicated, and evidence-based.
- Each harvested item must name source corpus, canonical destination, overlap risk, and no-go boundary.
- No upstream skill directory may be treated as a second skill runtime or a default installer feed.

## Required Invariants

- `selective_harvest_only = true` remains fixed.
- `raw_import_forbidden = true` remains fixed.
- `second_skill_runtime_forbidden = true` remains fixed.
- Promotion requires a scorecard, no-go note, and lifecycle placement before bundling.

## Non-Goals

- No wholesale mirroring into canonical bundles.
- No execution routing authority is inherited from upstream skill repos.

Validation is performed by `scripts/verify/vibe-skill-harvest-v2-gate.ps1`.
