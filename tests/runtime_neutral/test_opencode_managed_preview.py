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
    def _assert_opencode_command_wrapper(self, wrapper_path: Path, *, agent: str) -> None:
        text = wrapper_path.read_text(encoding="utf-8")
        self.assertIn(f"agent: {agent}", text)
        self.assertIn('"schema": "vibe-wrapper-trampoline/v1"', text)
        self.assertIn('"launch_mode": "canonical-entry"', text)
        self.assertIn('"host_id": "opencode"', text)
        self.assertNotIn("Use the `vibe` skill", text)
        self.assertIn("$ARGUMENTS", text)

    def test_python_installer_materializes_opencode_host_closure_without_touching_real_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            _, payload = run_package_install(host="opencode", target_root=target_root)
            closure_path = target_root / ".vibeskills" / "host-closure.json"
            bootstrap_receipt_path = Path(str(payload["global_instruction_bootstrap_receipt"]))
            agents_path = target_root / "AGENTS.md"
            settings_path = target_root / "opencode.json"
            example_path = target_root / "opencode.json.example"

            self.assertEqual("opencode", payload["host_id"])
            self.assertEqual("preview-guidance", payload["install_mode"])
            self.assertTrue(closure_path.exists())
            self.assertTrue(bootstrap_receipt_path.exists())
            self.assertTrue(agents_path.exists())
            self.assertFalse(settings_path.exists())
            self.assertTrue(example_path.exists())
            self.assertTrue((target_root / ".vibeskills" / "host-settings.json").exists())
            self.assertTrue((target_root / "commands" / "vibe.md").exists())
            self.assertTrue((target_root / "command" / "vibe.md").exists())
            self.assertTrue((target_root / "agents" / "vibe-plan.md").exists())
            self.assertTrue((target_root / "agent" / "vibe-plan.md").exists())
            self._assert_opencode_command_wrapper(target_root / "commands" / "vibe.md", agent="vibe-plan")
            self._assert_opencode_command_wrapper(target_root / "command" / "vibe.md", agent="vibe-plan")
            self.assertFalse((target_root / "commands" / "vibe-how-do-we-do.md").exists())
            self.assertFalse((target_root / "command" / "vibe-how-do-we-do.md").exists())
            closure = json.loads(closure_path.read_text(encoding="utf-8"))
            self.assertEqual([str((target_root / ".vibeskills" / "host-settings.json").resolve())], closure["settings_materialized"])
            self.assertEqual(str(target_root.resolve()), closure["runtime_root"])
            self.assertEqual(str(target_root.resolve()), closure["host_bridge_root"])
            self.assertEqual(payload["desired_shared_runtime_root"], closure["desired_shared_runtime_root"])
            self.assertEqual("legacy-host-root-override", closure["runtime_layout_mode"])
            self.assertEqual(str(target_root.resolve()), payload["runtime_root"])
            self.assertEqual(str(target_root.resolve()), payload["host_bridge_root"])
            self.assertNotEqual(str(target_root.resolve()), payload["desired_shared_runtime_root"])
            self.assertEqual("legacy-host-root-override", payload["runtime_layout_mode"])
            self.assertIsNone(payload["legacy_opencode_config_cleanup"])

    def test_python_installer_leaves_existing_opencode_config_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            settings_path = target_root / "opencode.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://opencode.ai/config.json",
                        "theme": "system",
                        "permission": {
                            "read": "allow",
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
            self.assertEqual("system", preserved["theme"])
            self.assertNotIn("mcp", preserved)
            self.assertIsNone(payload["legacy_opencode_config_cleanup"])

    def test_shell_install_and_check_use_skills_dir_without_touching_real_opencode_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir)
            skills_dir = target_root / "skills"
            settings_path = target_root / "opencode.json"
            original = {
                "$schema": "https://opencode.ai/config.json",
                "theme": "system",
                "permission": {
                    "read": "allow",
                },
            }
            settings_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

            install_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--skills-dir",
                    str(skills_dir),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            install_payload = json.loads(install_result.stdout)
            self.assertEqual("vibe-skill-install", install_payload["receipt_kind"])

            check_result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--skills-dir",
                    str(skills_dir),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            check_payload = json.loads(check_result.stdout)
            self.assertTrue(check_payload["ok"])
            self.assertEqual(original, json.loads(settings_path.read_text(encoding="utf-8")))
            self.assertTrue((skills_dir / "vibe" / "SKILL.md").exists())
            self.assertTrue((skills_dir / "vibe" / ".vibeskills" / "install-receipt.json").exists())
            self.assertFalse((target_root / "commands").exists())
            self.assertFalse((target_root / "command").exists())
            self.assertFalse((target_root / "agents").exists())
            self.assertFalse((target_root / "agent").exists())
            self.assertFalse((target_root / ".vibeskills" / "host-settings.json").exists())


if __name__ == "__main__":
    unittest.main()
