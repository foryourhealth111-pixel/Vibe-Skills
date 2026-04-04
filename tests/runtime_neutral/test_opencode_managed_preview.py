from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
INSTALLER_CORE_SRC = REPO_ROOT / "packages" / "installer-core" / "src"


def run_package_install(*, host: str, target_root: Path, profile: str = "full") -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(CONTRACTS_SRC), str(INSTALLER_CORE_SRC), env.get("PYTHONPATH", "")]).strip(os.pathsep)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vgo_installer.install_runtime",
            "--repo-root",
            str(REPO_ROOT),
            "--target-root",
            str(target_root),
            "--host",
            host,
            "--profile",
            profile,
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result, json.loads(result.stdout)


class OpenCodeManagedPreviewTests(unittest.TestCase):
    def test_python_installer_materializes_opencode_host_closure_without_touching_real_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            _, payload = run_package_install(host="opencode", target_root=target_root)
            closure_path = target_root / ".vibeskills" / "host-closure.json"
            settings_path = target_root / "opencode.json"
            example_path = target_root / "opencode.json.example"

            self.assertEqual("opencode", payload["host_id"])
            self.assertEqual("preview-guidance", payload["install_mode"])
            self.assertTrue(closure_path.exists())
            self.assertFalse(settings_path.exists())
            self.assertTrue(example_path.exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "command").exists())
            self.assertFalse((target_root / "agents").exists())
            self.assertFalse((target_root / "agent").exists())
            closure = json.loads(closure_path.read_text(encoding="utf-8"))
            self.assertEqual([str((target_root / ".vibeskills" / "host-settings.json").resolve())], closure["settings_materialized"])
            self.assertIsNone(payload["legacy_opencode_config_cleanup"])

    def test_python_installer_leaves_existing_opencode_config_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            settings_path = target_root / "opencode.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://opencode.ai/config.json",
                        "mcp": {
                            "playwright": {
                                "enabled": True,
                                "type": "local",
                                "command": ["npx", "@playwright/mcp@latest"],
                            }
                        },
                        "vibeskills": {
                            "host_id": "opencode",
                            "managed": True,
                            "commands_root": str((target_root / "commands").resolve()),
                            "agents_root": str((target_root / "agents").resolve()),
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            _, payload = run_package_install(host="opencode", target_root=target_root)

            preserved = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertIn("vibeskills", preserved)
            self.assertIn("mcp", preserved)
            self.assertIsNone(payload["legacy_opencode_config_cleanup"])

    def test_shell_install_and_check_use_sidecar_only_opencode_preview_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            settings_path = target_root / "opencode.json"
            original = {
                "$schema": "https://opencode.ai/config.json",
                "mcp": {
                    "playwright": {
                        "enabled": True,
                        "type": "local",
                        "command": ["npx", "@playwright/mcp@latest"],
                    }
                },
            }
            settings_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "opencode",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Mode   : preview-guidance", install_result.stdout)

            check_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "opencode",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("[OK] host settings sidecar", check_result.stdout)
            self.assertIn("[OK] opencode preview config example", check_result.stdout)
            self.assertNotIn("[FAIL] opencode command/", check_result.stdout)
            self.assertNotIn("[FAIL] opencode agent/", check_result.stdout)
            self.assertEqual(original, json.loads(settings_path.read_text(encoding="utf-8")))
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "agents").exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())


if __name__ == "__main__":
    unittest.main()
