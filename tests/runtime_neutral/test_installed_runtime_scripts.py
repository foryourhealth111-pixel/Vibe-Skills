from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_ENTRY_RUNTIME_SURFACES = (
    "scripts/runtime/Invoke-VibeCanonicalEntry.ps1",
    "scripts/verify/vibe-canonical-entry-truth-gate.ps1",
)


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class InstalledRuntimeScriptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.skills_dir = self.root / "skills"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def install_shell_runtime(self) -> None:
        subprocess.run(
            [
                "bash",
                str(REPO_ROOT / "install.sh"),
                "--skills-dir",
                str(self.skills_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def install_powershell_runtime(self, powershell: str) -> None:
        subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-SkillsDir",
                str(self.skills_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def disable_installed_deep_discovery_and_remove_catalog(self) -> Path:
        installed_root = self.skills_dir / "vibe"
        policy_path = installed_root / "config" / "deep-discovery-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["enabled"] = True
        policy["mode"] = "off"
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        catalog_path = installed_root / "config" / "capability-catalog.json"
        if catalog_path.exists():
            catalog_path.unlink()
        return installed_root

    def test_shell_install_writes_install_receipt(self) -> None:
        self.install_shell_runtime()

        receipt_path = self.skills_dir / "vibe" / ".vibeskills" / "install-receipt.json"
        self.assertTrue(receipt_path.exists())

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual("vibe-skill-install", receipt["receipt_kind"])
        self.assertEqual("vibe", receipt["skill_id"])
        self.assertEqual(str(self.skills_dir.resolve()), receipt["skills_dir"])
        self.assertEqual(str((self.skills_dir / "vibe").resolve()), receipt["install_root"])
        self.assertTrue(receipt["files"])

    def test_shell_reinstall_restores_canonical_entry_runtime_surfaces(self) -> None:
        self.install_shell_runtime()

        installed_root = self.skills_dir / "vibe"
        removed = [installed_root / relpath for relpath in CANONICAL_ENTRY_RUNTIME_SURFACES]
        for path in removed:
            self.assertTrue(path.exists(), path.as_posix())
            path.unlink()
            self.assertFalse(path.exists(), path.as_posix())

        self.install_shell_runtime()

        for path in removed:
            self.assertTrue(path.exists(), path.as_posix())

    def test_shell_check_reports_payload_drift_when_owned_files_change(self) -> None:
        self.install_shell_runtime()
        self.disable_installed_deep_discovery_and_remove_catalog()

        result = subprocess.run(
            [
                "bash",
                str(REPO_ROOT / "check.sh"),
                "--skills-dir",
                str(self.skills_dir),
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertIn("config/capability-catalog.json", payload["missing_files"])
        self.assertIn("config/deep-discovery-policy.json", payload["drifted_files"])

    def test_powershell_check_reports_payload_drift_when_owned_files_change(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        self.install_powershell_runtime(powershell)
        self.disable_installed_deep_discovery_and_remove_catalog()

        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "check.ps1"),
                "-SkillsDir",
                str(self.skills_dir),
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertIn("config/capability-catalog.json", payload["missing_files"])
        self.assertIn("config/deep-discovery-policy.json", payload["drifted_files"])

    def test_installed_freshness_gate_verifies_receipt_owned_hashes(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        self.install_powershell_runtime(powershell)
        installed_root = self.skills_dir / "vibe"
        gate_path = installed_root / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1"
        command = [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(gate_path),
            "-TargetRoot",
            str(self.root),
        ]

        fresh = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, fresh.returncode, fresh.stderr)

        (installed_root / "SKILL.md").write_text("drifted\n", encoding="utf-8")
        drifted = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(0, drifted.returncode)
        self.assertIn("hash mismatch: SKILL.md", drifted.stderr)


if __name__ == "__main__":
    unittest.main()
