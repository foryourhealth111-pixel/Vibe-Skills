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

This aggregate command includes the governed runtime contract proof gate in its subgate closure.

Artifacts are written to `outputs/verify/` when `-WriteArtifacts` is provided.

## Fixtures (Batch C Minimum Set)

- `tests/replay/fixtures/host-capability-matrix.json` (host/platform truth + no-overclaim lanes)
- `tests/replay/fixtures/provider-state-matrix.json` (provider-state truth + offline degrade contract)

## Additional Retained Fixtures

- `tests/replay/platform/linux-without-pwsh.json` (runtime-neutral router-bridge fixture for Linux without PowerShell degradation handling)
- `tests/replay/route/recovery-wave-curated-prompts.json` (curated prompt pack consumed by router-bridge runtime tests)
- `tests/replay/promotion/claude-code-managed-closure.json` (proof-bundle-backed promotion candidate)

## OpenClaw Runtime-Core-Preview Fixtures

- `tests/replay/route/openclaw-runtime-core-preview.json` (route truth for OpenClaw preview lane; no full-closure claim)
- `tests/replay/degrade/openclaw-runtime-core-preview.json` (explicit degrade and host-managed abstain semantics)
- `tests/replay/install/openclaw-runtime-core-preview-isolation.json` (install isolation boundary for runtime-core-preview)
- `tests/replay/promotion/openclaw-runtime-core-preview.json` (promotion ceiling guardrail: stay `preview` until evidence is complete)

## Governed Runtime Contract Proof

Tracked runtime replay goldens are no longer part of the retained minimum set.
Current governed-runtime proof is generated fresh by `scripts/verify/vibe-governed-runtime-contract-gate.ps1`.
