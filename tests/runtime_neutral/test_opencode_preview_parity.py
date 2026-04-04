from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"
RESOLVER = REPO_ROOT / "scripts" / "common" / "resolve_vgo_adapter.py"


class OpenCodePreviewParityTests(unittest.TestCase):
    def test_adapter_registry_exposes_isolated_default_target_root_for_opencode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(RESOLVER),
                "--repo-root",
                str(REPO_ROOT),
                "--host",
                "opencode",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual("opencode", payload["id"])
        self.assertEqual(".vibeskills/targets/opencode", payload["default_target_root"]["rel"])
        self.assertEqual("isolated-home", payload["default_target_root"]["kind"])

    def test_python_installer_materializes_opencode_preview_wrappers(self) -> None:
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
                    "opencode",
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(result.stdout)

            self.assertEqual("opencode", payload["host_id"])
            self.assertEqual("preview-guidance", payload["install_mode"])
            self.assertTrue((target_root / "commands" / "vibe.md").exists())
            self.assertTrue((target_root / "command" / "vibe.md").exists())
            self.assertTrue((target_root / "agents" / "vibe-plan.md").exists())
            self.assertTrue((target_root / "agent" / "vibe-plan.md").exists())
            self.assertTrue((target_root / "opencode.json.example").exists())
            self.assertFalse((target_root / "opencode.json").exists())

    def test_powershell_check_accepts_opencode_preview_wrappers(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)

            install_result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                    "-HostId",
                    "opencode",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Host   : opencode", install_result.stdout)
            self.assertIn("Mode   : preview-guidance", install_result.stdout)

            check_result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(REPO_ROOT / "check.ps1"),
                    "-HostId",
                    "opencode",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                    "-Deep",
                ],
                capture_output=True,
                text=True,
            )
            if check_result.returncode != 0:
                self.fail(
                    "PowerShell opencode deep check should pass once preview wrappers are installed.\n"
                    f"stdout:\n{check_result.stdout}\n\nstderr:\n{check_result.stderr}"
                )
            self.assertNotIn("[FAIL] opencode command/", check_result.stdout)
            self.assertNotIn("[FAIL] opencode agent/", check_result.stdout)
            self.assertIn("[OK] opencode preview config example", check_result.stdout)


if __name__ == "__main__":
    unittest.main()
