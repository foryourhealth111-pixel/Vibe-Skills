from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATES = [
    REPO_ROOT / "scripts" / "verify" / "vibe-benchmark-autonomous-proof-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-governed-runtime-contract-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-specialist-dispatch-closure-gate.ps1",
    REPO_ROOT / "scripts" / "verify" / "vibe-child-specialist-escalation-gate.ps1",
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
