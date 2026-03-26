from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class InstalledRuntimeScriptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.target_root = self.root / "target-a"
        self.target_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def install_shell_runtime(self, host: str = "codex") -> None:
        cmd = [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            host,
            "--profile",
            "full",
            "--target-root",
            str(self.target_root),
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    def test_installed_shell_scripts_work_without_repo_level_adapter_registry(self) -> None:
        self.install_shell_runtime()

        installed_root = self.target_root / "skills" / "vibe"
        check_cmd = [
            "bash",
            str(installed_root / "check.sh"),
            "--host",
            "codex",
            "--profile",
            "full",
            "--target-root",
            str(self.target_root),
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        self.assertIn("=== VCO Adapter Health Check ===", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stderr)

    def test_installed_runtime_bootstrap_supports_openclaw_without_self_deleting_source(self) -> None:
        self.install_shell_runtime(host="openclaw")

        installed_root = self.target_root / "skills" / "vibe"
        env = os.environ.copy()
        env["HOME"] = str(self.root / "home")
        env["OPENCLAW_HOME"] = str(self.target_root)
        bootstrap_cmd = [
            "bash",
            str(installed_root / "scripts" / "bootstrap" / "one-shot-setup.sh"),
            "--host",
            "openclaw",
            "--profile",
            "full",
            "--target-root",
            str(self.target_root),
        ]
        bootstrap_result = subprocess.run(bootstrap_cmd, capture_output=True, text=True, check=True, env=env)

        self.assertIn("Host                  : openclaw", bootstrap_result.stdout)
        self.assertIn("One-shot setup completed.", bootstrap_result.stdout)
        self.assertTrue((installed_root / "SKILL.md").exists())
        self.assertTrue((self.target_root / "mcp_config.json").exists())

    def test_installed_powershell_scripts_work_without_repo_level_adapter_registry(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        install_cmd = [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(self.target_root),
        ]
        subprocess.run(install_cmd, capture_output=True, text=True, check=True)

        installed_root = self.target_root / "skills" / "vibe"
        check_cmd = [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(installed_root / "check.ps1"),
            "-HostId",
            "codex",
            "-Profile",
            "full",
            "-TargetRoot",
            str(self.target_root),
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
        self.assertIn("=== VCO Adapter Health Check ===", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stdout)
        self.assertNotIn("VGO adapter registry not found", check_result.stderr)


if __name__ == "__main__":
    unittest.main()
