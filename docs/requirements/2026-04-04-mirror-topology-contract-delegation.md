# 2026-04-04 Mirror-Topology Contract Delegation

## Goal

Make Python-side governance consumers resolve canonical and generated-compatibility topology from one shared contract helper instead of repeating direct `source_of_truth` reads inline across installer-core and verification-core.

## Scope

In scope:
- `packages/contracts/src/vgo_contracts/` shared mirror-topology helper
- `packages/installer-core/src/vgo_installer/materializer.py`
- `packages/installer-core/src/vgo_installer/uninstall_service.py`
- `packages/verification-core/src/vgo_verify/policies.py`
- focused tests for contract ownership and behavior preservation

Out of scope:
- removing legacy `source_of_truth` fields from governance JSON
- changing installed runtime payload contents
- changing release operator, router, or PowerShell governance helper behavior beyond keeping parity with the new Python contract boundary

## Acceptance Criteria

1. Installer-core and verification-core consume one shared mirror-topology contract helper instead of owning inline topology fallback logic.
2. `sync_vibe_canonical` resolves the canonical root from mirror-topology contract semantics, with bounded compatibility fallback only inside the shared helper.
3. Generated nested compatibility resolution remains behaviorally identical for current topology-bearing and legacy-fallback governance inputs.
4. Focused tests lock the new owner boundary and full regression remains green.
