from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
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
    approved_specialist_skill_ids: list[str] | None = None,
    artifact_root: Path,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-custom-admission-" + uuid.uuid4().hex[:10]
    approved = approved_specialist_skill_ids or []
    approved_literal = (
        "@(" + ",".join("'" + skill.replace("'", "''") + "'" for skill in approved) + ")"
        if approved
        else "@()"
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$env:VCO_HOST_ID = 'codex'; "
            f"$env:CODEX_HOME = '{target_root}'; "
            f"$result = & '{FREEZE_SCRIPT}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ApprovedSpecialistSkillIds {approved_literal} "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def run_full_runtime(
    *,
    task: str,
    target_root: Path,
    approved_specialist_skill_ids: list[str] | None = None,
    artifact_root: Path,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-custom-runtime-" + uuid.uuid4().hex[:10]
    approved = approved_specialist_skill_ids or []
    approved_literal = (
        "@(" + ",".join("'" + skill.replace("'", "''") + "'" for skill in approved) + ")"
        if approved
        else "@()"
    )
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$env:VCO_HOST_ID = 'codex'; "
            f"$env:CODEX_HOME = '{target_root}'; "
            f"$result = & '{INVOKE_RUNTIME_SCRIPT}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ApprovedSpecialistSkillIds {approved_literal} "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


class CustomAdmissionBridgeTests(unittest.TestCase):
    def test_runtime_neutral_router_admits_advisory_custom_candidate_without_route_authority(self) -> None:
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

            self.assertEqual("admitted", result["custom_admission"]["status"])
            self.assertIn(
                "genomics-qc-flow",
                [row["skill_id"] for row in result["custom_admission"]["admitted_candidates"]],
            )

            custom_ranked = next(
                (row for row in result["ranked"] if row["pack_id"] == "custom-workflow-genomics-qc-flow"),
                None,
            )
            self.assertIsNotNone(custom_ranked)
            self.assertFalse(bool(custom_ranked["route_authority_eligible"]))
            self.assertNotEqual("genomics-qc-flow", result["selected"]["skill"])

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

            self.assertEqual("admitted", result["custom_admission"]["status"])
            self.assertEqual("genomics-qc-flow", result["selected"]["skill"])
            self.assertEqual("custom-workflow-genomics-qc-flow", result["selected"]["pack_id"])

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

            self.assertEqual("custom_dependencies_missing", result["custom_admission"]["status"])
            self.assertEqual([], result["custom_admission"]["admitted_candidates"])
            self.assertEqual(1, len(result["custom_admission"]["dependency_failures"]))
            self.assertEqual(
                ["missing-dependency-skill"],
                result["custom_admission"]["dependency_failures"][0]["missing_dependencies"],
            )

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
                approved_specialist_skill_ids=["genomics-qc-flow"],
                artifact_root=artifact_root,
            )
            packet = payload["packet"]

            self.assertEqual("admitted", packet["custom_admission"]["status"])
            self.assertIn("genomics-qc-flow", packet["custom_admission"]["admitted_skill_ids"])

            custom_recommendation = next(
                item for item in packet["specialist_recommendations"] if item["skill_id"] == "genomics-qc-flow"
            )
            self.assertEqual("workflow", custom_recommendation["binding_profile"])
            self.assertEqual("in_execution", custom_recommendation["dispatch_phase"])
            self.assertEqual("bounded_native_custom_skill", custom_recommendation["lane_policy"])
            self.assertTrue(bool(custom_recommendation["parallelizable_in_root_xl"]))
            self.assertTrue(bool(custom_recommendation["native_usage_required"]))
            self.assertTrue(bool(custom_recommendation["must_preserve_workflow"]))
            self.assertTrue(str(custom_recommendation["native_skill_entrypoint"]).endswith("skills/custom/genomics-qc-flow/SKILL.md"))

            approved_dispatch = packet["specialist_dispatch"]["approved_dispatch"]
            self.assertIn("genomics-qc-flow", [item["skill_id"] for item in approved_dispatch])

    def test_runtime_freeze_uses_resolved_runtime_mirror_entrypoint_in_progressive_load_policy(self) -> None:
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
                approved_specialist_skill_ids=["genomics-qc-flow"],
                artifact_root=artifact_root,
            )
            packet = payload["packet"]
            custom_recommendation = next(
                item for item in packet["specialist_recommendations"] if item["skill_id"] == "genomics-qc-flow"
            )

            self.assertTrue(
                str(custom_recommendation["native_skill_entrypoint"]).endswith("SKILL.runtime-mirror.md")
            )
            self.assertEqual(
                f"Open the specialist {custom_recommendation['native_skill_entrypoint']} entrypoint first.",
                list(custom_recommendation["progressive_load_policy"])[0],
            )

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
                approved_specialist_skill_ids=["genomics-qc-flow"],
                artifact_root=artifact_root,
            )
            summary = payload["summary"]
            execution_manifest = json.loads(Path(summary["artifacts"]["execution_manifest"]).read_text(encoding="utf-8"))

            self.assertGreaterEqual(int(execution_manifest["specialist_accounting"]["recommendation_count"]), 1)
            self.assertGreaterEqual(int(execution_manifest["specialist_accounting"]["dispatch_unit_count"]), 1)
            self.assertIn(
                "genomics-qc-flow",
                [str(skill_id) for skill_id in execution_manifest["specialist_accounting"]["specialist_skills"]],
            )
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["approved_dispatch_fully_executed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["prompt_injection_complete_for_executed_specialists"]))
            self.assertEqual([], list(execution_manifest["dispatch_integrity"]["prompt_injection_incomplete_skill_ids"]))
            self.assertIn(
                "genomics-qc-flow",
                [str(skill_id) for skill_id in execution_manifest["dispatch_integrity"]["executed_specialist_skill_ids"]],
            )


if __name__ == "__main__":
    unittest.main()
