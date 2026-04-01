# Runtime-Core / Skill-Catalog Follow-up Fixes Plan

Date: 2026-04-01
Runtime: `vibe`
Status: `active`
Topic: `runtime-core-skill-catalog-followup-fixes`

## Internal Grade

`M`

The work is narrow, single-repo, and isolated to packaging/gate consumers plus
targeted tests.

## Steps

1. Remove catalog manifests from runtime payload and runtime freshness markers
   in `config/version-governance.json`.
2. Route catalog packaging resolution through
   `config/runtime-core-packaging.json.catalog_packaging_manifest` in:
   - `scripts/install/install_vgo_adapter.py`
   - `scripts/install/Install-VgoAdapter.ps1`
   - `scripts/verify/vibe-skill-catalog-profile-gate.ps1`
3. Add regression tests for:
   - runtime truth no longer including catalog manifests
   - manifest indirection being honored by runtime consumers
4. Run focused proof commands and stop if any regression appears outside the
   declared scope.

## Verification

- `git diff --check`
- `python3 -m pytest -q tests/runtime_neutral/test_bundled_runtime_mirror.py tests/runtime_neutral/test_install_profile_differentiation.py tests/runtime_neutral/test_python_validation_contract.py`
- `python3 -m pytest -q tests/runtime_neutral/test_installed_runtime_scripts.py`

## Completion Rule

Do not claim the fixes are complete unless both boundary regressions are covered
by tests and the proof commands pass.
