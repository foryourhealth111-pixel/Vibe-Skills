from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_powershell_installed_runtime_defaults_delegate_to_contract_bridge_with_compat_fallback() -> None:
    helper = (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8")
    bridge = (REPO_ROOT / "scripts" / "common" / "runtime_contracts.py").read_text(encoding="utf-8")
    baseline = (REPO_ROOT / "scripts" / "verify" / "vibe-official-runtime-baseline-gate.ps1").read_text(encoding="utf-8")

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
    assert "$runtimeConfig.frontmatter_gate" in baseline
    assert "frontmatter_gate declaration matches effective runtime contract" in baseline
    assert "frontmatter_gate points to vibe-bom-frontmatter-gate.ps1" not in baseline
