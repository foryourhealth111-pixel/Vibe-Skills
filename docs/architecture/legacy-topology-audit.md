# Legacy Topology Audit

## Status Summary

The repository is no longer treating legacy Python runtime-neutral entrypoints, release operators, or verification wrappers as semantic owners.
The active sign-off surface for that claim is now `docs/proof/2026-04-04-owner-consumer-consistency-proof.md`.
The remaining architecture question is no longer whether shared owners exist, but whether bounded fallbacks and retained compatibility surfaces are documented honestly enough for final closure language.

## Current Cutover Progress

Task 8 and Task 9 are effectively cut over. Catalog export, installer consumption, and distribution assembly now route through package-owned cores.

This phase also removed legacy installer shim paths from release-lane proof metadata for:

- `dist/host-claude-code/manifest.json`
- `dist/host-windsurf/manifest.json`
- `dist/host-openclaw/manifest.json`
- `adapters/claude-code/host-profile.json`

Those surfaces now point at `apps/vgo-cli` and `packages/installer-core` as the authoritative installer evidence.

The runtime-neutral generated nested install fixture now also enters through `vgo_cli.main install` instead of the legacy Python installer shim. Preview/runtime-core runtime-neutral callers for Claude Code, Cursor, OpenCode, Windsurf, and OpenClaw now also enter through package-owned installer cores instead of the legacy Python installer shim. `check` entrypoints, bootstrap entrypoints, the adapter-closure verification gate, and the retained PowerShell installer compatibility surface now all resolve adapter metadata directly from adapter-registry configuration instead of routing through resolver shims. That means the remaining direct shim dependencies are concentrated in explicit compatibility-contract tests, router compatibility payloads, installed-runtime mirrors that intentionally ship the retained shim files, and historical documentation. Runtime script packaging also no longer projects `scripts/common` as a broad installed-runtime directory. The runtime payload now ships only the explicitly required common support files, currently `scripts/common/vibe-governance-helpers.ps1` and `scripts/common/AntiProxyGoalDrift.ps1`, while keeping package-owned cores and compatibility shims as the semantic authorities. Install and uninstall compatibility surfaces now follow the same pattern: the runtime payload projects only the retained PowerShell shim files explicitly instead of shipping the whole `scripts/install` and `scripts/uninstall` directories, while the Python shim entrypoints remain repo-level compatibility files rather than installed-runtime payload surfaces. Governed runtime script support, router module support, OpenCode runtime-config support, and router/verification runtime-neutral compatibility surfaces now all follow explicit file projection, so the runtime payload no longer carries the `scripts/runtime`, `scripts/router/modules`, `config/opencode`, `scripts/router/runtime_neutral`, or `scripts/verify/runtime_neutral` directories as broad compatibility roots. Installer materialization now also applies the shared runtime-artifact ignore policy during directory copies, so local `__pycache__`, `.pyc`, `.coverage`, and similar generated noise no longer leak into installed runtime payloads. The CLI install support path also no longer depends on the `vgo_installer` package root aggregator; it imports the precise installer-core ledger module it needs. Installer-core also no longer repeats contracts path bootstrap logic inline across multiple modules; that responsibility is now centralized in a local bootstrap helper. Verification-core and skill-catalog now follow the same package-owned rule for contracts bootstrap, so their remaining contracts imports no longer depend on ad hoc inline `sys.path` setup inside semantic modules. Verification-core also now shares one package-owned repo-root resolver across policies and support modules instead of repeating the same path-walk logic in each verifier surface. The same package now also centralizes shared verification IO helpers (`utc_now`, `write_text`, `load_json`) instead of redefining them in each support module. Installer-core now follows the same package-owned rule for JSON IO (`load_json`, `write_json`, `write_json_file`) instead of redefining those helpers across install, uninstall, registry, ledger, and packaging modules. Runtime-core now also shares one repo-root resolver between `router_bridge.py` and `router_contract_support.py` instead of keeping a second local path-walk implementation in the bridge entrypoint. The same runtime-core support layer now also owns router config bundle loading, so `router_contract_runtime.py` no longer hardcodes the router configuration file topology inline. The remaining broad `vgo_installer` package-root import has also been eliminated from test surfaces, so current installer-core consumption now uses explicit module boundaries rather than package-root aggregation. VGO CLI now follows the same boundary rule for repo/config infrastructure: install support delegates governance loading, installed-runtime config merging, and canonical repo-root resolution to a dedicated `vgo_cli.repo` helper instead of owning those base concerns inline. The same CLI layer now also separates external provisioning concerns into `vgo_cli.external`, so install postcondition logic no longer owns npm/pip/manual plugin provisioning behavior. Command orchestration also now delegates CLI output parsing, install banner rendering, and install completion messaging to `vgo_cli.output`, so the commands layer no longer owns presentation helpers inline and install postcondition support no longer owns banner rendering. The same commands layer now also delegates workspace package-path extension and dynamic installer/runtime core loading to `vgo_cli.core_bridge`, so command handlers no longer own package bootstrap or core entrypoint imports inline. The installed-runtime governance marker set now also tracks the split CLI owner modules (`repo`, `external`, `output`, `install_gates`, `installer_bridge`, `skill_surface`, `core_bridge`) and the shipped governed runtime stage/support scripts (`Invoke-SkeletonCheck`, `Invoke-DeepInterview`, `Write-RequirementDoc`, `Write-XlPlan`, `Invoke-AntiProxyGoalDriftCompaction`, `Invoke-DelegatedLaneUnit`, `Invoke-PhaseCleanup`, `VibeExecution.Common`, `VibeMemoryActivation.Common`), so runtime ownership evidence no longer reflects either the pre-split CLI topology or an under-tracked runtime payload surface. Install postcondition support now also delegates installer-core ledger refresh bridging to `vgo_cli.installer_bridge` and JSON payload rendering to `vgo_cli.output`, so it no longer owns dynamic installer import wiring or ledger payload formatting inline. The same layer now also delegates duplicate Codex skill-surface detection and quarantine to `vgo_cli.skill_surface`, so postcondition orchestration no longer owns host-surface hygiene helpers inline. Gate execution now also lives in `vgo_cli.install_gates`, so install postcondition orchestration no longer owns offline/freshness gate runner implementations inline. The retained runtime-neutral verification Python shims now also share one local `_bootstrap` helper for verification-core path setup, so compatibility entrypoints no longer repeat inline sys.path bootstrap boilerplate across every verification surface. That helper is now also projected explicitly through the runtime script manifest as a compatibility verification support file, so installed payloads do not depend on an implicit sibling-file assumption. The runtime config manifest now mirrors the same explicit-projection discipline through exclusive role-group buckets, so governance review can tighten config ownership boundaries without widening the installed payload surface or reintroducing broad `config/opencode` directory projection.

### 2026-04-04 Closure Additions

The current remaining-architecture-closure track tightened several owner boundaries beyond the earlier shim-retirement wave:

- release closure gates now consume `config/operator-preview-contract.json` instead of scraping `scripts/governance/release-cut.ps1` text for gate membership
- installer-core and verification-core now share one contract-owned mirror-topology helper instead of owning duplicate topology logic inline
- CLI runtime entrypoints, verification runtime entrypoints, and frontmatter/runtime guards now consume shared runtime-contract owners instead of parallel local defaults
- PowerShell installed-runtime helpers and release/postcheck paths still retain bounded fallbacks, but those fallbacks are now explicitly compatibility paths rather than primary semantic owners

Fresh verification evidence for the latest completed cut in this track is:

- focused verification: `5 passed in 2.09s`
- full regression: `403 passed, 66 subtests passed in 509.44s (0:08:29)`
- hygiene: `git diff --check` clean

The live status-spine catch-up for `roadmap`, `operator-dry-run`, `plans/README`, and `path-dependency-census` has now also landed. Final owner -> consumer sign-off, residual-boundary language, and live closure reporting are now aligned; any further work belongs to post-closure backlog rather than the completed root plan.


## 1. Compatibility Shims To Keep

These files remain valid only because they preserve public or test-visible compatibility surfaces while delegating into package-owned cores.
They are not deletion candidates until their remaining callers or compatibility assertions are intentionally retired.

- `scripts/install/install_vgo_adapter.py`
- `scripts/uninstall/uninstall_vgo_adapter.py`
- `scripts/router/invoke-pack-route.py`
- `scripts/router/runtime_neutral/router_contract.py`
- `scripts/router/runtime_neutral/custom_admission.py`
- `scripts/verify/runtime_neutral/bootstrap_doctor.py`
- `scripts/verify/runtime_neutral/release_notes_quality.py`
- `scripts/verify/runtime_neutral/runtime_delivery_acceptance.py`
- `scripts/verify/runtime_neutral/router_ai_connectivity_probe.py`
- `scripts/verify/runtime_neutral/router_bridge_gate.py`
- `scripts/verify/runtime_neutral/opencode_preview_smoke.py`

### Evidence

These paths are still referenced by one or more of:

- compatibility and integration tests
- packaging manifests and installed runtime payloads
- PowerShell gates and shell checks
- adapter platform contracts and replay fixtures
- operator-facing install and verification documentation

## 2. Legacy Router Retirement

`resolve-pack-route.legacy.ps1` has been removed from the working tree.
The active router contract gate now relies on `tests/replay/route/router-contract-gate-golden.json` as its frozen baseline.

### Remaining References

Remaining mentions of the retired file are historical only:

- release and planning history documents
- changelog and technical debt review records

Those references are retained as evidence of the migration path, not as active runtime dependencies.

## 3. Public Wrapper Outcome Already Completed

Top-level install and uninstall wrappers now depend on `vgo_cli.main` rather than directly calling legacy installer or uninstaller Python scripts. Shell and PowerShell `check` entrypoints also resolve host metadata from adapter-registry configuration directly instead of routing through resolver shims. Shell and PowerShell bootstrap entrypoints now follow the same rule for adapter bootstrap metadata, and the retained PowerShell installer compatibility shim now follows it for install-mode routing as well. This is the current architectural cut line for wrapper decoupling.

- `install.sh`
- `uninstall.sh`
- `install.ps1`
- `uninstall.ps1`
- `check.sh`
- `check.ps1`
- `scripts/bootstrap/one-shot-setup.sh`
- `scripts/bootstrap/one-shot-setup.ps1`

### Guard Rails

This contract is protected by:

- `tests/integration/test_shell_wrapper_contract.py`
- `tests/integration/test_pwsh_wrapper_contract.py`
- `tests/integration/test_check_entrypoint_registry_cutover.py`
- `tests/integration/test_bootstrap_entrypoint_registry_cutover.py`
- `tests/integration/test_powershell_installer_registry_cutover.py`
- `tests/runtime_neutral/test_shell_entrypoint_compatibility.py`
- `tests/runtime_neutral/test_install_generated_nested_bundled.py`
- `tests/runtime_neutral/test_claude_preview_scaffold.py`
- `tests/runtime_neutral/test_cursor_managed_preview.py`
- `tests/runtime_neutral/test_opencode_managed_preview.py`
- `tests/runtime_neutral/test_windsurf_runtime_core.py`
- `tests/runtime_neutral/test_openclaw_runtime_core.py`
- `tests/runtime_neutral/test_installed_runtime_scripts.py`

## 4. Generated Noise Safe To Remove

The following are generated artifacts and should never be treated as refactor work:

- `__pycache__/`
- `*.pyc`

These were removed from the working tree during this phase.

## Next Migration Boundary

The root 2026-04-04 architecture-closure sign-off is complete. The next migration boundary is therefore post-closure backlog, not unfinished root-plan work:

- keep the final owner -> consumer proof authoritative via `docs/proof/2026-04-04-owner-consumer-consistency-proof.md` as later changes land
- keep bounded fallback inventory explicit, especially for release gates, release postchecks, installed-runtime emergency defaults, mirror-topology compatibility inputs, and cleanup-mode compatibility behavior
- open follow-up work only through new requirement/plan pairs for outputs strict-mode, third-party root parameterization, archive/prune windows, or narrowly proven shim retirement

The retained compatibility shims remain governed delegates, not deletion candidates, while manifests, tests, installed payloads, or user-facing wrappers still rely on them. Post-closure changes should reuse the proof surface and live status pages as guardrails, not reopen this completed root plan.
