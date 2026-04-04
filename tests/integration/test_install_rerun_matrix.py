from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
INSTALLER_SRC = ROOT / 'packages' / 'installer-core' / 'src'
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_installer.install_plan import build_install_plan


def test_build_install_plan_preserves_rerun_semantics(tmp_path) -> None:
    previous_skill_root = tmp_path / 'skills' / 'legacy-skill'
    previous_skill_root.mkdir(parents=True)
    (previous_skill_root / 'SKILL.md').write_text('# legacy\n', encoding='utf-8')

    plan = build_install_plan(
        profile='full',
        host_id='codex',
        target_root=tmp_path,
        managed_skill_names=['vibe', 'brainstorming'],
        existing_install_ledger={
            'managed_skill_names': ['legacy-skill', '../bad'],
            'created_paths': [str(previous_skill_root)],
            'canonical_vibe_root': str(tmp_path / 'skills' / 'vibe'),
        },
    )

    assert plan.profile == 'full'
    assert plan.host_id == 'codex'
    assert plan.target_root == tmp_path.resolve()
    assert plan.managed_skill_names == ('brainstorming', 'vibe')
    assert plan.previous_managed_skill_names == ('legacy-skill', 'vibe')
