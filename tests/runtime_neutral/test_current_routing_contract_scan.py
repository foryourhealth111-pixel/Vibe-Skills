from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
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
    def test_scan_script_treats_module_assignments_as_only_current_execution_truth_phrase(self) -> None:
        text = SCAN_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("derived_from_module_assignments", text)
        self.assertIn("source = ''module_assignments.units[*].bound_skill''", text)
        self.assertNotIn("derived_from_skill_routing_selected", text)
        self.assertNotIn("source = ''skill_routing.selected''", text)

    def test_scan_script_powershell_subprocess_calls_have_timeouts(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        run_call = "subprocess" + ".run("
        timeout_kwarg = "timeout" + "=60"

        self.assertEqual(3, text.count(run_call))
        self.assertEqual(3, text.count(timeout_kwarg))

    def test_scan_script_reports_json_and_no_current_surface_violations(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCAN_SCRIPT), "-Json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=True,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(0, int(payload["current_entrypoint_guidance_violation_count"]))
        self.assertEqual(0, int(payload["current_surface_violation_count"]))
        self.assertEqual(0, int(payload["current_runtime_old_format_fallback_count"]))
        self.assertIn("retired_old_format_reference_count", payload)
        self.assertIn("historical_reference_count", payload)
        self.assertIn("hard_cleanup_current_doc_retired_term_violation_count", payload)
        self.assertIn("hard_cleanup_current_behavior_test_retired_field_read_count", payload)
        self.assertIn("hard_cleanup_historical_doc_retired_term_file_count", payload)
        self.assertIn("hard_cleanup_historical_doc_marked_retired_term_count", payload)
        self.assertIn("hard_cleanup_historical_doc_unmarked_retired_term_count", payload)
        self.assertIn("hard_cleanup_execution_internal_specialist_dispatch_reference_count", payload)
        self.assertIn("hard_cleanup_current_policy_helper_dispatch_vocabulary_reference_count", payload)
        self.assertIn("hard_cleanup_fail_count", payload)
        self.assertIn("hard_cleanup_review_count", payload)
        self.assertEqual(0, int(payload["hard_cleanup_current_doc_retired_term_violation_count"]))
        self.assertEqual(0, int(payload["hard_cleanup_current_behavior_test_retired_field_read_count"]))
        self.assertGreater(int(payload["hard_cleanup_historical_doc_retired_term_file_count"]), 50)
        self.assertGreater(int(payload["hard_cleanup_historical_doc_marked_retired_term_count"]), 50)
        self.assertGreaterEqual(int(payload["hard_cleanup_historical_doc_unmarked_retired_term_count"]), 0)
        self.assertEqual(0, int(payload["hard_cleanup_execution_internal_specialist_dispatch_reference_count"]))
        self.assertEqual(0, int(payload["hard_cleanup_current_policy_helper_dispatch_vocabulary_reference_count"]))
        self.assertEqual(0, int(payload["hard_cleanup_fail_count"]))
        self.assertEqual(0, int(payload["hard_cleanup_review_count"]))
        self.assertEqual([], payload["findings"])

    def test_scan_script_plain_output_has_pass_gate(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCAN_SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=True,
        )

        self.assertIn("VCO Current Routing Contract Scan", completed.stdout)
        self.assertIn("Current entrypoint guidance violations: 0", completed.stdout)
        self.assertIn("Retired old-format references:", completed.stdout)
        self.assertIn("Hard cleanup current behavior test retired-field reads: 0", completed.stdout)
        self.assertIn("Hard cleanup historical docs with retired terms:", completed.stdout)
        self.assertIn("Hard cleanup historical docs with retired marker:", completed.stdout)
        self.assertIn("Hard cleanup current policy/helper dispatch vocabulary references: 0", completed.stdout)
        self.assertIn("Hard cleanup blocking failures: 0", completed.stdout)
        self.assertIn("Gate Result: PASS", completed.stdout)

    def test_scan_script_json_reports_fallback_hard_cleanup_fail_count(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available")

        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir)
            verify_dir = repo_root / "scripts" / "verify"
            verify_dir.mkdir(parents=True, exist_ok=True)
            hard_cleanup = verify_dir / "vibe-routing-terminology-hard-cleanup-scan.ps1"
            hard_cleanup.write_text(
                "param([string]$RepoRoot, [switch]$Json)\n"
                "[pscustomobject]@{ summary = [pscustomobject]@{ "
                "current_doc_retired_term_violation_count = 1; "
                "current_behavior_test_retired_field_read_count = 2; "
                "current_policy_helper_dispatch_vocabulary_reference_count = 3; "
                "review_count = 0 "
                "} } | ConvertTo-Json -Depth 10\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCAN_SCRIPT), "-RepoRoot", str(repo_root), "-Json"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=60,
            )
            payload = json.loads(completed.stdout)

            self.assertNotEqual(0, completed.returncode)
            self.assertEqual(6, int(payload["hard_cleanup_fail_count"]))
