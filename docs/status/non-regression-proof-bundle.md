# Non-Regression Proof Bundle

Updated: 2026-06-24

## Positioning

This page is the minimum proof contract for structure-changing work after the 2026-04-04 architecture-closure sign-off.
It is an operator and contributor closeout contract.
It is not the everyday public proof ladder.

Keep the narrow public claims separate from this bundle:

- `installed locally` -> `check`
- `runtime coherent` -> returned `session_root` truth artifacts
- `delivery accepted` -> delivery-acceptance report

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
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-governed-runtime-contract-gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-canonical-entry-truth-gate.ps1 -SessionRoot <returned session_root>
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-runtime-execution-proof-gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-release-truth-consistency-gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify/vibe-repo-cleanliness-gate.ps1
```

Additional final regression checks stay outside the default closure gate set:

```powershell
python3 -m pytest tests/contract tests/unit tests/integration tests/e2e tests/runtime_neutral -q
git diff --check
```

Add-on audit commands are opt-in. Use them only when the change actually touches those surfaces:

```powershell
powershell -NoProfile -File scripts/verify/vibe-pack-routing-smoke.ps1
powershell -NoProfile -File scripts/verify/vibe-current-routing-debt-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-version-packaging-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-mirror-edit-hygiene-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-output-artifact-boundary-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-installed-runtime-freshness-gate.ps1
powershell -NoProfile -File scripts/verify/vibe-release-install-runtime-coherence-gate.ps1
```

Historical phase-end wrapper, retained only as an operator aid rather than the active proof owner:

```powershell
powershell -NoProfile -File scripts/governance/phase-end-cleanup.ps1 -WriteArtifacts
```

## Recommended Run Order

Default closure should stay small:

1. `vibe-governed-runtime-contract-gate.ps1`
   - validates the governed runtime contract
2. `vibe-canonical-entry-truth-gate.ps1`
   - validates canonical entry truth and required session artifacts for a specific returned `session_root`
3. `vibe-runtime-execution-proof-gate.ps1`
   - validates execution proof for the current runtime story
4. `vibe-release-truth-consistency-gate.ps1`
   - validates narrow release wording against the current truth surfaces
5. `vibe-repo-cleanliness-gate.ps1`
   - validates current cleanliness contract

Packaging, freshness, and retired-routing audit gates are still useful, but they are opt-in audit tools instead of the normal closeout path.

Final regression and patch hygiene still matter before completion claims, but they are separate from the default closure gate set:

- full pytest regression
- `git diff --check`

## Batch-to-Proof Mapping

| Batch Type | Minimum Required Proof |
| --- | --- |
| docs spine only | small default closure set + final regression checks |
| routing / router config | small default closure set + routing smoke + router contract + current routing debt audit |
| compatibility topology / packaging | small default closure set + version packaging + mirror hygiene |
| install / check / runtime | small default closure set + installed runtime freshness + release/install/runtime coherence |
| fallback / degraded truth / release wording | small default closure set + final regression checks |
| outputs / fixtures | small default closure set + output artifact boundary |
| cleanliness policy / plane split | small default closure set + final regression checks |
| destructive prune | small default closure set + final regression checks + every add-on audit gate touched by the change |

## Evidence Reading Rule

This page names the required proof. It is not the source of the latest proof outcome.

To determine the current status of a cleanup batch, read the latest receipt for each gate from `outputs/verify/*.json`, inspect `gate_result`, then pair that with the latest full regression result and current closure receipt.

Artifact anchors:

- default closure:
  - `outputs/verify/vibe-governed-runtime-contract-gate.json`
  - `outputs/verify/vibe-canonical-entry-truth-gate.json`
  - `outputs/verify/vibe-runtime-execution-proof-gate.json`
  - `outputs/verify/vibe-release-truth-consistency-gate.json`
  - `outputs/verify/vibe-repo-cleanliness-gate.json`
- add-on audits when touched:
  - `outputs/verify/vibe-pack-routing-smoke.summary.json`
  - `outputs/verify/vibe-current-routing-debt-gate.json`
  - `outputs/verify/vibe-version-packaging-gate.json`
  - `outputs/verify/vibe-mirror-edit-hygiene-gate.json`
  - `outputs/verify/vibe-output-artifact-boundary-gate.json`
  - `outputs/verify/vibe-installed-runtime-freshness-gate.json`
  - `outputs/verify/vibe-release-install-runtime-coherence-gate.json`

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
