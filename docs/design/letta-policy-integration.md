# Letta Policy Integration

## Role

`Letta` contributes policy vocabulary and contracts to VCO. It does **not** contribute runtime orchestration authority.

## Imported Concepts

1. Memory blocks -> mapped to VCO memory owners
2. Archival search contract -> clarifies long-term retrieval expectations
3. Tool rules -> constrains tool choice and escalation surfaces
4. Token-pressure policy -> helps define compaction / confirmation guidance

## Explicit Non-Goals

- No Letta agent runtime inside VCO control plane
- No second workflow surface
- No autonomous route selection or reassignment

## Output Form

Letta-derived value is stored as:
- `config/letta-governance-contract.json`
- `references/memory-block-contract.md`
- `references/tool-rule-contract.md`

## Rollout

Always starts in `shadow`. Promotion means stricter contract checking, not more authority.
