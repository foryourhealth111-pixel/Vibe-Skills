from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
INSTALLER_SRC = ROOT / 'packages' / 'installer-core' / 'src'
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface
import vgo_installer.discoverable_wrappers as discoverable_wrappers
from vgo_installer.discoverable_wrappers import build_wrapper_descriptors


def test_build_wrapper_descriptors_renders_all_discoverable_entries_for_codex() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    rendered = build_wrapper_descriptors(
        host_id='codex',
        surface=surface,
    )

    assert sorted(rendered) == ['vibe', 'vibe-upgrade']
    assert rendered['vibe'].relpath.as_posix() == 'commands/vibe.md'
    assert rendered['vibe-upgrade'].relpath.as_posix() == 'skills/vibe-upgrade/SKILL.md'
    assert 'Wrapper entry: Vibe (`vibe`)' in rendered['vibe'].content
    assert '"schema": "vibe-wrapper-trampoline/v1"' in rendered['vibe'].content
    assert '"launch_mode": "canonical-entry"' in rendered['vibe'].content
    assert '"host_id": "codex"' in rendered['vibe'].content
    assert '"entry_id": "vibe"' in rendered['vibe'].content
    assert '"entry_id": "vibe-upgrade"' in rendered['vibe-upgrade'].content
    assert '"progressive_stage_stops": [' in rendered['vibe'].content
    assert 'Progressive stop sequence: `requirement_doc`, `xl_plan`, `phase_cleanup`' in rendered['vibe'].content
    assert 'Do not consume `--continue-from-run-id` and `--bounded-reentry-token` in the same assistant turn' in rendered['vibe'].content
    assert 'Dispatch through canonical-entry runtime bridge.' in rendered['vibe'].content
    assert 'Do not preflight-scan the current workspace or repository for canonical proof files before launch.' in rendered['vibe'].content
    assert 'validate canonical proof artifacts only inside that launched session root.' in rendered['vibe'].content
    assert 'Wrapper labels only select the bounded terminal stage.' in rendered['vibe'].content
    assert 'name: vibe-upgrade' in rendered['vibe-upgrade'].content
    assert 'Wrapper entry: Vibe: Upgrade (`vibe-upgrade`)' in rendered['vibe-upgrade'].content
    assert '"entry_id": "vibe-upgrade"' in rendered['vibe-upgrade'].content
    assert 'default to upgrading the current host installation' in rendered['vibe-upgrade'].content


def test_build_wrapper_descriptors_renders_skill_wrappers_for_skill_only_hosts() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    rendered = build_wrapper_descriptors(
        host_id='claude-code',
        surface=surface,
    )

    assert sorted(rendered) == ['vibe', 'vibe-upgrade']
    assert rendered['vibe'].relpath.as_posix() == 'skills/vibe/SKILL.md'
    assert rendered['vibe-upgrade'].relpath.as_posix() == 'skills/vibe-upgrade/SKILL.md'
    assert 'name: vibe' in rendered['vibe'].content
    assert 'Wrapper entry: Vibe (`vibe`)' in rendered['vibe'].content
    assert '"schema": "vibe-wrapper-trampoline/v1"' in rendered['vibe'].content
    assert '"launch_mode": "canonical-entry"' in rendered['vibe'].content
    assert '"host_id": "claude-code"' in rendered['vibe'].content
    assert '"entry_id": "vibe"' in rendered['vibe'].content
    assert '"entry_id": "vibe-upgrade"' in rendered['vibe-upgrade'].content
    assert '"progressive_stage_stops": [' in rendered['vibe'].content
    assert 'Progressive stop sequence: `requirement_doc`, `xl_plan`, `phase_cleanup`' in rendered['vibe'].content
    assert 'Dispatch through canonical-entry runtime bridge.' in rendered['vibe'].content
    assert 'Do not preflight-scan the current workspace or repository for canonical proof files before launch.' in rendered['vibe'].content
    assert 'validate canonical proof artifacts only inside that launched session root.' in rendered['vibe'].content
    assert '$ARGUMENTS' in rendered['vibe'].content
    assert 'name: vibe-upgrade' in rendered['vibe-upgrade'].content
    assert 'Wrapper entry: Vibe: Upgrade (`vibe-upgrade`)' in rendered['vibe-upgrade'].content


def test_build_wrapper_descriptors_renders_upgrade_as_skill_for_command_hosts() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    rendered = build_wrapper_descriptors(
        host_id='opencode',
        surface=surface,
    )

    assert rendered['vibe'].relpath.as_posix() == 'commands/vibe.md'
    assert rendered['vibe-upgrade'].relpath.as_posix() == 'skills/vibe-upgrade/SKILL.md'
    assert 'name: vibe-upgrade' in rendered['vibe-upgrade'].content
    assert 'Wrapper entry: Vibe: Upgrade (`vibe-upgrade`)' in rendered['vibe-upgrade'].content


def test_build_wrapper_descriptors_fails_closed_when_canonical_contract_is_unresolved(monkeypatch) -> None:
    surface = load_discoverable_entry_surface(ROOT)

    def fail_contract(repo_root, host_id):  # type: ignore[no-untyped-def]
        raise ValueError(f"canonical_vibe contract missing for host: {host_id}")

    monkeypatch.setattr(discoverable_wrappers, "resolve_canonical_vibe_contract", fail_contract)

    with pytest.raises(ValueError, match="canonical_vibe contract missing"):
        build_wrapper_descriptors(
            host_id="codex",
            surface=surface,
        )
