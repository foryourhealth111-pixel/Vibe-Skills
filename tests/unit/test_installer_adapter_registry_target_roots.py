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
    resolve_canonical_vibe_contract,
    resolve_default_target_root,
    resolve_matching_target_root_hosts,
    resolve_target_root_owner,
    resolve_target_root_spec,
)


def test_resolve_target_root_spec_projects_registry_target_root_semantics() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'windsurf')

    assert normalized == 'windsurf'
    assert spec['env'] == 'WINDSURF_HOME'
    assert spec['rel'] == '.codeium/windsurf'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'runtime-core'


def test_resolve_target_root_spec_projects_codex_to_real_host_root() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'codex')

    assert normalized == 'codex'
    assert spec['env'] == 'CODEX_HOME'
    assert spec['rel'] == '.codex'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'governed'


def test_resolve_target_root_spec_projects_claude_code_to_real_host_root() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'claude-code')

    assert normalized == 'claude-code'
    assert spec['env'] == 'CLAUDE_HOME'
    assert spec['rel'] == '.claude'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'preview-guidance'


def test_resolve_target_root_spec_projects_cursor_to_real_host_root() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'cursor')

    assert normalized == 'cursor'
    assert spec['env'] == 'CURSOR_HOME'
    assert spec['rel'] == '.cursor'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'preview-guidance'


def test_resolve_target_root_spec_projects_openclaw_to_real_host_root() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'openclaw')

    assert normalized == 'openclaw'
    assert spec['env'] == 'OPENCLAW_HOME'
    assert spec['rel'] == '.openclaw'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'runtime-core'


def test_resolve_target_root_spec_projects_opencode_to_real_host_root() -> None:
    normalized, spec = resolve_target_root_spec(REPO_ROOT, 'opencode')

    assert normalized == 'opencode'
    assert spec['env'] == 'OPENCODE_HOME'
    assert spec['rel'] == '.config/opencode'
    assert spec['kind'] == 'host-home'
    assert spec['install_mode'] == 'preview-guidance'


def test_resolve_canonical_vibe_contract_projects_supported_hosts() -> None:
    codex = resolve_canonical_vibe_contract(REPO_ROOT, 'codex')
    claude = resolve_canonical_vibe_contract(REPO_ROOT, 'claude-code')
    opencode = resolve_canonical_vibe_contract(REPO_ROOT, 'opencode')

    assert codex['entry_mode'] == 'direct_runtime'
    assert codex['launcher_kind'] == 'native_command'
    assert codex['fallback_policy'] == 'blocked'
    assert codex['allow_skill_doc_fallback'] is False
    assert codex['proof_required'] is True
    assert codex['supports_bounded_stop'] is True
    assert claude['entry_mode'] == 'bridged_runtime'
    assert claude['launcher_kind'] == 'managed_bridge'
    assert opencode['entry_mode'] == 'bridged_runtime'
    assert opencode['launcher_kind'] == 'managed_bridge'


def test_resolve_default_target_root_uses_env_projection() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'windsurf',
        env={'WINDSURF_HOME': '/tmp/windsurf-home'},
        home='/home/tester',
    )

    assert resolved == Path('/tmp/windsurf-home').resolve()


def test_resolve_default_target_root_defaults_codex_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'codex',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.codex').resolve()


def test_resolve_default_target_root_defaults_claude_code_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'claude-code',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.claude').resolve()


def test_resolve_default_target_root_defaults_cursor_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'cursor',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.cursor').resolve()


def test_resolve_default_target_root_defaults_windsurf_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'windsurf',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.codeium/windsurf').resolve()


def test_resolve_default_target_root_defaults_openclaw_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'openclaw',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.openclaw').resolve()


def test_resolve_default_target_root_defaults_opencode_to_real_home_root() -> None:
    resolved = resolve_default_target_root(
        REPO_ROOT,
        'opencode',
        env={},
        home='/home/tester',
    )

    assert resolved == Path('/home/tester/.config/opencode').resolve()


def test_resolve_matching_target_root_hosts_preserves_opencode_compatibility_signature(tmp_path: Path) -> None:
    matches = resolve_matching_target_root_hosts(REPO_ROOT, str(tmp_path / '.opencode'))

    assert matches == ['opencode']


def test_resolve_target_root_owner_recognizes_cursor_home_signature(tmp_path: Path) -> None:
    owner = resolve_target_root_owner(REPO_ROOT, str(tmp_path / '.cursor'))

    assert owner == 'cursor'
