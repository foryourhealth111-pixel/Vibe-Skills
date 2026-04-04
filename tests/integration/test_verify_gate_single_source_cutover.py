from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_host_adapter_contract_gate_prefers_registry_driven_contracts() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-host-adapter-contract-gate.ps1').read_text(encoding='utf-8')

    assert r'config\adapter-registry.json' in content
    assert 'supported_platform_contracts' in content
    assert "codex/settings-map.json" not in content
    assert "windsurf must remain preview until broader proof exists" not in content


def test_dist_manifest_gate_prefers_source_config_and_registry_truth() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-dist-manifest-gate.ps1').read_text(encoding='utf-8')

    assert r'config\distribution-manifest-sources.json' in content
    assert r'config\adapter-registry.json' in content
    assert 'inherit_official_runtime' in content
    assert "package_id = 'vibeskills-codex'" not in content
    assert "$manifest.lane_id -eq 'host-codex'" not in content
    assert "Find-MarkdownTableRow -Path $docsHostCapabilityMatrix -RowStartsWith '| Codex |'" not in content


def test_host_capability_schema_gate_prefers_discovered_profiles_and_registry() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-host-capability-schema-gate.ps1').read_text(encoding='utf-8')

    assert r'config\adapter-registry.json' in content
    assert 'host-capability-matrix.md' in content
    assert "Get-ChildItem -Path $adapterRoot -Recurse -Filter 'host-profile.json'" in content
    assert "duplicate host capability matrix rows" in content
    assert "'codex/host-profile.json'" not in content


def test_uninstall_coherence_gate_prefers_registry_driven_closure_paths() -> None:
    content = (REPO_ROOT / 'scripts' / 'verify' / 'vibe-uninstall-coherence-gate.ps1').read_text(encoding='utf-8')

    assert 'adapter-registry.json' in content
    assert 'adapterClosures' in content
    assert "'adapters', 'codex', 'closure.json'" not in content
