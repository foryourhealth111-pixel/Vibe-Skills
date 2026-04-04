# Python Clean Code Overlay Integration (clean-code-python x VCO)

## Purpose

Integrate `zedr/clean-code-python` principles into VCO as a **post-route advisory overlay**, without introducing a second router or replacing existing quality tooling.

This overlay focuses on Python-specific maintainability signals:
- Python file intent detection (`.py` / `.pyi`)
- Clean-code principle groups (naming, function/class design, side effects, duplication, error handling, tests)
- Anti-pattern detection and mode-gated confirmation advice

## Non-Redundancy Boundaries

1. **Single routing authority**: pack router remains the control plane.
2. **Advice-only rollout**: overlay does not mutate `selected.pack_id` or `selected.skill`.
3. **Python specialization only**:
   - `quality-debt-overlay` remains cross-language debt advisory.
   - `python-clean-code-overlay` adds Python-focused refactor guidance.
4. **No external hard dependency**: no required analyzer binary.
5. **Route invariance first**: strict mode may require confirmation in advice, but does not rewrite route assignment.

## Config

Primary policy:
- `config/python-clean-code-overlay.json`

Legacy compatibility note:
- tracked repo bundled config copies are retired
- `config/python-clean-code-overlay.json` is the only repo-tracked source of truth

Key fields:
- `enabled`, `mode` (`off|shadow|soft|strict`)
- `task_allow`, `grade_allow`
- `monitor.pack_allow`, `monitor.skill_allow`
- `path_probe` (extract `.py/.pyi` from prompt, optional workspace fallback)
- `language_keywords`
- `principle_groups`
- `anti_pattern_keywords`, `suppress_keywords`
- `thresholds`, `strict_confirm_scope`
- `recommendations_by_group`

## Runtime Behavior

Router:
- `scripts/router/resolve-pack-route.ps1`

New output:
- `python_clean_code_advice`

Semantics:
- `shadow`: advisory only.
- `soft`: advisory, may set `confirm_recommended`.
- `strict`: in strict scope and with high anti-pattern evidence, advice escalates to `confirm_required`.
- `off`: overlay disabled.

Current rollout remains **advice-first** and preserves route assignment.

## Auto-Trigger Strategy

Trigger score combines:
1. Python file signal (`.py` / `.pyi` path hits)
2. Python language/stack signal (`python`, `pytest`, `dataclass`, etc.)
3. Principle and anti-pattern semantics
4. Suppress signal penalty (`generated`, `migration`, `vendor`, etc.)

Goal: trigger automatically for Python file writing/editing while reducing false positives in non-Python tasks.

## Verification

Run dedicated gate:

```powershell
pwsh -File .\scripts\verify\vibe-python-clean-code-overlay-gate.ps1
```

Run legacy-named packaging gate:

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
- non-Python signal -> advisory metadata only, no activation
- overlay errors -> continue core VCO route path
