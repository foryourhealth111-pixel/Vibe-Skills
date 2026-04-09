from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
INSTALLER_SRC = ROOT / 'packages' / 'installer-core' / 'src'
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.install_plan import build_install_plan
from vgo_installer.ledger_service import (
    MaterializationLedgerState,
    build_install_ledger,
    build_payload_summary,
    sanitize_managed_skill_names,
)


def test_sanitize_managed_skill_names_rejects_traversal() -> None:
    assert sanitize_managed_skill_names(
        ['vibe', '../bad', 'brainstorming', '', 'brainstorming', 'nested/skill']
    ) == ['brainstorming', 'vibe']


def test_build_install_ledger_tracks_payload_summary(tmp_path) -> None:
    vibe_root = tmp_path / 'skills' / 'vibe'
    brainstorm_root = tmp_path / 'skills' / 'brainstorming'
    internal_non_core_root = tmp_path / 'skills' / 'vibe' / 'bundled' / 'skills' / 'scikit-learn'
    wrapper_root = tmp_path / 'commands'
    vibe_root.mkdir(parents=True)
    brainstorm_root.mkdir(parents=True)
    internal_non_core_root.mkdir(parents=True, exist_ok=True)
    wrapper_root.mkdir(parents=True, exist_ok=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    (brainstorm_root / 'SKILL.md').write_text('# brainstorming\n', encoding='utf-8')
    (internal_non_core_root / 'SKILL.runtime-mirror.md').write_text('# scikit-learn\n', encoding='utf-8')
    for name in ('vibe', 'vibe-want', 'vibe-how', 'vibe-do'):
        (wrapper_root / f'{name}.md').write_text(f'# {name}\n', encoding='utf-8')
    settings_path = tmp_path / 'settings.json'
    settings_path.write_text('{}\n', encoding='utf-8')

    plan = build_install_plan(
        profile='full',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe', 'brainstorming', 'scikit-learn'],
    )
    state = MaterializationLedgerState(
        created_paths={tmp_path, settings_path},
        managed_json_paths={settings_path},
        runtime_roots={vibe_root, tmp_path / 'skills' / 'vibe' / 'bundled' / 'skills'},
        compatibility_roots={brainstorm_root},
        sidecar_roots={tmp_path / '.vibeskills'},
        specialist_wrapper_paths=[wrapper_root / 'vibe.md', wrapper_root / 'vibe-want.md', wrapper_root / 'vibe-how.md', wrapper_root / 'vibe-do.md'],
        config_rollbacks=[{'path': settings_path, 'created_if_absent': False, 'managed_key': 'vibeskills'}],
        legacy_cleanup_candidates={tmp_path / 'skills' / 'legacy-skill'},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        external_fallback_used=['pwsh'],
        timestamp='2026-04-02T00:00:00Z',
    )

    assert ledger['managed_skill_names'] == ['brainstorming', 'scikit-learn', 'vibe']
    assert ledger['canonical_vibe_root'] == str((tmp_path / 'skills' / 'vibe').resolve())
    assert ledger['schema_version'] == 2
    assert ledger['payload_summary']['installed_skill_names'] == ['brainstorming', 'scikit-learn', 'vibe']
    assert ledger['payload_summary']['public_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['payload_summary']['host_visible_entry_names'] == ['vibe', 'vibe-do', 'vibe-how', 'vibe-want']
    assert ledger['payload_summary']['host_visible_entry_count'] == 4
    assert ledger['runtime_roots'] == ['skills/vibe', 'skills/vibe/bundled/skills']
    assert ledger['compatibility_roots'] == ['skills/brainstorming']
    assert ledger['sidecar_roots'] == ['.vibeskills']
    assert ledger['config_rollbacks'][0]['path'] == 'settings.json'
    assert ledger['legacy_cleanup_candidates'] == ['skills/legacy-skill']
    assert isinstance(ledger['payload_summary']['internal_skill_count'], int)
    assert ledger['payload_summary']['installed_file_count'] >= 3


def test_build_install_ledger_v2_ownership_keys_when_available(tmp_path) -> None:
    vibe_root = tmp_path / 'skills' / 'vibe'
    vibe_root.mkdir(parents=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')

    plan = build_install_plan(
        profile='full',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe'],
    )
    state = MaterializationLedgerState(
        created_paths={tmp_path},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        timestamp='2026-04-06T00:00:00Z',
    )

    required = {
        'runtime_roots',
        'compatibility_roots',
        'sidecar_roots',
        'config_rollbacks',
        'legacy_cleanup_candidates',
    }
    missing = required.difference(set(ledger))
    assert not missing, f'install ledger missing expected v2 payload keys: {sorted(missing)}'

    for key in ('runtime_roots', 'compatibility_roots', 'sidecar_roots', 'legacy_cleanup_candidates'):
        assert isinstance(ledger[key], list)
    assert isinstance(ledger['config_rollbacks'], list)


def test_payload_summary_counts_install_ledger_file_when_present(tmp_path) -> None:
    vibe_root = tmp_path / 'skills' / 'vibe'
    vibe_root.mkdir(parents=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')

    plan = build_install_plan(
        profile='minimal',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe'],
    )
    state = MaterializationLedgerState(
        created_paths={tmp_path},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        timestamp='2026-04-07T00:00:00Z',
    )
    ledger_path = tmp_path / '.vibeskills' / 'install-ledger.json'
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text('{}\n', encoding='utf-8')

    refreshed = build_payload_summary(tmp_path, ledger)

    assert refreshed['installed_file_count'] == 2


def test_payload_summary_counts_mcp_receipt_when_present(tmp_path) -> None:
    vibe_root = tmp_path / 'skills' / 'vibe'
    vibe_root.mkdir(parents=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')

    plan = build_install_plan(
        profile='minimal',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe'],
    )
    state = MaterializationLedgerState(
        created_paths={tmp_path},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        timestamp='2026-04-07T00:00:00Z',
    )
    sidecar_root = tmp_path / '.vibeskills'
    sidecar_root.mkdir(parents=True, exist_ok=True)
    (sidecar_root / 'mcp-auto-provision.json').write_text('{}\n', encoding='utf-8')

    refreshed = build_payload_summary(tmp_path, ledger)

    assert refreshed['installed_file_count'] == 2


def test_build_payload_summary_ignores_wrapper_paths_outside_target_root(tmp_path) -> None:
    with tempfile.TemporaryDirectory() as external_dir:
        external_wrapper = Path(external_dir) / 'vibe-how.md'
        external_wrapper.write_text('# vibe-how\n', encoding='utf-8')

        summary = build_payload_summary(
            tmp_path,
            {
                'managed_skill_names': [],
                'specialist_wrapper_paths': [str(external_wrapper)],
                'packaging_manifest': {},
                'runtime_roots': [],
                'compatibility_roots': [],
                'sidecar_roots': [],
                'owned_tree_roots': [],
                'created_paths': [],
                'managed_json_paths': [],
                'generated_from_template_if_absent': [],
                'merged_files': [],
                'config_rollbacks': [],
            },
        )

    assert summary['host_visible_entry_names'] == []
    assert summary['host_visible_entry_count'] == 0


def test_sanitize_managed_skill_names_stays_safe_with_v2_owned_root_like_values() -> None:
    # v2 introduces root-class ownership in ledgers; managed skill names must remain strict.
    assert sanitize_managed_skill_names(
        ['vibe', '/abs/path', '../escape', 'skills/vibe', 'dialectic']
    ) == ['dialectic', 'vibe']
