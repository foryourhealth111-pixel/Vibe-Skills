from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = ROOT / "packages" / "contracts" / "src"
INSTALLER_SRC = ROOT / "packages" / "installer-core" / "src"
for src in (CONTRACTS_SRC, INSTALLER_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_contracts.discoverable_entry_surface import load_discoverable_entry_surface
from vgo_installer.install_runtime import (
    prune_retired_discoverable_wrapper_paths,
    retired_discoverable_entry_ids,
)


def test_retired_discoverable_entry_ids_are_kept_for_cleanup_only() -> None:
    surface = load_discoverable_entry_surface(ROOT)

    assert set(surface.entry_by_id) == {"vibe"}
    assert retired_discoverable_entry_ids(surface) == [
        "vibe-what-do-i-want",
        "vibe-how-do-we-do",
        "vibe-do-it",
        "vibe-upgrade",
    ]


def test_prune_retired_discoverable_wrapper_paths_removes_old_installed_wrappers(tmp_path: Path) -> None:
    surface = load_discoverable_entry_surface(ROOT)
    target_root = tmp_path / "host"
    current_wrapper = target_root / "commands" / "vibe.md"
    retired_command = target_root / "commands" / "vibe-how-do-we-do.md"
    retired_skill = target_root / "skills" / "vibe-upgrade" / "SKILL.md"

    current_wrapper.parent.mkdir(parents=True, exist_ok=True)
    retired_command.parent.mkdir(parents=True, exist_ok=True)
    retired_skill.parent.mkdir(parents=True, exist_ok=True)
    current_wrapper.write_text("# vibe\n", encoding="utf-8")
    retired_command.write_text("# vibe-how-do-we-do\n", encoding="utf-8")
    retired_skill.write_text("---\nname: vibe-upgrade\n---\n", encoding="utf-8")

    previous_install_ledger = {
        "created_paths": [
            str(current_wrapper),
            str(retired_command),
            str(retired_skill),
            str(retired_skill.parent),
        ],
    }

    prune_retired_discoverable_wrapper_paths(
        target_root,
        surface,
        [current_wrapper],
        previous_install_ledger,
    )

    assert current_wrapper.exists()
    assert not retired_command.exists()
    assert not retired_skill.exists()
    assert not retired_skill.parent.exists()
