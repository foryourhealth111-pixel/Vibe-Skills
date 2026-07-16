import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
GATES = [
    REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-runtime-execution-proof-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-module-dispatch-closure-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-child-specialist-escalation-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-no-silent-fallback-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-no-duplicate-canonical-surface-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-root-child-hierarchy-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-remediation-foundation-gate.ps1",
]

RETIRED_SPECIALIST_TERMS = (
    "specialist_accounting",
    "specialist_decision",
    "specialist_user_disclosure",
    "skill_execution_unit_count",
    "module_skill_dispatch",
)


def test_verification_gates_use_runtime_entrypoint_helper() -> None:
    helper = (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8")

    assert "function Get-VgoRuntimeEntrypointPath" in helper
    assert "runtime_entrypoint = 'scripts/runtime/invoke-vibe-runtime.ps1'" in helper

    for gate in GATES:
        content = gate.read_text(encoding="utf-8")
        assert "Get-VgoRuntimeEntrypointPath" in content, gate.name
        assert "scripts/runtime/invoke-vibe-runtime.ps1" not in content.replace("\\", "/"), gate.name


def test_canonical_entry_truth_gate_enforces_runtime_backed_launch_proof() -> None:
    content = (REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1").read_text(encoding="utf-8")

    assert "host-launch-receipt.json" in content
    assert "runtime-input-packet.json" in content
    assert "governance-capsule.json" in content
    assert "stage-lineage.json" in content
    assert "module_assignments" in content
    assert "omits retired skill_usage ledger" in content
    assert "canonical_router" not in content
    assert "runtime_selected_skill = if" not in content


def test_no_silent_fallback_gate_requires_runtime_artifact_truth_chain_for_supported_hosts() -> None:
    gate = (REPO_ROOT / "scripts" / "verify" / "vibe-no-silent-fallback-contract-gate.ps1").read_text(encoding="utf-8")

    assert "candidate_discovery_only" in gate
    assert "no_local_candidate" in gate
    assert "legacy_fallback_guard" not in gate
    assert "module_assignments" in gate
    assert "module_work_plan" in gate
    assert "agent_execution_handoff" in gate
    assert "module_handoff" in gate
    assert "module-execution.json" in gate
    assert "codex" in gate
    assert "claude-code" in gate
    assert "opencode" in gate


def test_child_specialist_escalation_gate_uses_module_assignments_as_child_truth_surface() -> None:
    gate = (REPO_ROOT / "scripts" / "verify" / "vibe-child-specialist-escalation-gate.ps1").read_text(encoding="utf-8")

    assert "module_assignments" in gate
    assert "module_work_plan" in gate
    assert "agent_execution_handoff" in gate
    assert "module_handoff" in gate
    assert "child runtime packet includes module_assignments" in gate
    assert "child module_assignments keeps only the root-approved skill" in gate
    assert "child module_assignments matches the Agent skill organization" in gate
    assert "child candidate audit does not mutate module_assignments" in gate
    assert "child Agent handoff follows the approved module work plan" in gate


def test_module_dispatch_closure_gate_uses_module_plan_as_dispatch_authority() -> None:
    gate = (REPO_ROOT / "scripts" / "verify" / "vibe-module-dispatch-closure-gate.ps1").read_text(encoding="utf-8")

    assert "module_assignments" in gate
    assert "agent_execution_handoff" in gate
    assert "module_handoff" in gate
    assert "official smoke runtime packet includes module_assignments" in gate
    assert "official smoke module_assignments carries bounded skill truth" in gate
    assert "official smoke Agent handoff follows module-work-plan.json" in gate
    assert "child closure smoke keeps inherited bounded work in module_assignments" in gate
    assert "child closure smoke Agent handoff follows module-work-plan.json" in gate


def test_current_verification_gates_and_contracts_have_no_retired_specialist_dependencies() -> None:
    surfaces = [
        *GATES[:6],
        REPO_ROOT / "config" / "project-delivery-acceptance-contract.json",
        REPO_ROOT / "config" / "runtime-input-packet-policy.json",
    ]

    hits: dict[str, list[str]] = {}
    for surface in surfaces:
        content = surface.read_text(encoding="utf-8")
        matched = [term for term in RETIRED_SPECIALIST_TERMS if term in content]
        if matched:
            hits[surface.name] = matched

    assert not hits, hits


def test_agent_handoff_gates_do_not_require_retired_kernel_execution_policy() -> None:
    for gate_name in (
        "vibe-runtime-execution-proof-gate.ps1",
        "vibe-governed-runtime-contract-gate.ps1",
    ):
        gate = (REPO_ROOT / "scripts" / "verify" / gate_name).read_text(encoding="utf-8")

        assert "config/execution-runtime-policy.json" not in gate, gate_name
        assert "config/runtime-input-packet-policy.json" in gate, gate_name

    execution_gate = (
        REPO_ROOT / "scripts" / "verify" / "vibe-runtime-execution-proof-gate.ps1"
    ).read_text(encoding="utf-8")
    assert "tests/runtime_neutral/test_governed_runtime_bridge.py" not in execution_gate


def test_governed_runtime_contract_gate_runs_with_agent_led_skill_truth() -> None:
    shell = shutil.which("pwsh") or shutil.which("pwsh.exe")
    if shell is None:
        pytest.skip("PowerShell 7 is not available")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_governed_runtime_contract_gate_does_not_expect_agent_result_before_handoff() -> None:
    gate = (REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1").read_text(encoding="utf-8")

    artifact_expectations = gate.split("$artifactPaths = @(", 1)[1].split("\n)", 1)[0]
    assert "$summary.summary.artifacts.module_execution" not in artifact_expectations
    assert "module_handoff" in gate
    assert "agent_action_required" in gate
