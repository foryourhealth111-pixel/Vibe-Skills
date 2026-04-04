from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_sdk_resolves_metadata_from_contracts_registry_support_surface() -> None:
    loader = (REPO_ROOT / 'packages' / 'adapter-sdk' / 'src' / 'vgo_adapters' / 'descriptor_loader.py').read_text(encoding='utf-8')
    resolver = (REPO_ROOT / 'packages' / 'adapter-sdk' / 'src' / 'vgo_adapters' / 'target_root_resolver.py').read_text(encoding='utf-8')
    contracts_init = (REPO_ROOT / 'packages' / 'contracts' / 'src' / 'vgo_contracts' / '__init__.py').read_text(encoding='utf-8')
    support = (REPO_ROOT / 'packages' / 'contracts' / 'src' / 'vgo_contracts' / 'adapter_registry_support.py').read_text(encoding='utf-8')
    descriptor_contract = (REPO_ROOT / 'packages' / 'contracts' / 'src' / 'vgo_contracts' / 'adapter_descriptor.py').read_text(encoding='utf-8')

    assert 'from vgo_contracts.adapter_registry_support import load_adapter_registry, resolve_adapter_entry' in loader
    assert "default_target_root_env: str = ''" in descriptor_contract
    assert "default_target_root_kind: str = ''" in descriptor_contract
    assert "default_target_root_env=str(target_root.get('env') or '')" in loader
    assert "default_target_root_kind=str(target_root.get('kind') or '')" in loader
    assert 'load_descriptor_payload' not in resolver
    assert "getattr(descriptor, 'default_target_root_env', '')" in resolver
    assert "getattr(descriptor, 'default_target_root', '')" in resolver
    assert 'def resolve_adapter_registry_path(' in support
    assert 'def load_adapter_registry(' in support
    assert 'def normalize_adapter_host_id(' in support
    assert 'def resolve_adapter_entry(' in support
    assert 'resolve_adapter_registry_path' in contracts_init
    assert '_resolve_registry_path' not in loader
    assert '_load_registry' not in loader
    assert '_normalize_host_id' not in loader
    assert "'descriptors'" not in loader
    assert "'descriptors'" not in resolver


def test_adapter_sdk_no_longer_keeps_package_local_descriptor_truth_surface() -> None:
    descriptor_dir = REPO_ROOT / 'packages' / 'adapter-sdk' / 'src' / 'vgo_adapters' / 'descriptors'
    assert not descriptor_dir.exists()
