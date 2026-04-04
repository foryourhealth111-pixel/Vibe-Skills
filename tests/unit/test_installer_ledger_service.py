from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
INSTALLER_SRC = ROOT / 'packages' / 'installer-core' / 'src'
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.install_plan import build_install_plan
from vgo_installer.ledger_service import MaterializationLedgerState, build_install_ledger, sanitize_managed_skill_names


def test_sanitize_managed_skill_names_rejects_traversal() -> None:
    assert sanitize_managed_skill_names(
        ['vibe', '../bad', 'brainstorming', '', 'brainstorming', 'nested/skill']
    ) == ['brainstorming', 'vibe']


def test_build_install_ledger_tracks_payload_summary(tmp_path) -> None:
    vibe_root = tmp_path / 'skills' / 'vibe'
    brainstorm_root = tmp_path / 'skills' / 'brainstorming'
    vibe_root.mkdir(parents=True)
    brainstorm_root.mkdir(parents=True)
    (vibe_root / 'SKILL.md').write_text('# vibe\n', encoding='utf-8')
    (brainstorm_root / 'SKILL.md').write_text('# brainstorming\n', encoding='utf-8')
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
    )

    ledger = build_install_ledger(
        plan=plan,
        state=state,
        external_fallback_used=['pwsh'],
        timestamp='2026-04-02T00:00:00Z',
    )

    assert ledger['managed_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['canonical_vibe_root'] == str((tmp_path / 'skills' / 'vibe').resolve())
    assert ledger['payload_summary']['installed_skill_names'] == ['brainstorming', 'vibe']
    assert ledger['payload_summary']['installed_file_count'] >= 3
