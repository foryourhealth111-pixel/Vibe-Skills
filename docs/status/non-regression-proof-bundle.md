# Non-Regression Proof Bundle

Updated: 2026-04-04

## Positioning

This page is the minimum proof contract for structure-changing work after the 2026-04-04 architecture-closure sign-off.

It defines which commands must be rerun before a later cleanup or topology-changing batch can claim success. It does not carry the authoritative PASS/FAIL state itself. Current truth always lives in `outputs/verify/*.json`, fresh regression output, and the current closure receipt.

## Rule

Every structure-changing batch must name the proof it depends on before it modifies structure.

If a batch touches routing, compatibility topology, install/runtime behavior, operator contracts, output boundary, or cleanliness policy, it must rerun the affected commands and verify the resulting receipts before claiming success.

Protected official-runtime main-chain edits remain frozen by default.
If a batch needs to touch those surfaces, it must also be covered by:

- `config/official-runtime-main-chain-policy.json`
- a plan-backed contract such as `docs/universalization/linux-full-authoritative-contract.md`

Without those anchors, a green proof bundle is not enough to justify the change.

## Canonical Commands

Run from the canonical repo root:

```powershell
powershell -NoProfile -File scripts/verify/vibe-pack-routing-smoke.ps1
powershell -NoProfile -File scripts/verify/vibe-router-contract-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-version-packaging-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-mirror-edit-hygiene-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-output-artifact-boundary-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-installed-runtime-freshness-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-release-install-runtime-coherence-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-release-truth-consistency-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-repo-cleanliness-gate.ps1
python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q
git diff --check
```

Historical phase-end wrapper, retained only as an operator aid rather than the active proof owner:

```powershell
powershell -NoProfile -File scripts/governance/phase-end-cleanup.ps1 -WriteArtifacts
```

## Recommended Run Order

1. `vibe-pack-routing-smoke.ps1`
   - fast behavior smoke for routing
2. `vibe-router-contract-gate.ps1`
   - validates routing contract details
3. `vibe-version-packaging-gate.ps1`
   - validates canonical-only packaging governance and generated-compatibility wiring
4. `vibe-mirror-edit-hygiene-gate.ps1`
   - rejects accidental reintroduction of repo-tracked mirror drift
5. `vibe-output-artifact-boundary-gate.ps1`
   - validates output -> fixture boundary
6. `vibe-installed-runtime-freshness-gate.ps1`
   - validates installed runtime parity / receipt
7. `vibe-release-install-runtime-coherence-gate.ps1`
   - validates install/check/release coherence
8. `vibe-release-truth-consistency-gate.ps1`
   - validates fallback and degraded-truth consistency across release/promotion surfaces
9. `vibe-repo-cleanliness-gate.ps1`
   - validates current cleanliness contract
10. full pytest regression
   - validates the frozen architecture-closure surface end-to-end across contracts, unit, integration, e2e, and runtime-neutral coverage
11. `git diff --check`
   - rejects whitespace / patch hygiene regressions before closure language is allowed

## Batch-to-Proof Mapping

| Batch Type | Minimum Required Proof |
| --- | --- |
| docs spine only | manual link/readability review, then full regression + `git diff --check` before closure |
| routing / router config | routing smoke + router contract |
| compatibility topology / packaging | version packaging + mirror hygiene |
| install / check / runtime | installed runtime freshness + release/install/runtime coherence |
| fallback / degraded truth / release wording | release truth consistency gate |
| outputs / fixtures | output artifact boundary |
| cleanliness policy / plane split | repo cleanliness gate |
| destructive prune | all commands above |

## Evidence Reading Rule

This page names the required proof. It is not the source of the latest proof outcome.

To determine the current status of a cleanup batch, read the latest receipt for each gate from `outputs/verify/*.json`, inspect `gate_result`, then pair that with the latest full regression result and current closure receipt.

Artifact anchors:

- `outputs/verify/vibe-pack-routing-smoke.summary.json`
- `outputs/verify/vibe-router-contract-gate.json`
- `outputs/verify/vibe-version-packaging-gate.json`
- `outputs/verify/vibe-mirror-edit-hygiene-gate.json`
- `outputs/verify/vibe-output-artifact-boundary-gate.json`
- `outputs/verify/vibe-installed-runtime-freshness-gate.json`
- `outputs/verify/vibe-release-install-runtime-coherence-gate.json`
- `outputs/verify/vibe-release-truth-consistency-gate.json`
- `outputs/verify/vibe-repo-cleanliness-gate.json`

Latest known architecture-closure sign-off regression:

- `python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q`
- result: `403 passed, 66 subtests passed in 509.44s (0:08:29)` on `2026-04-04`

That snapshot is historical evidence, not a standing promise that every later worktree remains green.

## Contract Rule for Future Expansion

If a new protected capability is introduced, it is not covered by this bundle until:

1. a corresponding gate or bounded audit path exists;
2. that proof is added to this document; and
3. the resulting receipt is wired into the current closure flow.

Current rule after the 2026-04-04 sign-off is not to loosen the bundle, but to preserve it as the minimum closure contract before any further prune or topology reduction.
