This directory stores executable verification gates for local and CI use.

## Start Here

- family map and typical run order: [`gate-family-index.md`](./gate-family-index.md)
- minimum closure proof contract: [`../../docs/status/non-regression-proof-bundle.md`](../../docs/status/non-regression-proof-bundle.md)
- broader operator surface: [`../governance/README.md`](../governance/README.md)
- blackbox/probe workflow: [`../../docs/design/blackbox-probe-and-enhancement-playbook.md`](../../docs/design/blackbox-probe-and-enhancement-playbook.md)

## Most Common Commands

Bootstrap readiness:

```powershell
pwsh -NoProfile -File .\vibe-bootstrap-doctor-gate.ps1 -WriteArtifacts
```

Router AI advice connectivity:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\vibe-router-ai-connectivity-gate.ps1 -WriteArtifacts
```

Phase-end cleanup:

```powershell
pwsh -NoProfile -File .\..\governance\phase-end-cleanup.ps1 -WriteArtifacts
```

If packaging / compatibility topology changed:

```powershell
pwsh -NoProfile -File .\..\governance\phase-end-cleanup.ps1 -WriteArtifacts -IncludeMirrorGates
```

## Common Verify Sequence

```powershell
& ".\vibe-pack-routing-smoke.ps1"
& ".\vibe-router-contract-gate.ps1"
& ".\vibe-version-packaging-gate.ps1" -WriteArtifacts
& ".\vibe-output-artifact-boundary-gate.ps1" -WriteArtifacts
& ".\vibe-installed-runtime-freshness-gate.ps1" -WriteReceipt
& ".\vibe-release-install-runtime-coherence-gate.ps1" -WriteArtifacts
& ".\vibe-repo-cleanliness-gate.ps1" -WriteArtifacts
```

## High-Frequency Quick Starts

Routing stability:

```powershell
& ".\vibe-routing-stability-gate.ps1" -WriteArtifacts
```

Repo cleanliness:

```powershell
& ".\..\governance\install-local-worktree-excludes.ps1"
& ".\vibe-repo-cleanliness-gate.ps1" -WriteArtifacts
& ".\vibe-output-artifact-boundary-gate.ps1" -WriteArtifacts
```

Version / packaging:

```powershell
& ".\vibe-version-consistency-gate.ps1" -WriteArtifacts
& ".\vibe-version-packaging-gate.ps1" -WriteArtifacts
```

Installed runtime freshness:

```powershell
& ".\vibe-installed-runtime-freshness-gate.ps1" -WriteReceipt
```

## Legacy-Name Notes

- `vibe-version-packaging-gate.ps1` keeps its legacy name, but in the current contract it validates canonical-only packaging governance plus generated-compatibility wiring.
- `vibe-config-parity-gate.ps1` keeps its legacy name, but in canonical-only mode it validates config closure and confirms repo-tracked bundled copies stay absent.
- `vibe-mirror-edit-hygiene-gate.ps1` blocks accidental reintroduction of repo-tracked mirror edits.

## Boundaries

- Run topology-aware and execution-context-locked gates from the canonical repo root only.
- Latest PASS / FAIL truth lives in `outputs/verify/*.json`, not in this README.
- Deep family lists, plane-specific gates, and specialist workflows stay in [`gate-family-index.md`](./gate-family-index.md) and linked topic docs.
- Flat gate filenames remain compatibility contracts; family regrouping must preserve callable entrypoint stability until an explicit replacement contract exists.
