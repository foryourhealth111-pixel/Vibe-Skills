# Verify Gate Family Index

`scripts/verify/` 是 VCO 的 evidence-running surface。这个索引负责 gate family 分组、典型运行顺序，以及把操作者引到 proof contract 的正式页面。

## Start Here

- minimum closure proof contract: [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- operator-oriented verify entrypoint: [`README.md`](./README.md)
- broader operator surface: [`../governance/README.md`](../governance/README.md)

## What This Page Owns

- verify-family grouping
- typical closure-facing gate run order
- executable gate discovery inside `scripts/verify/`

This page does not own:

- the authoritative closure contract
- the latest PASS / FAIL truth
- the broader operator console outside `scripts/verify/`

Current truth always lives in `outputs/verify/*.json`.

## Typical Closure Run Order

When a structure-changing cleanup batch needs the standard proof surface, the usual verify sequence is:

1. `vibe-pack-routing-smoke.ps1`
   - fast routing smoke before deeper contract checks
2. `vibe-router-contract-gate.ps1`
   - routing contract validation
3. `vibe-version-packaging-gate.ps1`
   - canonical to bundled packaging parity
4. `vibe-mirror-edit-hygiene-gate.ps1`
   - mirror-only drift rejection
5. `vibe-output-artifact-boundary-gate.ps1`
   - output versus fixture boundary
6. `vibe-installed-runtime-freshness-gate.ps1`
   - installed runtime freshness
7. `vibe-release-install-runtime-coherence-gate.ps1`
   - install, check, and release coherence
8. `vibe-release-truth-consistency-gate.ps1`
   - release and promotion truth honesty for fallback and degraded paths
9. `vibe-repo-cleanliness-gate.ps1`
   - current cleanliness contract

The authoritative requirement set for closure remains [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md).

## Gate Families

| Family | Typical Scripts | When to Run |
| --- | --- | --- |
| Runtime Integrity / Packaging | `vibe-bom-frontmatter-gate.ps1`, `vibe-version-packaging-gate.ps1`, `vibe-installed-runtime-freshness-gate.ps1`, `vibe-release-install-runtime-coherence-gate.ps1` | packaging, install, frontmatter, runtime freshness |
| Fallback Governance / Truth Honesty | `vibe-no-silent-fallback-contract-gate.ps1`, `vibe-no-self-introduced-fallback-gate.ps1`, `vibe-release-truth-consistency-gate.ps1` | degraded-path governance, hazard honesty, release truth alignment |
| Managed Runtime / Process Hygiene | `vibe-node-zombie-gate.ps1` | managed Node ownership, stale-process classification, report-only cleanup safety |
| Cleanliness / Outputs / Mirror Hygiene | `vibe-repo-cleanliness-gate.ps1`, `vibe-output-artifact-boundary-gate.ps1`, `vibe-mirror-edit-hygiene-gate.ps1`, `vibe-nested-bundled-parity-gate.ps1` | canonical cleanup batches, sync-before or sync-after, fixture migrations |
| Plane Governance | `vibe-browserops-*.ps1`, `vibe-desktopops-*.ps1`, `vibe-docling-*.ps1`, `vibe-connector-*.ps1` | plane contract, rollout, replay, sandbox, benchmark changes |
| Capability / Role / Upstream Value Ops | `vibe-capability-*.ps1`, `vibe-role-pack-*.ps1`, `vibe-upstream-*.ps1`, `vibe-third-party-disclosure-parity-gate.ps1`, `vibe-upstream-lock-coverage-gate.ps1`, `vibe-origin-provenance-gate.ps1`, `vibe-skill-harvest-v2-gate.ps1` | upstream distillation, disclosure parity, provenance, role-pack and capability closure |
| Release / Promotion / Observability | `vibe-promotion-board-gate.ps1`, `vibe-release-evidence-bundle-gate.ps1`, `vibe-release-train-v2-gate.ps1`, `vibe-release-truth-consistency-gate.ps1`, `vibe-ops-cockpit-gate.ps1` | release, promotion, observability, and cockpit updates |
| Operator Preview / Apply Safety | `vibe-operator-preview-contract-gate.ps1`, `vibe-manual-apply-policy-gate.ps1` | preview or apply contract changes for write-capable governance scripts |
| Execution-Context / Wave Runner | `vibe-wave121-upstream-mapping-gate.ps1`, `vibe-wave124-ops-cockpit-v2-gate.ps1`, `vibe-wave125-gate-family-convergence-gate.ps1` | manifest families, wave-runner coverage, and execution-context lock hardening |
| Remediation Foundation / Proof Classes | `vibe-remediation-foundation-gate.ps1`, `vibe-benchmark-autonomous-proof-gate.ps1` | remediation baseline, proof-class honesty, shadow executor presence, cleanup taxonomy |

## Cross-Layer Handoff

- operator entrypoints live at [`../README.md`](../README.md) and [`../governance/README.md`](../governance/README.md)
- closure proof contract lives at [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- long-lived contracts, ledgers, and reference playbooks live at [`../../references/index.md`](../../references/index.md)
