# Runtime-Core / Skill-Catalog Split Plan

Date: 2026-04-01
Runtime: `vibe`
Status: `implemented`
Topic: `runtime-core-skill-catalog-split`

## Goal

Split the repository packaging model into two same-repo release units:

- `runtime-core`
- `skill-catalog`

The split must reduce runtime payload coupling without breaking existing public
install and check entrypoints for `minimal` and `full`.

## Why This Plan Is Required

This change crosses:

- `Z0 Frozen Control Plane`
  - `check.sh`
  - `check.ps1`
  - install/uninstall entry logic
- `Z1 Guarded Governance and Policy`
  - `config/runtime-core-packaging*.json`
  - `config/skill-catalog-*.json`
  - `config/version-governance.json`
- `Z3 Preferred Contribution Zones`
  - `scripts/verify/vibe-skill-catalog-profile-gate.ps1`
  - test coverage updates

Per [developer-change-governance.md](../developer-change-governance.md),
runtime-affecting packaging and install changes require an attached plan and a
proof bundle.

## Frozen Requirement

Keep one git repository, but stop treating the full bundled skill tree as part
of the runtime-core payload contract.

The public profiles remain stable:

- `minimal` => `runtime-core` + `foundation-workflow`
- `full` => `runtime-core` + `default-full`

## Implementation Shape

### 1. Packaging split

- `config/runtime-core-packaging.json` remains the runtime entry manifest
- `config/runtime-core-packaging.minimal.json` and
  `config/runtime-core-packaging.full.json` now declare runtime and catalog
  profile composition instead of copying `bundled/skills`
- `config/skill-catalog-packaging.json`,
  `config/skill-catalog-profiles.json`, and
  `config/skill-catalog-groups.json` define catalog ownership separately

### 2. Installer split

`scripts/install/install_vgo_adapter.py` and
`scripts/install/Install-VgoAdapter.ps1` resolve installation in two phases:

1. install `runtime-core`
2. install the selected catalog profile

The install ledger must dual-write:

- `managed_runtime_units`
- `managed_runtime_skill_names`
- `managed_catalog_profiles`
- `managed_catalog_skill_names`

Legacy `managed_skill_names` remains as a derived compatibility field.

### 3. Compatibility boundary tightening

Nested generated compatibility under `skills/vibe/bundled/skills/**` mirrors
runtime-core-managed skills only. It must not mirror the full catalog by
default.

### 4. Verification split

Catalog profile validation is enforced separately from runtime freshness and
runtime coherence through:

- `scripts/verify/vibe-skill-catalog-profile-gate.ps1`
- `check.sh`
- `check.ps1`
- `.github/workflows/vco-gates.yml`

### 5. Uninstall safety

Uninstall must respect the dual-unit install ledger and must not delete shared
non-skill directories wholesale when replaying managed paths.

## Acceptance Criteria

- `runtime-core` no longer copies `bundled/skills` wholesale
- `skill-catalog` owns catalog manifests and profile selection
- `minimal` still installs only runtime-core plus foundation workflow skills
- `full` still installs runtime-core plus the broader catalog profile
- nested compatibility mirrors only runtime-core-managed skills
- local and CI checks run the catalog gate separately from runtime gates
- install and uninstall tests pass for both public profiles

## Proof Bundle

The change is accepted only with the following proof:

| Command | Expected result |
| --- | --- |
| `git diff --check` | no output |
| `python3 -m pytest -q tests/runtime_neutral/test_bundled_runtime_mirror.py tests/runtime_neutral/test_install_profile_differentiation.py tests/runtime_neutral/test_python_validation_contract.py tests/runtime_neutral/test_generated_nested_bundled.py` | pass |
| `python3 -m pytest -q tests/runtime_neutral/test_installed_runtime_scripts.py` | pass |
| `python3 -m pytest -q tests/runtime_neutral/test_installed_runtime_uninstall.py tests/runtime_neutral/test_uninstall_vgo_adapter.py` | pass |

## Delivery Note

Implementation and proof for this plan are complete in the same change set. This
document exists to satisfy the in-repo plan requirement for a runtime-affecting
packaging split and to provide a PR-linkable governance artifact.
