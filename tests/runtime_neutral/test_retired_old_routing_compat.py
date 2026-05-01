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
SKILL_ROUTING_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeSkillRouting.Common.ps1"

CURRENT_TASK = (
    "Build a scikit-learn classification baseline, include a result figure, "
    "and report selected skills and skill_usage evidence."
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


def run_ps_json(script: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")
    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def run_runtime(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available")

    run_id = "pytest-retired-routing-compat-" + uuid.uuid4().hex[:10]
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


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class RetiredOldRoutingCompatibilityTests(unittest.TestCase):
    def test_current_selection_ignores_old_top_level_specialist_dispatch(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "specialist_dispatch = [pscustomobject]@{ approved_dispatch = @([pscustomobject]@{ skill_id = 'legacy-only' }) } "
            "}; "
            "$ids = Get-VibeSkillRoutingSelectedSkillIds -RuntimeInputPacket $packet; "
            "[pscustomobject]@{ selected_skill_ids = @($ids) } | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual([], as_list(payload["selected_skill_ids"]))

    def test_current_selection_ignores_legacy_skill_routing_container(self) -> None:
        payload = run_ps_json(
            "& { "
            f". {ps_quote(str(RUNTIME_COMMON))}; "
            f". {ps_quote(str(SKILL_ROUTING_COMMON))}; "
            "$packet = [pscustomobject]@{ "
            "legacy_skill_routing = [pscustomobject]@{ "
            "specialist_recommendations = @([pscustomobject]@{ skill_id = 'legacy-recommendation' }); "
            "stage_assistant_hints = @([pscustomobject]@{ skill_id = 'legacy-helper' }); "
            "specialist_dispatch = [pscustomobject]@{ approved_dispatch = @([pscustomobject]@{ skill_id = 'legacy-dispatch' }) } "
            "} "
            "}; "
            "$ids = Get-VibeSkillRoutingSelectedSkillIds -RuntimeInputPacket $packet; "
            "$projection = Get-VibeRuntimeSelectedSkillExecutionProjection -RuntimeInputPacket $packet; "
            "$recommendations = @(Get-VibeRuntimeSpecialistRecommendations -RuntimeInputPacket $packet); "
            "$hints = @(Get-VibeRuntimeStageAssistantHints -RuntimeInputPacket $packet); "
            "[pscustomobject]@{ "
            "selected_skill_ids = @($ids); "
            "dispatch_is_null = ($null -eq $projection); "
            "recommendation_count = @($recommendations).Count; "
            "hint_count = @($hints).Count "
            "} | ConvertTo-Json -Depth 20 "
            "}"
        )

        self.assertEqual([], as_list(payload["selected_skill_ids"]))
        self.assertTrue(bool(payload["dispatch_is_null"]))
        self.assertEqual(0, int(payload["recommendation_count"]))
        self.assertEqual(0, int(payload["hint_count"]))

    def test_new_runtime_packet_does_not_emit_old_routing_compatibility_box(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(CURRENT_TASK, Path(tempdir))
            packet_path = Path(payload["summary"]["artifacts"]["runtime_input_packet"])
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

        self.assertIn("skill_routing", packet)
        self.assertIn("skill_usage", packet)
        self.assertNotIn("legacy_skill_routing", packet)
        self.assertNotIn("specialist_recommendations", packet)
        self.assertNotIn("stage_assistant_hints", packet)

    def test_new_runtime_generated_docs_do_not_emit_specialist_consultation_section(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(CURRENT_TASK, Path(tempdir))
            artifacts = payload["summary"]["artifacts"]
            requirement_doc = Path(artifacts["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(artifacts["execution_plan"]).read_text(encoding="utf-8")
            host_briefing = Path(artifacts["host_user_briefing"]).read_text(encoding="utf-8")

        for label, text in {
            "requirement_doc": requirement_doc,
            "execution_plan": execution_plan,
            "host_briefing": host_briefing,
        }.items():
            self.assertNotIn("## Specialist Consultation", text, msg=label)
            self.assertIn("skill_usage", text, msg=label)


if __name__ == "__main__":
    unittest.main()
