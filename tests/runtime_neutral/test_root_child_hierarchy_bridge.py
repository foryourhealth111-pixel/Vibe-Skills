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

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-root-child-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            "-GovernanceScope root "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
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
        env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
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
    approved_specialist_skill_ids: list[str] | None = None,
    delegation_envelope_path: Path | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    effective_run_id = run_id or ("pytest-child-lane-" + uuid.uuid4().hex[:10])
    approved = approved_specialist_skill_ids or []
    approved_literal = (
        "@(" + ",".join("'" + skill.replace("'", "''") + "'" for skill in approved) + ")"
        if approved
        else "@()"
    )
    delegation_literal = (
        f"-DelegationEnvelopePath '{delegation_envelope_path}' "
        if delegation_envelope_path is not None
        else ""
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            "-GovernanceScope child "
            f"-RunId '{effective_run_id}' "
            f"-RootRunId '{root_run_id}' "
            f"-ParentRunId '{root_run_id}' "
            "-ParentUnitId 'pytest-child-unit' "
            f"-InheritedRequirementDocPath '{inherited_requirement_doc_path}' "
            f"-InheritedExecutionPlanPath '{inherited_execution_plan_path}' "
            f"-ApprovedSpecialistSkillIds {approved_literal} "
            f"{delegation_literal}"
            f"-ArtifactRoot '{artifact_root}'; "
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
        env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
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
    approved_specialists: list[str] | None = None,
) -> Path:
    approved = approved_specialists or []
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
        "approved_specialists": approved,
        "review_mode": "native_contract",
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
        self.assertIn("A child lane may detect that more specialist help is useful", stable_text)

    def test_runtime_input_policy_declares_hierarchy_fields(self) -> None:
        policy_path = REPO_ROOT / "config" / "runtime-input-packet-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy_text = json.dumps(policy, ensure_ascii=False, sort_keys=True)

        expected_tokens = [
            "governance_scope",
            "hierarchy_contract",
            "child_specialist_suggestion_contract",
            "required_specialist_recommendation_count",
            "fallback_specialists_by_task_type",
            "allow_requirement_freeze",
            "allow_plan_freeze",
            "allow_global_dispatch",
            "allow_completion_claim",
            "specialist_dispatch",
            "auto_promote_when_safe_same_round",
            "escalation_required",
        ]
        for token in expected_tokens:
            with self.subTest(token=token):
                self.assertIn(token, policy_text)

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

            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))
            execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))

            self.assertEqual("vibe", runtime_input_packet["route_snapshot"]["selected_skill"])
            self.assertEqual("vibe", runtime_input_packet["authority_flags"]["explicit_runtime_skill"])
            self.assertEqual("root", runtime_input_packet["governance_scope"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_requirement_freeze"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_plan_freeze"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_global_dispatch"])
            self.assertTrue(runtime_input_packet["authority_flags"]["allow_completion_claim"])

            self.assertEqual("requirements", requirement_doc_path.parent.name)
            self.assertEqual("plans", execution_plan_path.parent.name)
            self.assertEqual("root", execution_manifest["governance_scope"])
            self.assertTrue(execution_manifest["authority"]["completion_claim_allowed"])
            self.assertEqual("vibe", execution_manifest["route_runtime_alignment"]["runtime_selected_skill"])
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))

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

    def test_child_specialist_policy_prefers_same_round_auto_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            root_payload = run_governed_runtime(
                "Root specialist dispatch seed for child escalation checks.",
                artifact_root=artifact_root,
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input_packet = json.loads(
                Path(root_artifacts["runtime_input_packet"]).read_text(encoding="utf-8")
            )

            root_approved_dispatch = list(
                (root_runtime_input_packet.get("specialist_dispatch") or {}).get("approved_dispatch") or []
            )
            approved_skill_ids: list[str] = []
            if root_approved_dispatch:
                first_skill_id = str(root_approved_dispatch[0].get("skill_id", "")).strip()
                if first_skill_id:
                    approved_skill_ids = [first_skill_id]

            child_run_id = "pytest-child-lane-" + uuid.uuid4().hex[:10]
            envelope_path = write_delegation_envelope_fixture(
                artifact_root=artifact_root,
                root_payload=root_payload,
                child_run_id=child_run_id,
                approved_specialists=approved_skill_ids,
            )

            child_payload = run_child_runtime(
                task="Child specialist escalation advisory smoke.",
                root_run_id=str(root_summary["run_id"]),
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                artifact_root=artifact_root,
                approved_specialist_skill_ids=approved_skill_ids,
                delegation_envelope_path=envelope_path,
                run_id=child_run_id,
            )
            child_summary = child_payload["summary"]
            runtime_input_packet = json.loads(Path(child_summary["artifacts"]["runtime_input_packet"]).read_text(encoding="utf-8"))
            execution_manifest = json.loads(Path(child_summary["artifacts"]["execution_manifest"]).read_text(encoding="utf-8"))
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

            specialist_dispatch = runtime_input_packet["specialist_dispatch"]
            local_suggestions = list(specialist_dispatch.get("local_specialist_suggestions") or [])
            approved_dispatch = list(specialist_dispatch.get("approved_dispatch") or [])
            approved_ids = {str(entry.get("skill_id", "")) for entry in approved_dispatch}

            if local_suggestions:
                self.assertTrue(bool(specialist_dispatch.get("escalation_required", False)))
                self.assertEqual("root_approval_required", str(specialist_dispatch.get("escalation_status", "")))
                for suggestion in local_suggestions:
                    with self.subTest(suggestion=str(suggestion.get("skill_id", ""))):
                        self.assertNotIn(str(suggestion.get("skill_id", "")), approved_ids)

            self.assertEqual("auto_promote_when_safe_same_round", str(specialist_dispatch.get("status", "")))
            self.assertEqual("child", execution_manifest["governance_scope"])
            self.assertFalse(execution_manifest["authority"]["completion_claim_allowed"])
            self.assertEqual("vibe", execution_manifest["route_runtime_alignment"]["runtime_selected_skill"])
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["local_suggestions_contained"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["executed_specialists_subset_of_approved_dispatch"]))
            if local_suggestions:
                self.assertIn(
                    str(execution_manifest["specialist_accounting"]["auto_absorb_gate"]["status"]),
                    {"auto_approved_same_round", "partially_auto_approved_same_round"},
                )
            self.assertEqual(child_run_id, delegation_validation_receipt["child_run_id"])
            self.assertEqual(str(envelope_path.resolve()), str(Path(delegation_validation_receipt["envelope_path"]).resolve()))
            self.assertTrue(bool(delegation_validation_receipt["write_scope_valid"]))
            self.assertTrue(bool(delegation_validation_receipt["specialist_approval_valid"]))

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
