from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DOC = REPO_ROOT / "docs" / "governance" / "current-runtime-field-contract.md"
HARD_SCAN = REPO_ROOT / "scripts" / "verify" / "vibe-routing-terminology-hard-cleanup-scan.ps1"


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


class RoutingTerminologyHardCleanupTests(unittest.TestCase):
    def test_current_runtime_field_contract_defines_allowed_layers(self) -> None:
        self.assertTrue(CONTRACT_DOC.exists(), "current runtime field contract must exist")
        text = CONTRACT_DOC.read_text(encoding="utf-8")

        self.assertIn("skill_candidates -> skill_routing.selected -> skill_usage.used / skill_usage.unused", text)
        for required in [
            "## Routing Layer",
            "## Usage Layer",
            "## Execution Layer",
            "## Retired Layer",
            "`skill_routing.selected`",
            "`skill_usage.used`",
            "`skill_usage.unused`",
            "`skill_usage.evidence`",
            "`approved_skill_execution`",
            "`skill_execution_units`",
            "`execution_skill_outcomes`",
        ]:
            self.assertIn(required, text)

        current_section = text.split("## Retired Layer", 1)[0].lower()
        for forbidden in [
            "primary skill",
            "secondary skill",
            "route owner",
            "consultation expert",
            "auxiliary expert",
            "stage assistant",
        ]:
            self.assertNotIn(forbidden, current_section)

    def test_hard_cleanup_scan_reports_json(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-File", str(HARD_SCAN), "-Json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        payload = json.loads(completed.stdout)
        self.assertIn("current_doc_retired_term_violation_count", payload)
        self.assertIn("current_behavior_test_retired_field_read_count", payload)
        self.assertIn("historical_doc_unmarked_retired_term_count", payload)
        self.assertIn("execution_internal_specialist_dispatch_reference_count", payload)
        self.assertEqual([], payload["findings"])


if __name__ == "__main__":
    unittest.main()
