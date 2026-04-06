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
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
ML_PROMPT = (
    "Build a scikit-learn tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
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


def freeze_runtime_packet(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-freeze-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{FREEZE_SCRIPT}' "
                f"-Task '{task}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=dict(os.environ),
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class SkillPromotionFreezeContractTests(unittest.TestCase):
    def test_eligible_matched_skill_is_approved_and_not_ghosted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = freeze_runtime_packet(ML_PROMPT, Path(tempdir))
            packet = load_json(payload["packet_path"])
            dispatch = packet["specialist_dispatch"]

            self.assertIn("scikit-learn", as_list(dispatch["matched_skill_ids"]))
            self.assertIn("scikit-learn", list(dispatch["approved_skill_ids"]))
            self.assertGreaterEqual(len(as_list(dispatch["surfaced_skill_ids"])), len(as_list(dispatch["matched_skill_ids"])))
            self.assertEqual([], as_list(dispatch["blocked_skill_ids"]))
            self.assertEqual([], as_list(dispatch["degraded_skill_ids"]))
            self.assertEqual([], as_list(dispatch["ghost_match_skill_ids"]))

            promotion_outcomes = list(dispatch["promotion_outcomes"])
            scikit_learn_outcome = next(
                item for item in promotion_outcomes if item["skill_id"] == "scikit-learn"
            )
            self.assertEqual("approved_dispatch", scikit_learn_outcome["promotion_state"])
            self.assertFalse(scikit_learn_outcome["destructive"])
            self.assertTrue(scikit_learn_outcome["contract_complete"])

    def test_freeze_records_explicit_states_for_all_surfaced_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = freeze_runtime_packet(ML_PROMPT, Path(tempdir))
            packet = load_json(payload["packet_path"])
            dispatch = packet["specialist_dispatch"]

            surfaced = {str(skill_id) for skill_id in as_list(dispatch["surfaced_skill_ids"])}
            outcome_ids = {str(item["skill_id"]) for item in list(dispatch["promotion_outcomes"])}

            self.assertTrue(surfaced)
            self.assertEqual(surfaced, outcome_ids)
