# Replay Harness (No-Regression Proof)

This directory contains **machine-readable replay fixtures** used to prove that
the repository's universalization work did **not** regress the current official
runtime behavior.

The fixtures here are intentionally conservative and are designed to:

- Run offline (no network, no provider credentials required).
- Avoid overclaiming cross-host parity that is not backed by evidence.
- Provide a minimal "proof chain" that can be executed by verify gates.

See: `docs/universalization/no-regression-proof-standard.md`

## Canonical Run Command (Batch C)

From the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-universalization-no-regression-gate.ps1 -WriteArtifacts
```

Artifacts are written to `outputs/verify/` when `-WriteArtifacts` is provided.

## Fixtures (Batch C Minimum Set)

- `tests/replay/fixtures/host-capability-matrix.json` (host/platform truth + no-overclaim lanes)
- `tests/replay/fixtures/provider-state-matrix.json` (provider-state truth + offline degrade contract)

## OpenClaw Runtime-Core-Preview Fixtures

- `tests/replay/route/openclaw-runtime-core-preview.json` (route truth for OpenClaw preview lane; no full-closure claim)
- `tests/replay/degrade/openclaw-runtime-core-preview.json` (explicit degrade and host-managed abstain semantics)
- `tests/replay/install/openclaw-runtime-core-preview-isolation.json` (install isolation boundary for runtime-core-preview)
- `tests/replay/promotion/openclaw-runtime-core-preview.json` (promotion ceiling guardrail: stay `preview` until evidence is complete)

## Governed Runtime Contract Fixtures

- `tests/replay/runtime/governed-runtime-contract-golden.json` (canonical field/key contract surface for governed runtime replay)
- `tests/replay/runtime/runtime-contract-golden.json` (curated normalized case baseline for governed runtime replay)
