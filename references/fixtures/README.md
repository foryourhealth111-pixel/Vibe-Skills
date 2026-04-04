# Fixture Migration Stage 2

This directory holds governed baseline fixtures mirrored from historically tracked `outputs/**` files.

## Why it exists

Wave123 moves the repository toward a clean boundary:

- runtime outputs stay in `outputs/**` and remain untracked;
- baseline fixture material moves to `references/fixtures/**`;
- legacy tracked outputs were mirrored here before strict cleanup removed the tracked `outputs/**` copies.

## Fixture groups

- `external-corpus/`: external-corpus candidate and routing baseline fixture material
- `retro-compare/`: safety, sample-run, and smoke retro-compare baseline fixture snapshots
- `runtime-contract/`: governed runtime packet / execution manifest curated golden fixtures
- `verify/routing-stability/`: routing-stability baseline fixture snapshots

## Consumer Ledger

- family-level consumer map: [`consumer-ledger.md`](./consumer-ledger.md)
- `external-corpus/`, `retro-compare/`, and `verify/routing-stability/` are active canonical fixture roots under `config/outputs-boundary-policy.json`
- `runtime-contract/` remains active through `tests/runtime_neutral/test_runtime_contract_goldens.py`
- `anti-proxy-goal-drift/` is currently retained pending an explicit archive-or-rewrite decision; do not move it based on grep counts alone

## Reading rule

- treat these files as reference fixtures, not live runtime output;
- use `migration-map.json` as the source-of-truth map from tracked outputs to mirrored fixture copies;
- The migration label remains `stage2_mirrored` for migration-map compatibility.
- Current enforcement is already strict on repo-tracked `outputs/**`: `expected_tracked_output_count = 0` and `strict_requires_zero_tracked_outputs = true`.
