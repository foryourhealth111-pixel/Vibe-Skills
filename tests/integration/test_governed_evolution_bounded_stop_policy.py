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
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"


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


def invoke_runtime(*, run_id: str, requested_stage_stop: str, entry_intent_id: str) -> dict:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    outputs_root = REPO_ROOT / "outputs"
    outputs_root.mkdir(parents=True, exist_ok=True)
    artifact_root = Path(
        tempfile.mkdtemp(prefix=f"pytest-bounded-stop-{uuid.uuid4().hex}-", dir=outputs_root)
    )
    try:
        completed = subprocess.run(
            [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                (
                    "& { "
                    f"$result = & '{RUNTIME_SCRIPT}' "
                    "-Task 'Summarize the repository structure and stop at the bounded stage.' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-EntryIntentId '{entry_intent_id}' "
                    f"-RequestedStageStop '{requested_stage_stop}' "
                    f"-ArtifactRoot '{artifact_root}'; "
                    "$result | ConvertTo-Json -Depth 20 }"
                ),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
        )
        payload = json.loads(completed.stdout)
        summary_path = Path(payload["summary_path"])
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return {
            "payload": payload,
            "summary": summary,
            "artifact_root": artifact_root,
            "session_root": Path(payload["session_root"]),
        }
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        permission_markers = (
            "Access to the path",
            "Permission denied",
            "Could not find a part of the path",
            "could not open directory",
        )
        if any(marker in stderr for marker in permission_markers):
            shutil.rmtree(artifact_root, ignore_errors=True)
            raise unittest.SkipTest(f"Local filesystem permissions prevented bounded-stop execution: {stderr.strip()}")
        shutil.rmtree(artifact_root, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(artifact_root, ignore_errors=True)
        raise


class GovernedEvolutionBoundedStopPolicyTests(unittest.TestCase):
    def test_requirement_doc_stop_skips_governed_evolution_artifacts(self) -> None:
        run = invoke_runtime(
            run_id="pytest-bounded-stop-requirement-doc",
            requested_stage_stop="requirement_doc",
            entry_intent_id="vibe-want",
        )
        try:
            summary = run["summary"]
            artifacts = summary["artifacts"]

            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                summary["executed_stage_order"],
            )
            self.assertIsNone(artifacts["observed_failure_patterns"])
            self.assertIsNone(artifacts["observed_pitfall_events"])
            self.assertIsNone(artifacts["atomic_skill_call_chain"])
            self.assertIsNone(artifacts["proposal_layer"])
            self.assertIsNone(artifacts["application_readiness_report"])

            self.assertFalse((run["session_root"] / "failure-patterns.json").exists())
            self.assertFalse((run["session_root"] / "pitfall-events.json").exists())
            self.assertFalse((run["session_root"] / "atomic-skill-call-chain.json").exists())
            self.assertFalse((run["session_root"] / "proposal-layer.json").exists())
            self.assertFalse((run["session_root"] / "application-readiness-report.json").exists())
        finally:
            shutil.rmtree(run["artifact_root"], ignore_errors=True)

    def test_xl_plan_stop_keeps_light_artifacts_but_skips_readiness_and_extended_proposals(self) -> None:
        run = invoke_runtime(
            run_id="pytest-bounded-stop-xl-plan",
            requested_stage_stop="xl_plan",
            entry_intent_id="vibe-how",
        )
        try:
            summary = run["summary"]
            artifacts = summary["artifacts"]
            failure_payload = json.loads(
                (run["session_root"] / "failure-patterns.json").read_text(encoding="utf-8")
            )
            pitfall_payload = json.loads(
                (run["session_root"] / "pitfall-events.json").read_text(encoding="utf-8")
            )
            call_chain_payload = json.loads(
                (run["session_root"] / "atomic-skill-call-chain.json").read_text(encoding="utf-8")
            )
            warning_cards_payload = json.loads(
                (run["session_root"] / "warning-cards.json").read_text(encoding="utf-8")
            )
            preflight_payload = json.loads(
                (run["session_root"] / "preflight-checklist.json").read_text(encoding="utf-8")
            )
            pattern_ids = {pattern["pattern_id"] for pattern in failure_payload["patterns"]}
            pitfall_types = {event["pitfall_type"] for event in pitfall_payload["events"]}
            event_types = {event["event_type"] for event in call_chain_payload["events"]}
            card_ids = {card["card_id"] for card in warning_cards_payload["cards"]}
            check_ids = {check["check_id"] for check in preflight_payload["checks"]}
            source_signals = {check["source_signal"] for check in preflight_payload["checks"]}

            self.assertEqual("xl_plan", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan"],
                summary["executed_stage_order"],
            )
            self.assertIsNotNone(artifacts["observed_failure_patterns"])
            self.assertIsNotNone(artifacts["observed_pitfall_events"])
            self.assertIsNotNone(artifacts["atomic_skill_call_chain"])
            self.assertIsNotNone(artifacts["warning_cards"])
            self.assertIsNotNone(artifacts["preflight_checklist"])
            self.assertIsNotNone(artifacts["proposal_layer"])
            self.assertIsNotNone(artifacts["proposal_layer_markdown"])

            self.assertIsNone(artifacts["remediation_notes"])
            self.assertIsNone(artifacts["candidate_composite_skill_draft"])
            self.assertIsNone(artifacts["threshold_policy_suggestion"])
            self.assertIsNone(artifacts["application_readiness_report"])
            self.assertIsNone(artifacts["application_readiness_markdown"])

            self.assertTrue((run["session_root"] / "proposal-layer.json").exists())
            self.assertFalse((run["session_root"] / "remediation-notes.json").exists())
            self.assertFalse((run["session_root"] / "candidate-composite-skill-draft.json").exists())
            self.assertFalse((run["session_root"] / "threshold-policy-suggestion.json").exists())
            self.assertFalse((run["session_root"] / "application-readiness-report.json").exists())
            self.assertFalse({"cleanup_degraded", "delivery_gate_failed", "process_health_risk"} & pattern_ids)
            self.assertFalse({"cleanup_candidate_present", "managed_stale_detected", "cleanup_degraded", "delivery_gate_failed"} & pitfall_types)
            self.assertFalse({"skill_execution_finished", "skill_execution_degraded"} & event_types)
            self.assertFalse(
                {
                    "warning-cleanup_degraded",
                    "warning-delivery_gate_failed",
                    "warning-process_health_risk",
                    "warning-pitfall-cleanup_candidate_present",
                    "warning-pitfall-managed_stale_detected",
                    "warning-pitfall-cleanup_degraded",
                    "warning-pitfall-delivery_gate_failed",
                    "warning-delivery-acceptance",
                }
                & card_ids
            )
            self.assertNotIn("check-phase-cleanup", check_ids)
            self.assertNotIn("missing_phase_cleanup", source_signals)
            self.assertFalse(
                {
                    "check-cleanup_degraded",
                    "check-delivery_gate_failed",
                    "check-process_health_risk",
                    "check-pitfall-cleanup_candidate_present",
                    "check-pitfall-managed_stale_detected",
                    "check-pitfall-cleanup_degraded",
                    "check-pitfall-delivery_gate_failed",
                }
                & check_ids
            )
        finally:
            shutil.rmtree(run["artifact_root"], ignore_errors=True)
