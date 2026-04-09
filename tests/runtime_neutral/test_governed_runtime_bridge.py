from __future__ import annotations

import json
import os
import stat
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STAGE_IDS = [
    "skeleton_check",
    "deep_interview",
    "requirement_doc",
    "xl_plan",
    "plan_execute",
    "phase_cleanup",
]


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


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _create_fake_command(directory: Path, name: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"{name}{suffix}"
    if os.name == "nt":
        command_path.write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
    else:
        command_path.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


SPECIALIST_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."


def resolve_python_command_spec_via_powershell(command_spec: str, path_entries: list[Path]) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    helper = REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1"
    scoped_path = os.pathsep.join(str(entry) for entry in path_entries)
    ps_script_parts = [f"$env:PATH = {_ps_single_quote(scoped_path)}; "]
    if os.name == "nt":
        ps_script_parts.append("$env:PATHEXT = '.CMD;.EXE;.BAT;.PS1'; ")
    ps_script_parts.extend(
        [
            f". {_ps_single_quote(str(helper))}; ",
            f"$result = Resolve-VgoPythonCommandSpec -Command {_ps_single_quote(command_spec)}; ",
            "$result | ConvertTo-Json -Depth 5",
        ]
    )
    ps_script = "".join(ps_script_parts)
    completed = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


class GovernedRuntimeBridgeTests(unittest.TestCase):
    def test_version_governance_bridges_governed_runtime_surfaces(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        packaging = governance["packaging"]["runtime_payload"]
        runtime = governance["runtime"]["installed_runtime"]
        contract = json.loads((REPO_ROOT / "config" / "runtime-contract.json").read_text(encoding="utf-8"))

        self.assertIn("templates", packaging["directories"])
        self.assertIn("mcp", packaging["directories"])
        self.assertNotIn("scripts", packaging["directories"])
        self.assertNotIn("config", packaging["directories"])
        self.assertIn("config/runtime-script-manifest.json", packaging["files"])
        self.assertIn("config/runtime-config-manifest.json", packaging["files"])
        self.assertNotIn("docs", packaging["directories"])
        self.assertNotIn("references", packaging["directories"])
        self.assertNotIn("protocols", packaging["directories"])

        required_markers = set(runtime["required_runtime_markers"])
        self.assertIn("config/runtime-script-manifest.json", required_markers)
        self.assertIn("config/runtime-config-manifest.json", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/__init__.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/main.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/errors.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/hosts.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/process.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/install_support.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/workspace.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/commands.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/repo.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/version_reminder.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/external.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/output.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/install_gates.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/installer_bridge.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/skill_surface.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/core_bridge.py", required_markers)
        self.assertIn("packages/contracts/src/vgo_contracts/__init__.py", required_markers)
        self.assertIn("packages/contracts/src/vgo_contracts/install_ledger.py", required_markers)
        self.assertIn("packages/installer-core/src/vgo_installer/__init__.py", required_markers)
        self.assertIn("packages/installer-core/src/vgo_installer/install_runtime.py", required_markers)
        self.assertIn("packages/installer-core/src/vgo_installer/uninstall_runtime.py", required_markers)
        self.assertIn("packages/installer-core/src/vgo_installer/ledger_service.py", required_markers)
        self.assertIn("packages/runtime-core/src/vgo_runtime/router_bridge.py", required_markers)
        self.assertIn("packages/runtime-core/src/vgo_runtime/router_contract_runtime.py", required_markers)
        self.assertIn("packages/runtime-core/src/vgo_runtime/custom_admission.py", required_markers)
        self.assertIn("scripts/runtime/VibeRuntime.Common.ps1", required_markers)
        self.assertIn("scripts/runtime/VibeExecution.Common.ps1", required_markers)
        self.assertIn("scripts/runtime/VibeMemoryActivation.Common.ps1", required_markers)
        self.assertIn("scripts/runtime/Freeze-RuntimeInputPacket.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-SkeletonCheck.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-DeepInterview.ps1", required_markers)
        self.assertIn("scripts/runtime/Write-RequirementDoc.ps1", required_markers)
        self.assertIn("scripts/runtime/Write-XlPlan.ps1", required_markers)
        self.assertIn("scripts/runtime/invoke-vibe-runtime.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-DelegatedLaneUnit.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-PlanExecute.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-PhaseCleanup.ps1", required_markers)
        self.assertIn("scripts/verify/vibe-governed-runtime-contract-gate.ps1", required_markers)
        self.assertIn("config/runtime-contract.json", required_markers)
        self.assertIn("config/runtime-modes.json", required_markers)
        self.assertIn("config/runtime-input-packet-policy.json", required_markers)
        self.assertIn("config/proof-class-registry.json", required_markers)
        self.assertIn("config/requirement-doc-policy.json", required_markers)
        self.assertIn("config/plan-execution-policy.json", required_markers)
        self.assertIn("config/phase-cleanup-policy.json", required_markers)

        execution_policy = json.loads(
            (REPO_ROOT / "config" / "execution-runtime-policy.json").read_text(encoding="utf-8")
        )
        first_unit = execution_policy["profiles"][0]["waves"][0]["units"][0]
        self.assertEqual("python_command", first_unit["kind"])
        self.assertEqual("${VGO_PYTHON}", first_unit["command"])

        linux_no_pwsh_gate = (REPO_ROOT / "scripts" / "verify" / "vibe-linux-router-no-pwsh-gate.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("Get-VgoPythonCommand", linux_no_pwsh_gate)
        self.assertNotIn("& python @args", linux_no_pwsh_gate)

        self.assertEqual(
            EXPECTED_STAGE_IDS,
            [stage["id"] for stage in contract["stages"]],
        )

        runtime_entry = (REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1").read_text(encoding="utf-8")
        runtime_common = (REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1").read_text(encoding="utf-8")
        self.assertIn("Get-VibeUpgradeReminder", runtime_common)
        self.assertIn("Get-VibeUpgradeReminder", runtime_entry)

    def test_invoke_vibe_runtime_produces_six_stage_closure_under_temp_artifact_root(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                (
                    "& { "
                    f"$result = & '{script_path}' "
                    f"-Task '{SPECIALIST_TASK}' "
                    "-Mode interactive_governed "
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
                check=True,
            )

            payload = json.loads(completed.stdout)
            summary_path = Path(payload["summary_path"])
            session_root = Path(payload["session_root"])
            repo_root_text = str(REPO_ROOT.resolve()).lower()

            self.assertEqual(session_root / "runtime-summary.json", summary_path)
            self.assertFalse(str(session_root).lower().startswith(repo_root_text))
            self.assertFalse(str(summary_path).lower().startswith(repo_root_text))
            self.assertEqual(run_id, session_root.name)
            self.assertEqual("vibe-sessions", session_root.parent.name)
            self.assertEqual("runtime", session_root.parent.parent.name)
            self.assertEqual("outputs", session_root.parent.parent.parent.name)

            summary = payload["summary"]
            summary_path_relative = summary.get("session_root_relative")
            if summary_path.exists():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            elif summary_path_relative:
                reconstructed_summary_path = artifact_root / summary_path_relative / "runtime-summary.json"
                if reconstructed_summary_path.exists():
                    summary = json.loads(reconstructed_summary_path.read_text(encoding="utf-8"))
            self.assertEqual("interactive_governed", summary["mode"])
            self.assertEqual(
                EXPECTED_STAGE_IDS,
                summary["stage_order"],
            )

            artifacts = summary["artifacts"]
            relative_artifacts = summary.get("artifacts_relative", {})

            def resolve_artifact_path(key: str) -> Path:
                relative = relative_artifacts.get(key)
                if relative:
                    return artifact_root / Path(relative)
                return Path(artifacts[key])

            for key in (
                "skeleton_receipt",
                "runtime_input_packet",
                "governance_capsule",
                "stage_lineage",
                "intent_contract",
                "requirement_doc",
                "requirement_receipt",
                "execution_plan",
                "execution_plan_receipt",
                "execute_receipt",
                "execution_manifest",
                "execution_proof_manifest",
                "cleanup_receipt",
            ):
                self.assertFalse(str(Path(artifacts[key])).lower().startswith(repo_root_text), key)
                if key in relative_artifacts:
                    self.assertFalse(Path(relative_artifacts[key]).is_absolute(), key)
                    if os.name != "nt":
                        self.assertNotIn("\\", relative_artifacts[key], key)

            requirement_doc_path = resolve_artifact_path("requirement_doc")
            execution_plan_path = resolve_artifact_path("execution_plan")
            execute_receipt_path = resolve_artifact_path("execute_receipt")
            execution_manifest_path = resolve_artifact_path("execution_manifest")
            execution_proof_path = resolve_artifact_path("execution_proof_manifest")
            runtime_input_packet_path = resolve_artifact_path("runtime_input_packet")
            governance_capsule_path = resolve_artifact_path("governance_capsule")
            stage_lineage_path = resolve_artifact_path("stage_lineage")

            if requirement_doc_path.exists():
                requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
                self.assertIn("## Acceptance Criteria", requirement_doc)
                self.assertIn("## Assumptions", requirement_doc)
                self.assertIn("## Runtime Input Truth", requirement_doc)
                self.assertIn("## Specialist Recommendations", requirement_doc)
            self.assertEqual("requirements", requirement_doc_path.parent.name)
            self.assertEqual("plans", execution_plan_path.parent.name)
            execution_plan = execution_plan_path.read_text(encoding="utf-8")
            self.assertIn("## Specialist Skill Dispatch Plan", execution_plan)

            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))
            governance_capsule = json.loads(governance_capsule_path.read_text(encoding="utf-8"))
            stage_lineage = json.loads(stage_lineage_path.read_text(encoding="utf-8"))
            execute_receipt = json.loads(execute_receipt_path.read_text(encoding="utf-8"))
            execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
            execution_proof = json.loads(execution_proof_path.read_text(encoding="utf-8"))

            self.assertEqual("vibe", governance_capsule["runtime_selected_skill"])
            self.assertEqual(summary["run_id"], governance_capsule["run_id"])
            self.assertEqual(EXPECTED_STAGE_IDS, [item["stage_name"] for item in stage_lineage["stages"]])
            self.assertEqual("runtime_input_freeze", runtime_input_packet["stage"])
            self.assertEqual("interactive_governed", runtime_input_packet["runtime_mode"])
            self.assertFalse(runtime_input_packet["canonical_router"]["unattended"])
            self.assertEqual("structure", runtime_input_packet["provenance"]["proof_class"])
            self.assertEqual("vibe", runtime_input_packet["authority_flags"]["explicit_runtime_skill"])
            self.assertEqual("vibe", runtime_input_packet["route_snapshot"]["selected_skill"])
            self.assertFalse(runtime_input_packet["divergence_shadow"]["skill_mismatch"])
            self.assertGreaterEqual(len(runtime_input_packet["specialist_recommendations"]), 1)
            self.assertIn(
                "systematic-debugging",
                [item["skill_id"] for item in runtime_input_packet["specialist_recommendations"]],
            )
            self.assertNotEqual("execution-contract-prepared", execute_receipt["status"])
            self.assertGreaterEqual(execute_receipt["executed_unit_count"], 2)
            self.assertTrue(Path(execute_receipt["plan_shadow_path"]).exists())
            self.assertEqual("runtime", execute_receipt["proof_class"])
            self.assertGreaterEqual(execute_receipt["specialist_recommendation_count"], 1)
            self.assertGreaterEqual(execute_receipt["specialist_dispatch_unit_count"], 1)
            self.assertIn("systematic-debugging", execute_receipt["specialist_skills"])
            self.assertEqual(execute_receipt["executed_unit_count"], execution_manifest["executed_unit_count"])
            self.assertEqual("completed", execution_manifest["status"])
            self.assertGreaterEqual(execution_manifest["successful_unit_count"], 2)
            self.assertEqual(0, execution_manifest["failed_unit_count"])
            self.assertEqual("runtime", execution_manifest["proof_class"])
            self.assertTrue(Path(execution_manifest["plan_shadow"]["path"]).exists())
            self.assertEqual("vibe", execution_manifest["route_runtime_alignment"]["router_selected_skill"])
            self.assertEqual("vibe", execution_manifest["route_runtime_alignment"]["runtime_selected_skill"])
            self.assertFalse(execution_manifest["route_runtime_alignment"]["skill_mismatch"])
            self.assertGreaterEqual(execution_manifest["specialist_accounting"]["recommendation_count"], 1)
            self.assertGreaterEqual(execution_manifest["specialist_accounting"]["dispatch_unit_count"], 1)
            self.assertIn("systematic-debugging", execution_manifest["specialist_accounting"]["specialist_skills"])
            self.assertGreaterEqual(execution_manifest["plan_shadow"]["specialist_dispatch_unit_count"], 1)
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["approved_dispatch_fully_executed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["executed_specialists_subset_of_approved_dispatch"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["local_suggestions_contained"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["prompt_injection_complete_for_executed_specialists"]))
            self.assertEqual([], list(execution_manifest["dispatch_integrity"]["prompt_injection_incomplete_skill_ids"]))
            self.assertTrue(execution_proof["proof_passed"])
            self.assertGreaterEqual(execution_proof["executed_unit_count"], 2)
            self.assertEqual("runtime", execution_proof["proof_class"])
            self.assertTrue(Path(execution_proof["plan_shadow_path"]).exists())
            self.assertGreaterEqual(execution_proof["specialist_recommendation_count"], 1)
            self.assertGreaterEqual(execution_proof["specialist_dispatch_unit_count"], 1)
            self.assertTrue(bool(execution_proof["dispatch_integrity_proof_passed"]))

            cleanup_receipt = json.loads(resolve_artifact_path("cleanup_receipt").read_text(encoding="utf-8"))
            self.assertEqual("receipt_only", cleanup_receipt["cleanup_mode"])
            self.assertEqual("runtime", cleanup_receipt["proof_class"])
            self.assertFalse(cleanup_receipt["default_bounded_cleanup_applied"])

            for result_path in execution_proof["result_paths"]:
                result = json.loads(Path(result_path).read_text(encoding="utf-8"))
                self.assertEqual(0, result["exit_code"])
                self.assertTrue(Path(result["stdout_path"]).exists())
                self.assertTrue(Path(result["stderr_path"]).exists())
                if result.get("kind") == "specialist_dispatch" and bool(result.get("degraded")):
                    self.assertEqual("degraded_non_authoritative", result["status"])
                    self.assertFalse(bool(result["verification_passed"]))
                else:
                    self.assertEqual("completed", result["status"])

    def test_resolve_vgo_python_command_spec_falls_back_to_python3(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            fake_dir = Path(tempdir)
            _create_fake_command(fake_dir, "python3")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [fake_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("python3"))
            self.assertEqual([], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_uses_py_launcher_with_dash3_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            fake_dir = Path(tempdir)
            _create_fake_command(fake_dir, "py")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [fake_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("py"))
            self.assertEqual(["-3"], resolved["prefix_arguments"])


if __name__ == "__main__":
    unittest.main()
