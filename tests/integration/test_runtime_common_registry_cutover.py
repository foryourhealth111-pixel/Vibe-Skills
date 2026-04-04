from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vibe_runtime_common_delegates_adapter_registry_resolution_to_governance_helpers() -> None:
    helper = (REPO_ROOT / 'scripts' / 'common' / 'vibe-governance-helpers.ps1').read_text(encoding='utf-8')
    runtime = (REPO_ROOT / 'scripts' / 'runtime' / 'VibeRuntime.Common.ps1').read_text(encoding='utf-8')

    assert 'function Resolve-VgoAdapterEntry' in helper
    assert 'return Resolve-VgoAdapterEntry -StartPath $RepoRoot -HostId $HostId' in runtime
    assert r'adapters\index.json' not in runtime
    assert r'config\adapter-registry.json' not in runtime
