from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_platform_doctor_parity_gate_prefers_registry_and_host_profile_contracts() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-platform-doctor-parity-gate.ps1').read_text(encoding='utf-8')

    assert r'config\adapter-registry.json' in content
    assert 'supported_platform_contracts' in content
    assert "adapters/codex/platform-windows.json" not in content
    assert "adapters/codex/platform-linux.json" not in content
    assert "adapters/codex/platform-macos.json" not in content
