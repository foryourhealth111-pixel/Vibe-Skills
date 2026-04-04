# Prompt Intelligence Evaluation Governance

## Purpose

Wave87 adds QA and evaluation criteria for prompt cards distilled from Prompt-Engineering-Guide and prior prompt-intelligence productization work.
The evaluation layer checks whether cards remain advisory-first, route-safe, and useful to operators without becoming a second prompt router.

## Governance Scope

- Prompt cards remain downstream of VCO routing and pack selection.
- Card QA must measure provenance, duplication risk, safety labeling, and route usefulness without granting route override powers.
- Evaluation evidence must explicitly flag any attempt to widen prompt cards into default control-plane logic.

## Required Invariants

- `advisory_first = true` and `allow_route_override = false` remain fixed.
- `second_prompt_router_forbidden = true` for all prompt card bundles and review assets.
- Every card must keep provenance to its canonical pattern source and an explicit risk note.
- Prompt QA outputs may recommend edits but cannot mutate pack-manifest or thresholds automatically.

## Non-Goals

- No prompt card becomes a hidden task classifier.
- No prompt source corpus is wholesale imported without harvest review.

Validation is performed by `scripts/verify/vibe-prompt-intelligence-eval-gate.ps1`.
