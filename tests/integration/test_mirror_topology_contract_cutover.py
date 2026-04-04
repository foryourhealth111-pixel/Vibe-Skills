from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_topology_consumers_delegate_to_contract_helper() -> None:
    helper = (REPO_ROOT / 'packages' / 'contracts' / 'src' / 'vgo_contracts' / 'mirror_topology_contract.py').read_text(encoding='utf-8')
    materializer = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'materializer.py').read_text(encoding='utf-8')
    uninstall_service = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'uninstall_service.py').read_text(encoding='utf-8')
    policies = (REPO_ROOT / 'packages' / 'verification-core' / 'src' / 'vgo_verify' / 'policies.py').read_text(encoding='utf-8')

    assert 'def resolve_mirror_topology_targets(' in helper
    assert 'def resolve_canonical_mirror_relpath(' in helper
    assert 'def resolve_generated_nested_compatibility_suffix(' in helper

    assert 'from vgo_contracts.mirror_topology_contract import (' in materializer
    assert 'resolve_canonical_mirror_relpath' in materializer
    assert 'resolve_generated_nested_compatibility_suffix' in materializer
    assert 'governance["source_of_truth"]["canonical_root"]' not in materializer
    assert 'topology = governance.get("mirror_topology") or {}' not in materializer
    assert 'source = governance.get("source_of_truth") or {}' not in materializer

    assert 'from vgo_contracts.mirror_topology_contract import resolve_generated_nested_compatibility_suffix' in uninstall_service
    assert 'topology = governance.get("mirror_topology") or {}' not in uninstall_service
    assert 'source = governance.get("source_of_truth") or {}' not in uninstall_service

    assert 'resolve_mirror_topology_targets as _contract_resolve_mirror_targets' in policies
    assert 'def _mirror_topology_targets_fallback(' in policies
    assert 'def _attach_full_paths(' in policies
