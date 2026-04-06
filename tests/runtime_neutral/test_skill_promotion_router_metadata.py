from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_SCRIPT = REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"
ML_PROMPT = (
    "Please use scikit-learn to prototype a tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
)
DESTRUCTIVE_PROMPT = (
    "Delete the old generated artifacts, remove the obsolete branch, "
    "and overwrite the install settings to reset the environment."
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


def run_route(prompt: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(ROUTE_SCRIPT),
            "-Prompt",
            prompt,
            "-Grade",
            "M",
            "-TaskType",
            "coding",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class SkillPromotionRouterMetadataTests(unittest.TestCase):
    def test_non_destructive_ml_prompt_exposes_auto_dispatch_promotion_metadata(self) -> None:
        route = run_route(ML_PROMPT)

        selected = route["selected"]
        self.assertEqual("data-ml", selected["pack_id"])
        self.assertEqual("scikit-learn", selected["skill"])
        self.assertTrue(selected["promotion_eligible"])
        self.assertFalse(selected["destructive"])
        self.assertEqual([], as_list(selected["destructive_reason_codes"]))
        self.assertFalse(selected["snapshot_required"])
        self.assertFalse(selected["rollback_possible"])
        self.assertTrue(selected["contract_complete"])
        self.assertEqual("auto_dispatch", selected["recommended_promotion_action"])

        option = route["confirm_ui"]["options"][0]
        self.assertEqual("scikit-learn", option["skill"])
        self.assertTrue(option["promotion_eligible"])
        self.assertFalse(option["destructive"])
        self.assertTrue(option["contract_complete"])
        self.assertEqual("auto_dispatch", option["recommended_promotion_action"])

    def test_destructive_prompt_exposes_confirmation_gated_promotion_metadata(self) -> None:
        route = run_route(DESTRUCTIVE_PROMPT)

        selected = route["selected"]
        self.assertEqual("autonomous-builder", selected["skill"])
        self.assertFalse(selected["promotion_eligible"])
        self.assertTrue(selected["destructive"])
        self.assertTrue(selected["snapshot_required"])
        self.assertTrue(selected["rollback_possible"])
        self.assertTrue(selected["contract_complete"])
        self.assertEqual("require_confirmation", selected["recommended_promotion_action"])
        self.assertGreaterEqual(len(as_list(selected["destructive_reason_codes"])), 1)

        option = route["confirm_ui"]["options"][0]
        self.assertEqual("autonomous-builder", option["skill"])
        self.assertFalse(option["promotion_eligible"])
        self.assertTrue(option["destructive"])
        self.assertTrue(option["snapshot_required"])
        self.assertEqual("require_confirmation", option["recommended_promotion_action"])
