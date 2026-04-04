# Fixture Consumer Ledger

Updated: 2026-04-04

This ledger records which `references/fixtures/**` families are still live regression surfaces versus which ones are merely weakly referenced.

## Family Classification

| Family | Status | Primary Consumers | Retention Rule |
| --- | --- | --- | --- |
| `external-corpus/` | active | `tests/runtime_neutral/test_outputs_boundary_migration.py`, `references/fixtures/migration-map.json`, `config/outputs-boundary-policy.json` | keep live |
| `retro-compare/` | active | `tests/runtime_neutral/test_outputs_boundary_migration.py`, `references/fixtures/migration-map.json`, `config/outputs-boundary-policy.json` | keep live |
| `verify/routing-stability/` | active | `tests/runtime_neutral/test_outputs_boundary_migration.py`, `references/fixtures/migration-map.json`, `config/outputs-boundary-policy.json` | keep live |
| `anti-proxy-goal-drift/` | retained-pending-decision | historical verification corpus; current repo no longer carries a live `vibe-anti-proxy-goal-drift-*.ps1` family reference | keep in place until an explicit archive-or-rewrite wave lands |
| `runtime-contract/` | active-but-ambiguous | `tests/runtime_neutral/test_runtime_contract_goldens.py` | keep live |

## Rules

- Do not classify a fixture family as historical-only from slash-path grep evidence alone.
- Windows-style path joins, directory enumeration, and code-built paths count as live consumers.
- Archive-first is allowed only after family-level consumer proof is empty or the consumer is rewritten to a replacement canonical root.
