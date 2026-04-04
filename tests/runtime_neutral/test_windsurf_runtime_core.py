from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"
RESOLVER = REPO_ROOT / "scripts" / "common" / "resolve_vgo_adapter.py"


class WindsurfRuntimeCoreTests(unittest.TestCase):
    def test_adapter_registry_exposes_windsurf_parallel_root(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(RESOLVER),
                "--repo-root",
                str(REPO_ROOT),
                "--host",
                "windsurf",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("windsurf", payload["id"])
        self.assertEqual("runtime-core", payload["install_mode"])
        self.assertEqual(".vibeskills/targets/windsurf", payload["default_target_root"]["rel"])
        self.assertEqual("isolated-home", payload["default_target_root"]["kind"])

    def test_python_installer_uses_runtime_core_without_codex_host_state(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--repo-root",
                    str(REPO_ROOT),
                    "--target-root",
                    str(target_root),
                    "--host",
                    "windsurf",
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(result.stdout)

            self.assertEqual("windsurf", payload["host_id"])
            self.assertEqual("runtime-core", payload["install_mode"])
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "skills" / "brainstorming" / "SKILL.md").exists())
            self.assertTrue((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())
            self.assertFalse((target_root / "config" / "plugins-manifest.codex.json").exists())

    def test_shell_install_and_check_support_windsurf_runtime_core(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "windsurf",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host   : windsurf", install_result.stdout)
            self.assertIn("Mode   : runtime-core", install_result.stdout)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())

            check_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "windsurf",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host: windsurf", check_result.stdout)
            self.assertNotIn("[FAIL] settings.json", check_result.stdout)


if __name__ == "__main__":
    unittest.main()
