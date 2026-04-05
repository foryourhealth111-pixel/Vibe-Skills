from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_ROOT = REPO_ROOT / "apps"
VGO_CLI_ROOT = APPS_ROOT / "vgo-cli" / "src" / "vgo_cli"


class AppsSurfaceHygieneTests(unittest.TestCase):
    def test_apps_tree_contains_no_python_bytecode_residue(self) -> None:
        forbidden = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in APPS_ROOT.rglob("*")
            if path.is_file()
            and (path.suffix == ".pyc" or "__pycache__" in path.parts)
        )

        self.assertEqual([], forbidden)

    def test_vgo_cli_semantic_owner_files_remain_present(self) -> None:
        expected = [
            "__init__.py",
            "main.py",
            "commands.py",
            "core_bridge.py",
            "errors.py",
            "external.py",
            "hosts.py",
            "install_gates.py",
            "install_support.py",
            "installer_bridge.py",
            "output.py",
            "process.py",
            "repo.py",
            "skill_surface.py",
            "workspace.py",
        ]

        missing = [
            name for name in expected if not (VGO_CLI_ROOT / name).exists()
        ]

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
