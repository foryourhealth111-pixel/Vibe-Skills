# Verify Gate Family Index

`scripts/verify/` 是 evidence-running surface。这里仅负责 family 分组和常见运行顺序；最新真相仍在 `outputs/verify/*.json`。

## Start Here

- closure proof contract: [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- verify entrypoint: [`README.md`](./README.md)
- broader operator surface: [`../governance/README.md`](../governance/README.md)

## Default release closure

1. `vibe-governed-runtime-contract-gate.ps1`
2. `vibe-canonical-entry-truth-gate.ps1`
3. `vibe-runtime-execution-proof-gate.ps1`
4. `vibe-release-truth-consistency-gate.ps1`
5. `vibe-repo-cleanliness-gate.ps1`

Default closure should stay small. Packaging, mirror, freshness, and retired-routing audit gates are still useful, but they are opt-in audit tools instead of the normal closeout path.

## Touched-surface extension gates

- Install receipt / installed-copy health: `check.ps1`, `vibe-installed-runtime-freshness-gate.ps1`
- Routing / retired-routing audits: `vibe-pack-routing-smoke.ps1`, `vibe-current-routing-debt-gate.ps1`
- Runtime / packaging: `vibe-bom-frontmatter-gate.ps1`, `vibe-version-packaging-gate.ps1`, `vibe-installed-runtime-freshness-gate.ps1`
- Release / truth honesty: `vibe-dist-manifest-gate.ps1`, `vibe-release-notes-quality-gate.ps1`, `vibe-release-truth-consistency-gate.ps1`
- Cleanliness / outputs / compatibility hygiene: `vibe-current-routing-debt-gate.ps1` is the current routing debt audit. It verifies retired routing terms stay out of current runtime, router, docs, and current tests while allowing explicit retired/historical evidence; `vibe-repo-cleanliness-gate.ps1`, `vibe-output-artifact-boundary-gate.ps1`, `vibe-mirror-edit-hygiene-gate.ps1`, `vibe-nested-bundled-parity-gate.ps1`
- Plane governance: `vibe-browserops-*.ps1`, `vibe-desktopops-*.ps1`, `vibe-docling-*.ps1`, `vibe-connector-*.ps1`
- Capability / upstream / role packs: `vibe-capability-*.ps1`, `vibe-role-pack-*.ps1`, `vibe-upstream-*.ps1`
- Operator Preview / Apply Safety: `vibe-operator-preview-contract-gate.ps1`, `vibe-manual-apply-policy-gate.ps1`
- Execution-Context / Wave Runner: `vibe-wave121-upstream-mapping-gate.ps1`, `vibe-wave124-ops-cockpit-v2-gate.ps1`, `vibe-wave125-gate-family-convergence-gate.ps1`

## Boundary

- proof contract 在 [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- operator 导航在 [`../README.md`](../README.md)
- 长期 contracts / ledgers / playbooks 在 [`../../references/index.md`](../../references/index.md)
