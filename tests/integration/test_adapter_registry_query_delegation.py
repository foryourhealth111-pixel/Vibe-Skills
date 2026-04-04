from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_registry_query_delegates_core_registry_semantics_to_installer_core() -> None:
    content = (REPO_ROOT / 'scripts' / 'common' / 'adapter_registry_query.py').read_text(encoding='utf-8')

    assert 'from vgo_installer import adapter_registry as module' in content
    assert 'resolve_registry_path = _ADAPTER_REGISTRY.resolve_registry_path' in content
    assert 'resolve_registry = _ADAPTER_REGISTRY.resolve_registry' in content
    assert 'resolve_adapter = _ADAPTER_REGISTRY.resolve_adapter' in content
    assert 'resolve_bootstrap_choices = _ADAPTER_REGISTRY.resolve_bootstrap_choices' in content
    assert 'resolve_supported_hosts = _ADAPTER_REGISTRY.resolve_supported_hosts' in content
    assert 'resolve_target_root_owner = _ADAPTER_REGISTRY.resolve_target_root_owner' in content
    assert 'def default_bootstrap_summary(' not in content
    assert 'def bootstrap_choices(' not in content
    assert 'def supported_hosts(' not in content
    assert 'def path_matches_relative_signature(' not in content
    assert 'def resolve_target_root_owner(' not in content
