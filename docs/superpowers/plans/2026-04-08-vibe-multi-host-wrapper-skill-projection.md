# Vibe Multi-Host Wrapper Skill Projection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize `vibe`, `vibe-want`, `vibe-how`, and `vibe-do` as host-visible wrapper entries across supported hosts while preserving one canonical governed runtime authority: `vibe`.

**Architecture:** Keep `config/vibe-entry-surfaces.json` as the single discoverable-entry truth, route all wrapper selections back into canonical `vibe`, and add a shared projection/materialization layer that packaging, installer-core, host adapters, install/check reporting, and docs all consume consistently. Public wrapper visibility must be verified as a host-visible outcome, not inferred from docs, sidecars, or runtime payload presence.

**Tech Stack:** Python installer-core, Python runtime-core, contracts package, shell and PowerShell wrappers, pytest, JSON packaging manifests, host adapter metadata

---

**Spec:** `docs/superpowers/specs/2026-04-08-vibe-multi-host-wrapper-skill-projection-design.md`

## File Structure

### Shared contract and packaging
- Modify: `config/runtime-core-packaging.json`
  Responsibility: make base packaging declare discoverable wrapper public-surface semantics.
- Modify: `config/runtime-core-packaging.full.json`
  Responsibility: full profile must publicly project all discoverable wrappers while keeping bundled specialist corpus internal.
- Modify: `config/runtime-core-packaging.minimal.json`
  Responsibility: minimal profile must publicly project the same wrapper entries without widening internal skill scope.
- Create: `packages/contracts/src/vgo_contracts/discoverable_entry_surface.py`
  Responsibility: load and validate `config/vibe-entry-surfaces.json` once for cross-package reuse.
- Modify: `packages/installer-core/src/vgo_installer/runtime_packaging.py`
  Responsibility: resolve wrapper-aware public-surface projections from shared contract.
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_support.py`
  Responsibility: expose wrapper-aware public-surface metadata to runtime descriptor resolution.

### Installer materialization and ledger
- Create: `packages/installer-core/src/vgo_installer/discoverable_wrappers.py`
  Responsibility: render host-visible wrapper descriptors from shared discoverable-entry metadata.
- Modify: `packages/installer-core/src/vgo_installer/materializer.py`
  Responsibility: delegate wrapper file creation to the focused wrapper materializer.
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`
  Responsibility: call wrapper materialization during install and record wrapper roots/paths in ledger state.
- Modify: `packages/installer-core/src/vgo_installer/install_plan.py`
  Responsibility: carry wrapper-aware packaging manifest metadata into install ledger generation.
- Modify: `packages/installer-core/src/vgo_installer/ledger_service.py`
  Responsibility: distinguish canonical public skills from host-visible entry surfaces in payload summaries.

### Host adapters and host-visible checks
- Modify: `config/adapter-registry.json`
  Responsibility: declare shared discoverable-entry surface plus projection-mode metadata.
- Modify: `adapters/index.json`
  Responsibility: keep adapter index aligned with registry-level wrapper projection truth.
- Modify: `adapters/codex/host-profile.json`
- Modify: `adapters/claude-code/host-profile.json`
- Modify: `adapters/cursor/host-profile.json`
- Modify: `adapters/windsurf/host-profile.json`
- Modify: `adapters/openclaw/host-profile.json`
- Modify: `adapters/opencode/host-profile.json`
  Responsibility: preserve `presentational_only: true` while adding truthful `host-visible projection` metadata.
- Modify: `check.sh`
  Responsibility: validate host-visible wrapper entry readiness on Linux/macOS shells.
- Modify: `check.ps1`
  Responsibility: validate host-visible wrapper entry readiness on Windows/PowerShell.

### Wrapper source surfaces and docs
- Modify: `commands/vibe.md`
  Responsibility: keep canonical wrapper source stable for generated host command variants.
- Modify: `config/opencode/commands/vibe.md`
  Responsibility: keep OpenCode canonical wrapper source stable for generated host command variants.
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `docs/quick-start.md`
- Modify: `docs/quick-start.en.md`
  Responsibility: describe discoverable wrappers as actual shipped host-visible surfaces, not hypothetical labels.

### Tests
- Modify: `tests/contract/test_vibe_discoverable_entry_contract.py`
- Modify: `tests/contract/test_adapter_descriptor_contract.py`
- Modify: `tests/unit/test_adapter_registry_support.py`
- Modify: `tests/unit/test_runtime_packaging_resolver.py`
- Modify: `tests/unit/test_router_contract_support_descriptor_sources.py`
- Modify: `tests/integration/test_runtime_core_packaging_roles.py`
- Modify: `tests/unit/test_installer_ledger_service.py`
- Modify: `tests/runtime_neutral/test_install_profile_differentiation.py`
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`
- Modify: `tests/runtime_neutral/test_claude_preview_scaffold.py`
- Modify: `tests/runtime_neutral/test_opencode_preview_parity.py`
- Modify: `tests/runtime_neutral/test_windsurf_runtime_core.py`
- Modify: `tests/runtime_neutral/test_openclaw_runtime_core.py`
- Create: `tests/unit/test_discoverable_entry_surface.py`
- Create: `tests/unit/test_discoverable_wrappers.py`
- Create: `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py`

## Chunk 1: Shared Contract And Packaging Resolution

### Task 1: Lock the wrapper-aware public-surface contract in tests

**Files:**
- Modify: `tests/contract/test_vibe_discoverable_entry_contract.py`
- Modify: `tests/unit/test_runtime_packaging_resolver.py`
- Modify: `tests/integration/test_runtime_core_packaging_roles.py`

- [ ] **Step 1: Extend contract tests to require a wrapper-aware public surface**

Add assertions that packaging resolves:

```python
assert full["public_skill_surface"]["mode"] == "discoverable_wrapper_projection"
assert full["public_skill_surface"]["discoverable_entry_surface"] == "config/vibe-entry-surfaces.json"
assert full["public_skill_surface"]["projected_skill_names"] == ["vibe", "vibe-want", "vibe-how", "vibe-do"]
assert minimal["public_skill_surface"]["projected_skill_names"] == ["vibe", "vibe-want", "vibe-how", "vibe-do"]
```

- [ ] **Step 2: Run the packaging tests to verify failure**

Run:

```bash
pytest \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/integration/test_runtime_core_packaging_roles.py -q
```

Expected: FAIL because manifests still expose only `["vibe"]`.

- [ ] **Step 3: Update base and profile packaging manifests**

Edit:
- `config/runtime-core-packaging.json`
- `config/runtime-core-packaging.full.json`
- `config/runtime-core-packaging.minimal.json`

Use a wrapper-aware shape like:

```json
"public_skill_surface": {
  "mode": "discoverable_wrapper_projection",
  "canonical_vibe_target_relpath": "skills/vibe",
  "discoverable_entry_surface": "config/vibe-entry-surfaces.json",
  "projected_skill_names": ["vibe", "vibe-want", "vibe-how", "vibe-do"]
}
```

Keep:
- `compatibility_skill_projections.projected_skill_names == []`
- internal corpus under `skills/vibe/bundled/skills`

- [ ] **Step 4: Re-run the packaging tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  config/runtime-core-packaging.json \
  config/runtime-core-packaging.full.json \
  config/runtime-core-packaging.minimal.json \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/integration/test_runtime_core_packaging_roles.py
git commit -m "feat: project discoverable vibe wrappers in packaging manifests"
```

### Task 2: Centralize discoverable-entry loading so runtime and installer read one truth

**Files:**
- Create: `packages/contracts/src/vgo_contracts/discoverable_entry_surface.py`
- Create: `tests/unit/test_discoverable_entry_surface.py`
- Modify: `packages/installer-core/src/vgo_installer/runtime_packaging.py`
- Modify: `packages/runtime-core/src/vgo_runtime/router_contract_support.py`
- Modify: `tests/unit/test_router_contract_support_descriptor_sources.py`

- [ ] **Step 1: Write failing unit tests for the shared discoverable-entry loader**

Create `tests/unit/test_discoverable_entry_surface.py` with coverage for:

```python
surface = load_discoverable_entry_surface(REPO_ROOT)
assert surface.canonical_runtime_skill == "vibe"
assert surface.projected_skill_names == ["vibe", "vibe-want", "vibe-how", "vibe-do"]
assert surface.grade_flag_map["--xl"] == "XL"
assert surface.entry_by_id["vibe-want"].allow_grade_flags is False
```

Update `tests/unit/test_router_contract_support_descriptor_sources.py` to assert router contract support can read wrapper-aware public surface metadata without falling back to hardcoded `skills` assumptions.

- [ ] **Step 2: Run the loader/resolver tests to verify failure**

Run:

```bash
pytest \
  tests/unit/test_discoverable_entry_surface.py \
  tests/unit/test_router_contract_support_descriptor_sources.py -q
```

Expected: FAIL because the shared loader module does not exist yet.

- [ ] **Step 3: Implement the shared contract helper and use it in resolver code**

Create `packages/contracts/src/vgo_contracts/discoverable_entry_surface.py` with a small typed API such as:

```python
@dataclass(frozen=True)
class DiscoverableEntry:
    id: str
    display_name: str
    requested_stage_stop: str
    allow_grade_flags: bool

def load_discoverable_entry_surface(repo_root: Path) -> DiscoverableEntrySurface: ...
```

Then:
- call it from `packages/installer-core/src/vgo_installer/runtime_packaging.py`
- call it from `packages/runtime-core/src/vgo_runtime/router_contract_support.py`
- remove any duplicated wrapper-name lists from resolver logic

- [ ] **Step 4: Re-run the loader/resolver tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  packages/contracts/src/vgo_contracts/discoverable_entry_surface.py \
  packages/installer-core/src/vgo_installer/runtime_packaging.py \
  packages/runtime-core/src/vgo_runtime/router_contract_support.py \
  tests/unit/test_discoverable_entry_surface.py \
  tests/unit/test_router_contract_support_descriptor_sources.py
git commit -m "refactor: centralize discoverable vibe entry surface loading"
```

## Chunk 2: Wrapper Materialization And Host Projection

### Task 3: Introduce a focused installer helper that renders host-visible wrapper descriptors

**Files:**
- Create: `packages/installer-core/src/vgo_installer/discoverable_wrappers.py`
- Create: `tests/unit/test_discoverable_wrappers.py`
- Modify: `packages/installer-core/src/vgo_installer/materializer.py`
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`

- [ ] **Step 1: Write failing tests for wrapper rendering and install-time materialization**

Create `tests/unit/test_discoverable_wrappers.py` with cases like:

```python
rendered = build_wrapper_descriptors(
    host_id="codex",
    projected_entries=["vibe", "vibe-want", "vibe-how", "vibe-do"],
)
assert sorted(rendered.keys()) == ["vibe", "vibe-do", "vibe-how", "vibe-want"]
assert "Use the `vibe` skill" in rendered["vibe-how"].content
assert "Vibe: How Do We Do It?" in rendered["vibe-how"].description
```

Add an install-time test asserting a temp Codex or OpenCode target root receives wrapper files after installer execution.

- [ ] **Step 2: Run the wrapper tests to verify failure**

Run:

```bash
pytest \
  tests/unit/test_discoverable_wrappers.py \
  tests/runtime_neutral/test_install_profile_differentiation.py -q
```

Expected: FAIL because no wrapper materializer exists and install payload summary still sees only canonical `vibe`.

- [ ] **Step 3: Implement generated wrapper rendering in a focused helper**

Create `packages/installer-core/src/vgo_installer/discoverable_wrappers.py` with host-focused responsibilities only:

```python
def render_wrapper_frontmatter(host_id: str, entry: DiscoverableEntry) -> str: ...
def render_wrapper_body(entry: DiscoverableEntry) -> str: ...
def materialize_host_visible_wrappers(... ) -> list[Path]: ...
```

Use existing canonical sources as style references:
- `commands/vibe.md`
- `config/opencode/commands/vibe.md`

Then update:
- `materializer.py` to delegate wrapper generation instead of growing more mixed responsibilities
- `install_runtime.py` to call the helper and record generated wrapper paths

- [ ] **Step 4: Re-run the wrapper tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  packages/installer-core/src/vgo_installer/discoverable_wrappers.py \
  packages/installer-core/src/vgo_installer/materializer.py \
  packages/installer-core/src/vgo_installer/install_runtime.py \
  tests/unit/test_discoverable_wrappers.py \
  tests/runtime_neutral/test_install_profile_differentiation.py
git commit -m "feat: materialize discoverable vibe wrapper entries"
```

### Task 4: Align adapter metadata with generated wrapper projection truth

**Files:**
- Modify: `config/adapter-registry.json`
- Modify: `adapters/index.json`
- Modify: `adapters/codex/host-profile.json`
- Modify: `adapters/claude-code/host-profile.json`
- Modify: `adapters/cursor/host-profile.json`
- Modify: `adapters/windsurf/host-profile.json`
- Modify: `adapters/openclaw/host-profile.json`
- Modify: `adapters/opencode/host-profile.json`
- Modify: `tests/contract/test_adapter_descriptor_contract.py`
- Modify: `tests/unit/test_adapter_registry_support.py`

- [ ] **Step 1: Extend adapter tests to require projection metadata**

Keep the existing invariant:

```python
assert discoverable_entries["presentational_only"] is True
```

Add new assertions such as:

```python
assert discoverable_entries["projection_mode"] == "generated_wrapper_entries"
assert discoverable_entries["shared_source"] == "config/vibe-entry-surfaces.json"
assert discoverable_entries["authority_owner"] == "vibe"
assert discoverable_entries["host_visible_surface"]
```

- [ ] **Step 2: Run adapter contract tests to verify failure**

Run:

```bash
pytest \
  tests/contract/test_adapter_descriptor_contract.py \
  tests/unit/test_adapter_registry_support.py -q
```

Expected: FAIL because profiles currently stop at `presentational_only` with no host-visible projection metadata.

- [ ] **Step 3: Update adapter registry and host profiles**

Add per-adapter fields that stay truthful and host-specific without owning semantics, for example:

```json
"discoverable_entries": {
  "shared_source": "config/vibe-entry-surfaces.json",
  "authority_owner": "vibe",
  "presentational_only": true,
  "projection_mode": "generated_wrapper_entries",
  "host_visible_surface": "commands"
}
```

Use host-appropriate `host_visible_surface` values:
- Codex: command surface
- Claude Code: command or managed launcher surface
- Cursor: preview-guidance command/skill surface
- Windsurf/OpenClaw: runtime-core wrapper surface
- OpenCode: command/agent surface

- [ ] **Step 4: Re-run adapter contract tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  config/adapter-registry.json \
  adapters/index.json \
  adapters/codex/host-profile.json \
  adapters/claude-code/host-profile.json \
  adapters/cursor/host-profile.json \
  adapters/windsurf/host-profile.json \
  adapters/openclaw/host-profile.json \
  adapters/opencode/host-profile.json \
  tests/contract/test_adapter_descriptor_contract.py \
  tests/unit/test_adapter_registry_support.py
git commit -m "docs: declare host-visible wrapper projection metadata"
```

## Chunk 3: Ledger Truth, Check Surfaces, And Cross-Platform Validation

### Task 5: Separate canonical public skills from host-visible wrapper entries in install ledgers

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/install_plan.py`
- Modify: `packages/installer-core/src/vgo_installer/ledger_service.py`
- Modify: `tests/unit/test_installer_ledger_service.py`
- Modify: `tests/runtime_neutral/test_install_profile_differentiation.py`
- Modify: `tests/runtime_neutral/test_installed_runtime_scripts.py`

- [ ] **Step 1: Write failing tests for host-visible entry summary fields**

Extend ledger tests to require fields like:

```python
assert ledger["payload_summary"]["public_skill_names"] == ["vibe"]
assert ledger["payload_summary"]["host_visible_entry_names"] == ["vibe", "vibe-do", "vibe-how", "vibe-want"]
assert ledger["payload_summary"]["host_visible_entry_count"] == 4
```

Extend runtime-neutral install tests so both `minimal` and `full` installs still report only canonical public top-level skills while also reporting all host-visible wrapper entries.

- [ ] **Step 2: Run the ledger/install summary tests to verify failure**

Run:

```bash
pytest \
  tests/unit/test_installer_ledger_service.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py -q
```

Expected: FAIL because `build_payload_summary()` only counts `skills/<name>` directories today.

- [ ] **Step 3: Update ledger summary generation**

Modify `ledger_service.py` so payload summary distinguishes:

```python
{
  "public_skill_names": ["vibe"],
  "public_skill_count": 1,
  "host_visible_entry_names": ["vibe", "vibe-do", "vibe-how", "vibe-want"],
  "host_visible_entry_count": 4,
}
```

Use wrapper paths recorded during install rather than inferring host-visible readiness from `skills/` directories alone.

- [ ] **Step 4: Re-run the ledger/install summary tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  packages/installer-core/src/vgo_installer/install_plan.py \
  packages/installer-core/src/vgo_installer/ledger_service.py \
  tests/unit/test_installer_ledger_service.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py
git commit -m "feat: report host-visible vibe wrapper entries in install ledger"
```

### Task 6: Make `check.sh` and `check.ps1` validate host-visible wrapper readiness honestly

**Files:**
- Modify: `check.sh`
- Modify: `check.ps1`
- Create: `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py`
- Modify: `tests/runtime_neutral/test_claude_preview_scaffold.py`
- Modify: `tests/runtime_neutral/test_opencode_preview_parity.py`
- Modify: `tests/runtime_neutral/test_windsurf_runtime_core.py`
- Modify: `tests/runtime_neutral/test_openclaw_runtime_core.py`

- [ ] **Step 1: Write failing runtime-neutral checks for wrapper visibility**

Create `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py` with shell and PowerShell coverage:

```python
result = subprocess.run([... "check.sh", "--host", "codex", "--target-root", str(target_root)], ...)
assert "host-visible discoverable entries" in result.stdout
assert "[OK]" in result.stdout
```

Add a degraded case where wrapper files are removed after install and assert check output contains a failure such as `not host-visible`.

- [ ] **Step 2: Run the check-surface tests to verify failure**

Run:

```bash
pytest \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py \
  tests/runtime_neutral/test_opencode_preview_parity.py \
  tests/runtime_neutral/test_windsurf_runtime_core.py \
  tests/runtime_neutral/test_openclaw_runtime_core.py -q
```

Expected: FAIL because current check scripts do not validate wrapper visibility.

- [ ] **Step 3: Update shell and PowerShell check flows**

Teach both scripts to:
- load install ledger payload summary
- inspect recorded wrapper paths
- report a dedicated line for host-visible discoverable entry readiness
- fail or warn honestly when runtime payload exists but wrappers are missing

Keep platform-specific wrapper behavior equivalent:
- `check.sh` for Linux/macOS
- `check.ps1` for Windows/PowerShell

- [ ] **Step 4: Re-run the check-surface tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  check.sh \
  check.ps1 \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py \
  tests/runtime_neutral/test_opencode_preview_parity.py \
  tests/runtime_neutral/test_windsurf_runtime_core.py \
  tests/runtime_neutral/test_openclaw_runtime_core.py
git commit -m "feat: verify host-visible vibe wrapper readiness in check flows"
```

### Task 7: Update user-facing docs so they describe shipped wrapper surfaces truthfully

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `docs/quick-start.md`
- Modify: `docs/quick-start.en.md`

- [ ] **Step 1: Add or update doc assertions in existing text-based tests**

If no dedicated doc test already covers the changed wording, extend an existing discoverability-oriented test or add a small integration test that asserts wording like:

```python
assert "If your host exposes the installed wrapper entries" in quick_start
assert "host-visible" in quick_start
```

- [ ] **Step 2: Run the affected docs/discoverability tests to verify failure**

Run:

```bash
pytest \
  tests/integration/test_codex_install_prompt_discoverability.py \
  tests/integration/test_version_governance_runtime_roles.py -q
```

Expected: FAIL or require wording updates because docs currently overpromise discoverability without install-time host-visible proof.

- [ ] **Step 3: Update docs**

Make docs say the truthful shipped behavior:
- wrapper entries are installed host-visible surfaces on supported hosts
- they still resolve to canonical `vibe`
- `$vibe` textual invocation remains valid but is not the primary discoverable UX

- [ ] **Step 4: Re-run the affected docs/discoverability tests to verify pass**

Run the same `pytest` command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  README.md \
  README.zh.md \
  docs/quick-start.md \
  docs/quick-start.en.md \
  tests/integration/test_codex_install_prompt_discoverability.py \
  tests/integration/test_version_governance_runtime_roles.py
git commit -m "docs: align multi-host wrapper discoverability wording"
```

## Chunk 4: End-To-End Verification And Delivery Evidence

### Task 8: Run the full wrapper-projection verification matrix before claiming completion

**Files:**
- Inspect only: working tree, install receipts, generated wrapper files, test logs

- [ ] **Step 1: Run the focused pytest regression matrix**

Run:

```bash
pytest \
  tests/contract/test_vibe_discoverable_entry_contract.py \
  tests/contract/test_adapter_descriptor_contract.py \
  tests/unit/test_adapter_registry_support.py \
  tests/unit/test_discoverable_entry_surface.py \
  tests/unit/test_discoverable_wrappers.py \
  tests/unit/test_runtime_packaging_resolver.py \
  tests/unit/test_router_contract_support_descriptor_sources.py \
  tests/unit/test_installer_ledger_service.py \
  tests/integration/test_runtime_core_packaging_roles.py \
  tests/runtime_neutral/test_install_profile_differentiation.py \
  tests/runtime_neutral/test_installed_runtime_scripts.py \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py \
  tests/runtime_neutral/test_opencode_preview_parity.py \
  tests/runtime_neutral/test_windsurf_runtime_core.py \
  tests/runtime_neutral/test_openclaw_runtime_core.py -q
```

Expected: PASS.

- [ ] **Step 2: Run shell install/check smoke tests in temp roots**

Run:

```bash
tmp_root="$(mktemp -d)"
bash ./install.sh --host codex --profile full --target-root "${tmp_root}/codex"
bash ./check.sh --host codex --profile full --target-root "${tmp_root}/codex" --deep
```

Expected:
- install succeeds
- check reports host-visible discoverable entries ready
- generated wrapper files exist under the Codex host-visible command surface

- [ ] **Step 3: Run PowerShell install/check smoke tests in temp roots**

Run:

```bash
pwsh -NoProfile -File ./install.ps1 -HostId codex -Profile full -TargetRoot "${tmp_root}/codex-ps"
pwsh -NoProfile -File ./check.ps1 -HostId codex -Profile full -TargetRoot "${tmp_root}/codex-ps" -Deep
```

Expected:
- install succeeds
- check reports host-visible discoverable entries ready
- wrapper visibility status matches shell lane

- [ ] **Step 4: Inspect git diff and summarize proof artifacts**

Run:

```bash
git status --short
git diff --stat
```

Expected:
- only planned files changed
- no stray host-temp artifacts remain

- [ ] **Step 5: Commit final implementation batch**

```bash
git add .
git commit -m "feat: project discoverable vibe wrappers across supported hosts"
```

## Plan Notes
- Keep `presentational_only: true` in adapter metadata. The wrappers are still presentational launch surfaces, even after they become real host-visible installed entries.
- Do not widen `compatibility_skill_projections` into semantic truth. Wrapper visibility belongs to `public_skill_surface` plus generated host entry artifacts.
- Do not solve this by hand-maintaining four semantic copies of runtime command files per host. Use generation or a focused render helper so semantics remain centralized.
- Do not claim Windows/Linux compatibility until both install/check smoke lanes and the runtime-neutral tests pass.
