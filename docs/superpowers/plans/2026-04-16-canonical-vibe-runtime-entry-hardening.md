# Canonical Vibe Runtime Entry Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make explicit `$vibe` and `/vibe` on Codex, Claude Code, and OpenCode launch canonical runtime or block, with proof-gated truth and no silent `SKILL.md` fallback.

**Architecture:** Introduce a single `canonical_vibe` host capability contract, route explicit entry through a shared canonical-entry launcher, and require a new host launch receipt plus the existing governed runtime artifacts before any canonical claim is allowed. Keep the six-stage runtime kernel unchanged; constrain code changes to host capability resolution, entry launching, wrapper/bootstraps, and verification gates.

**Tech Stack:** Python contracts and installer/runtime-core packages, PowerShell runtime and verification scripts, Markdown wrapper generation, pytest, PowerShell gate tests.

---

## Spec Input

- Approved design: `docs/superpowers/specs/2026-04-16-canonical-vibe-runtime-entry-hardening-design.md`
- Governed run: `outputs/runtime/vibe-sessions/canonical-vibe-runtime-entry-hardening-plan/`
- Governed requirement: `docs/requirements/2026-04-16-write-a-detailed-implementation-plan-for-the-approved-canonical.md`
- Governed execution plan: `docs/plans/2026-04-16-write-a-detailed-implementation-plan-for-the-approved-canonical-execution-plan.md`

## File Map

### Capability and contract layer

- Modify: `config/adapter-registry.json`
  - Add `canonical_vibe` entry semantics for Codex, Claude Code, and OpenCode.
- Create: `packages/contracts/src/vgo_contracts/canonical_vibe_contract.py`
  - Resolve host capability truth from adapter registry.
- Modify: `packages/contracts/src/vgo_contracts/runtime_surface_contract.py`
  - Remove host-entry semantics that do not belong in runtime surface packaging rules.
- Modify: `packages/contracts/src/vgo_contracts/__init__.py`
  - Export canonical-vibe contract helpers instead of `SKILL_ONLY_ACTIVATION_HOSTS`.
- Modify: `scripts/common/runtime_contracts.py`
  - Re-export canonical-vibe contract helpers for PowerShell and compatibility consumers.
- Modify: `packages/installer-core/src/vgo_installer/adapter_registry.py`
  - Surface resolved `canonical_vibe` semantics to installer and wrapper code.

### Canonical entry launcher layer

- Create: `packages/contracts/src/vgo_contracts/host_launch_receipt.py`
  - Typed contract for canonical entry launch receipts.
- Create: `packages/runtime-core/src/vgo_runtime/canonical_entry.py`
  - Shared canonical-entry launcher that invokes `scripts/runtime/invoke-vibe-runtime.ps1` and verifies minimum truth artifacts.
- Modify: `packages/runtime-core/src/vgo_runtime/__init__.py`
  - Export launcher helpers if the package already exposes runtime entry utilities.
- Modify: `apps/vgo-cli/src/vgo_cli/core_bridge.py`
  - Add `run_canonical_entry_core`.
- Modify: `apps/vgo-cli/src/vgo_cli/commands.py`
  - Add `canonical-entry` CLI surface or equivalent dedicated entry path.
- Create: `scripts/runtime/Invoke-VibeCanonicalEntry.ps1`
  - PowerShell bridge script for launcher use and parity tests.

### Host adaptation layer

- Modify: `packages/installer-core/src/vgo_installer/discoverable_wrappers.py`
  - Emit launch trampolines instead of prose-only guidance wrappers.
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`
  - Materialize launcher-aware wrappers and host closure metadata.
- Modify: `config/global-bootstrap/codex-vibe-bootstrap.md`
  - State executable launch requirement and blocked fallback.
- Modify: `config/global-bootstrap/claude-code-vibe-bootstrap.md`
  - Same rule for Claude Code.
- Modify: `config/global-bootstrap/opencode-vibe-bootstrap.md`
  - Same rule for OpenCode.
- Modify: `config/opencode/opencode.json.example`
  - Replace prose command template with canonical-entry trampoline instructions.
- Modify: `config/opencode/commands/vibe.md`
  - Keep as documentation/example, but align with launcher contract.
- Modify: `config/opencode/agents/vibe-plan.md`
  - Keep as documentation/example, but align with launcher contract.
- Modify: `adapters/claude-code/host-profile.json`
  - Document `bridged_runtime` semantics.
- Modify: `adapters/opencode/host-profile.json`
  - Document `bridged_runtime` semantics.

### Verification and truth layer

- Create: `scripts/verify/vibe-canonical-entry-truth-gate.ps1`
  - Fail if launch receipt or governed truth artifacts are missing or inconsistent.
- Modify: `scripts/verify/vibe-no-silent-fallback-contract-gate.ps1`
  - Assert explicit canonical-entry blocked behavior, not just general fallback honesty.
- Modify: `SKILL.md`
  - State that reading `SKILL.md` is not proof of canonical runtime entry.
- Modify: `protocols/runtime.md`
  - Document launcher and truth-gate expectations.

### Test layer

- Create: `tests/unit/test_canonical_vibe_contract.py`
- Create: `tests/unit/test_host_launch_receipt.py`
- Create: `tests/unit/test_canonical_vibe_entry_launcher.py`
- Modify: `tests/unit/test_runtime_surface_contract.py`
- Modify: `tests/unit/test_discoverable_wrappers.py`
- Modify: `tests/unit/test_vgo_cli_core_bridge.py`
- Modify: `tests/unit/test_vgo_cli_commands.py`
- Modify: `tests/unit/test_installer_adapter_registry_target_roots.py`
- Create: `tests/runtime_neutral/test_canonical_vibe_host_entry.py`
- Modify: `tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py`
- Modify: `tests/runtime_neutral/test_claude_preview_scaffold.py`
- Modify: `tests/runtime_neutral/test_opencode_managed_preview.py`
- Modify: `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py`
- Modify: `tests/runtime_neutral/test_installed_host_runtime_simulation.py`
- Create: `tests/integration/test_canonical_vibe_truth_gate.py`
- Modify: `tests/integration/test_cli_runtime_entrypoint_contract_cutover.py`
- Modify: `tests/integration/test_powershell_installed_runtime_contract_bridge.py`
- Modify: `tests/integration/test_verification_runtime_entrypoint_contract_cutover.py`

## Chunk 1: Single Source Of Truth

### Task 1: Add canonical-vibe host capability contract

**Files:**
- Modify: `config/adapter-registry.json`
- Create: `packages/contracts/src/vgo_contracts/canonical_vibe_contract.py`
- Modify: `packages/contracts/src/vgo_contracts/runtime_surface_contract.py`
- Modify: `packages/contracts/src/vgo_contracts/__init__.py`
- Modify: `scripts/common/runtime_contracts.py`
- Modify: `packages/installer-core/src/vgo_installer/adapter_registry.py`
- Test: `tests/unit/test_canonical_vibe_contract.py`
- Test: `tests/unit/test_runtime_surface_contract.py`
- Test: `tests/unit/test_installer_adapter_registry_target_roots.py`

- [ ] **Step 1: Write failing contract tests for Codex, Claude Code, and OpenCode**

```python
def test_resolve_canonical_vibe_contract_projects_supported_hosts() -> None:
    assert resolve_canonical_vibe_contract(REPO_ROOT, "codex")["entry_mode"] == "direct_runtime"
    assert resolve_canonical_vibe_contract(REPO_ROOT, "claude-code")["entry_mode"] == "bridged_runtime"
    assert resolve_canonical_vibe_contract(REPO_ROOT, "opencode")["entry_mode"] == "bridged_runtime"


def test_supported_hosts_forbid_skill_doc_fallback() -> None:
    for host_id in ("codex", "claude-code", "opencode"):
        contract = resolve_canonical_vibe_contract(REPO_ROOT, host_id)
        assert contract["fallback_policy"] == "blocked"
        assert contract["allow_skill_doc_fallback"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/unit/test_canonical_vibe_contract.py tests/unit/test_runtime_surface_contract.py tests/unit/test_installer_adapter_registry_target_roots.py
```

Expected: FAIL because `canonical_vibe` does not exist and runtime surface helpers still depend on `SKILL_ONLY_ACTIVATION_HOSTS`.

- [ ] **Step 3: Add the adapter-registry data and resolver**

Use this shape in `config/adapter-registry.json`:

```json
"canonical_vibe": {
  "entry_mode": "direct_runtime",
  "fallback_policy": "blocked",
  "proof_required": true,
  "allow_skill_doc_fallback": false,
  "launcher_kind": "native_command",
  "supports_bounded_stop": true
}
```

Create a resolver similar to:

```python
def resolve_canonical_vibe_contract(repo_root: Path, host_id: str | None) -> dict[str, Any]:
    entry = resolve_adapter_entry(load_adapter_registry(repo_root), host_id or "")
    contract = dict(entry.get("canonical_vibe") or {})
    if not contract:
        raise ValueError(f"canonical_vibe contract missing for host: {host_id}")
    return contract
```

Retire `SKILL_ONLY_ACTIVATION_HOSTS` from host-entry semantics. Keep `runtime_surface_contract.py` focused on packaging/noise filtering only.

- [ ] **Step 4: Re-run the targeted tests**

Run:

```bash
pytest -q tests/unit/test_canonical_vibe_contract.py tests/unit/test_runtime_surface_contract.py tests/unit/test_installer_adapter_registry_target_roots.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/adapter-registry.json \
  packages/contracts/src/vgo_contracts/canonical_vibe_contract.py \
  packages/contracts/src/vgo_contracts/runtime_surface_contract.py \
  packages/contracts/src/vgo_contracts/__init__.py \
  scripts/common/runtime_contracts.py \
  packages/installer-core/src/vgo_installer/adapter_registry.py \
  tests/unit/test_canonical_vibe_contract.py \
  tests/unit/test_runtime_surface_contract.py \
  tests/unit/test_installer_adapter_registry_target_roots.py
git commit -m "feat: add canonical vibe host capability contract"
```

## Chunk 2: Canonical Launcher

### Task 2: Add host launch receipt and canonical-entry launcher

**Files:**
- Create: `packages/contracts/src/vgo_contracts/host_launch_receipt.py`
- Create: `packages/runtime-core/src/vgo_runtime/canonical_entry.py`
- Modify: `packages/runtime-core/src/vgo_runtime/__init__.py`
- Modify: `apps/vgo-cli/src/vgo_cli/core_bridge.py`
- Modify: `apps/vgo-cli/src/vgo_cli/commands.py`
- Create: `scripts/runtime/Invoke-VibeCanonicalEntry.ps1`
- Test: `tests/unit/test_host_launch_receipt.py`
- Test: `tests/unit/test_canonical_vibe_entry_launcher.py`
- Test: `tests/unit/test_vgo_cli_core_bridge.py`
- Test: `tests/unit/test_vgo_cli_commands.py`

- [ ] **Step 1: Write failing launcher and receipt tests**

```python
def test_canonical_entry_writes_host_launch_receipt(tmp_path: Path) -> None:
    result = launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="plan runtime entry hardening",
        requested_stage_stop="phase_cleanup",
        artifact_root=tmp_path,
    )
    receipt = json.loads((tmp_path / "outputs/runtime/vibe-sessions" / result.run_id / "host-launch-receipt.json").read_text())
    assert receipt["host_id"] == "codex"
    assert receipt["entry_id"] == "vibe"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/unit/test_host_launch_receipt.py tests/unit/test_canonical_vibe_entry_launcher.py tests/unit/test_vgo_cli_core_bridge.py tests/unit/test_vgo_cli_commands.py
```

Expected: FAIL because no canonical-entry launcher or host launch receipt exists.

- [ ] **Step 3: Implement the receipt contract and launcher**

Receipt dataclass shape:

```python
@dataclass(slots=True)
class HostLaunchReceipt:
    host_id: str
    entry_id: str
    launch_mode: str
    launcher_path: str
    requested_stage_stop: str | None
    requested_grade_floor: str | None
    runtime_entrypoint: str
    run_id: str
    created_at: str
    launch_status: str
```

Launcher responsibilities:

```python
def launch_canonical_vibe(...):
    contract = resolve_canonical_vibe_contract(repo_root, host_id)
    if contract["fallback_policy"] != "blocked":
        raise RuntimeError("unsupported fallback policy")
    receipt = write_host_launch_receipt(...)
    runtime_result = invoke_vibe_runtime(...)
    assert_minimum_truth_artifacts(runtime_result, receipt)
    return runtime_result
```

Expose the launcher through:

- `vgo_runtime.canonical_entry`
- `vgo_cli.core_bridge.run_canonical_entry_core`
- `vgo_cli.commands` subcommand `canonical-entry`
- `scripts/runtime/Invoke-VibeCanonicalEntry.ps1`

- [ ] **Step 4: Re-run launcher tests**

Run:

```bash
pytest -q tests/unit/test_host_launch_receipt.py tests/unit/test_canonical_vibe_entry_launcher.py tests/unit/test_vgo_cli_core_bridge.py tests/unit/test_vgo_cli_commands.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/contracts/src/vgo_contracts/host_launch_receipt.py \
  packages/runtime-core/src/vgo_runtime/canonical_entry.py \
  packages/runtime-core/src/vgo_runtime/__init__.py \
  apps/vgo-cli/src/vgo_cli/core_bridge.py \
  apps/vgo-cli/src/vgo_cli/commands.py \
  scripts/runtime/Invoke-VibeCanonicalEntry.ps1 \
  tests/unit/test_host_launch_receipt.py \
  tests/unit/test_canonical_vibe_entry_launcher.py \
  tests/unit/test_vgo_cli_core_bridge.py \
  tests/unit/test_vgo_cli_commands.py
git commit -m "feat: add canonical vibe entry launcher"
```

## Chunk 3: Host Wrapper Cutover

### Task 3: Convert discoverable wrappers and bootstraps into launch trampolines

**Files:**
- Modify: `packages/installer-core/src/vgo_installer/discoverable_wrappers.py`
- Modify: `packages/installer-core/src/vgo_installer/install_runtime.py`
- Modify: `config/global-bootstrap/codex-vibe-bootstrap.md`
- Modify: `config/global-bootstrap/claude-code-vibe-bootstrap.md`
- Modify: `config/global-bootstrap/opencode-vibe-bootstrap.md`
- Modify: `config/opencode/opencode.json.example`
- Modify: `config/opencode/commands/vibe.md`
- Modify: `config/opencode/agents/vibe-plan.md`
- Modify: `adapters/claude-code/host-profile.json`
- Modify: `adapters/opencode/host-profile.json`
- Test: `tests/unit/test_discoverable_wrappers.py`
- Test: `tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py`
- Test: `tests/runtime_neutral/test_claude_preview_scaffold.py`
- Test: `tests/runtime_neutral/test_opencode_managed_preview.py`
- Test: `tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py`

- [ ] **Step 1: Write failing wrapper/bootstraps tests**

```python
def test_vibe_wrapper_uses_canonical_entry_trampoline() -> None:
    descriptors = build_wrapper_descriptors("opencode", load_discoverable_entry_surface(REPO_ROOT))
    content = descriptors["vibe"].content
    assert "canonical-entry" in content
    assert "Do not continue by reading `skills/vibe/SKILL.md`." in content
    assert "Use the `vibe` skill and follow its governed runtime contract" not in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/unit/test_discoverable_wrappers.py tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py tests/runtime_neutral/test_claude_preview_scaffold.py tests/runtime_neutral/test_opencode_managed_preview.py tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py
```

Expected: FAIL because wrappers and examples still emit prose guidance instead of launcher instructions.

- [ ] **Step 3: Replace prose wrappers with launcher instructions**

Wrapper body target:

```markdown
Run the canonical vibe entry launcher for this request.

Required call:
`vgo canonical-entry --host <host-id> --entry <entry-id> --requested-stage-stop <stop> --prompt "$ARGUMENTS"`

If the launcher cannot run, report blocked.
Do not continue by reading `skills/vibe/SKILL.md`.
Reading `SKILL.md` alone is not canonical vibe entry.
```

Bootstrap target language:

- explicit `$vibe` or `/vibe` must launch canonical entry first
- if launcher cannot run, report blocked
- bootstrap text is not runtime proof

- [ ] **Step 4: Re-run wrapper/bootstraps tests**

Run:

```bash
pytest -q tests/unit/test_discoverable_wrappers.py tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py tests/runtime_neutral/test_claude_preview_scaffold.py tests/runtime_neutral/test_opencode_managed_preview.py tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/installer-core/src/vgo_installer/discoverable_wrappers.py \
  packages/installer-core/src/vgo_installer/install_runtime.py \
  config/global-bootstrap/codex-vibe-bootstrap.md \
  config/global-bootstrap/claude-code-vibe-bootstrap.md \
  config/global-bootstrap/opencode-vibe-bootstrap.md \
  config/opencode/opencode.json.example \
  config/opencode/commands/vibe.md \
  config/opencode/agents/vibe-plan.md \
  adapters/claude-code/host-profile.json \
  adapters/opencode/host-profile.json \
  tests/unit/test_discoverable_wrappers.py \
  tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py \
  tests/runtime_neutral/test_opencode_managed_preview.py \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py
git commit -m "feat: cut host wrappers over to canonical entry trampolines"
```

## Chunk 4: Truth Gate

### Task 4: Add canonical-entry truth gate and false-claim rejection

**Files:**
- Create: `scripts/verify/vibe-canonical-entry-truth-gate.ps1`
- Modify: `scripts/verify/vibe-no-silent-fallback-contract-gate.ps1`
- Modify: `SKILL.md`
- Modify: `protocols/runtime.md`
- Test: `tests/integration/test_canonical_vibe_truth_gate.py`
- Test: `tests/integration/test_verification_runtime_entrypoint_contract_cutover.py`
- Test: `tests/integration/test_powershell_installed_runtime_contract_bridge.py`

- [ ] **Step 1: Write failing truth-gate tests**

```python
def test_truth_gate_rejects_missing_launch_receipt(tmp_path: Path) -> None:
    result = run_truth_gate(tmp_path, expect_success=False)
    assert "host-launch-receipt.json" in result.stderr


def test_truth_gate_rejects_doc_only_activation(tmp_path: Path) -> None:
    write_fake_skill_only_wrapper(tmp_path)
    result = run_truth_gate(tmp_path, expect_success=False)
    assert "reading SKILL.md alone is not canonical vibe entry" in result.stderr
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/integration/test_canonical_vibe_truth_gate.py tests/integration/test_verification_runtime_entrypoint_contract_cutover.py tests/integration/test_powershell_installed_runtime_contract_bridge.py
```

Expected: FAIL because the canonical-entry truth gate does not exist yet.

- [ ] **Step 3: Implement the gate and contract text**

Gate assertions must require:

- `host-launch-receipt.json`
- `runtime-input-packet.json`
- `governance-capsule.json`
- `stage-lineage.json`
- runtime packet fields:
  - `canonical_router`
  - `route_snapshot`
  - `specialist_recommendations`
  - `specialist_dispatch`
  - `divergence_shadow`

Also update docs/contracts so they state:

- reading `SKILL.md` is not proof of canonical entry
- launch proof is required before canonical claims

- [ ] **Step 4: Re-run truth-gate tests**

Run:

```bash
pytest -q tests/integration/test_canonical_vibe_truth_gate.py tests/integration/test_verification_runtime_entrypoint_contract_cutover.py tests/integration/test_powershell_installed_runtime_contract_bridge.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify/vibe-canonical-entry-truth-gate.ps1 \
  scripts/verify/vibe-no-silent-fallback-contract-gate.ps1 \
  SKILL.md \
  protocols/runtime.md \
  tests/integration/test_canonical_vibe_truth_gate.py \
  tests/integration/test_verification_runtime_entrypoint_contract_cutover.py \
  tests/integration/test_powershell_installed_runtime_contract_bridge.py
git commit -m "feat: add canonical vibe truth gate"
```

## Chunk 5: Multi-Host Deep Testing

### Task 5: Add real Codex, Claude Code, and OpenCode launch-path coverage

**Files:**
- Create: `tests/runtime_neutral/test_canonical_vibe_host_entry.py`
- Modify: `tests/runtime_neutral/test_installed_host_runtime_simulation.py`
- Modify: `tests/integration/test_cli_runtime_entrypoint_contract_cutover.py`
- Modify: `tests/integration/test_host_capability_matrix_single_source.py`

- [ ] **Step 1: Write failing multi-host launch tests**

```python
@pytest.mark.parametrize("host_id,expected_mode", [
    ("codex", "direct_runtime"),
    ("claude-code", "bridged_runtime"),
    ("opencode", "bridged_runtime"),
])
def test_supported_hosts_launch_canonical_entry_for_real(host_id: str, expected_mode: str, tmp_path: Path) -> None:
    result = run_canonical_entry(host_id=host_id, target_root=tmp_path / host_id)
    receipt = load_json(result["host_launch_receipt"])
    assert receipt["launch_mode"] == expected_mode
    assert Path(result["runtime_input_packet"]).exists()
    assert Path(result["governance_capsule"]).exists()
    assert Path(result["stage_lineage"]).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/runtime_neutral/test_canonical_vibe_host_entry.py tests/runtime_neutral/test_installed_host_runtime_simulation.py -k "canonical_vibe or high_fidelity_planning_debug_and_execution_tasks" tests/integration/test_cli_runtime_entrypoint_contract_cutover.py tests/integration/test_host_capability_matrix_single_source.py
```

Expected: FAIL because real host entry still degrades and no launch receipt exists.

- [ ] **Step 3: Wire launcher into host install/runtime simulation**

Implementation target:

- Codex uses `direct_runtime`
- Claude Code uses `bridged_runtime`
- OpenCode uses `bridged_runtime`
- all three emit a host launch receipt
- any bridge/launcher failure returns blocked or degraded truth, never canonical success

- [ ] **Step 4: Re-run multi-host launch tests**

Run:

```bash
pytest -q tests/runtime_neutral/test_canonical_vibe_host_entry.py tests/runtime_neutral/test_installed_host_runtime_simulation.py -k "canonical_vibe or high_fidelity_planning_debug_and_execution_tasks" tests/integration/test_cli_runtime_entrypoint_contract_cutover.py tests/integration/test_host_capability_matrix_single_source.py
```

Expected: PASS for the new canonical-entry path. If the old installed-host specialist-execution assertion remains too strict, update it so canonical truth is asserted independently from native specialist execution status.

- [ ] **Step 5: Commit**

```bash
git add tests/runtime_neutral/test_canonical_vibe_host_entry.py \
  tests/runtime_neutral/test_installed_host_runtime_simulation.py \
  tests/integration/test_cli_runtime_entrypoint_contract_cutover.py \
  tests/integration/test_host_capability_matrix_single_source.py
git commit -m "test: cover canonical vibe host entry across codex claude and opencode"
```

## Chunk 6: Final Verification And Closeout

### Task 6: Run full targeted verification and prepare execution handoff

**Files:**
- No new code files in this task.
- Verification evidence: `outputs/verify/` and runtime session artifacts under `outputs/runtime/vibe-sessions/`

- [ ] **Step 1: Run the unit and integration contract set**

Run:

```bash
pytest -q \
  tests/unit/test_canonical_vibe_contract.py \
  tests/unit/test_host_launch_receipt.py \
  tests/unit/test_canonical_vibe_entry_launcher.py \
  tests/unit/test_discoverable_wrappers.py \
  tests/unit/test_vgo_cli_core_bridge.py \
  tests/unit/test_vgo_cli_commands.py \
  tests/integration/test_canonical_vibe_truth_gate.py \
  tests/integration/test_cli_runtime_entrypoint_contract_cutover.py \
  tests/integration/test_verification_runtime_entrypoint_contract_cutover.py
```

Expected: PASS.

- [ ] **Step 2: Run runtime-neutral host verification**

Run:

```bash
pytest -q \
  tests/runtime_neutral/test_canonical_vibe_host_entry.py \
  tests/runtime_neutral/test_global_instruction_bootstrap_runtime.py \
  tests/runtime_neutral/test_claude_preview_scaffold.py \
  tests/runtime_neutral/test_opencode_managed_preview.py \
  tests/runtime_neutral/test_discoverable_wrapper_host_visibility.py \
  tests/runtime_neutral/test_installed_host_runtime_simulation.py
```

Expected: PASS for Codex, Claude Code, and OpenCode.

- [ ] **Step 3: Run PowerShell verification gates**

Run:

```bash
pwsh -NoLogo -NoProfile -File scripts/verify/vibe-no-silent-fallback-contract-gate.ps1 -WriteArtifacts
pwsh -NoLogo -NoProfile -File scripts/verify/vibe-canonical-entry-truth-gate.ps1 -WriteArtifacts
```

Expected: both gates PASS and write artifacts under `outputs/verify/`.

- [ ] **Step 4: Inspect real evidence paths**

Check that these exist for each host scenario:

```text
outputs/runtime/vibe-sessions/<run-id>/host-launch-receipt.json
outputs/runtime/vibe-sessions/<run-id>/runtime-input-packet.json
outputs/runtime/vibe-sessions/<run-id>/governance-capsule.json
outputs/runtime/vibe-sessions/<run-id>/stage-lineage.json
```

Record the evidence paths in the PR description or release notes.

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: harden canonical vibe runtime entry across supported hosts"
```

## Notes For Executor

- Keep the six-stage runtime kernel unchanged unless a failing test proves a launcher boundary cannot be satisfied without a minimal runtime-core hook.
- Do not broaden host scope beyond Codex, Claude Code, and OpenCode.
- Do not preserve compatibility by silently falling back to prose activation. Block instead.
- If a host cannot produce `host-launch-receipt.json`, treat that as a real failure, not an advisory warning.
