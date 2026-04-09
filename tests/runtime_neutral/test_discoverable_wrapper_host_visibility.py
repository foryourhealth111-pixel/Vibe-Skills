from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import json


REPO_ROOT = Path(__file__).resolve().parents[2]


class DiscoverableWrapperHostVisibilityTests(unittest.TestCase):
    def _require_bash(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash not available")

    def _write_external_wrapper_ledger_path(self, target_root: Path, external_wrapper: Path) -> None:
        ledger_path = target_root / ".vibeskills" / "install-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["specialist_wrapper_paths"] = [str(external_wrapper)]
        ledger["payload_summary"]["host_visible_entry_names"] = ["vibe"]
        ledger["payload_summary"]["host_visible_entry_count"] = 1
        ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    def test_shell_checks_skip_when_bash_is_unavailable(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(unittest.SkipTest):
                self._require_bash()

    def test_shell_check_reports_host_visible_discoverable_entries(self) -> None:
        self._require_bash()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("[OK] host-visible discoverable entries", result.stdout)

    def test_shell_check_fails_when_both_wrapper_command_and_skill_entry_are_missing(self) -> None:
        self._require_bash()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            (target_root / "commands" / "vibe-how.md").unlink()
            shutil.rmtree(target_root / "skills" / "vibe-how-do-we-do")

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] host-visible discoverable entries", result.stdout)

    def test_shell_check_fails_when_public_wrapper_skill_is_missing_even_if_hidden_bundle_exists(self) -> None:
        self._require_bash()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            shutil.rmtree(target_root / "skills" / "vibe-how-do-we-do")
            self.assertTrue((target_root / "skills" / "vibe" / "bundled" / "skills" / "vibe-how-do-we-do").exists())

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] skill/vibe-how-do-we-do", result.stdout)

    def test_shell_check_rejects_wrapper_inventory_outside_target_root(self) -> None:
        self._require_bash()
        with tempfile.TemporaryDirectory() as tempdir, tempfile.TemporaryDirectory() as external_dir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            external_wrapper = Path(external_dir) / "vibe.md"
            external_wrapper.write_text("# vibe\n", encoding="utf-8")
            self._write_external_wrapper_ledger_path(target_root, external_wrapper)

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] host-visible discoverable entries", result.stdout)

    def test_shell_check_keeps_discoverable_entry_validation_separate_from_bridge_launcher_validation(self) -> None:
        self._require_bash()
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            closure = json.loads((target_root / ".vibeskills" / "host-closure.json").read_text(encoding="utf-8"))
            Path(closure["specialist_wrapper"]["launcher_path"]).unlink()

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "full",
                    "--target-root",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] specialist wrapper launcher", result.stdout)
            self.assertIn("[OK] host-visible discoverable entries", result.stdout)

    def test_powershell_check_reports_host_visible_discoverable_entries(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn("[OK] host-visible discoverable entries", result.stdout)

    def test_powershell_check_treats_null_host_visible_entry_names_as_empty_inventory(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            ledger_path = target_root / ".vibeskills" / "install-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["payload_summary"]["host_visible_entry_names"] = None
            ledger["payload_summary"]["host_visible_entry_count"] = None
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

            result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("[OK] host-visible discoverable entries", result.stdout)
            self.assertNotIn("PropertyNotFoundException", result.stderr)
            self.assertNotIn("Check-CodexDuplicateSkillSurface", result.stderr)

    def test_powershell_check_rejects_wrapper_inventory_outside_target_root(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        with tempfile.TemporaryDirectory() as tempdir, tempfile.TemporaryDirectory() as external_dir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            external_wrapper = Path(external_dir) / "vibe.md"
            external_wrapper.write_text("# vibe\n", encoding="utf-8")
            self._write_external_wrapper_ledger_path(target_root, external_wrapper)

            result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] host-visible discoverable entries", result.stdout)

    def test_powershell_check_keeps_discoverable_entry_validation_separate_from_bridge_launcher_validation(self) -> None:
        if shutil.which("pwsh") is None:
            self.skipTest("pwsh not available")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / "codex-root"
            subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            closure = json.loads((target_root / ".vibeskills" / "host-closure.json").read_text(encoding="utf-8"))
            Path(closure["specialist_wrapper"]["launcher_path"]).unlink()

            result = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(REPO_ROOT / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "full",
                    "-TargetRoot",
                    str(target_root),
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("[FAIL] specialist wrapper launcher", result.stdout)
            self.assertIn("[OK] host-visible discoverable entries", result.stdout)


if __name__ == "__main__":
    unittest.main()
