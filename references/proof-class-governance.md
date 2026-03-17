# Proof Class Governance

This file defines the minimum honest proof taxonomy for the governed runtime.

## Classes

| Class | Meaning | Promotion suitability |
| --- | --- | --- |
| `structure` | Schema, packet, contract, or board exists | no |
| `fixture` | Deterministic gate or replay on bounded cases | no |
| `runtime` | Canonical runtime actually executed and emitted aligned artifacts | bounded |
| `field` | Messy, cross-surface, operator-relevant evidence | yes |

## Interpretation Rules

- Do not treat all green artifacts as equivalent.
- A `structure` artifact may prove a contract exists without proving that the runtime obeyed it.
- A `fixture` artifact may prove a bounded path remains stable without proving field relevance.
- A `runtime` artifact is the minimum class required before claiming that the governed runtime actually performed the described work.
- A `field` artifact is required before promoting shadow candidates into stronger authority for messy real tasks.

## Current Baseline

- `runtime-input-packet.json` is `structure`.
- `execution-manifest.json` is `runtime`.
- `benchmark-proof/manifest.json` is `runtime`.
- `cleanup-receipt.json` is `runtime`.
- `messy-real-task-corpus.json` is a `field` candidate asset, not field proof by itself.
