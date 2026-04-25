from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


class SpecialistDecisionProjectionTests(unittest.TestCase):
    def _run_projection(self, script_body: str) -> dict[str, object]:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        runtime_common = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
        ps_command = (
            "& { "
            f". {_ps_single_quote(str(runtime_common))}; "
            f"{script_body}"
            " }"
        )
        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-Command", ps_command],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return json.loads(completed.stdout)

    def test_specialist_decision_projection_preserves_explicit_match_and_surface_ids(self) -> None:
        payload = self._run_projection(
            "$result = New-VibeSpecialistDecisionProjection "
            "-ApprovedDispatch @([pscustomobject]@{ skill_id = 'systematic-debugging' }) "
            "-MatchedSkillIds @('systematic-debugging', 'flashrag-evidence') "
            "-SurfacedSkillIds @('systematic-debugging', 'flashrag-evidence', 'test-driven-development') "
            "-RecommendationCount 3; "
            "$result | ConvertTo-Json -Depth 10"
        )

        self.assertEqual(
            ["systematic-debugging", "flashrag-evidence"],
            payload["matched_skill_ids"],
        )
        self.assertEqual(
            ["systematic-debugging", "flashrag-evidence", "test-driven-development"],
            payload["surfaced_skill_ids"],
        )

    def test_specialist_decision_projection_recomputes_notes_when_override_changes_resolution(self) -> None:
        payload = self._run_projection(
            "$override = [pscustomobject]@{ "
            "decision_state = 'no_specialist_recommendations'; "
            "resolution_mode = 'no_specialist_needed'; "
            "repo_asset_fallback = [pscustomobject]@{ "
            "used = $false; "
            "asset_paths = @(); "
            "reason = ''; "
            "legal_basis = ''; "
            "traceability_basis = @() "
            "} "
            "}; "
            "$result = New-VibeSpecialistDecisionProjection "
            "-RecommendationCount 0 "
            "-OverridePayload $override "
            "-OverrideSourcePath 'specialist-decision.json'; "
            "$result | ConvertTo-Json -Depth 10"
        )

        self.assertEqual("no_specialist_needed", payload["resolution_mode"])
        self.assertIn("no specialist help was needed", str(payload["notes"]).lower())
        self.assertNotIn("repo-asset fallback", str(payload["notes"]).lower())

    def test_specialist_decision_projection_defaults_missing_traceability_basis_to_empty_list(self) -> None:
        payload = self._run_projection(
            "$override = [pscustomobject]@{ "
            "decision_state = 'no_specialist_recommendations'; "
            "resolution_mode = 'repo_asset_fallback'; "
            "repo_asset_fallback = [pscustomobject]@{ "
            "used = $true; "
            "asset_paths = @('outputs/foo.py'); "
            "reason = 'Reuse the repo-local plotting asset.'; "
            "legal_basis = 'Repo-local governed asset.' "
            "} "
            "}; "
            "$result = New-VibeSpecialistDecisionProjection "
            "-RecommendationCount 0 "
            "-OverridePayload $override; "
            "$result | ConvertTo-Json -Depth 10"
        )

        self.assertEqual("repo_asset_fallback", payload["resolution_mode"])
        self.assertEqual([], payload["repo_asset_fallback"]["traceability_basis"])

    def test_specialist_decision_projection_defaults_empty_match_and_surface_ids_to_empty_lists(self) -> None:
        payload = self._run_projection(
            "$result = New-VibeSpecialistDecisionProjection "
            "-RecommendationCount 0; "
            "$result | ConvertTo-Json -Depth 10"
        )

        self.assertEqual([], payload["matched_skill_ids"])
        self.assertEqual([], payload["surfaced_skill_ids"])
        self.assertEqual("no_specialist_recommendations", payload["decision_state"])
        self.assertEqual("no_matching_specialist", payload["resolution_mode"])
        self.assertEqual([], payload["candidate_skill_ids_reviewed"])
        self.assertEqual([], payload["selected_skill_ids"])
        self.assertEqual([], payload["rejected_candidates"])
