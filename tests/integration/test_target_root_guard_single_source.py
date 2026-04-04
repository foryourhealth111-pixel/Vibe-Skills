from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vgo_target_root_guard_gate_generates_cases_from_host_catalog() -> None:
    gate = (REPO_ROOT / 'scripts' / 'verify' / 'vgo-adapter-target-root-guard-gate.ps1').read_text(encoding='utf-8')

    assert 'Resolve-VgoHostCatalog' in gate
    assert 'default-target-root' in gate
    assert "@{ host = 'codex'" not in gate


def test_vgo_governance_helpers_prefers_registry_driven_host_resolution() -> None:
    helper = (REPO_ROOT / 'scripts' / 'common' / 'vibe-governance-helpers.ps1').read_text(encoding='utf-8')

    assert r'config\adapter-registry.json' in helper
    assert 'Resolve-VgoHostCatalog' in helper
    assert "return [System.IO.Path]::GetFullPath((Join-Path $homeDir '.codex'))" not in helper
    assert "switch ($resolvedHostId)" not in helper
