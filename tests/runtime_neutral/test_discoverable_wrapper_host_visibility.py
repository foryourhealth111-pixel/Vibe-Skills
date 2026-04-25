from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_HOSTS = ("codex", "claude-code", "opencode")
EXPECTED_DISCOVERABLE_ENTRIES = {"vibe", "vibe-upgrade"}
RETIRED_DISCOVERABLE_ENTRIES = ("vibe-what-do-i-want", "vibe-how-do-we-do", "vibe-do-it")


def _install_host(target_root: Path, host_id: str) -> None:
    command = [
        "bash",
        str(REPO_ROOT / "install.sh"),
        "--host",
        host_id,
        "--profile",
        "full",
        "--target-root",
        str(target_root),
    ]
    if host_id != "codex":
        command.append("--require-closed-ready")
    subprocess.run(command, capture_output=True, text=True, check=True)


class DiscoverableWrapperHostVisibilityTests(unittest.TestCase):
    def _require_bash(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash not available")

    def test_install_ledger_exposes_host_visible_discoverable_entries_for_supported_hosts(self) -> None:
        self._require_bash()
        for host_id in SUPPORTED_HOSTS:
            with self.subTest(host=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    target_root = Path(tempdir) / f"{host_id}-root"
                    _install_host(target_root, host_id)

                    ledger_path = target_root / ".vibeskills" / "install-ledger.json"
                    self.assertTrue(ledger_path.exists(), host_id)
                    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                    payload_summary = ledger.get("payload_summary") or {}

                    names = payload_summary.get("host_visible_entry_names") or []
                    self.assertGreaterEqual(len(names), 1, host_id)
                    self.assertIn("vibe", names, host_id)
                    self.assertEqual(int(payload_summary.get("host_visible_entry_count") or 0), len(names), host_id)
                    self.assertTrue(EXPECTED_DISCOVERABLE_ENTRIES.issubset(set(names)), host_id)
                    self.assertTrue((target_root / "skills" / "vibe-upgrade" / "SKILL.md").exists(), host_id)
                    self.assertFalse((target_root / "commands" / "vibe-upgrade.md").exists(), host_id)
                    self.assertFalse((target_root / "command" / "vibe-upgrade.md").exists(), host_id)

    def test_shell_check_accepts_supported_host_discoverable_surfaces(self) -> None:
        self._require_bash()
        for host_id in SUPPORTED_HOSTS:
            with self.subTest(host=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    target_root = Path(tempdir) / f"{host_id}-root"
                    _install_host(target_root, host_id)

                    result = subprocess.run(
                        [
                            "bash",
                            str(REPO_ROOT / "check.sh"),
                            "--host",
                            host_id,
                            "--profile",
                            "full",
                            "--target-root",
                            str(target_root),
                        ],
                        capture_output=True,
                        text=True,
                    )

                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                    self.assertIn("[OK] specialist wrapper launcher", result.stdout)
                    self.assertNotIn("[FAIL] specialist wrapper launcher", result.stdout)

    def test_install_prunes_retired_discoverable_wrapper_files_from_host_surfaces(self) -> None:
        self._require_bash()
        for host_id in SUPPORTED_HOSTS:
            with self.subTest(host=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    target_root = Path(tempdir) / f"{host_id}-root"
                    _install_host(target_root, host_id)

                    for entry_id in RETIRED_DISCOVERABLE_ENTRIES:
                        self.assertFalse((target_root / "commands" / f"{entry_id}.md").exists(), (host_id, entry_id))
                        self.assertFalse((target_root / "command" / f"{entry_id}.md").exists(), (host_id, entry_id))
                        self.assertFalse((target_root / "skills" / entry_id).exists(), (host_id, entry_id))


if __name__ == "__main__":
    unittest.main()
