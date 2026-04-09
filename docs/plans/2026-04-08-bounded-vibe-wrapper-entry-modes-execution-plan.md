# Bounded Vibe Wrapper Entry Modes Execution Plan

## Goal
Align wrapper behavior, runtime stop targets, packaging truth, and Codex validation so the `vibe` wrapper family behaves like bounded canonical entry modes.

## Implementation Strategy
Use the existing discoverable-entry stop-target mechanism instead of inventing a second runtime path.

This change is ordered to reduce drift:

1. lock contract truth in docs and tests
2. fix entry-surface and runtime-facing wording
3. fix Codex validation and uninstall truth
4. run focused then broader regression verification

## Step 1: Lock Stop-Target Contract
Files:

- `config/vibe-entry-surfaces.json`
- `tests/contract/test_vibe_discoverable_entry_contract.py`
- `tests/integration/test_runtime_packet_execution.py`
- `docs/quick-start.md`
- `SKILL.md`
- `core/skills/vibe/instruction.md`

Actions:

- change `vibe-want` stop target from `deep_interview` to `requirement_doc`
- keep `vibe-how` at `xl_plan`
- keep `vibe-do` at `phase_cleanup`
- update docs and tests so shortcut semantics are stop targets, not freeform hints

Verification:

```bash
python3 -m pytest \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/integration/test_runtime_packet_execution.py -q
```

## Step 2: Make Wrapper Skills And Command Shims Honest
Files:

- `bundled/skills/vibe-what-do-i-want/SKILL.md`
- `bundled/skills/vibe-how-do-we-do/SKILL.md`
- `bundled/skills/vibe-do-it/SKILL.md`
- `commands/vibe-what-do-i-want.md`
- `commands/vibe-how-do-we-do.md`
- `commands/vibe-do-it.md`

Actions:

- replace "bias only" wording with bounded-stage wording
- explicitly state the stop boundary for each wrapper
- explicitly forbid continuing to later stages unless the user re-enters an appropriate wrapper or canonical `vibe`
- preserve canonical `vibe` as the only runtime authority

Verification:

```bash
python3 -m pytest \
  tests/integration/test_dist_manifest_surface_roles.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q -k 'vibe or codex'
```

## Step 3: Fix Codex Validation And Packaging Truth
Files:

- `check.sh`
- `check.ps1`
- `config/runtime-core-packaging.json`
- `config/runtime-core-packaging.full.json`
- `tests/integration/test_runtime_core_packaging_roles.py`
- `tests/unit/test_runtime_packaging_resolver.py`
- `tests/runtime_neutral/test_install_profile_differentiation.py`

Actions:

- make Codex wrapper skill checks validate only the public `skills/<wrapper>/SKILL.md` roots
- keep command shim checks optional
- repair the aggregated full-profile `payload_roles.delivery_model.compatibility_skill_projections`
- add ledger assertions for `compatibility_roots`

Verification:

```bash
python3 -m pytest \
  tests/integration/test_runtime_core_packaging_roles.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py -q
```

## Step 4: Fix Codex Uninstall Truth
Files:

- `packages/installer-core/src/vgo_installer/uninstall_service.py`
- `tests/runtime_neutral/test_uninstall_vgo_adapter.py`

Actions:

- remove stale colon-named wrapper command inventory
- if Codex fallback inventory tracks command shims, use the actual hyphenated filenames only
- strengthen the uninstall test to assert real filesystem deletion

Verification:

```bash
python3 -m pytest \
  tests/runtime_neutral/test_uninstall_vgo_adapter.py -q
```

## Step 5: Full Verification
Run:

```bash
python3 -m pytest \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/integration/test_runtime_packet_execution.py \
  tests/integration/test_runtime_core_packaging_roles.py \
  tests/integration/test_dist_manifest_surface_roles.py \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py \
  tests/runtime_neutral/test_offline_skills_gate.py \
  tests/runtime_neutral/test_uninstall_vgo_adapter.py \
  tests/unit/test_runtime_packaging_resolver.py -q
```

Then run a real Codex full-profile smoke install/check into a temp root:

```bash
CODEX_HOME="$(mktemp -d)/.codex" bash ./install.sh --host codex --profile full
bash ./check.sh --host codex --profile full --target-root "$CODEX_HOME"
```

## Completion Rule
Do not update the PR as ready until:

- stop-target semantics are consistent across wrapper docs, runtime config, and quick-start docs
- Codex public-wrapper verification cannot be satisfied by hidden bundled copies
- packaging truth is internally consistent
- uninstall fallback truth is corrected
- fresh verification evidence is recorded in this session
