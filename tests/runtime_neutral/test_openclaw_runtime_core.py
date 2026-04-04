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


class OpenClawRuntimeCoreTests(unittest.TestCase):
    def test_adapter_registry_exposes_openclaw_preview_runtime_core_lane(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(RESOLVER),
                "--repo-root",
                str(REPO_ROOT),
                "--host",
                "openclaw",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("openclaw", payload["id"])
        self.assertEqual("preview", payload["status"])
        self.assertEqual("runtime-core", payload["install_mode"])
        self.assertEqual(".vibeskills/targets/openclaw", payload["default_target_root"]["rel"])
        self.assertEqual("isolated-home", payload["default_target_root"]["kind"])
        self.assertEqual("runtime-core-preview", payload["closure_json"]["closure_level"])
        self.assertEqual("preview", payload["host_profile_json"]["status"])
        self.assertEqual("~/.openclaw", payload["host_profile_json"]["settings_surface"]["path"])
        self.assertIn(
            "global_workflows/** when commands exist",
            payload["closure_json"]["host_state_written"],
        )
        self.assertIn(
            "mcp_config.json when absent",
            payload["closure_json"]["host_state_written"],
        )

    def test_python_installer_uses_runtime_core_with_preview_lane_boundaries(self) -> None:
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
                    "openclaw",
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(result.stdout)

            self.assertEqual("openclaw", payload["host_id"])
            self.assertEqual("runtime-core", payload["install_mode"])
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "skills" / "brainstorming" / "SKILL.md").exists())
            self.assertTrue((target_root / "commands").exists())
            self.assertTrue((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())
            self.assertFalse((target_root / "config" / "plugins-manifest.codex.json").exists())

    def test_shell_install_and_check_support_openclaw_runtime_core_preview_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "openclaw",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host   : openclaw", install_result.stdout)
            self.assertIn("Mode   : runtime-core", install_result.stdout)
            self.assertTrue((target_root / "skills" / "vibe" / "SKILL.md").exists())
            self.assertTrue((target_root / "commands").exists())
            self.assertTrue((target_root / "mcp_config.json").exists())
            self.assertFalse((target_root / "settings.json").exists())

            check_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "openclaw",
                    "--target-root",
                    str(target_root),
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host: openclaw", check_result.stdout)
            self.assertIn("Mode: runtime-core", check_result.stdout)
            self.assertIn("[OK] npm check skipped for non-governed adapter mode", check_result.stdout)
            self.assertNotIn("[FAIL] settings.json", check_result.stdout)
            self.assertNotIn("[FAIL] config/plugins-manifest.codex.json", check_result.stdout)


if __name__ == "__main__":
    unittest.main()
