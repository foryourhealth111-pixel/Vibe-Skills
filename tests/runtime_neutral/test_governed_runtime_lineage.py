from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "runtime-input-packet-policy.json"
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _agent_direct_host_decision_json() -> str:
    return json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "XL",
                "modules": [
                    {
                        "module_id": "runtime_lineage",
                        "goal": "Verify governed runtime lineage artifacts.",
                        "candidate_skill_ids": [],
                        "execution_mode": "agent_direct",
                        "write_scope": "outputs/runtime-lineage/**",
                        "expected_outputs": ["outputs/runtime-lineage/verification.json"],
                        "verification": ["Check the governed lineage artifacts and record the result."],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "lineage-result",
                                "description": "The governed runtime lineage artifacts are verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [],
                "uncovered_modules": [],
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


def run_governed_runtime(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-lineage-" + uuid.uuid4().hex[:10]
    host_decision_json = _agent_direct_host_decision_json()
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
                f"$result = & {_ps_single_quote(str(RUNTIME_ENTRY))} "
                f"-Task {_ps_single_quote(task)} "
                "-Mode interactive_governed "
                f"-RunId {_ps_single_quote(run_id)} "
                f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
                f"-HostDecisionJson {_ps_single_quote(host_decision_json)}; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


class GovernedRuntimeLineageTests(unittest.TestCase):
    def test_runtime_policy_declares_governance_artifact_contract(self) -> None:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        artifact_contract = policy["hierarchy_contract"]["governance_artifacts"]

        self.assertEqual("governance-capsule.json", artifact_contract["capsule"])
        self.assertEqual("stage-lineage.json", artifact_contract["lineage"])
        self.assertEqual("delegation-envelope.json", artifact_contract["delegation_envelope"])
        self.assertEqual("delegation-validation-receipt.json", artifact_contract["delegation_validation"])

    def test_root_runtime_writes_capsule_and_stage_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_governed_runtime(
                "Governed entry lineage runtime smoke.",
                artifact_root=Path(tempdir),
            )
            artifacts = payload["summary"]["artifacts"]

            capsule = json.loads(Path(artifacts["governance_capsule"]).read_text(encoding="utf-8"))
            lineage = json.loads(Path(artifacts["stage_lineage"]).read_text(encoding="utf-8"))

            self.assertEqual("vibe", capsule["runtime_selected_skill"])
            self.assertEqual("root", capsule["governance_scope"])
            self.assertEqual(
                [
                    "skeleton_check",
                    "deep_interview",
                    "requirement_doc",
                    "xl_plan",
                    "plan_execute",
                ],
                [entry["stage_name"] for entry in lineage["stages"]],
            )
            self.assertEqual("plan_execute", payload["summary"]["terminal_stage"])
            self.assertIsNone(artifacts["cleanup_receipt"])
            self.assertIsNone(artifacts["memory_activation_report"])


if __name__ == "__main__":
    unittest.main()
