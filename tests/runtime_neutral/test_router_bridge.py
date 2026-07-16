# ruff: noqa: RUF001

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "runtime-core" / "src"))
from vgo_runtime.router_contract_runtime import route_prompt


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "router" / "invoke-pack-route.py"
ROUTE_FIXTURE = REPO_ROOT / "tests" / "replay" / "route" / "recovery-wave-curated-prompts.json"
ROUTE_SKILLS = [
    "flashrag-evidence",
    "generating-test-reports",
    "gh-fix-ci",
    "latex-submission-pipeline",
    "literature-review",
    "ml-data-leakage-guard",
    "pdf",
    "preprocessing-data-with-automated-pipelines",
    "scientific-reporting",
    "scientific-schematics",
    "scientific-visualization",
    "scikit-learn",
    "sentry",
    "systematic-debugging",
    "webthinker-deep-research",
]


def install_route_skills(target_root: Path) -> None:
    skills_root = target_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    for skill_id in ROUTE_SKILLS:
        source = REPO_ROOT / "bundled" / "skills" / skill_id
        if source.exists():
            shutil.copytree(source, skills_root / skill_id)


def run_bridge(
    prompt: str,
    grade: str,
    task_type: str,
    requested_skill: str | None = None,
    entry_intent_id: str | None = None,
) -> dict:
    with tempfile.TemporaryDirectory() as tempdir:
        target_root = Path(tempdir) / ".agents"
        install_route_skills(target_root)
        command = [
            sys.executable,
            str(BRIDGE_SCRIPT),
            "--prompt",
            prompt,
            "--grade",
            grade,
            "--task-type",
            task_type,
            "--target-root",
            str(target_root),
            "--force-runtime-neutral",
        ]
        if requested_skill:
            command.extend(["--requested-skill", requested_skill])
        if entry_intent_id:
            command.extend(["--entry-intent-id", entry_intent_id])
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return json.loads(completed.stdout)


def run_powershell_route(prompt: str, grade: str, task_type: str, requested_skill: str | None = None) -> dict:
    powershell = shutil.which("pwsh")
    if not powershell:
        raise unittest.SkipTest("PowerShell 7 (pwsh) not found in PATH")

    with tempfile.TemporaryDirectory() as tempdir:
        target_root = Path(tempdir) / ".agents"
        install_route_skills(target_root)
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "router" / "resolve-pack-route.ps1"),
            "-Prompt",
            prompt,
            "-Grade",
            grade,
            "-TaskType",
            task_type,
            "-TargetRoot",
            str(target_root),
        ]
        if requested_skill:
            command.extend(["-RequestedSkill", requested_skill])

        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            check=True,
        )
        return json.loads(completed.stdout)


class RouterBridgeTests(unittest.TestCase):
    def test_runtime_neutral_bridge_satisfies_curated_route_cases(self) -> None:
        fixture = json.loads(ROUTE_FIXTURE.read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                result = run_bridge(case["prompt"], case["grade"], case["task_type"])
                expected = case["expected"]
                candidate_focus = result.get("candidate_focus") or {}

                self.assertEqual("local_skill_index", result["candidate_source"])
                if "route_mode" in expected:
                    self.assertEqual(expected["route_mode"], result["route_mode"])
                if "allowed_route_modes" in expected:
                    self.assertIn(result["route_mode"], expected["allowed_route_modes"])
                if "candidate_focus_pack" in expected:
                    self.assertEqual(expected["candidate_focus_pack"], candidate_focus["pack_id"])
                if "candidate_focus_skill" in expected:
                    self.assertEqual(expected["candidate_focus_skill"], candidate_focus["skill"])

    def test_no_local_candidate_omits_retired_confirmation_fields(self) -> None:
        result = run_bridge(
            "Help me clarify scope, choose repo path, define constraints, and then implement the feature with verification and deliverables.",
            "L",
            "planning",
        )

        self.assertEqual("no_local_candidate", result["route_mode"])
        self.assertEqual("no_local_candidate_above_threshold", result["route_reason"])
        self.assertIsNone(result["candidate_focus"])
        self.assertNotIn("confirm_required", result)
        self.assertNotIn("confirm_ui", result)
        self.assertEqual("local_index_no_match", result["truth_level"])

    def test_powershell_planning_prompt_uses_same_fallback_guard(self) -> None:
        result = run_powershell_route(
            "create implementation plan and task breakdown",
            "L",
            "planning",
        )

        self.assertEqual("no_local_candidate", result["route_mode"])
        self.assertEqual("no_local_candidate_above_threshold", result["route_reason"])
        self.assertIsNone(result["candidate_focus"])
        self.assertNotIn("confirm_ui", result)

    def test_requested_mixed_case_active_skill_becomes_candidate_focus(self) -> None:
        result = run_bridge(
            "请用机器学习专家视角审视这个分类方案",
            "L",
            "research",
            requested_skill="Scikit-Learn",
        )

        self.assertEqual("local_skill_overlay", result["route_mode"])
        self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
        self.assertEqual("scikit-learn", result["candidate_focus"]["skill"])

    def test_canonical_entry_intent_does_not_override_candidate_focus(self) -> None:
        prompt = (
            "Please use scikit-learn to prototype a tabular classification baseline, "
            "run feature selection, and compare cross-validation metrics."
        )
        baseline = route_prompt(prompt=prompt, grade="L", task_type="coding", repo_root=REPO_ROOT)
        wrapped = route_prompt(
            prompt=prompt,
            grade="L",
            task_type="coding",
            entry_intent_id="vibe",
            repo_root=REPO_ROOT,
        )

        self.assertEqual(baseline["route_mode"], wrapped["route_mode"])
        self.assertEqual(baseline["candidate_focus"]["pack_id"], wrapped["candidate_focus"]["pack_id"])
        self.assertEqual(baseline["candidate_focus"]["skill"], wrapped["candidate_focus"]["skill"])
        self.assertEqual("vibe", wrapped["alias"]["entry_intent_id"])

    def test_requested_vibe_preserves_runtime_authority_while_route_focuses_candidate(self) -> None:
        result = run_bridge(
            "I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
            "XL",
            "debug",
            requested_skill="vibe",
        )

        self.assertEqual("local_skill_overlay", result["route_mode"])
        self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
        self.assertEqual("systematic-debugging", result["candidate_focus"]["skill"])
        self.assertEqual("vibe", result["alias"]["requested_canonical"])


if __name__ == "__main__":
    unittest.main()
