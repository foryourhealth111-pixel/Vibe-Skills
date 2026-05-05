from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
RETIRED_CONSULTATION_COMMON = REPO_ROOT / "scripts" / "runtime" / "legacy" / "VibeRetiredConsultation.Common.ps1"

CURRENT_TASK = (
    "Build a scikit-learn classification baseline, include a result figure, "
    "and explain which selected skills were used or unused."
)

ACTIVE_FORBIDDEN_PATTERNS = [
    r"\bstage assistant\b",
    r"\broute owner\b",
    r"\broute authority\b",
    r"\bprimary skill\b",
    r"\bsecondary skill\b",
    r"\bconsultation expert\b",
    r"\bauxiliary expert\b",
    r"\bconsulted units\b",
    r"\bapproved consultation\b",
    r"## Specialist Consultation",
]


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


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_runtime(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-current-routing-contract-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & {ps_quote(str(RUNTIME_SCRIPT))} "
                f"-Task {ps_quote(task)} "
                "-Mode interactive_governed "
                f"-RunId {ps_quote(run_id)} "
                f"-ArtifactRoot {ps_quote(str(artifact_root))}; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=180,
        env={
            **os.environ,
            "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1",
            "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "0",
            "VGO_SPECIALIST_CONSULTATION_MODE": "",
            "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
        },
    )
    return json.loads(completed.stdout)


def assert_current_text_clean(testcase: unittest.TestCase, text: str, *, label: str) -> None:
    lowered = text.lower()
    for pattern in ACTIVE_FORBIDDEN_PATTERNS:
        testcase.assertIsNone(
            re.search(pattern, lowered, flags=re.IGNORECASE),
            msg=f"{label} contains active legacy routing wording matching {pattern!r}",
        )


class CurrentRoutingContractCleanupTests(unittest.TestCase):
    def test_new_runtime_outputs_only_current_routing_and_usage_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(CURRENT_TASK, Path(tempdir))

            summary = payload["summary"]
            artifacts = summary["artifacts"]
            session_root = Path(payload["session_root"])

            self.assertIsNone(summary.get("specialist_consultation"))
            self.assertIsNone(artifacts.get("discussion_specialist_consultation"))
            self.assertIsNone(artifacts.get("planning_specialist_consultation"))
            self.assertEqual(
                [],
                sorted(path.name for path in session_root.glob("*specialist-consultation*.json")),
            )

            lifecycle = summary["specialist_lifecycle_disclosure"]
            self.assertEqual("skill_routing_usage_evidence", lifecycle["truth_model"])
            self.assertIn("skill_usage.used", lifecycle["rendered_text"])
            self.assertIn("selected skills", lifecycle["rendered_text"].lower())
            assert_current_text_clean(self, lifecycle["rendered_text"], label="lifecycle rendered text")

            requirement_doc = Path(artifacts["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(artifacts["execution_plan"]).read_text(encoding="utf-8")
            host_briefing = Path(artifacts["host_user_briefing"]).read_text(encoding="utf-8")

            for label, text in {
                "requirement doc": requirement_doc,
                "execution plan": execution_plan,
                "host briefing": host_briefing,
            }.items():
                assert_current_text_clean(self, text, label=label)
                self.assertIn("skill_usage", text, msg=f"{label} should mention skill_usage evidence")

            self.assertIn("## Skill Usage", requirement_doc)
            self.assertIn("## Binary Skill Usage Plan", execution_plan)

    def test_runtime_packet_does_not_emit_old_routing_compatibility_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(CURRENT_TASK, Path(tempdir))
            packet_path = Path(payload["summary"]["artifacts"]["runtime_input_packet"])
            packet = load_json(packet_path)

            self.assertIn("skill_routing", packet)
            self.assertIn("skill_usage", packet)
            self.assertNotIn("legacy_skill_routing", packet)
            self.assertNotIn("specialist_recommendations", packet)
            self.assertNotIn("specialist_dispatch", packet)
            self.assertNotIn("stage_assistant_hints", packet)

    def test_legacy_consultation_projection_is_explicitly_legacy(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        script = (
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(RETIRED_CONSULTATION_COMMON))}; "
            "$receipt = [pscustomobject]@{ "
            "enabled = $true; "
            "window_id = 'discussion'; "
            "stage = 'deep_interview'; "
            "user_disclosures = @([pscustomobject]@{ "
            "skill_id = 'legacy-skill'; "
            "why_now = 'old packet disclosure'; "
            "native_skill_entrypoint = 'C:\\legacy\\SKILL.md'; "
            "native_skill_description = 'legacy compatibility only' "
            "}); "
            "consulted_units = @(); "
            "routed_units = @([pscustomobject]@{ "
            "skill_id = 'legacy-skill'; "
            "status = 'routed_pending_current_session'; "
            "summary = 'old routed receipt, not use evidence' "
            "}); "
            "summary = [pscustomobject]@{ consulted_unit_count = 0; routed_unit_count = 1 }; "
            "freeze_gate = [pscustomobject]@{ passed = $true; errors = @() } "
            "}; "
            "$layer = New-VibeRetiredSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt; "
            "$lifecycle = New-VibeSpecialistLifecycleDisclosureProjection -RuntimeInputPacket $null -DiscussionConsultationReceipt $receipt; "
            "$markdown = Get-VibeSpecialistLifecycleDisclosureMarkdownLines -LifecycleDisclosure $lifecycle; "
            "[pscustomobject]@{ "
            "layer_id = $layer.layer_id; "
            "truth_layer = $layer.truth_layer; "
            "truth_model = $lifecycle.truth_model; "
            "markdown = ($markdown -join \"`n\") "
            "} | ConvertTo-Json -Depth 20 "
            "}"
        )
        completed = subprocess.run(
            [shell, "-NoLogo", "-NoProfile", "-Command", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=60,
        )
        payload = json.loads(completed.stdout)

        self.assertEqual("discussion_consultation", payload["layer_id"])
        self.assertEqual("consultation", payload["truth_layer"])
        self.assertEqual("legacy_routing_consultation_execution_separated", payload["truth_model"])
        self.assertIn("## Legacy Specialist Lifecycle Disclosure", payload["markdown"])
        self.assertIn("Usage claims still require `skill_usage.used` evidence", payload["markdown"])

    def test_retired_consultation_fallback_fails_when_helper_missing_for_non_null_receipt(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            runtime_dir = temp_root / "scripts" / "runtime"
            common_dir = temp_root / "scripts" / "common"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            common_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RUNTIME_COMMON, runtime_dir / "VibeRuntime.Common.ps1")
            shutil.copy2(
                REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1",
                common_dir / "vibe-governance-helpers.ps1",
            )

            copied_runtime = runtime_dir / "VibeRuntime.Common.ps1"
            script = (
                "& { "
                "$ErrorActionPreference = 'Stop'; "
                f". {ps_quote(str(copied_runtime))}; "
                "$receipt = [pscustomobject]@{ enabled = $true }; "
                "$payload = try { "
                "  New-VibeRetiredSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt | Out-Null; "
                "  [pscustomobject]@{ failed = $false; message = '' } "
                "} catch { "
                "  [pscustomobject]@{ failed = $true; message = $_.Exception.Message } "
                "}; "
                "$payload | ConvertTo-Json -Depth 5 "
                "}"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                timeout=60,
            )
            payload = json.loads(completed.stdout)

            self.assertTrue(payload["failed"])
            self.assertIn("Missing retired consultation helper", payload["message"])
            self.assertIn("VibeRetiredConsultation.Common.ps1", payload["message"])

    def test_retired_stage_event_fallback_returns_null_for_non_consultation_segment_when_helper_missing(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            runtime_dir = temp_root / "scripts" / "runtime"
            common_dir = temp_root / "scripts" / "common"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            common_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RUNTIME_COMMON, runtime_dir / "VibeRuntime.Common.ps1")
            shutil.copy2(
                REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1",
                common_dir / "vibe-governance-helpers.ps1",
            )

            copied_runtime = runtime_dir / "VibeRuntime.Common.ps1"
            script = (
                "& { "
                "$ErrorActionPreference = 'Stop'; "
                f". {ps_quote(str(copied_runtime))}; "
                "$payload = try { "
                "  $eventId = Get-VibeRetiredHostStageDisclosureEventId "
                "    -SegmentId 'discussion_routing' "
                "    -Skills @([pscustomobject]@{ skill_id = 'x'; state = 'selected' }); "
                "  [pscustomobject]@{ failed = $false; is_null = ($null -eq $eventId); message = '' } "
                "} catch { "
                "  [pscustomobject]@{ failed = $true; is_null = $false; message = $_.Exception.Message } "
                "}; "
                "$payload | ConvertTo-Json -Depth 5 "
                "}"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                timeout=60,
            )
            payload = json.loads(completed.stdout)

            self.assertFalse(payload["failed"], payload["message"])
            self.assertTrue(payload["is_null"])

    def test_current_routing_governance_doc_defines_only_current_terms(self) -> None:
        path = REPO_ROOT / "docs" / "governance" / "current-routing-contract.md"
        text = path.read_text(encoding="utf-8")

        self.assertIn(
            "skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage.used / skill_usage.unused",
            text,
        )
        for required in [
            "`candidate`",
            "`selected`",
            "`used`",
            "`unused`",
            "`evidence`",
            "`retired old-format fields`",
        ]:
            self.assertIn(required, text)

        active_section = text.split("## Retired Old-Format Fields", 1)[0]
        for forbidden in [
            "route owner",
            "primary skill",
            "secondary skill",
            "consultation expert",
            "auxiliary expert",
        ]:
            self.assertNotIn(forbidden, active_section.lower())

    def test_retired_consultation_field_reads_live_outside_current_runtime_common(self) -> None:
        current_text = RUNTIME_COMMON.read_text(encoding="utf-8")
        legacy_text = RETIRED_CONSULTATION_COMMON.read_text(encoding="utf-8")

        for retired_field in [
            "consulted_units",
            "routed_units",
            "discussion_consultation",
            "planning_consultation",
        ]:
            self.assertNotIn(retired_field, current_text)
            self.assertIn(retired_field, legacy_text)

        self.assertIn("New-VibeRetiredSpecialistConsultationLifecycleLayerProjection", legacy_text)
        self.assertNotIn("New-VibeSpecialistConsultationLifecycleLayerProjection", current_text)


if __name__ == "__main__":
    unittest.main()
