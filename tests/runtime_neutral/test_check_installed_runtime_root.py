from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def install_minimal_codex_runtime(target_root: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "install.sh"),
            "--host",
            "codex",
            "--profile",
            "minimal",
            "--skip-runtime-freshness-gate",
            "--target-root",
            str(target_root),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"install failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")


class CheckInstalledRuntimeRootTests(unittest.TestCase):
    def test_check_sh_accepts_installed_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            install_minimal_codex_runtime(target_root)
            installed_root = target_root / "skills" / "vibe"

            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "check.sh"),
                    "--host",
                    "codex",
                    "--profile",
                    "minimal",
                    "--skip-runtime-freshness-gate",
                    "--target-root",
                    str(installed_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        self.assertNotIn("skills/vibe/skills/vibe", result.stdout)

    def test_check_ps1_accepts_installed_runtime_root(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            install_minimal_codex_runtime(target_root)
            installed_root = target_root / "skills" / "vibe"

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(installed_root / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "minimal",
                    "-SkipRuntimeFreshnessGate",
                    "-TargetRoot",
                    str(installed_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        normalized_stdout = result.stdout.replace("\\", "/")
        self.assertNotIn("skills/vibe/skills/vibe", normalized_stdout)

    def test_check_ps1_reports_invalid_receipt_version_without_crashing(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            install_minimal_codex_runtime(target_root)
            installed_root = target_root / "skills" / "vibe"
            installed_governance = json.loads(
                (installed_root / "config" / "version-governance.json").read_text(encoding="utf-8-sig")
            )
            release = installed_governance.get("release") or {}
            receipt_path = installed_root / "outputs" / "runtime-freshness-receipt.json"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "gate_result": "PASS",
                        "receipt_version": "abc",
                        "target_root": str(target_root),
                        "installed_root": str(installed_root),
                        "release": {
                            "version": str(release.get("version") or ""),
                            "updated": str(release.get("updated") or ""),
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(installed_root / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "minimal",
                    "-TargetRoot",
                    str(target_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("[FAIL] vibe runtime freshness receipt version", result.stdout)
        self.assertNotIn("Cannot convert value", result.stderr)

    def test_check_ps1_fails_closed_when_expected_receipt_contract_version_is_invalid(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            install_minimal_codex_runtime(target_root)
            installed_root = target_root / "skills" / "vibe"
            governance_path = installed_root / "config" / "version-governance.json"
            installed_governance = json.loads(governance_path.read_text(encoding="utf-8-sig"))
            installed_governance["runtime"]["installed_runtime"]["receipt_contract_version"] = "abc"
            governance_path.write_text(json.dumps(installed_governance) + "\n", encoding="utf-8")

            release = installed_governance.get("release") or {}
            receipt_path = installed_root / "outputs" / "runtime-freshness-receipt.json"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "gate_result": "PASS",
                        "receipt_version": 2,
                        "target_root": str(target_root),
                        "installed_root": str(installed_root),
                        "release": {
                            "version": str(release.get("version") or ""),
                            "updated": str(release.get("updated") or ""),
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(installed_root / "check.ps1"),
                    "-HostId",
                    "codex",
                    "-Profile",
                    "minimal",
                    "-TargetRoot",
                    str(target_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("[FAIL] vibe runtime freshness receipt version", result.stdout)
        self.assertIn("expected=", result.stdout)


if __name__ == "__main__":
    unittest.main()