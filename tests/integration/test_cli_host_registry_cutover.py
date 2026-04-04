from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vgo_cli_hosts_delegate_adapter_registry_resolution_to_installer_core() -> None:
    hosts = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'hosts.py').read_text(encoding='utf-8')
    workspace = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'workspace.py').read_text(encoding='utf-8')

    assert 'def extend_workspace_package_path(' in workspace
    assert 'def _resolve_workspace_repo_root(' in hosts
    assert 'from .workspace import extend_workspace_package_path' in hosts
    assert 'from vgo_installer import adapter_registry as module' in hosts
    assert 'module.resolve_adapter(repo_root, requested_host)' in hosts
    assert 'module.resolve_target_root_spec(repo_root, requested_host)' in hosts
    assert 'module.resolve_default_target_root(repo_root, requested_host, env=dict(os.environ), home=Path.home())' in hosts
    assert 'module.resolve_matching_target_root_hosts(repo_root, str(target_root))' in hosts
    assert 'def _adapter_registry(' not in hosts
    assert 'def _path_matches_relative_signature(' not in hosts
    assert 'def _target_root_signatures(' not in hosts
    assert "registry.get('adapters')" not in hosts
    assert 'HOST_SPECS' not in hosts
    assert 'HOST_ALIASES' not in hosts



def test_vgo_cli_host_guard_uses_registry_driven_signatures() -> None:
    hosts = (REPO_ROOT / 'apps' / 'vgo-cli' / 'src' / 'vgo_cli' / 'hosts.py').read_text(encoding='utf-8')
    adapter_registry = (REPO_ROOT / 'packages' / 'installer-core' / 'src' / 'vgo_installer' / 'adapter_registry.py').read_text(encoding='utf-8')

    assert 'matching_hosts' in hosts
    assert 'resolve_matching_target_root_hosts' in hosts
    assert 'def _target_root_signatures(' not in hosts
    assert 'def _target_root_signatures(' in adapter_registry
    assert '.opencode' in adapter_registry
    assert "'.cursor'" not in hosts
