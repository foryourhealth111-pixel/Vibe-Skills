from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
import uuid


REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "verify" / "vibe-governed-evolution-smoke.ps1"


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


class GovernedEvolutionSmokeTests(unittest.TestCase):
    def test_governed_evolution_smoke_script_passes_with_temp_artifact_root(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        self.assertTrue(SMOKE_SCRIPT.exists(), f"Missing smoke script: {SMOKE_SCRIPT}")

        artifact_root = Path(
            tempfile.mkdtemp(prefix=f"pytest-governed-evolution-{uuid.uuid4().hex}-")
        )
        try:
            run_id = "pytest-governed-evolution-smoke"
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SMOKE_SCRIPT),
                    "-RunId",
                    run_id,
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            session_root = Path(payload["session_root"])

            self.assertEqual("passed", payload["status"])
            self.assertEqual(run_id, payload["run_id"])
            self.assertEqual(13, payload["checked_artifact_count"])
            self.assertGreaterEqual(payload["failure_pattern_count"], 0)
            self.assertGreaterEqual(payload["pitfall_event_count"], 0)
            self.assertGreaterEqual(payload["atomic_skill_event_count"], 0)
            self.assertGreaterEqual(payload["warning_card_count"], 0)
            self.assertGreaterEqual(payload["preflight_check_count"], 0)
            self.assertGreaterEqual(payload["remediation_note_count"], 0)
            self.assertGreaterEqual(payload["candidate_draft_count"], 0)
            self.assertGreaterEqual(payload["threshold_policy_suggestion_count"], 0)
            self.assertGreaterEqual(payload["lane_a_candidate_count"], 0)
            self.assertGreaterEqual(payload["lane_b_candidate_count"], 0)

            self.assertTrue(session_root.exists())
            self.assertEqual(run_id, session_root.name)
            session_root.relative_to(artifact_root)
        finally:
            shutil.rmtree(artifact_root, ignore_errors=True)
