# No-Regression Proof Standard (Task 6 / Replay Harness)

> Status baseline: 2026-03-13  
> Scope: Task 6 of `docs/plans/2026-03-13-universal-vibeskills-execution-program.md`

This document defines the **minimum, conservative, replay-based proof standard** used by
the Task 6 harness to support a bounded claim:

- We can automatically detect regressions in **routing**, **provider-missing degrade**, **install isolation**, and **platform support statements**.
- We do **not** overclaim cross-host parity or multi-OS execution parity beyond current evidence.

## Non-Negotiable Rule

The replay harness must remain **additive by default** and must not require changing the official runtime
main chain to pass unless the change is explicitly admitted by the file-scoped policy at
`config/official-runtime-main-chain-policy.json`.

Protected main-chain surfaces remain:

- `scripts/router/**`
- `scripts/bootstrap/**`
- `install.ps1` / `check.ps1`
- `install.sh` / `check.sh`
- `config/version-governance.json`

If the proof can only pass by changing those surfaces without an active, plan-backed, file-scoped
exception window, the proof is invalid.

If an exception window is used, it must:

- name the exact files allowed to change;
- point to the governing migration plan;
- keep the default mode frozen for every other protected path; and
- require fresh verification evidence for the exception batch.

## What This Harness Proves (Bounded)

### Route replay (offline baseline)

Proves: the router still selects the **same pack/skill** for a small set of high-signal prompts.

Fixture:
- `tests/replay/route/official-runtime-golden.json`

Gate:
- `scripts/verify/vibe-cross-host-route-parity-gate.ps1`

### Provider missing degrade (explicit abstention)

Proves: when a provider secret is missing, the relevant helper returns an **explicit abstained**
result with a reason code (no silent behavior changes and no network call required for the missing-secret path).

Fixture:
- `tests/replay/degrade/provider-missing.json`

Gate:
- `scripts/verify/vibe-cross-host-degrade-contract-gate.ps1`

### Install isolation (no repo-root pollution markers)

Proves: the harness does not create common "pollution markers" (for example `node_modules/`, `.venv/`) in the repo root,
and validates that runtime state is written under `outputs/`.

Fixture:
- `tests/replay/install/host-isolation.json`

Gate:
- `scripts/verify/vibe-cross-host-install-isolation-gate.ps1`

### Platform replay (contract-only, no overclaim)

Proves: the repo includes explicit platform support statements (keywords) so docs cannot drift into overclaim.
This does **not** prove that Linux/macOS behavior equals Windows.

Fixture:
- `tests/replay/platform/windows-vs-linux.json`

Validated by:
- `scripts/verify/vibe-universalization-no-regression-gate.ps1`

## How To Run (Task 6 Canonical)

From the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-route-parity-gate.ps1 -WriteArtifacts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-degrade-contract-gate.ps1 -WriteArtifacts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-install-isolation-gate.ps1 -WriteArtifacts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-universalization-no-regression-gate.ps1 -WriteArtifacts
```

Artifacts are written under `outputs/verify/` when `-WriteArtifacts` is provided.
