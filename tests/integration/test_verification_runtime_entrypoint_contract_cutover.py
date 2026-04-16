from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATES = [
    REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-runtime-execution-proof-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-specialist-dispatch-closure-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-child-specialist-escalation-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-no-silent-fallback-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-no-duplicate-canonical-surface-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-root-child-hierarchy-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-remediation-foundation-gate.ps1",
]


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
    assert "route_snapshot" in content
    assert "specialist_recommendations" in content
    assert "specialist_dispatch" in content
    assert "divergence_shadow" in content


def test_no_silent_fallback_gate_requires_runtime_artifact_truth_chain_for_supported_hosts() -> None:
    gate = (REPO_ROOT / "scripts" / "verify" / "vibe-no-silent-fallback-contract-gate.ps1").read_text(encoding="utf-8")

    assert "route_snapshot" in gate
    assert "specialist_dispatch" in gate
    assert "specialist_recommendations" in gate
    assert "execution_manifest" in gate
    assert "codex" in gate
    assert "claude-code" in gate
    assert "opencode" in gate
