# CUDA Kernel Overlay Integration (LeetCUDA x VCO)

## Purpose

Integrate `xlite-dev/LeetCUDA` as a **post-route CUDA optimization advisory overlay** without creating a second router or replacing existing pack selection.

This overlay focuses on CUDA/GPU kernel optimization quality for `coding/debug/research`:
- CUDA optimization intent signals (PTX, WMMA/MMA, tensor core, occupancy, shared memory, bank conflict)
- kernel-level coverage dimensions (target hotspot, memory hierarchy, profiling evidence, correctness guard, fallback strategy)
- mode-gated confirmation advice when optimization evidence/completeness is weak

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the only control plane.
2. **Advice-only rollout**: no mutation of `selected.pack_id` or `selected.skill`.
3. **Domain boundary**:
   - `data-ml` handles model/pipeline tasks.
   - `code-quality` handles general quality/debug.
   - CUDA overlay only adds kernel-level optimization governance.
4. **No runtime hard dependency**: methodology-first overlay; no required external binary.
5. **Route invariance first**: strict mode escalates advice metadata (`confirm_required`) and preserves route assignment.

## License Boundary

`LeetCUDA` upstream is GPL-3.0. VCO integration is methodology-level advisory only:
- no upstream source vendoring
- no direct code copy from upstream into this repository
- keep attribution in `THIRD_PARTY_LICENSES.md`

## Config

Primary policy:
- `config/cuda-kernel-overlay.json`

Bundled mirror:
- `bundled/skills/vibe/config/cuda-kernel-overlay.json`

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `positive_keywords`, `negative_keywords`
- `file_signals`, `environment_signals`
- `optimization_dimensions`
- `thresholds`, `strict_confirm_scope`
- `artifact_contract`, `recommendations_by_dimension`

## Runtime Behavior

Router:
- `scripts/router/resolve-pack-route.ps1`

New output:
- `cuda_kernel_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: advisory + `confirm_recommended` on stronger CUDA-risk signals.
- `strict`: in strict scope, weak optimization evidence can be escalated to `confirm_required`.
- `off`: overlay disabled.

Current rollout remains **advice-first** and does not alter pack/skill assignment.

## Trigger Strategy

Signal score combines:
1. CUDA optimization keyword intent (`positive_keywords`)
2. optimization-dimension coverage score (`optimization_dimensions`)
3. file/environment context signal (`file_signals`, `environment_signals`)
4. suppress penalty (`negative_keywords`)

Goal: trigger reliably for real CUDA kernel optimization work while suppressing interview/noise prompts.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-cuda-kernel-overlay-gate.ps1
```

Run config parity gate:

```powershell
pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1
```

Run routing stability gate:

```powershell
pwsh -File .\scripts\verify\vibe-routing-stability-gate.ps1 -Strict
```

## Failure Semantics

- missing policy -> bypass overlay advice
- outside scope -> no enforcement, keep routing unchanged
- low CUDA signal -> advisory metadata only
- overlay parsing/runtime errors -> continue core VCO route path
