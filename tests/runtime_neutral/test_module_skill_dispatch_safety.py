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
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
ML_PROMPT = (
    "Build a scikit-learn tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
)
DESTRUCTIVE_PROMPT = (
    "Build a scikit-learn tabular classification baseline, "
    "then delete old generated artifacts and overwrite install settings."
)


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def host_decision_json(*, include_blocked_gap: bool = False) -> str:
    modules = [
        {
            "module_id": "tabular_classification",
            "goal": "Build and evaluate the tabular classification baseline.",
            "candidate_skill_ids": ["scikit-learn"],
            "execution_mode": "skill_assigned",
            "acceptance_criteria": [
                {
                    "criterion_id": "tabular-result",
                    "description": "The tabular baseline result is present and verified.",
                    "verification_mode": "automated",
                }
            ],
        }
    ]
    uncovered_modules = []
    if include_blocked_gap:
        modules.append(
            {
                "module_id": "unsupported_validation",
                "goal": "Validate the result with a missing local specialist.",
                "candidate_skill_ids": [],
                "execution_mode": "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "unsupported-validation-result",
                        "description": "The unsupported validation gap is explicitly reported.",
                        "verification_mode": "manual",
                    }
                ],
            }
        )
        uncovered_modules.append(
            {
                "module_id": "unsupported_validation",
                "reason": "No installed local Skill owns this validation module.",
            }
        )

    return json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "XL",
                "modules": modules,
                "selected_skills": [
                    {
                        "skill_id": "scikit-learn",
                        "module_ids": ["tabular_classification"],
                        "responsibility": "Build and evaluate the tabular model.",
                        "reason": "Its SKILL.md directly owns scikit-learn workflows.",
                    }
                ],
                "uncovered_modules": uncovered_modules,
                "workflow_level_contract": {
                    "L": "Use one serial governed lane.",
                    "XL": "Use bounded waves when the approved organization needs them.",
                },
            }
        }
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


def run_runtime(
    task: str,
    artifact_root: Path,
    *,
    extra_env: dict[str, str] | None = None,
    include_blocked_gap: bool = False,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-promotion-" + uuid.uuid4().hex[:10]
    decision_json = host_decision_json(include_blocked_gap=include_blocked_gap)
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "& { "
                f"$result = & {ps_quote(RUNTIME_ENTRY)} "
                f"-Task {ps_quote(task)} "
                "-Mode interactive_governed "
                f"-RunId {ps_quote(run_id)} "
                f"-ArtifactRoot {ps_quote(artifact_root)} "
                f"-HostDecisionJson {ps_quote(decision_json)}; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env={**os.environ, **(extra_env or {})},
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


def write_installed_skill(target_root: Path, skill_id: str) -> Path:
    skill_path = target_root / "skills" / skill_id / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (
            "---\n"
            f"name: {skill_id}\n"
            f"description: Installed {skill_id} test skill.\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return skill_path


class ModuleSkillDispatchSafetyTests(unittest.TestCase):
    def test_destructive_guard_stays_in_planning_state_without_prebuilt_result(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / ".agents"
            write_installed_skill(target_root, "scikit-learn")
            payload = run_runtime(
                DESTRUCTIVE_PROMPT,
                temp_path,
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            module_execution_path = Path(handoff["module_execution_path"])
            assignment = runtime_input["module_assignments"]["units"][0]

            self.assertNotIn("specialist_dispatch", runtime_input)
            self.assertNotIn("specialist_decision", runtime_input)
            self.assertNotIn("specialist_accounting", execution_manifest)
            self.assertTrue(assignment["destructive"])
            self.assertEqual(
                ["destructive_delete", "destructive_overwrite"],
                assignment["destructive_reason_codes"],
            )
            self.assertEqual("agent_action_required", execution_manifest["module_handoff"]["status"])
            self.assertIsNone(summary["artifacts"]["module_execution"])
            self.assertFalse(module_execution_path.exists())
            self.assertTrue(all("state" not in unit for unit in handoff["units"]))

    def test_agent_handoff_does_not_claim_contribution_before_module_work_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / ".agents"
            write_installed_skill(target_root, "scikit-learn")
            payload = run_runtime(
                ML_PROMPT,
                temp_path,
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            self.assertNotIn("specialist_accounting", execution_manifest)
            self.assertEqual("agent_action_required", execution_manifest["module_handoff"]["status"])
            self.assertEqual(["scikit-learn"], execution_manifest["module_handoff"]["assigned_skill_ids"])
            self.assertIsNone(summary["artifacts"]["module_execution"])
            self.assertFalse(Path(handoff["module_execution_path"]).exists())
            self.assertTrue(all("state" not in unit for unit in handoff["units"]))

    def test_blocked_gap_stays_in_module_plan_until_agent_return(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / ".agents"
            write_installed_skill(target_root, "scikit-learn")
            payload = run_runtime(
                ML_PROMPT,
                temp_path,
                extra_env={"VIBE_AGENTS_HOME": str(target_root)},
                include_blocked_gap=True,
            )
            summary = payload["summary"]
            module_work_plan = load_json(summary["artifacts"]["module_work_plan"])
            handoff = load_json(summary["artifacts"]["agent_execution_handoff"])
            gap = next(
                module
                for module in module_work_plan["modules"]
                if module["module_id"] == "unsupported_validation"
            )

            self.assertEqual("blocked_gap", gap["execution_mode"])
            self.assertEqual(
                "No installed local Skill owns this validation module.",
                gap["gap_reason"],
            )
            self.assertNotIn("unsupported_validation", [unit["module_id"] for unit in handoff["units"]])
            self.assertIsNone(summary["artifacts"]["module_execution"])
            self.assertFalse(Path(handoff["module_execution_path"]).exists())
