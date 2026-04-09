# Verify Gate Family Index

`scripts/verify/` 是 evidence-running surface。这里仅负责 family 分组和常见运行顺序；最新真相仍在 `outputs/verify/*.json`。

## Start Here

- closure proof contract: [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- verify entrypoint: [`README.md`](./README.md)
- broader operator surface: [`../governance/README.md`](../governance/README.md)

## Typical Closure Order

1. `vibe-pack-routing-smoke.ps1`
2. `vibe-router-contract-gate.ps1`
3. `vibe-version-packaging-gate.ps1`
   current meaning: canonical-only packaging governance + generated compatibility wiring
4. `vibe-mirror-edit-hygiene-gate.ps1`
   current meaning: block repo-tracked mirror reintroduction
5. `vibe-output-artifact-boundary-gate.ps1`
6. `vibe-installed-runtime-freshness-gate.ps1`
7. `vibe-release-install-runtime-coherence-gate.ps1`
8. `vibe-release-truth-consistency-gate.ps1`
9. `vibe-repo-cleanliness-gate.ps1`

## Families

- Runtime / packaging: `vibe-bom-frontmatter-gate.ps1`, `vibe-version-packaging-gate.ps1`, `vibe-installed-runtime-freshness-gate.ps1`
- Release / truth honesty: `vibe-dist-manifest-gate.ps1`, `vibe-release-notes-quality-gate.ps1`, `vibe-release-truth-consistency-gate.ps1`
- Cleanliness / outputs / compatibility hygiene: `vibe-repo-cleanliness-gate.ps1`, `vibe-output-artifact-boundary-gate.ps1`, `vibe-mirror-edit-hygiene-gate.ps1`, `vibe-nested-bundled-parity-gate.ps1`
- Plane governance: `vibe-browserops-*.ps1`, `vibe-desktopops-*.ps1`, `vibe-docling-*.ps1`, `vibe-connector-*.ps1`
- Capability / upstream / role packs: `vibe-capability-*.ps1`, `vibe-role-pack-*.ps1`, `vibe-upstream-*.ps1`
- Operator Preview / Apply Safety: `vibe-operator-preview-contract-gate.ps1`, `vibe-manual-apply-policy-gate.ps1`
- Execution-Context / Wave Runner: `vibe-wave121-upstream-mapping-gate.ps1`, `vibe-wave124-ops-cockpit-v2-gate.ps1`, `vibe-wave125-gate-family-convergence-gate.ps1`

## Boundary

- proof contract 在 [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- operator 导航在 [`../README.md`](../README.md)
- 长期 contracts / ledgers / playbooks 在 [`../../references/index.md`](../../references/index.md)
