from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"


SPECIALIST_TASK = (
    "I have a failing test and a stack trace. Help me debug systematically "
    "before proposing fixes."
)


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

    run_id = "pytest-active-consult-off-" + uuid.uuid4().hex[:10]
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
        env={
            **os.environ,
            "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1",
            "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "0",
            "VGO_SPECIALIST_CONSULTATION_MODE": "",
            "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
        },
    )
    return json.loads(completed.stdout)


class ActiveConsultationSimplificationTests(unittest.TestCase):
    def test_default_runtime_closes_without_active_consultation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(SPECIALIST_TASK, Path(tempdir))

            summary = payload["summary"]
            artifacts = summary["artifacts"]
            session_root = Path(payload["session_root"])

            self.assertIsNone(artifacts.get("discussion_specialist_consultation"))
            self.assertIsNone(artifacts.get("planning_specialist_consultation"))
            self.assertIsNone(summary.get("specialist_consultation"))
            self.assertEqual(
                [],
                sorted(path.name for path in session_root.glob("*specialist-consultation*.json")),
            )

            lifecycle = summary["specialist_lifecycle_disclosure"]
            layer_ids = [str(layer["layer_id"]) for layer in list(lifecycle["layers"])]
            self.assertIn("discussion_routing", layer_ids)
            self.assertNotIn("discussion_consultation", layer_ids)
            self.assertNotIn("planning_consultation", layer_ids)
            self.assertNotIn("consultation", str(lifecycle["truth_model"]).lower())

            requirement_doc = Path(artifacts["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(artifacts["execution_plan"]).read_text(encoding="utf-8")
            for text in (requirement_doc, execution_plan, lifecycle["rendered_text"]):
                self.assertNotIn("## Specialist Consultation", text)
                self.assertNotIn("consultation truth", text)
                self.assertNotIn("stage assistant", text.lower())
            self.assertIn("## Skill Usage", requirement_doc)
            self.assertIn("## Binary Skill Usage Plan", execution_plan)
            self.assertIn("used` / `unused", requirement_doc)
            self.assertIn("skill_usage.used` / `skill_usage.unused", execution_plan)

    def test_legacy_consultation_projection_remains_readable_without_usage_claim(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        script = (
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
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
            "$layer = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt; "
            "$segment = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $layer -ConsultationReceipt $receipt; "
            "[pscustomobject]@{ "
            "layer_id = $layer.layer_id; "
            "truth_layer = $layer.truth_layer; "
            "skill_state = $layer.skills[0].state; "
            "segment_category = $segment.category; "
            "rendered_text = $segment.rendered_text "
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
        )
        payload = json.loads(completed.stdout)

        self.assertEqual("discussion_consultation", payload["layer_id"])
        self.assertEqual("consultation", payload["truth_layer"])
        self.assertEqual("routed_pending_current_session", payload["skill_state"])
        self.assertEqual("consultation", payload["segment_category"])
        self.assertIn("Usage claims still require `skill_usage` evidence", payload["rendered_text"])


if __name__ == "__main__":
    unittest.main()
