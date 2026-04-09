# Memory Quality Evaluation Governance

## Purpose

Wave84 adds a quality-evaluation pack for `memory-runtime-v3`, `mem0`, and `Letta` without changing canonical owners or routing authority.
The evaluation pack measures quality gaps such as preference write precision, fallback integrity, compaction discipline, and owner-boundary preservation.

## Governance Scope

- The scorecard is evidence only; it cannot promote `mem0` or `Letta` into primary truth-sources.
- The evaluation pack must stay downstream of `memory-runtime-v3-policy.json`, `mem0-backend-policy.json`, and `letta-governance-contract.json`.
- Every scenario must prove that canonical memory owners remain `state_store`, `Serena`, `ruflo`, and `Cognee`.

## Required Invariants

- `optional_external_preference_backend` remains the only allowed role for `mem0`.
- `contract_source_only` remains the only allowed role for `Letta`.
- Evaluation outputs cannot become a second memory control plane or a promotion writer.
- Fallback-to-shadow must remain valid whenever quality evidence is stale or ambiguous.

## Non-Goals

- No new memory backend is introduced.
- No scorecard dimension may override owner-boundary failures.

Validation is performed by `scripts/verify/vibe-memory-quality-eval-gate.ps1`.
