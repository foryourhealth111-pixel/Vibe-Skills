# Runtime-Neutral Verification Core

## Purpose

This directory contains the portable verification core used to reduce PowerShell-only authority assumptions in the official runtime.

It exists to support truthful cross-platform progress without weakening the Windows reference lane.

## Components

| File | Responsibility |
| --- | --- |
| `freshness_gate.py` | installed runtime freshness decision logic |
| `coherence_gate.py` | release / install / runtime coherence decision logic |
| `bootstrap_doctor.py` | bootstrap doctor / deep-check portability layer |
| `workflow_acceptance_runner.py` | downstream project-delivery acceptance decision logic |
| `runtime_delivery_acceptance.py` | main-chain per-run delivery truth evaluator for governed `vibe` sessions |
| `release_truth_gate.py` | aggregates workflow acceptance reports into release/completion truth |

## Design Rules

1. These modules own decision semantics, not shell UX.
2. Shell and PowerShell wrappers may call into them, but must not fork the core pass/fail meaning.
3. Receipt fields must remain stable or evolve as explicit supersets with contract review.
4. A runtime-neutral success must never hide a degraded state that should still be surfaced to operators.

## Current Wrapper Usage

The current migration batch uses these modules from:

- `install.sh`
- `check.sh`

Windows PowerShell remains the baseline authority lane during the migration.

## Verification

Run the direct Python checks:

```powershell
python tests/runtime_neutral/test_freshness_gate.py
python tests/runtime_neutral/test_bootstrap_doctor.py
python tests/runtime_neutral/test_coherence_gate.py
python tests/runtime_neutral/test_workflow_acceptance_runner.py
python tests/runtime_neutral/test_runtime_delivery_acceptance.py
python tests/runtime_neutral/test_release_truth_gate.py
```

Run the shell wrapper syntax checks:

```powershell
bash -n install.sh
bash -n check.sh
```

Run the governance gates:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-cross-host-install-isolation-gate.ps1 -WriteArtifacts
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-universalization-no-regression-gate.ps1 -WriteArtifacts
```

## Non-Goal

This directory does not itself promote Linux to `full-authoritative`.
It only provides the portable core needed for that promotion to become technically possible.
