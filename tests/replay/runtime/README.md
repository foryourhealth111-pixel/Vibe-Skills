# Runtime Contract Goldens

This directory stores governed-runtime replay baselines for public runtime artifacts.

Files:

- `governed-runtime-contract-golden.json`: canonical field-and-key replay contract.
- `runtime-contract-golden.json`: curated normalized case baseline aligned to optional `host_adapter.closure_path` semantics.

Rules:

- it validates a stable semantic subset, not full JSON parity
- dynamic values must be normalized before comparison
- packet and manifest goldens are allowed to evolve only through governed runtime contract changes
