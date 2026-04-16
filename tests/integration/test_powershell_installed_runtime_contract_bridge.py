from pathlib import Path
import json


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_installed_runtime_defaults_delegate_to_contract_bridge_with_compat_fallback() -> None:
    helper = (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8")
    bridge = (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8")

    assert "installed-runtime-config" in bridge
    assert "default_installed_runtime_config" in bridge
    assert "default_coherence_runtime_config" in bridge
    assert "Get-VgoInstalledRuntimeDefaultsFromContracts" in helper
    assert "function Get-VgoRuntimeEntrypointPath" in helper
    assert "Get-VgoInstalledRuntimeEmergencyFallbackDefaults" in helper
    assert "Get-VgoInstalledRuntimeFallbackDefaults" in helper
    assert "$defaults = Get-VgoInstalledRuntimeEmergencyFallbackDefaults" in helper
    assert "runtime_contracts.py" in helper
    assert "frontmatter_gate = 'scripts/verify/vibe-bom-frontmatter-gate.ps1'" in helper
    assert "neutral_freshness_gate = 'scripts/verify/runtime_neutral/freshness_gate.py'" in helper
    assert "runtime_entrypoint = 'scripts/runtime/invoke-vibe-runtime.ps1'" in helper
    assert "install.ps1" not in helper.split("function Get-VgoInstalledRuntimeEmergencyFallbackDefaults", 1)[1].split("function Get-VgoInstalledRuntimeFallbackDefaults", 1)[0]


def test_official_runtime_baseline_surfaces_are_removed() -> None:
    assert not (REPO_ROOT / "scripts" / "verify" / "vibe-official-runtime-baseline-gate.ps1").exists()
    assert not (REPO_ROOT / "docs" / "universalization" / "official-runtime-baseline.md").exists()
    assert not (REPO_ROOT / "references" / "proof-bundles" / "official-runtime-baseline").exists()


def test_canonical_entry_truth_gate_rejects_doc_only_activation_claims() -> None:
    truth_gate = (REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1").read_text(encoding="utf-8")

    assert "host-launch-receipt.json" in truth_gate
    assert "reading SKILL.md alone is not canonical vibe entry" in truth_gate


def test_canonical_entry_bridge_and_truth_gating_contract_are_present() -> None:
    bridge_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1"
    launcher = (REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "canonical_entry.py").read_text(encoding="utf-8")

    assert bridge_path.exists()
    assert "MINIMUM_TRUTH_ARTIFACTS" in launcher
    assert "runtime_input_packet" in launcher
    assert "governance_capsule" in launcher
    assert "stage_lineage" in launcher
    assert "Missing required runtime artifacts" in launcher
