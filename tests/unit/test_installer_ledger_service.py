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
    wrapper_root = tmp_path / 'commands'
    vibe_root.mkdir(parents=True)
    brainstorm_root.mkdir(parents=True)
    wrapper_root.mkdir(parents=True, exist_ok=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    (brainstorm_root / 'SKILL.md').write_text('# brainstorming\n', encoding='utf-8')
    for name in ('vibe',):
        (wrapper_root / f'{name}.md').write_text(f'# {name}\n', encoding='utf-8')
    settings_path = tmp_path / 'settings.json'
    settings_path.write_text('{}\n', encoding='utf-8')

    plan = build_install_plan(
        profile='full',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe', 'brainstorming'],
    )
    state = MaterializationLedgerState(
        created_paths={tmp_path, settings_path},
        managed_json_paths={settings_path},
        runtime_roots={vibe_root},
        compatibility_roots={brainstorm_root},
        sidecar_roots={tmp_path / '.vibeskills'},
        host_visible_entry_paths=[
            wrapper_root / 'vibe.md',
        ],
        config_rollbacks=[{'path': settings_path, 'created_if_absent': False, 'managed_key': 'vibeskills'}],
        legacy_cleanup_candidates={tmp_path / 'skills' / 'legacy-skill'},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        external_fallback_used=['pwsh'],
        timestamp='2026-04-02T00:00:00Z',
    )

    assert ledger['managed_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['canonical_vibe_root'] == str((tmp_path / 'skills' / 'vibe').resolve())
    assert ledger['schema_version'] == 2
    assert ledger['runtime_root'] == str(tmp_path.resolve())
    assert ledger['host_bridge_root'] == str(tmp_path.resolve())
    assert ledger['desired_shared_runtime_root'] == str(tmp_path.resolve())
    assert ledger['runtime_layout_mode'] == 'co-located'
    assert ledger['payload_summary']['installed_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['payload_summary']['public_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['payload_summary']['host_visible_entry_names'] == ['vibe']
    assert ledger['host_visible_entry_paths'] == [str((wrapper_root / 'vibe.md').resolve())]
    assert 'specialist_wrapper_paths' not in ledger
    assert 'installed_skill_count' not in ledger['payload_summary']
    assert 'public_skill_count' not in ledger['payload_summary']
    assert 'host_visible_entry_count' not in ledger['payload_summary']
    assert ledger['runtime_roots'] == ['skills/vibe']
    assert ledger['compatibility_roots'] == ['skills/brainstorming']
    assert ledger['sidecar_roots'] == ['.vibeskills']
    assert ledger['config_rollbacks'][0]['path'] == 'settings.json'
    assert ledger['legacy_cleanup_candidates'] == ['skills/legacy-skill']
    assert 'internal_skill_count' not in ledger['payload_summary']
    assert ledger['payload_summary']['installed_file_count'] >= 3
    assert ledger['internal_skill_target_relpath'] == ''
    assert 'packaging_manifest' not in ledger


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


def test_build_install_ledger_keeps_runtime_layout_metadata_when_runtime_and_bridge_split(tmp_path) -> None:
    runtime_root = tmp_path / '.agents'
    bridge_root = tmp_path / '.codex'
    shared_root = tmp_path / '.agents'
    vibe_root = bridge_root / 'skills' / 'vibe'
    vibe_root.mkdir(parents=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')

    plan = build_install_plan(
        profile='full',
        host_id='codex',
        target_root=bridge_root,
        runtime_root=runtime_root,
        host_bridge_root=bridge_root,
        desired_shared_runtime_root=shared_root,
        runtime_layout_mode='split-shared-runtime',
        managed_skill_names=['vibe'],
    )
    state = MaterializationLedgerState(
        created_paths={bridge_root},
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        timestamp='2026-06-26T00:00:00Z',
    )

    assert ledger['target_root'] == str(bridge_root.resolve())
    assert ledger['runtime_root'] == str(runtime_root.resolve())
    assert ledger['host_bridge_root'] == str(bridge_root.resolve())
    assert ledger['desired_shared_runtime_root'] == str(shared_root.resolve())
    assert ledger['runtime_layout_mode'] == 'split-shared-runtime'


def test_build_payload_summary_reads_installed_skills_from_external_runtime_root(tmp_path) -> None:
    runtime_root = tmp_path / '.agents'
    bridge_root = tmp_path / '.openclaw'
    (runtime_root / 'skills' / 'vibe').mkdir(parents=True)
    (runtime_root / 'skills' / 'vibe' / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    (runtime_root / 'skills' / 'verification-before-completion').mkdir(parents=True)
    (runtime_root / 'skills' / 'verification-before-completion' / 'SKILL.md').write_text(
        '# verification-before-completion\n',
        encoding='utf-8',
    )
    (bridge_root / 'skills' / 'vibe').mkdir(parents=True)
    (bridge_root / 'skills' / 'vibe' / 'SKILL.md').write_text('# wrapper vibe\n', encoding='utf-8')

    summary = build_payload_summary(
        bridge_root,
        {
            'managed_skill_names': ['vibe', 'verification-before-completion'],
            'runtime_root': str(runtime_root.resolve()),
            'internal_skill_target_relpath': '',
            'host_visible_entry_paths': [str((bridge_root / 'skills' / 'vibe' / 'SKILL.md').resolve())],
            'runtime_roots': ['skills/vibe'],
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

    assert summary['installed_skill_names'] == ['verification-before-completion', 'vibe']
    assert summary['public_skill_names'] == ['verification-before-completion', 'vibe']
    assert summary['host_visible_entry_names'] == ['vibe']


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


def test_payload_summary_counts_upgrade_status_when_present(tmp_path) -> None:
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
    (sidecar_root / 'upgrade-status.json').write_text('{}\n', encoding='utf-8')

    refreshed = build_payload_summary(tmp_path, ledger)

    assert refreshed['installed_file_count'] == 2


def test_build_payload_summary_ignores_host_visible_entry_paths_outside_target_root(tmp_path) -> None:
    with tempfile.TemporaryDirectory() as external_dir:
        external_wrapper = Path(external_dir) / 'vibe-how-do-we-do.md'
        external_wrapper.write_text('# vibe-how-do-we-do\n', encoding='utf-8')

        summary = build_payload_summary(
            tmp_path,
            {
                'managed_skill_names': [],
                'host_visible_entry_paths': [str(external_wrapper)],
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
    assert 'host_visible_entry_count' not in summary


def test_sanitize_managed_skill_names_stays_safe_with_v2_owned_root_like_values() -> None:
    # v2 introduces root-class ownership in ledgers; managed skill names must remain strict.
    assert sanitize_managed_skill_names(
        ['vibe', '/abs/path', '../escape', 'skills/vibe', 'dialectic']
    ) == ['dialectic', 'vibe']
