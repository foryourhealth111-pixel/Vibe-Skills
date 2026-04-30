from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "verify" / "vibe-current-routing-contract-scan.ps1"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class CurrentRoutingContractScanTests(unittest.TestCase):
    def test_scan_script_reports_json_and_no_current_surface_violations(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-File", str(SCAN_SCRIPT), "-Json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(0, int(payload["current_surface_violation_count"]))
        self.assertIn("legacy_reference_count", payload)
        self.assertIn("historical_reference_count", payload)
        self.assertEqual([], payload["findings"])

    def test_scan_script_plain_output_has_pass_gate(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-File", str(SCAN_SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )

        self.assertIn("VCO Current Routing Contract Scan", completed.stdout)
        self.assertIn("Gate Result: PASS", completed.stdout)
