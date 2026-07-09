from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
INSTALLER_SRC = ROOT / "packages" / "installer-core" / "src"
if str(INSTALLER_SRC) not in sys.path:
    sys.path.insert(0, str(INSTALLER_SRC))

from vgo_installer.uninstall_service import host_inventory


def test_host_inventory_keeps_retired_wrapper_paths_for_legacy_cleanup() -> None:
    inventory = host_inventory(ROOT, "codex")

    assert "commands/vibe-what-do-i-want.md" in inventory
    assert "commands/vibe-how-do-we-do.md" in inventory
    assert "commands/vibe-do-it.md" in inventory
    assert "skills/vibe-what-do-i-want/SKILL.md" in inventory
    assert "skills/vibe-how-do-we-do/SKILL.md" in inventory
    assert "skills/vibe-do-it/SKILL.md" in inventory
    assert "skills/vibe-upgrade/SKILL.md" in inventory
