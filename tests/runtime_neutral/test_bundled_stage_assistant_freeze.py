from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"


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


class BundledStageAssistantFreezeTests(unittest.TestCase):
    def test_runtime_freeze_keeps_vibe_as_route_authority_and_splits_stage_assistants_from_specialists(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            run_id = "pytest-bundled-stage-assistant"
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(FREEZE_SCRIPT),
                "-Task",
                "Please keep task_plan.md and progress.md updated for this complex task.",
                "-Mode",
                "interactive_governed",
                "-RunId",
                run_id,
                "-ArtifactRoot",
                str(artifact_root),
            ]
            subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)

            packet_path = next(artifact_root.rglob("runtime-input-packet.json"))
            packet = json.loads(packet_path.read_text(encoding="utf-8"))

            self.assertEqual("vibe", packet["route_snapshot"]["selected_skill"])

            recommendation_pairs = [
                (item["skill_id"], item["source"])
                for item in packet["specialist_recommendations"]
            ]
            self.assertNotIn(("writing-plans", "route_stage_assistant"), recommendation_pairs)
            self.assertNotIn(("planning-with-files", "route_stage_assistant"), recommendation_pairs)

            hint_pairs = [
                (item["skill_id"], item["source"])
                for item in packet["stage_assistant_hints"]
            ]
            self.assertIn(("writing-plans", "route_stage_assistant"), hint_pairs)
            self.assertIn(("planning-with-files", "route_stage_assistant"), hint_pairs)


if __name__ == "__main__":
    unittest.main()
