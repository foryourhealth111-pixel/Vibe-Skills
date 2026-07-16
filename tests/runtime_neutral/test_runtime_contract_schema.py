from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
SPECIALIST_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."


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


def all_uncovered_host_decision_json() -> str:
    return json.dumps(
        {
            "agent_skill_organization": {
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "XL",
                "modules": [
                    {
                        "module_id": "runtime_contract_schema",
                        "goal": "Verify shared runtime packet, manifest, and receipt truth.",
                        "candidate_skill_ids": [],
                        "execution_mode": "blocked_gap",
                        "acceptance_criteria": [
                            {
                                "criterion_id": "runtime-contract-result",
                                "description": "The shared runtime contract truth is verified.",
                                "verification_mode": "automated",
                            }
                        ],
                    }
                ],
                "selected_skills": [],
                "uncovered_modules": [
                    {
                        "module_id": "runtime_contract_schema",
                        "reason": "The schema contract does not require a task specialist.",
                    }
                ],
                "workflow_level_contract": {
                    "L": "Use one serial governed lane.",
                    "XL": "Use bounded waves when the approved organization needs them.",
                },
            }
        }
    )


def run_ps_json(body: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", body],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def run_runtime(artifact_root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-contract-" + uuid.uuid4().hex[:10]
    host_decision_json = all_uncovered_host_decision_json()
    effective_env = os.environ.copy()
    if extra_env:
        effective_env.update(extra_env)

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
                f"$result = & {ps_quote(str(RUNTIME_ENTRY))} "
                f"-Task {ps_quote(SPECIALIST_TASK)} "
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
        env=effective_env,
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class RuntimeContractSchemaTests(unittest.TestCase):
    def test_workspace_project_descriptor_defaults_to_workspace_sidecar_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace_root = Path(tempdir) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)

            payload = run_ps_json(
                "& { "
                f". {ps_quote(str(RUNTIME_COMMON))}; "
                "$path = Initialize-VibeWorkspaceProjectDescriptor "
                f"-RepoRoot {ps_quote(str(workspace_root.resolve()))}; "
                "$descriptor = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json; "
                "$descriptor | ConvertTo-Json -Depth 10 }"
            )

        expected_sidecar_root = str((workspace_root / ".vibeskills").resolve())
        expected_project_descriptor = str((workspace_root / ".vibeskills" / "project.json").resolve())
        self.assertEqual(str(workspace_root.resolve()), payload["workspace_root"])
        self.assertEqual(expected_sidecar_root, payload["workspace_sidecar_root"])
        self.assertEqual(expected_project_descriptor, payload["project_descriptor_path"])
        self.assertEqual(expected_sidecar_root, payload["default_artifact_root"])
        self.assertEqual(expected_project_descriptor, payload["memory_plane"]["identity_root"])
        self.assertEqual("workspace_shared_memory_v1", payload["memory_plane"]["driver_contract"])

    def test_runtime_packet_storage_uses_artifact_root_as_workspace_when_workspace_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                Path(tempdir),
                extra_env={"VCO_HOST_ID": "openclaw"},
            )
            runtime_input = load_json(payload["summary"]["artifacts"]["runtime_input_packet"])
            storage = runtime_input["storage"]

        expected_workspace_root = Path(tempdir).resolve()
        self.assertEqual(str(expected_workspace_root), storage["workspace_root"])
        self.assertEqual(str((expected_workspace_root / ".vibeskills").resolve()), storage["workspace_sidecar_root"])
        self.assertEqual(str(expected_workspace_root), storage["artifact_root"])
        self.assertEqual("explicit_override", storage["artifact_root_source"])
        self.assertFalse(storage["default_workspace_sidecar_artifact_root"])

    def test_runtime_packet_and_execution_manifest_share_host_and_hierarchy_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

        runtime_host = runtime_input["host_adapter"]
        self.assertEqual("openclaw", runtime_host["requested_host_id"])
        self.assertEqual("openclaw", runtime_host["effective_host_id"])
        handoff = execution_manifest["module_handoff"]
        self.assertEqual(runtime_host["requested_host_id"], handoff["requested_host_adapter_id"])
        self.assertEqual(runtime_host["effective_host_id"], handoff["effective_host_adapter_id"])
        self.assertNotIn("route_runtime_alignment", execution_manifest)
        self.assertEqual(runtime_input["hierarchy"], execution_manifest["hierarchy"])
        self.assertEqual("root", runtime_input["hierarchy"]["governance_scope"])
        self.assertEqual(runtime_input["run_id"], runtime_input["hierarchy"]["root_run_id"])

    def test_runtime_packet_execution_manifest_and_execute_receipt_share_authority_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            execute_receipt = load_json(summary["artifacts"]["execute_receipt"])

        authority_flags = runtime_input["authority_flags"]
        authority = execution_manifest["authority"]
        self.assertEqual(authority_flags["allow_requirement_freeze"], authority["canonical_requirement_write_allowed"])
        self.assertEqual(authority_flags["allow_plan_freeze"], authority["canonical_plan_write_allowed"])
        self.assertEqual(authority_flags["allow_global_dispatch"], authority["global_dispatch_allowed"])
        self.assertEqual(authority_flags["allow_completion_claim"], authority["completion_claim_allowed"])
        self.assertEqual(authority["completion_claim_allowed"], execute_receipt["completion_claim_allowed"])

    def test_runtime_summary_matches_payload_and_report_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(Path(tempdir), extra_env={"VCO_HOST_ID": "openclaw"})
            summary = payload["summary"]
            summary_from_file = load_json(payload["summary_path"])

        self.assertEqual(summary, summary_from_file)
        self.assertEqual("plan_execute", summary["terminal_stage"])
        self.assertIsNotNone(summary["artifacts"]["agent_execution_handoff"])
        self.assertIsNone(summary["artifacts"]["memory_activation_report"])
        self.assertIsNone(summary["memory_activation"])
        self.assertIsNone(summary["artifacts"]["delivery_acceptance_report"])
        self.assertIsNone(summary["delivery_acceptance"])


if __name__ == "__main__":
    unittest.main()
