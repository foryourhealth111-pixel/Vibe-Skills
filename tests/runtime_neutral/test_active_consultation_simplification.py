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
    target_root = artifact_root / ".agents"
    skill_path = target_root / "skills" / "systematic-debugging" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "---\nname: systematic-debugging\ndescription: Debug failing tests and stack traces systematically.\n---\n",
        encoding="utf-8",
    )
    host_decision_json = json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "L",
                "modules": [
                    {
                        "module_id": "debug_failure",
                        "goal": "Debug the failing test and stack trace.",
                        "candidate_skill_ids": ["systematic-debugging"],
                        "execution_mode": "skill_assigned",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "diagnosis-result",
                                "description": "The failure diagnosis identifies a verified root cause.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [
                    {
                        "skill_id": "systematic-debugging",
                        "module_ids": ["debug_failure"],
                        "responsibility": "Own systematic failure diagnosis.",
                        "reason": "Its SKILL.md directly owns this work.",
                    }
                ],
                "uncovered_modules": [],
                "workflow_level_contract": {
                    "L": "Use one bounded serial debugging lane.",
                    "XL": "Use bounded parallel diagnosis and review lanes.",
                },
            }
        },
        separators=(",", ":"),
    )
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
                f"$result = & {ps_quote(str(RUNTIME_SCRIPT))} "
                f"-Task {ps_quote(task)} "
                "-Mode interactive_governed "
                f"-RunId {ps_quote(run_id)} "
                f"-ArtifactRoot {ps_quote(str(artifact_root))} "
                f"-HostDecisionJson {ps_quote(host_decision_json)}; "
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
            "VIBE_AGENTS_HOME": str(target_root),
        },
    )
    return json.loads(completed.stdout)


class ActiveConsultationSimplificationTests(unittest.TestCase):
    def test_default_runtime_closes_without_active_consultation_artifacts_even_with_selected_skill(self) -> None:
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

            self.assertNotIn("specialist_lifecycle_disclosure", summary)

            requirement_doc = Path(artifacts["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(artifacts["execution_plan"]).read_text(encoding="utf-8")
            for text in (requirement_doc, execution_plan):
                self.assertNotIn("## Specialist Consultation", text)
                self.assertNotIn("consultation truth", text)
                self.assertNotIn("stage assistant", text.lower())
            self.assertNotIn("## Skill Execution Decision", requirement_doc)
            self.assertNotIn("Decision state: approved_dispatch", requirement_doc)
            self.assertNotIn("## Selected Skill", requirement_doc)
            self.assertNotIn("Selected Skill: diagnose", requirement_doc)
            self.assertNotIn("## Skill Execution Decision Plan", execution_plan)
            self.assertNotIn("Frozen decision state: approved_dispatch", execution_plan)
            self.assertIn("## Module Work Plan", execution_plan)

    def test_retired_consultation_script_and_policy_are_not_packaged(self) -> None:
        self.assertFalse((REPO_ROOT / "scripts" / "runtime" / "VibeConsultation.Common.ps1").exists())
        self.assertFalse((REPO_ROOT / "scripts" / "runtime" / "legacy" / "VibeRetiredConsultation.Common.ps1").exists())
        self.assertFalse((REPO_ROOT / "config" / "specialist-consultation-policy.json").exists())

        current_surfaces = [
            REPO_ROOT / "config" / "runtime-script-manifest.json",
            REPO_ROOT / "config" / "runtime-config-manifest.json",
            REPO_ROOT / "config" / "version-governance.json",
            REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1",
        ]
        for path in current_surfaces:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("VibeConsultation.Common.ps1", text, str(path))
            self.assertNotIn("VibeRetiredConsultation.Common.ps1", text, str(path))
            self.assertNotIn("RetiredConsultation", text, str(path))
            self.assertNotIn("specialist-consultation-policy.json", text, str(path))


if __name__ == "__main__":
    unittest.main()
