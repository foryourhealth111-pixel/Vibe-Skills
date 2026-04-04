# Target Architecture

## Non-Negotiable Rules

- Domain semantics must live in package-owned cores, not in shell or PowerShell wrappers.
- Generated artifacts under distribution surfaces are outputs, never source of truth.
- Release-facing `dist/*` manifests must be materialized from `config/distribution-manifest-sources.json`; release operators may sync them, but must not own their semantics inline.
- Adapter registry semantics must be sourced from `config/adapter-registry.json`; `adapters/index.json` and adapter-entrypoint fallbacks are compatibility projections only.
- Installer profile skill inventory semantics must be sourced from the runtime-core profile manifests; installer-core may consume them, but must not hardcode a second required-skill owner.
- Runtime-core shared packaging semantics must be sourced from `config/runtime-core-packaging.json`; `runtime-core-packaging.minimal.json` and `.full.json` are generated compatibility projections only.
- Runtime, delivery, verification, and catalog must remain separately owned modules.
- Cross-platform support is provided by thin wrappers over a single semantic core.
- Legacy entrypoints may remain only as compatibility shims that delegate into package-owned cores.
- Runtime distribution manifests must classify semantic owners separately from compatibility shims; flat payload lists are compatibility projections only.
- Version-governance payload lists and required runtime marker lists must publish grouped role projections alongside their flat compatibility projections.
- Governance operators must consume config-owned contracts such as `config/operator-preview-contract.json` and `config/phase-cleanup-policy.json`; `scripts/governance/*` may orchestrate those contracts, but must not own gate inventories or cleanup modes inline.
- The current sign-off proof and shim-retention boundary are tracked in `docs/proof/2026-04-04-owner-consumer-consistency-proof.md` and `docs/architecture/legacy-topology-audit.md`.
