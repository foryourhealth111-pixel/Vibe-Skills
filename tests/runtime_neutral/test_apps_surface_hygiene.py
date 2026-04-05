from __future__ import annotations

import unittest

from _python_source_roots import PYTHON_SOURCE_ROOTS, REPO_ROOT

VGO_CLI_ROOT = REPO_ROOT / "apps" / "vgo-cli" / "src" / "vgo_cli"


class AppsSurfaceHygieneTests(unittest.TestCase):
    def test_repo_owned_python_surfaces_contain_no_python_bytecode_residue(self) -> None:
        forbidden = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for root in PYTHON_SOURCE_ROOTS
            if root.exists()
            for path in root.rglob("*")
            if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts)
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
