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


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def agent_skill_organization(selected_skill_ids: list[str]) -> dict[str, object]:
    module_id = "root_child_hierarchy"
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": module_id,
                "goal": "Verify root and child governed-runtime hierarchy behavior.",
                "candidate_skill_ids": selected_skill_ids,
                "execution_mode": "skill_assigned" if selected_skill_ids else "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "hierarchy-result",
                        "description": "The governed root and child hierarchy outcome is verified.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": skill_id,
                "module_ids": [module_id],
                "responsibility": "Own the module work delegated through the hierarchy test.",
                "reason": "The Agent selected this skill after reading its SKILL.md.",
            }
            for skill_id in selected_skill_ids
        ],
        "uncovered_modules": []
        if selected_skill_ids
        else [
            {
                "module_id": module_id,
                "reason": "The hierarchy assertion does not require a module Skill owner.",
            }
        ],
        "workflow_level_contract": {
            "L": "Use one serial governed lane.",
            "XL": "Use bounded waves when the approved organization needs them.",
        },
    }


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


def selected_skill_ids_from_packet(runtime_input_packet: dict[str, object]) -> set[str]:
    module_assignments = runtime_input_packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        return set()
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return set()
    return {
        str(unit.get("bound_skill", "")).strip()
        for unit in units
        if isinstance(unit, dict) and str(unit.get("bound_skill", "")).strip()
    }


def run_governed_runtime(
    task: str,
    artifact_root: Path,
    selected_skill_ids: list[str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-root-child-" + uuid.uuid4().hex[:10]
    host_decision_json = json.dumps(
        {"agent_skill_organization": agent_skill_organization(selected_skill_ids or [])}
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {ps_quote(script_path)} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            "-GovernanceScope root "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env={**os.environ},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def run_child_runtime(
    task: str,
    root_run_id: str,
    inherited_requirement_doc_path: Path,
    inherited_execution_plan_path: Path,
    artifact_root: Path,
    delegation_envelope_path: Path | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    effective_run_id = run_id or ("pytest-child-lane-" + uuid.uuid4().hex[:10])
    host_decision_json = json.dumps(
        {"agent_skill_organization": agent_skill_organization([])}
    )
    delegation_literal = (
        f"-DelegationEnvelopePath {ps_quote(delegation_envelope_path)} "
        if delegation_envelope_path is not None
        else ""
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {ps_quote(script_path)} "
            f"-Task {ps_quote(task)} "
            "-Mode interactive_governed "
            "-GovernanceScope child "
            f"-RunId {ps_quote(effective_run_id)} "
            f"-RootRunId {ps_quote(root_run_id)} "
            f"-ParentRunId {ps_quote(root_run_id)} "
            "-ParentUnitId 'pytest-child-unit' "
            f"-InheritedRequirementDocPath {ps_quote(inherited_requirement_doc_path)} "
            f"-InheritedExecutionPlanPath {ps_quote(inherited_execution_plan_path)} "
            f"{delegation_literal}"
            f"-ArtifactRoot {ps_quote(artifact_root)} "
            f"-HostDecisionJson {ps_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env={**os.environ},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime(child) returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def write_delegation_envelope_fixture(
    artifact_root: Path,
    root_payload: dict[str, object],
    child_run_id: str,
) -> Path:
    root_summary = root_payload["summary"]
    root_artifacts = root_summary["artifacts"]
    session_root = artifact_root / "outputs" / "runtime" / "vibe-sessions" / child_run_id
    session_root.mkdir(parents=True, exist_ok=True)
    envelope_path = session_root / "delegation-envelope.json"
    envelope = {
        "root_run_id": str(root_summary["run_id"]),
        "parent_run_id": str(root_summary["run_id"]),
        "parent_unit_id": "pytest-child-unit",
        "child_run_id": child_run_id,
        "governance_scope": "child_governed",
        "requirement_doc_path": str(Path(root_artifacts["requirement_doc"]).resolve()),
        "execution_plan_path": str(Path(root_artifacts["execution_plan"]).resolve()),
        "write_scope": "pytest:child-lane",
        "review_mode": "module_acceptance",
        "prompt_tail_required": "$vibe",
        "allow_requirement_freeze": False,
        "allow_plan_freeze": False,
        "allow_root_completion_claim": False,
    }
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return envelope_path


class RootChildHierarchyBridgeTests(unittest.TestCase):
    def test_contract_docs_exist(self) -> None:
        requirement_doc = REPO_ROOT / "docs" / "requirements" / "2026-03-28-root-child-vibe-hierarchy-governance.md"
        execution_plan = REPO_ROOT / "docs" / "plans" / "2026-03-28-root-child-vibe-hierarchy-governance-plan.md"
        stable_doc = REPO_ROOT / "docs" / "root-child-vibe-hierarchy-governance.md"

        self.assertTrue(requirement_doc.exists())
        self.assertTrue(execution_plan.exists())
        self.assertTrue(stable_doc.exists())

        stable_text = stable_doc.read_text(encoding="utf-8")
        self.assertIn("Root `vibe`: the only top-level governor", stable_text)
        self.assertIn("Child `vibe`: a subordinate execution lane", stable_text)
        self.assertIn("module-work-plan.json", stable_text)
        self.assertIn("agent-execution-handoff.json", stable_text)
        self.assertIn("module-execution.json", stable_text)
        self.assertNotIn("Specialist-Native Lane", stable_text)
        self.assertNotIn("bounded native units", stable_text)

    def test_runtime_input_policy_declares_hierarchy_fields(self) -> None:
        policy_path = REPO_ROOT / "config" / "runtime-input-packet-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy_text = json.dumps(policy, ensure_ascii=False, sort_keys=True)

        expected_tokens = [
            "governance_scope",
            "hierarchy_contract",
            "allow_requirement_freeze",
            "allow_plan_freeze",
            "allow_global_dispatch",
            "allow_completion_claim",
            "agent_skill_organization",
            "module_assignments",
            "module_skill_contract",
            "escalation_required",
        ]
        for token in expected_tokens:
            with self.subTest(token=token):
                self.assertIn(token, policy_text)
        for retired_token in (
            "skill_execution_contract",
            "native_skill_entrypoint",
            "direct_current_session_route",
        ):
            with self.subTest(retired_token=retired_token):
                self.assertNotIn(retired_token, policy_text)

    def test_root_runtime_keeps_vibe_authority_and_single_canonical_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_governed_runtime(
                "Root child hierarchy runtime smoke for authority and canonical surface checks.",
                artifact_root=Path(tempdir),
            )
            summary = payload["summary"]
            artifacts = summary["artifacts"]

            runtime_input_packet_path = Path(artifacts["runtime_input_packet"])
            requirement_doc_path = Path(artifacts["requirement_doc"])
            execution_plan_path = Path(artifacts["execution_plan"])
            execution_manifest_path = Path(artifacts["execution_manifest"])
            handoff_path = Path(artifacts["agent_execution_handoff"])

            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))
            execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            result_contract = handoff["result_contract"]
            module_execution_path = Path(handoff["module_execution_path"])
            module_handoff = execution_manifest["module_handoff"]

            selected_skill_ids = selected_skill_ids_from_packet(runtime_input_packet)
            bound_skill_ids = {
                str(unit.get("bound_skill", "")).strip()
                for unit in list(runtime_input_packet["module_assignments"]["units"])
                if str(unit.get("bound_skill", "")).strip()
            }
            self.assertEqual(bound_skill_ids, selected_skill_ids)
            self.assertEqual("vibe", runtime_input_packet["authority_flags"]["explicit_runtime_skill"])
            self.assertEqual("root", runtime_input_packet["governance_scope"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_requirement_freeze"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_plan_freeze"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_global_dispatch"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_completion_claim"])

            self.assertEqual("requirements", requirement_doc_path.parent.name)
            self.assertEqual("plans", execution_plan_path.parent.name)
            self.assertEqual("root", execution_manifest["governance_scope"])
            self.assertNotIn("route_runtime_alignment", execution_manifest)
            self.assertEqual("agent_action_required", module_handoff["status"])
            self.assertEqual("agent", module_handoff["control_owner"])
            self.assertEqual([], module_handoff["assigned_skill_ids"])
            self.assertEqual("agent_execution_handoff_v1", handoff["schema_version"])
            self.assertEqual(module_handoff["status"], handoff["status"])
            self.assertEqual(module_handoff["control_owner"], handoff["control_owner"])
            self.assertEqual(module_handoff["work_units"], handoff["units"])
            self.assertEqual("module_execution_v1", result_contract["schema_version"])
            self.assertEqual(summary["run_id"], result_contract["source_run_id"])
            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertFalse(artifacts["cleanup_receipt"])
            self.assertIsNone(artifacts["module_execution"])
            self.assertFalse(module_execution_path.exists())
            self.assertEqual([], handoff["units"])
            self.assertEqual([], result_contract["units"])
            self.assertEqual(
                ["blocked_gap"],
                [module["execution_mode"] for module in result_contract["modules"]],
            )
            self.assertTrue(result_contract["modules"][0]["gap_reason"])

    def test_child_runtime_requires_delegation_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            root_payload = run_governed_runtime(
                "Root child envelope seed for missing envelope rejection.",
                artifact_root=artifact_root,
            )

            with self.assertRaises(subprocess.CalledProcessError):
                run_child_runtime(
                    task="Child governed runtime should require delegation envelope.",
                    root_run_id=str(root_payload["summary"]["run_id"]),
                    inherited_requirement_doc_path=Path(root_payload["summary"]["artifacts"]["requirement_doc"]),
                    inherited_execution_plan_path=Path(root_payload["summary"]["artifacts"]["execution_plan"]),
                    artifact_root=artifact_root,
                )

    def test_child_runtime_keeps_agent_organization_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            root_payload = run_governed_runtime(
                "Root module handoff seed for child authority checks.",
                artifact_root=artifact_root,
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input_packet = json.loads(
                Path(root_artifacts["runtime_input_packet"]).read_text(encoding="utf-8")
            )

            self.assertEqual(set(), selected_skill_ids_from_packet(root_runtime_input_packet))
            child_run_id = "pytest-child-lane-" + uuid.uuid4().hex[:10]
            envelope_path = write_delegation_envelope_fixture(
                artifact_root=artifact_root,
                root_payload=root_payload,
                child_run_id=child_run_id,
            )

            child_payload = run_child_runtime(
                task="Child module handoff authority smoke.",
                root_run_id=str(root_summary["run_id"]),
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                artifact_root=artifact_root,
                delegation_envelope_path=envelope_path,
                run_id=child_run_id,
            )
            child_summary = child_payload["summary"]
            runtime_input_packet = json.loads(Path(child_summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8"))
            execution_manifest = json.loads(Path(child_summary["artifacts"]["execution_manifest"]).read_text(encoding="utf-8"))
            handoff = json.loads(Path(child_summary["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8"))
            result_contract = handoff["result_contract"]
            module_execution_path = Path(handoff["module_execution_path"])
            module_handoff = execution_manifest["module_handoff"]
            requirement_receipt = json.loads(Path(child_summary["artifacts"]["requirement_receipt"]).read_text(encoding="utf-8"))
            plan_receipt = json.loads(Path(child_summary["artifacts"]["execution_plan_receipt"]).read_text(encoding="utf-8"))
            delegation_validation_receipt = json.loads(
                Path(child_summary["artifacts"]["delegation_validation_receipt"]).read_text(encoding="utf-8")
            )

            self.assertEqual("child", child_summary["governance_scope"])
            self.assertEqual("child", runtime_input_packet["governance_scope"])
            self.assertEqual("vibe", runtime_input_packet["authority_flags"]["explicit_runtime_skill"])
            self.assertFalse(runtime_input_packet["authority_flags"]["allow_requirement_freeze"])
            self.assertFalse(runtime_input_packet["authority_flags"]["allow_plan_freeze"])
            self.assertFalse(runtime_input_packet["authority_flags"]["allow_global_dispatch"])
            self.assertFalse(runtime_input_packet["authority_flags"]["allow_completion_claim"])

            self.assertFalse(requirement_receipt["canonical_write_allowed"])
            self.assertFalse(plan_receipt["canonical_write_allowed"])
            self.assertEqual(
                str(Path(root_artifacts["requirement_doc"]).resolve()),
                str(Path(requirement_receipt["requirement_doc_path"]).resolve()),
            )
            self.assertEqual(
                str(Path(root_artifacts["execution_plan"]).resolve()),
                str(Path(plan_receipt["execution_plan_path"]).resolve()),
            )

            self.assertNotIn("specialist_dispatch", runtime_input_packet)
            self.assertNotIn("specialist_decision", runtime_input_packet)
            self.assertEqual([], list(runtime_input_packet["agent_skill_organization"]["selected_skills"]))
            self.assertEqual(set(), selected_skill_ids_from_packet(runtime_input_packet))
            self.assertEqual("child", execution_manifest["governance_scope"])
            self.assertFalse(execution_manifest["authority"]["completion_claim_allowed"])
            self.assertNotIn("route_runtime_alignment", execution_manifest)
            self.assertEqual("agent_action_required", module_handoff["status"])
            self.assertEqual("agent", module_handoff["control_owner"])
            self.assertEqual([], module_handoff["assigned_skill_ids"])
            self.assertEqual("agent_execution_handoff_v1", handoff["schema_version"])
            self.assertEqual(module_handoff["status"], handoff["status"])
            self.assertEqual(module_handoff["control_owner"], handoff["control_owner"])
            self.assertEqual(module_handoff["work_units"], handoff["units"])
            self.assertEqual(module_handoff["waves"], handoff["waves"])
            self.assertEqual("module_execution_v1", result_contract["schema_version"])
            self.assertEqual(child_run_id, result_contract["source_run_id"])
            self.assertNotIn("specialist_accounting", execution_manifest)
            self.assertNotIn("specialist_decision", execution_manifest)
            self.assertNotIn("specialist_user_disclosure", execution_manifest)
            self.assertEqual([], handoff["units"])
            self.assertEqual([], handoff["waves"])
            self.assertEqual([], result_contract["units"])
            self.assertEqual(
                ["blocked_gap"],
                [module["execution_mode"] for module in result_contract["modules"]],
            )
            self.assertTrue(result_contract["modules"][0]["gap_reason"])
            self.assertIsNone(child_summary["artifacts"]["module_execution"])
            self.assertFalse(module_execution_path.exists())
            self.assertFalse(child_summary["artifacts"]["cleanup_receipt"])
            self.assertEqual(child_run_id, delegation_validation_receipt["child_run_id"])
            self.assertEqual(str(envelope_path.resolve()), str(Path(delegation_validation_receipt["envelope_path"]).resolve()))
            self.assertTrue(bool(delegation_validation_receipt["write_scope_valid"]))

    def test_child_runtime_rejects_delegation_envelope_for_other_child_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            root_payload = run_governed_runtime(
                "Root child envelope seed for child-run mismatch rejection.",
                artifact_root=artifact_root,
            )
            envelope_path = write_delegation_envelope_fixture(
                artifact_root=artifact_root,
                root_payload=root_payload,
                child_run_id="pytest-child-lane-envelope-" + uuid.uuid4().hex[:10],
            )

            with self.assertRaises(subprocess.CalledProcessError):
                run_child_runtime(
                    task="Child governed runtime should reject envelope for another child run.",
                    root_run_id=str(root_payload["summary"]["run_id"]),
                    inherited_requirement_doc_path=Path(root_payload["summary"]["artifacts"]["requirement_doc"]),
                    inherited_execution_plan_path=Path(root_payload["summary"]["artifacts"]["execution_plan"]),
                    artifact_root=artifact_root,
                    delegation_envelope_path=envelope_path,
                    run_id="pytest-child-lane-runtime-" + uuid.uuid4().hex[:10],
                )


if __name__ == "__main__":
    unittest.main()
