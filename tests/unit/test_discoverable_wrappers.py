from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
INSTALLER_SRC = ROOT / 'packages' / 'installer-core' / 'src'
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface
from vgo_installer.discoverable_wrappers import build_wrapper_descriptors


def test_build_wrapper_descriptors_renders_all_discoverable_entries_for_codex() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    rendered = build_wrapper_descriptors(
        host_id='codex',
        surface=surface,
    )

    assert sorted(rendered) == ['vibe', 'vibe-do', 'vibe-how', 'vibe-upgrade', 'vibe-want']
    assert rendered['vibe-how'].relpath.as_posix() == 'commands/vibe-how.md'
    assert rendered['vibe-upgrade'].relpath.as_posix() == 'commands/vibe-upgrade.md'
    assert 'Vibe: How Do We Do It?' in rendered['vibe-how'].content
    assert 'Vibe: Upgrade' in rendered['vibe-upgrade'].content
    assert '"schema": "vibe-wrapper-trampoline/v1"' in rendered['vibe-how'].content
    assert '"launch_mode": "canonical-entry"' in rendered['vibe-how'].content
    assert '"host_id": "codex"' in rendered['vibe-how'].content
    assert '"entry_id": "vibe-how"' in rendered['vibe-how'].content
    assert 'Dispatch through canonical-entry runtime bridge.' in rendered['vibe-how'].content
    assert 'report blocked instead of silently falling back' in rendered['vibe-how'].content
    assert 'Use the `vibe` skill' not in rendered['vibe-how'].content
    assert 'Default stop target: `xl_plan`' in rendered['vibe-how'].content
    assert 'Default stop target: `requirement_doc`' in rendered['vibe-want'].content
    assert 'Public grade flags allowed: no' in rendered['vibe-upgrade'].content


def test_build_wrapper_descriptors_renders_skill_wrappers_for_skill_only_hosts() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    rendered = build_wrapper_descriptors(
        host_id='claude-code',
        surface=surface,
    )

    assert sorted(rendered) == ['vibe', 'vibe-do', 'vibe-how', 'vibe-upgrade', 'vibe-want']
    assert rendered['vibe-how'].relpath.as_posix() == 'skills/vibe-how/SKILL.md'
    assert rendered['vibe-upgrade'].relpath.as_posix() == 'skills/vibe-upgrade/SKILL.md'
    assert 'name: vibe-how' in rendered['vibe-how'].content
    assert 'name: vibe-upgrade' in rendered['vibe-upgrade'].content
    assert 'Vibe: How Do We Do It?' in rendered['vibe-how'].content
    assert 'Vibe: Upgrade' in rendered['vibe-upgrade'].content
    assert '"schema": "vibe-wrapper-trampoline/v1"' in rendered['vibe-how'].content
    assert '"launch_mode": "canonical-entry"' in rendered['vibe-how'].content
    assert '"host_id": "claude-code"' in rendered['vibe-how'].content
    assert '"entry_id": "vibe-how"' in rendered['vibe-how'].content
    assert 'Dispatch through canonical-entry runtime bridge.' in rendered['vibe-how'].content
    assert 'Use the `vibe` skill' not in rendered['vibe-how'].content
    assert 'Default stop target: `xl_plan`' in rendered['vibe-how'].content
    assert '$ARGUMENTS' in rendered['vibe-how'].content
