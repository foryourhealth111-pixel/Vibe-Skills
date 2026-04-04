from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_resolver_shim_delegates_to_installer_core_adapter_registry() -> None:
    content = (REPO_ROOT / 'scripts' / 'common' / 'resolve_vgo_adapter.py').read_text(encoding='utf-8')

    assert 'from vgo_installer import adapter_registry as module' in content
    assert 'resolve_registry_path = _ADAPTER_REGISTRY.resolve_registry_path' in content
    assert 'resolve_registry = _ADAPTER_REGISTRY.resolve_registry' in content
    assert 'resolve_adapter = _ADAPTER_REGISTRY.resolve_adapter' in content
    assert 'def resolve_adapter(' not in content


def test_powershell_resolver_shim_delegates_to_governance_helpers() -> None:
    content = (REPO_ROOT / 'scripts' / 'common' / 'Resolve-VgoAdapter.ps1').read_text(encoding='utf-8')

    assert 'vibe-governance-helpers.ps1' in content
    assert "registry = Get-VgoAdapterRegistryPayload -StartPath $resolution.root" in content
    assert 'Resolve-VgoAdapterEntry -StartPath $registryRoot -HostId $HostId' in content
    assert "source = 'vibe-governance-helpers'" in content
