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
UI_TASK = "Build a responsive dashboard UI with clear interaction feedback, meaningful states, and desktop/mobile layout coverage."
DOC_TASK = "Reformat the project README headings and spacing without changing application code."
DOC_CODE_TASK = "Implement the markdown export pipeline for the docs renderer and add targeted verification for the parser."
DOC_DECK_TASK = "Build the release deck slides and refine presentation spacing without changing application code."
RESEARCH_EXECUTION_TASK = (
    "execute governed-plan facial-recognition dataset-download literature-review "
    "few-shot-modeling baseline-training algorithm-enhancement experiment-run gpu-aware latex-paper"
)


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
        encoding="utf-8",
        errors="replace",
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
        self.assertIn("docs", packaging["directories"])
        self.assertNotIn("references", packaging["directories"])
        self.assertIn("protocols", packaging["directories"])
        self.assertIn("core/skill-contracts/v1/vibe.json", packaging["files"])

        script_manifest = json.loads(
            (REPO_ROOT / "config" / "runtime-script-manifest.json").read_text(encoding="utf-8")
        )
        verification_gates = set(script_manifest["role_groups"]["files"]["verification_gates"])
        self.assertTrue(
            {
                "scripts/verify/vibe-canonical-entry-truth-gate.ps1",
                "scripts/verify/vibe-bootstrap-doctor-gate.ps1",
                "scripts/verify/vibe-no-silent-fallback-contract-gate.ps1",
                "scripts/verify/vibe-no-self-introduced-fallback-gate.ps1",
                "scripts/verify/vibe-release-truth-consistency-gate.ps1",
            }.issubset(verification_gates)
        )

        config_manifest = json.loads(
            (REPO_ROOT / "config" / "runtime-config-manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn("config/operator-preview-contract.json", set(config_manifest["files"]))
        self.assertIn("config/secrets-policy.json", set(config_manifest["files"]))
        self.assertIn("config/tool-registry.json", set(config_manifest["files"]))
        self.assertIn("config/vibe-entry-surfaces.json", set(config_manifest["files"]))
        self.assertIn(
            "config/operator-preview-contract.json",
            set(config_manifest["role_groups"]["files"]["runtime_governance_files"]),
        )
        self.assertIn(
            "config/secrets-policy.json",
            set(config_manifest["role_groups"]["files"]["runtime_governance_files"]),
        )
        self.assertIn(
            "config/tool-registry.json",
            set(config_manifest["role_groups"]["files"]["runtime_governance_files"]),
        )
        self.assertIn(
            "config/vibe-entry-surfaces.json",
            set(config_manifest["role_groups"]["files"]["runtime_governance_files"]),
        )

        required_markers = set(runtime["required_runtime_markers"])
        self.assertIn("config/plugins-manifest.codex.json", required_markers)
        self.assertIn("config/runtime-script-manifest.json", required_markers)
        self.assertIn("config/runtime-config-manifest.json", required_markers)
        self.assertIn("config/secrets-policy.json", required_markers)
        self.assertIn("config/tool-registry.json", required_markers)
        self.assertIn("config/vibe-entry-surfaces.json", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/__init__.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/main.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/errors.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/hosts.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/process.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/install_support.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/workspace.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/commands.py", required_markers)
        self.assertIn("apps/vgo-cli/src/vgo_cli/repo.py", required_markers)
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
        self.assertIn("scripts/runtime/Invoke-VibeCanonicalEntry.ps1", required_markers)
        self.assertIn("scripts/runtime/invoke-vibe-runtime.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-AntiProxyGoalDriftCompaction.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-DelegatedLaneUnit.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-PlanExecute.ps1", required_markers)
        self.assertIn("scripts/runtime/Invoke-PhaseCleanup.ps1", required_markers)
        self.assertIn("scripts/verify/vibe-bootstrap-doctor-gate.ps1", required_markers)
        self.assertIn("scripts/verify/vibe-canonical-entry-truth-gate.ps1", required_markers)
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
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
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
                self.assertIn("## Specialist Decision", requirement_doc)
                self.assertIn("## Specialist Recommendations", requirement_doc)
                self.assertIn("## Artifact Review Requirements", requirement_doc)
                self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
                self.assertIn("- Record failing-first evidence for the changed behavior before implementation or defect correction.", requirement_doc)
                self.assertIn("## Code Task TDD Exceptions", requirement_doc)
                self.assertIn("No code-task TDD exceptions were frozen for this run.", requirement_doc)
                self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
                self.assertIn("No baseline document quality dimensions were frozen for this run.", requirement_doc)
                self.assertIn("## Baseline UI Quality Dimensions", requirement_doc)
                self.assertIn("No baseline UI quality dimensions were frozen for this run.", requirement_doc)
                self.assertIn("## Task-Specific Acceptance Extensions", requirement_doc)
                self.assertIn("## Research Augmentation Sources", requirement_doc)
                self.assertIn("Only host-adopted or effective approved specialist dispatch is shown here", requirement_doc)
            self.assertEqual("requirements", requirement_doc_path.parent.name)
            self.assertEqual("plans", execution_plan_path.parent.name)
            execution_plan = execution_plan_path.read_text(encoding="utf-8")
            self.assertIn("## Specialist Decision Plan", execution_plan)
            self.assertIn("## Specialist Consultation", execution_plan)
            self.assertIn("## Unified Specialist Lifecycle Disclosure", execution_plan)
            self.assertIn("## Code Task TDD Evidence Plan", execution_plan)
            self.assertIn("## Baseline Document Quality Mapping", execution_plan)
            self.assertIn("## Baseline UI Quality Mapping", execution_plan)

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
            self.assertEqual("systematic-debugging", runtime_input_packet["route_snapshot"]["selected_skill"])
            self.assertEqual("vibe", runtime_input_packet["divergence_shadow"]["runtime_selected_skill"])
            self.assertTrue(runtime_input_packet["divergence_shadow"]["skill_mismatch"])
            self.assertGreaterEqual(len(runtime_input_packet["specialist_recommendations"]), 1)
            self.assertIn("specialist_decision", runtime_input_packet)
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
            self.assertIn("specialist_decision", execute_receipt)
            self.assertEqual(execute_receipt["executed_unit_count"], execution_manifest["executed_unit_count"])
            self.assertEqual("completed", execution_manifest["status"])
            self.assertGreaterEqual(execution_manifest["successful_unit_count"], 2)
            self.assertEqual(0, execution_manifest["failed_unit_count"])
            self.assertEqual("runtime", execution_manifest["proof_class"])
            self.assertTrue(Path(execution_manifest["plan_shadow"]["path"]).exists())
            self.assertEqual(
                runtime_input_packet["route_snapshot"]["selected_skill"],
                execution_manifest["route_runtime_alignment"]["router_selected_skill"],
            )
            self.assertEqual("vibe", execution_manifest["route_runtime_alignment"]["runtime_selected_skill"])
            self.assertTrue(execution_manifest["route_runtime_alignment"]["skill_mismatch"])
            self.assertGreaterEqual(execution_manifest["specialist_accounting"]["recommendation_count"], 1)
            self.assertGreaterEqual(execution_manifest["specialist_accounting"]["dispatch_unit_count"], 1)
            self.assertIn("systematic-debugging", execution_manifest["specialist_accounting"]["specialist_skills"])
            self.assertGreaterEqual(execution_manifest["plan_shadow"]["specialist_dispatch_unit_count"], 1)
            self.assertIn("specialist_decision", execution_manifest)
            self.assertIn("specialist_decision", summary)

            specialist_disclosure = execution_manifest["specialist_user_disclosure"]
            self.assertEqual("approved_dispatch_only", specialist_disclosure["scope"])
            self.assertEqual("before_execution", specialist_disclosure["timing"])
            self.assertEqual("native_skill_entrypoint", specialist_disclosure["path_source"])
            self.assertGreaterEqual(specialist_disclosure["routed_skill_count"], 1)
            self.assertEqual(specialist_disclosure["routed_skill_count"], len(specialist_disclosure["routed_skills"]))
            routed_entry = next(
                item for item in specialist_disclosure["routed_skills"] if item["skill_id"] == "systematic-debugging"
            )
            self.assertTrue(Path(routed_entry["native_skill_entrypoint"]).is_absolute())
            self.assertTrue(Path(routed_entry["native_skill_entrypoint"]).exists())
            self.assertIn("systematic-debugging", specialist_disclosure["rendered_text"])
            self.assertIn(routed_entry["native_skill_entrypoint"], specialist_disclosure["rendered_text"])
            self.assertEqual(specialist_disclosure, execute_receipt["specialist_user_disclosure"])
            self.assertEqual(specialist_disclosure, summary["specialist_user_disclosure"])
            specialist_decision = execution_manifest["specialist_decision"]
            self.assertEqual("approved_dispatch", specialist_decision["decision_state"])
            self.assertEqual("approved_dispatch", specialist_decision["resolution_mode"])
            self.assertEqual(
                runtime_input_packet["specialist_dispatch"]["surfaced_skill_ids"],
                specialist_decision["surfaced_skill_ids"],
            )
            self.assertIn("systematic-debugging", specialist_decision["surfaced_skill_ids"])
            self.assertEqual(
                specialist_decision["approved_dispatch_skill_ids"],
                execute_receipt["specialist_decision"]["approved_dispatch_skill_ids"],
            )
            self.assertEqual(specialist_decision, summary["specialist_decision"])

            consultation_summary = summary["specialist_consultation"]
            self.assertTrue(bool(consultation_summary["enabled"]))
            self.assertEqual(2, int(consultation_summary["window_count"]))
            self.assertEqual(
                ["discussion", "planning"],
                [str(window["window_id"]) for window in list(consultation_summary["windows"])],
            )
            self.assertGreaterEqual(int(consultation_summary["approved_consultation_count"]), 2)
            self.assertGreaterEqual(int(consultation_summary["user_disclosure_count"]), 2)
            self.assertIn("discussion_specialist_consultation", artifacts)
            self.assertIn("planning_specialist_consultation", artifacts)
            self.assertIn("specialist_lifecycle_disclosure", artifacts)
            self.assertIn("host_stage_disclosure", artifacts)
            discussion_receipt = json.loads(
                resolve_artifact_path("discussion_specialist_consultation").read_text(encoding="utf-8")
            )
            planning_receipt = json.loads(
                resolve_artifact_path("planning_specialist_consultation").read_text(encoding="utf-8")
            )
            lifecycle_disclosure = json.loads(
                resolve_artifact_path("specialist_lifecycle_disclosure").read_text(encoding="utf-8")
            )
            host_stage_disclosure = json.loads(resolve_artifact_path("host_stage_disclosure").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(list(discussion_receipt["approved_consultation"])), 1)
            self.assertGreaterEqual(len(list(planning_receipt["approved_consultation"])), 1)
            self.assertGreaterEqual(len(list(discussion_receipt["user_disclosures"])), 1)
            self.assertGreaterEqual(len(list(planning_receipt["user_disclosures"])), 1)
            self.assertEqual("routing_consultation_execution_separated", lifecycle_disclosure["truth_model"])
            self.assertEqual(
                ["discussion_routing", "discussion_consultation", "planning_consultation", "execution_dispatch"],
                [str(layer["layer_id"]) for layer in list(lifecycle_disclosure["layers"])],
            )
            self.assertIn("systematic-debugging", lifecycle_disclosure["rendered_text"])
            self.assertEqual(lifecycle_disclosure, summary["specialist_lifecycle_disclosure"])
            self.assertEqual("progressive_host_stage_disclosure", host_stage_disclosure["mode"])
            self.assertEqual(
                ["discussion_routing", "discussion_consultation", "planning_consultation", "execution_dispatch"],
                [str(event["segment_id"]) for event in list(host_stage_disclosure["events"])],
            )
            self.assertEqual([1, 2, 3, 4], [int(event["sequence"]) for event in list(host_stage_disclosure["events"])])
            self.assertEqual(host_stage_disclosure, summary["host_stage_disclosure"])

            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertFalse(bool(execution_manifest["dispatch_integrity"]["approved_dispatch_fully_executed"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["approved_dispatch_fully_resolved"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["executed_specialists_subset_of_approved_dispatch"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["routed_specialists_subset_of_approved_dispatch"]))
            self.assertTrue(bool(execution_manifest["dispatch_integrity"]["local_suggestions_contained"]))
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

    def test_invoke_vibe_runtime_freezes_default_ui_baseline_dimensions_for_ui_task(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-ui"
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
                    f"-Task '{UI_TASK}' "
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
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            session_root = Path(payload["session_root"])
            summary = payload["summary"]
            relative_artifacts = summary.get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertIn("## Baseline UI Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Completeness", requirement_doc)
            self.assertIn("- Interaction Feedback", requirement_doc)
            self.assertIn("- State Coverage", requirement_doc)
            self.assertIn("- Design System Consistency", requirement_doc)
            self.assertIn("- Responsive Stability", requirement_doc)
            self.assertIn("- Spec Fidelity", requirement_doc)
            self.assertNotIn("No baseline UI quality dimensions were frozen for this run.", requirement_doc)
            self.assertEqual(run_id, session_root.name)

    def test_invoke_vibe_runtime_freezes_default_document_baseline_dimensions_for_document_task(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-doc"
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
                    f"-Task '{DOC_TASK}' "
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
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertIn("## Artifact Review Requirements", requirement_doc)
            self.assertIn(
                "- Review the touched document artifact directly against each frozen baseline document quality dimension.",
                requirement_doc,
            )
            self.assertIn(
                "- Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.",
                requirement_doc,
            )
            self.assertIn(
                "- For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.",
                requirement_doc,
            )
            self.assertNotIn("No additional artifact review requirements were frozen for this run.", requirement_doc)
            self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn("No code-task TDD evidence requirements were frozen for this run.", requirement_doc)
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Integrity", requirement_doc)
            self.assertIn("- Formatting Consistency", requirement_doc)
            self.assertIn("- Content Completeness", requirement_doc)
            self.assertIn("- Link and Reference Integrity", requirement_doc)
            self.assertIn("- Layout and Asset Stability", requirement_doc)
            self.assertIn("- Output Fidelity", requirement_doc)
            self.assertNotIn("No baseline document quality dimensions were frozen for this run.", requirement_doc)
            self.assertIn("## Baseline UI Quality Dimensions", requirement_doc)
            self.assertIn("No baseline UI quality dimensions were frozen for this run.", requirement_doc)

    def test_invoke_vibe_runtime_keeps_markdown_code_tasks_on_code_tdd_path(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-doc-code"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            host_decision_json = json.dumps(
                {
                    "decision_kind": "approval_response",
                    "decision_action": "approve_requirement",
                    "approval_decision": "approve",
                },
                separators=(",", ":"),
            )
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                (
                    "& { "
                    f"$result = & '{script_path}' "
                    f"-Task '{DOC_CODE_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
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
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertIn("## Artifact Review Requirements", requirement_doc)
            self.assertIn("No additional artifact review requirements were frozen for this run.", requirement_doc)
            self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn(
                "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                requirement_doc,
            )
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("No baseline document quality dimensions were frozen for this run.", requirement_doc)

    def test_invoke_vibe_runtime_treats_presentation_artifact_tasks_as_non_code_document_work(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-doc-deck"
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
                    f"-Task '{DOC_DECK_TASK}' "
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
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertIn("## Artifact Review Requirements", requirement_doc)
            self.assertIn(
                "- Review the touched document artifact directly against each frozen baseline document quality dimension.",
                requirement_doc,
            )
            self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn("No code-task TDD evidence requirements were frozen for this run.", requirement_doc)
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Integrity", requirement_doc)
            self.assertIn("- Output Fidelity", requirement_doc)

    def test_invoke_vibe_runtime_keeps_research_execution_tasks_off_default_code_tdd_path(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-research"
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
                    f"-Task '{RESEARCH_EXECUTION_TASK}' "
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
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1"},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            runtime_input_packet_path = artifact_root / Path(relative_artifacts["runtime_input_packet"])
            self.assertTrue(requirement_doc_path.exists())
            self.assertTrue(runtime_input_packet_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))

            self.assertEqual("research", runtime_input_packet["canonical_router"]["task_type"])
            self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn("No code-task TDD evidence requirements were frozen for this run.", requirement_doc)
            self.assertNotIn(
                "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                requirement_doc,
            )

    def test_write_requirement_doc_preserves_explicit_document_artifact_review_requirements(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        run_id = "pytest-requirement-doc-explicit-artifact-review"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        explicit_requirements = [
            "Confirm the README heading hierarchy matches the requested structure exactly.",
            "Confirm spacing changes did not alter link targets or prose content.",
        ]
        intent_contract = {
            "title": "README formatting adjustment",
            "goal": DOC_TASK,
            "deliverable": "Updated README formatting only.",
            "constraints": [
                "Do not change application code.",
            ],
            "acceptance_criteria": [
                "Requirement document is frozen before execution.",
            ],
            "artifact_review_requirements": explicit_requirements,
            "non_goals": [
                "Do not widen scope beyond the README formatting task.",
            ],
            "autonomy_mode": "interactive_governed",
            "assumptions": [
                "The README is the only touched artifact.",
            ],
        }

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            intent_contract_path = artifact_root / "intent-contract.json"
            intent_contract_path.write_text(
                json.dumps(intent_contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-Command",
                (
                    "& { "
                    f"$result = & '{script_path}' "
                    f"-Task '{DOC_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-IntentContractPath '{intent_contract_path}' "
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
            )

            payload = json.loads(completed.stdout)
            requirement_doc_path = Path(payload["requirement_doc_path"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertIn("## Artifact Review Requirements", requirement_doc)
            for item in explicit_requirements:
                self.assertIn(f"- {item}", requirement_doc)
            self.assertNotIn(
                "- Review the touched document artifact directly against each frozen baseline document quality dimension.",
                requirement_doc,
            )
            self.assertNotIn(
                "- Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.",
                requirement_doc,
            )
            self.assertNotIn(
                "- For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.",
                requirement_doc,
            )
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Integrity", requirement_doc)

    def test_write_requirement_doc_does_not_require_tdd_for_review_only_bug_audit(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        cases = [
            (
                "pytest-requirement-doc-review-bug-audit",
                "Review CodeRabbit PR bug comments and audit which findings are real bugs.",
                False,
            ),
            (
                "pytest-requirement-doc-fix-parser-bug",
                "Fix bug in parser module and add targeted verification.",
                True,
            ),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            for run_id, task, should_require_tdd in cases:
                command = [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-Command",
                    (
                        "& { "
                        f"$result = & '{script_path}' "
                        f"-Task {_ps_single_quote(task)} "
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
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                )
                payload = json.loads(completed.stdout)
                requirement_doc = Path(payload["requirement_doc_path"]).read_text(encoding="utf-8")

                if should_require_tdd:
                    self.assertIn("TDD mode: required", requirement_doc)
                    self.assertIn(
                        "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                        requirement_doc,
                    )
                else:
                    self.assertIn("TDD mode: not_applicable", requirement_doc)
                    self.assertIn("No code-task TDD evidence requirements were frozen for this run.", requirement_doc)
                    self.assertNotIn(
                        "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                        requirement_doc,
                    )

    def test_resolve_vgo_python_command_spec_falls_back_to_python3(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            fake_dir = Path(tempdir)
            _create_fake_command(fake_dir, "python3")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [fake_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("python3"))
            self.assertEqual([], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_prefers_python3_over_python(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            python3_dir = root / "python3-dir"
            python_dir = root / "python-dir"
            python3_dir.mkdir(parents=True)
            python_dir.mkdir(parents=True)
            _create_fake_command(python3_dir, "python3")
            _create_fake_command(python_dir, "python")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [python3_dir, python_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("python3"))
            self.assertEqual(python3_dir.resolve(), Path(str(resolved["host_path"])).resolve().parent)
            self.assertEqual([], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_skips_windowsapps_python3_stub_and_uses_python(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            windowsapps_dir = root / "Microsoft" / "WindowsApps"
            real_dir = root / "real-python"
            windowsapps_dir.mkdir(parents=True)
            real_dir.mkdir(parents=True)
            _create_fake_command(windowsapps_dir, "python3")
            _create_fake_command(real_dir, "python")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [windowsapps_dir, real_dir])

            host_leaf = str(resolved["host_leaf"])
            self.assertTrue(host_leaf.startswith("python"))
            self.assertFalse(host_leaf.startswith("python3"))
            resolved_host = Path(str(resolved["host_path"])).resolve()
            self.assertEqual(real_dir.resolve(), resolved_host.parent)
            self.assertEqual([], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_skips_windowsapps_python_stub_and_uses_real_python_later_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            windowsapps_dir = root / "Microsoft" / "WindowsApps"
            real_dir = root / "real-python"
            windowsapps_dir.mkdir(parents=True)
            real_dir.mkdir(parents=True)
            _create_fake_command(windowsapps_dir, "python")
            _create_fake_command(windowsapps_dir, "python3")
            _create_fake_command(real_dir, "python")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [windowsapps_dir, real_dir])

            host_leaf = str(resolved["host_leaf"])
            self.assertTrue(host_leaf.startswith("python"))
            self.assertFalse(host_leaf.startswith("python3"))
            resolved_host = Path(str(resolved["host_path"])).resolve()
            self.assertEqual(real_dir.resolve(), resolved_host.parent)
            self.assertEqual([], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_skips_windowsapps_python_stub_and_uses_py_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            windowsapps_dir = root / "Microsoft" / "WindowsApps"
            launcher_dir = root / "launcher"
            windowsapps_dir.mkdir(parents=True)
            launcher_dir.mkdir(parents=True)
            _create_fake_command(windowsapps_dir, "python")
            _create_fake_command(launcher_dir, "py")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [windowsapps_dir, launcher_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("py"))
            self.assertEqual(["-3"], resolved["prefix_arguments"])

    def test_resolve_vgo_python_command_spec_uses_py_launcher_with_dash3_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            fake_dir = Path(tempdir)
            _create_fake_command(fake_dir, "py")

            resolved = resolve_python_command_spec_via_powershell("${VGO_PYTHON}", [fake_dir])

            self.assertTrue(str(resolved["host_leaf"]).startswith("py"))
            self.assertEqual(["-3"], resolved["prefix_arguments"])

    def test_verification_gates_use_governed_python_helper(self) -> None:
        gate_paths = [
            REPO_ROOT / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1",
            REPO_ROOT / "scripts" / "verify" / "vibe-release-install-runtime-coherence-gate.ps1",
            REPO_ROOT / "scripts" / "verify" / "vibe-release-notes-quality-gate.ps1",
            REPO_ROOT / "scripts" / "verify" / "vibe-release-truth-gate.ps1",
            REPO_ROOT / "scripts" / "verify" / "vibe-workflow-acceptance-gate.ps1",
        ]

        for gate_path in gate_paths:
            content = gate_path.read_text(encoding="utf-8")
            self.assertIn("Get-VgoPythonCommand", content, str(gate_path))
            self.assertIn("prefix_arguments", content, str(gate_path))
            self.assertNotIn("Get-Command python3 -ErrorAction SilentlyContinue", content, str(gate_path))


if __name__ == "__main__":
    unittest.main()
