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
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.custom_admission import load_custom_admission  # noqa: E402

ROUTER_BRIDGE = REPO_ROOT / "scripts" / "router" / "invoke-pack-route.py"
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
INVOKE_RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"


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


def normalize_path_text(value: object) -> str:
    return str(value).replace("\\", "/")


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def selected_rows_from_packet(packet: dict[str, object]) -> list[dict[str, object]]:
    module_assignments = packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        return []
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return []
    rows: list[dict[str, object]] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        skill_id = str(unit.get("bound_skill") or "").strip()
        if not skill_id:
            continue
        row = dict(unit)
        row["skill_id"] = skill_id
        rows.append(row)
    return rows


def agent_skill_organization(selected_skill_ids: list[str]) -> dict[str, object]:
    module_id = "custom_admission"
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": module_id,
                "goal": "Exercise custom skill admission through the governed runtime.",
                "candidate_skill_ids": selected_skill_ids,
                "execution_mode": "skill_assigned" if selected_skill_ids else "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "custom-admission-result",
                        "description": "The custom admission outcome is present and verified.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": skill_id,
                "module_ids": [module_id],
                "responsibility": "Own the custom governed workflow.",
                "reason": "The Agent selected this skill after reading its SKILL.md.",
            }
            for skill_id in selected_skill_ids
        ],
        "uncovered_modules": []
        if selected_skill_ids
        else [
            {
                "module_id": module_id,
                "reason": "No standard SKILL.md entrypoint was available for selection.",
            }
        ],
        "workflow_level_contract": {
            "L": "Use one serial governed lane.",
            "XL": "Use bounded waves when the approved organization needs them.",
        },
    }


def run_router(
    *,
    prompt: str,
    target_root: Path,
    requested_skill: str | None = None,
    grade: str = "L",
    task_type: str = "planning",
) -> dict[str, object]:
    command = [
        sys.executable,
        str(ROUTER_BRIDGE),
        "--prompt",
        prompt,
        "--grade",
        grade,
        "--task-type",
        task_type,
        "--force-runtime-neutral",
        "--host-id",
        "codex",
        "--target-root",
        str(target_root),
    ]
    if requested_skill:
        command.extend(["--requested-skill", requested_skill])
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=os.environ.copy(),
    )
    return json.loads(completed.stdout)


def write_custom_skill(
    target_root: Path,
    *,
    skill_id: str,
    entrypoint_filename: str = "SKILL.md",
    trigger_mode: str = "advisory",
    requires: list[str] | None = None,
    keywords: list[str] | None = None,
    intent_tags: list[str] | None = None,
    preferred_stages: list[str] | None = None,
    parallelizable_in_root_xl: bool = True,
) -> None:
    skill_dir = target_root / "skills" / "custom" / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    entrypoint_path = skill_dir / entrypoint_filename
    entrypoint_path.write_text(
        (
            "---\n"
            f"name: {skill_id}\n"
            f"description: Custom {skill_id} workflow for governed specialist execution.\n"
            "---\n"
            f"# {skill_id}\n"
        ),
        encoding="utf-8",
    )

    (target_root / "config").mkdir(parents=True, exist_ok=True)
    (target_root / "config" / "custom-workflows.json").write_text(
        json.dumps(
            {
                "workflows": [
                    {
                        "id": skill_id,
                        "enabled": True,
                        "path": f"skills/custom/{skill_id}/{entrypoint_filename}",
                        "keywords": keywords or ["bioanalysis", "qc", "workflow"],
                        "intent_tags": intent_tags or ["planning", "coding", "research"],
                        "non_goals": ["billing"],
                        "requires": requires or ["vibe"],
                        "trigger_mode": trigger_mode,
                        "preferred_stages": preferred_stages or ["plan_execute"],
                        "parallelizable_in_root_xl": parallelizable_in_root_xl,
                        "priority": 82,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def run_runtime_freeze(
    *,
    task: str,
    target_root: Path,
    selected_skill_ids: list[str],
    artifact_root: Path,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-custom-admission-" + uuid.uuid4().hex[:10]
    host_decision_json = json.dumps(
        {"agent_skill_organization": agent_skill_organization(selected_skill_ids)},
        ensure_ascii=False,
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
            f"$env:VCO_HOST_ID = 'codex'; "
            f"$env:VIBE_AGENTS_HOME = {_ps_single_quote(str(target_root))}; "
            f"$result = & {_ps_single_quote(str(FREEZE_SCRIPT))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(run_id)} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
            f"-HostDecisionJson {_ps_single_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=os.environ.copy(),
    )
    payload = json.loads(completed.stdout)
    if payload is None:
        raise AssertionError(
            "Freeze-RuntimeInputPacket.ps1 returned null. "
            f"stderr was: {completed.stderr.strip()}"
        )
    return payload


def run_full_runtime(
    *,
    task: str,
    target_root: Path,
    selected_skill_ids: list[str],
    artifact_root: Path,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-custom-runtime-" + uuid.uuid4().hex[:10]
    host_decision_json = json.dumps(
        {"agent_skill_organization": agent_skill_organization(selected_skill_ids)},
        ensure_ascii=False,
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
            f"$env:VCO_HOST_ID = 'codex'; "
            f"$env:VIBE_AGENTS_HOME = {_ps_single_quote(str(target_root))}; "
            f"$result = & {_ps_single_quote(str(INVOKE_RUNTIME_SCRIPT))} "
            f"-Task {_ps_single_quote(task)} "
            "-Mode interactive_governed "
            f"-RunId {_ps_single_quote(run_id)} "
            f"-ArtifactRoot {_ps_single_quote(str(artifact_root))} "
            f"-HostDecisionJson {_ps_single_quote(host_decision_json)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=os.environ.copy(),
    )
    payload = json.loads(completed.stdout)
    if payload is None:
        raise AssertionError(
            "invoke-vibe-runtime.ps1 returned null. "
            f"stderr was: {completed.stderr.strip()}"
        )
    return payload


class CustomAdmissionBridgeTests(unittest.TestCase):
    def test_custom_admission_internal_metadata_uses_route_usable_not_old_role_field(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            write_custom_skill(target_root, skill_id="genomics-qc-flow", trigger_mode="auto")

            admission = load_custom_admission(
                repo_root=REPO_ROOT,
                target_root=target_root,
                requested_canonical=None,
            )

            self.assertEqual("admitted", admission["status"])
            admitted = admission["admitted_candidates"][0]
            self.assertIn("_route_usable", admitted)
            self.assertTrue(bool(admitted["_route_usable"]))
            self.assertNotIn("route_authority_eligible", admitted)
            self.assertEqual(admitted["_route_usable"], admitted["pack"]["custom_admission"]["_route_usable"])
            self.assertNotIn("route_authority_eligible", admitted["pack"]["custom_admission"])

    def test_runtime_neutral_router_keeps_custom_admission_disabled_while_local_index_can_select_custom_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            write_custom_skill(target_root, skill_id="genomics-qc-flow", trigger_mode="advisory")

            result = run_router(
                prompt="Need bioanalysis qc workflow and governed planning for genomics deliverables.",
                target_root=target_root,
                requested_skill="vibe",
                grade="L",
                task_type="planning",
            )

            self.assertEqual("disabled_default_local_index_only", result["custom_admission"]["status"])
            self.assertEqual([], result["custom_admission"]["admitted_candidates"])

            custom_ranked = next((row for row in result["ranked"] if row["skill"] == "genomics-qc-flow"), None)
            self.assertIsNotNone(custom_ranked)
            self.assertNotIn("route_authority_eligible", custom_ranked)
            self.assertEqual("genomics-qc-flow", result["candidate_focus"]["skill"])
            self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
            self.assertEqual("local_skill_index", result["candidate_focus"]["candidate_source"])

    def test_runtime_neutral_router_explicit_request_can_activate_custom_route_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            write_custom_skill(target_root, skill_id="genomics-qc-flow", trigger_mode="explicit_only")

            result = run_router(
                prompt="Use the explicit custom genomics qc workflow for this governed task.",
                target_root=target_root,
                requested_skill="genomics-qc-flow",
                grade="L",
                task_type="planning",
            )

            self.assertEqual("disabled_default_local_index_only", result["custom_admission"]["status"])
            self.assertEqual("genomics-qc-flow", result["candidate_focus"]["skill"])
            self.assertEqual("local-skill-index", result["candidate_focus"]["pack_id"])
            self.assertEqual("explicit_local_skill", result["route_reason"])

    def test_runtime_neutral_router_reports_missing_custom_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            write_custom_skill(
                target_root,
                skill_id="broken-custom-flow",
                trigger_mode="advisory",
                requires=["missing-dependency-skill"],
            )

            result = run_router(
                prompt="Need broken custom flow keywords for admission diagnostics.",
                target_root=target_root,
                grade="L",
                task_type="planning",
            )

            self.assertEqual("disabled_default_local_index_only", result["custom_admission"]["status"])
            self.assertEqual([], result["custom_admission"]["admitted_candidates"])
            self.assertEqual([], result["custom_admission"]["dependency_failures"])

    def test_runtime_freeze_exports_custom_specialist_dispatch_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            artifact_root = Path(tempdir) / "artifacts"
            write_custom_skill(
                target_root,
                skill_id="genomics-qc-flow",
                trigger_mode="advisory",
                preferred_stages=["plan_execute"],
                parallelizable_in_root_xl=True,
            )

            payload = run_runtime_freeze(
                task="Need bioanalysis qc workflow and governed planning for genomics deliverables.",
                target_root=target_root,
                selected_skill_ids=["genomics-qc-flow"],
                artifact_root=artifact_root,
            )
            packet = payload["packet"]

            self.assertEqual("disabled_default_local_index_only", packet["custom_admission"]["status"])
            self.assertEqual(normalize_path_text(str(target_root.resolve())), normalize_path_text(packet["custom_admission"]["target_root"]))
            self.assertTrue((target_root / "vibe").exists())
            self.assertFalse((target_root / "skills" / "vibe").exists())

            custom_recommendation = next(
                item for item in selected_rows_from_packet(packet) if item["skill_id"] == "genomics-qc-flow"
            )
            self.assertEqual("default", custom_recommendation["binding_profile"])
            self.assertEqual("in_execution", custom_recommendation["dispatch_phase"])
            self.assertEqual("inherit_grade", custom_recommendation["lane_policy"])
            self.assertTrue(bool(custom_recommendation["parallelizable_in_root_xl"]))
            self.assertNotIn("native_usage_required", custom_recommendation)
            self.assertNotIn("usage_required", custom_recommendation)
            self.assertTrue(bool(custom_recommendation["must_preserve_workflow"]))
            self.assertTrue(
                normalize_path_text(custom_recommendation["skill_entrypoint"]).endswith(
                    "skills/custom/genomics-qc-flow/SKILL.md"
                )
            )

            self.assertNotIn("legacy_skill_routing", packet)
            self.assertIn("genomics-qc-flow", [item["skill_id"] for item in selected_rows_from_packet(packet)])

    def test_runtime_freeze_ignores_non_standard_runtime_mirror_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            artifact_root = Path(tempdir) / "artifacts"
            write_custom_skill(
                target_root,
                skill_id="genomics-qc-flow",
                entrypoint_filename="SKILL.runtime-mirror.md",
                trigger_mode="advisory",
                preferred_stages=["plan_execute"],
            )

            payload = run_runtime_freeze(
                task="Need bioanalysis qc workflow and governed planning for genomics deliverables.",
                target_root=target_root,
                selected_skill_ids=[],
                artifact_root=artifact_root,
            )
            packet = payload["packet"]
            self.assertEqual("disabled_default_local_index_only", packet["custom_admission"]["status"])
            self.assertNotIn("genomics-qc-flow", [item["skill_id"] for item in selected_rows_from_packet(packet)])

    def test_full_runtime_carries_custom_specialist_into_execution_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            target_root = Path(tempdir) / ".codex"
            artifact_root = Path(tempdir) / "artifacts"
            write_custom_skill(
                target_root,
                skill_id="genomics-qc-flow",
                trigger_mode="advisory",
                preferred_stages=["plan_execute"],
                parallelizable_in_root_xl=True,
            )

            payload = run_full_runtime(
                task="Need bioanalysis qc workflow and governed planning for genomics deliverables.",
                target_root=target_root,
                selected_skill_ids=["genomics-qc-flow"],
                artifact_root=artifact_root,
            )
            summary = payload["summary"]
            execution_manifest = json.loads(Path(summary["artifacts"]["execution_manifest"]).read_text(encoding="utf-8"))

            self.assertEqual("agent_action_required", execution_manifest["module_handoff"]["status"])
            self.assertIn("genomics-qc-flow", execution_manifest["module_handoff"]["assigned_skill_ids"])
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["planned_units_fully_handed_off"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["handed_off_skills_match_plan"]))
            self.assertNotIn("approved_dispatch_fully_handed_off", execution_manifest["dispatch_integrity"])
            self.assertNotIn(
                "prompt_injection_complete_for_executed_specialists",
                execution_manifest["dispatch_integrity"],
            )
            self.assertNotIn(
                "prompt_injection_incomplete_skill_ids",
                execution_manifest["dispatch_integrity"],
            )
            self.assertIn(
                "genomics-qc-flow",
                [str(skill_id) for skill_id in execution_manifest["dispatch_integrity"]["handed_off_skill_ids"]],
            )


if __name__ == "__main__":
    unittest.main()
