from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER_CORE_SRC = REPO_ROOT / 'packages' / 'installer-core' / 'src'
CONTRACTS_SRC = REPO_ROOT / 'packages' / 'contracts' / 'src'
for src in (INSTALLER_CORE_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.adapter_registry import (
    resolve_default_target_root,
    resolve_matching_target_root_hosts,
    resolve_target_root_spec,
)


def test_resolve_target_root_spec_projects_registry_target_root_semantics() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'windsurf')

    assert normalized == 'windsurf'
    assert spec['env'] == 'WINDSURF_HOME'
    assert spec['rel'] == '.codeium/windsurf'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'runtime-core'


def test_resolve_default_target_root_uses_env_projection() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'windsurf',
        env={'WINDSURF_HOME': '/tmp/windsurf-home'},
        home='/home/tester',
    )

    assert resolved == Path('/tmp/windsurf-home').resolve()


def test_resolve_matching_target_root_hosts_preserves_opencode_compatibility_signature(tmp_path: Path) -> None:
    matches = resolve_matching_target_root_hosts(REPO_ROOT, str(tmp_path / '.opencode'))

    assert matches == ['opencode']
