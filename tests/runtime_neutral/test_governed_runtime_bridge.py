from __future__ import annotations

import json
import os
import stat
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.runtime_neutral.test_l_xl_agent_execution_handoff import run_runtime


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


def write_installed_skill(target_root: Path, skill_id: str) -> Path:
    skill_path = target_root / "skills" / skill_id / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (
            "---\n"
            "name: failing test stack trace debug\n"
            "description: Debug failing tests and stack traces with systematic root-cause analysis before proposing fixes.\n"
            "---\n"
        ),
        encoding="utf-8",
    )
    return skill_path


def selected_skill_ids_from_packet(runtime_input_packet: dict[str, object]) -> list[str]:
    routing = runtime_input_packet.get("skill_routing")
    if isinstance(routing, dict):
        selected = routing.get("selected")
        if isinstance(selected, list) and selected:
            return [str(item.get("skill_id") or "") for item in selected if isinstance(item, dict) and str(item.get("skill_id") or "")]
    module_assignments = runtime_input_packet.get("module_assignments")
    if not isinstance(module_assignments, dict):
        return []
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return []
    return [str(item.get("bound_skill") or "") for item in units if isinstance(item, dict) and str(item.get("bound_skill") or "")]


SPECIALIST_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."
UI_TASK = "Build a responsive dashboard UI with clear interaction feedback, meaningful states, and desktop/mobile layout coverage."
DOC_TASK = "Reformat the project README headings and spacing without changing application code."
DOC_CODE_TASK = "Implement the markdown export pipeline for the docs renderer and add targeted verification for the parser."
DOC_DECK_TASK = "Build the release deck slides and refine presentation spacing without changing application code."
CHINESE_RESEARCH_DOC_TASK = "研究 TRIZ 方法及其适用边界，按用户批准的要求交付中文 Word 综述报告。"
NON_UI_CODE_DIAGNOSIS_TASK = "Diagnose a failing Python interface contract with TDD and add a regression test."
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
        [shell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


class GovernedRuntimeBridgeTests(unittest.TestCase):
    def test_runtime_wrappers_leave_runtime_summary_authority_to_python(self) -> None:
        common_text = (REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1").read_text(encoding="utf-8")
        invoke_text = (REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1").read_text(encoding="utf-8")

        self.assertNotIn("function New-VibePythonRuntimeSummaryProjection", common_text)
        self.assertIn("Missing Python-built runtime-input-packet.json.", invoke_text)

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

        self.assertEqual("skills/vibe/.vibeskills/install-receipt.json", runtime["receipt_relpath"])
        self.assertNotIn("required_runtime_markers", runtime)
        self.assertNotIn("required_runtime_marker_groups", runtime)
        self.assertNotIn("shell_degraded_behavior", runtime)

        linux_no_pwsh_gate = (REPO_ROOT / "scripts" / "verify" / "vibe-linux-router-no-pwsh-gate.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("Get-VgoPythonCommand", linux_no_pwsh_gate)
        self.assertNotIn("& python @args", linux_no_pwsh_gate)

        self.assertEqual(
            EXPECTED_STAGE_IDS,
            [stage["id"] for stage in contract["stages"]],
        )

    def test_invoke_vibe_runtime_returns_agent_handoff_under_temp_artifact_root(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            target_root = artifact_root / ".agents"
            write_installed_skill(target_root, "systematic-debugging")
            host_decision_json = json.dumps(
                {
                    "agent_skill_organization": {
                        "schema_version": "agent_skill_organization_v1",
                        "derived_by": "agent",
                        "workflow_level": "L",
                        "modules": [
                            {
                                "module_id": "debug_failure",
                                "goal": "Debug the failing test and stack trace systematically.",
                                "candidate_skill_ids": ["systematic-debugging"],
                                "execution_mode": "skill_assigned",
                                "acceptance_criteria": [
                                    {
                                        "criterion_id": "debug-result",
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
                                "responsibility": "Own the systematic debugging workflow.",
                                "reason": "Its SKILL.md directly owns failing-test and stack-trace diagnosis.",
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
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "& { "
                    f"$result = & '{script_path}' "
                    f"-Task '{SPECIALIST_TASK}' "
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
                env={
                    **os.environ,
                    "VIBE_AGENTS_HOME": str(target_root),
                },
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
            self.assertEqual("python", summary["truth_owner"])
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
                "agent_execution_handoff",
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
            agent_execution_handoff_path = resolve_artifact_path("agent_execution_handoff")
            runtime_input_packet_path = resolve_artifact_path("runtime_input_packet")
            governance_capsule_path = resolve_artifact_path("governance_capsule")
            stage_lineage_path = resolve_artifact_path("stage_lineage")
            handoff = json.loads(agent_execution_handoff_path.read_text(encoding="utf-8"))
            module_execution_path = Path(handoff["module_execution_path"])
            self.assertIsNone(artifacts["module_execution"])
            self.assertFalse(module_execution_path.exists())
            self.assertEqual("module_execution_v1", handoff["result_contract"]["schema_version"])

            if requirement_doc_path.exists():
                requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
                self.assertIn("## Acceptance Criteria", requirement_doc)
                self.assertIn("## Assumptions", requirement_doc)
                self.assertIn("## Code Task TDD Mode", requirement_doc)
                self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
                self.assertIn("- Record failing-first evidence for the changed behavior before implementation or defect correction.", requirement_doc)
                self.assertNotIn("## Runtime Input Truth", requirement_doc)
                self.assertNotIn("## Skill Execution Decision", requirement_doc)
                self.assertNotIn("## Selected Skill", requirement_doc)
                self.assertNotIn("## Artifact Review Requirements", requirement_doc)
                self.assertNotIn("## Code Task TDD Exceptions", requirement_doc)
                self.assertNotIn("## Baseline Document Quality Dimensions", requirement_doc)
                self.assertNotIn("## Baseline UI Quality Dimensions", requirement_doc)
                self.assertNotIn("## Task-Specific Acceptance Extensions", requirement_doc)
                self.assertNotIn("## Research Augmentation Sources", requirement_doc)
                self.assertNotIn("The current work surface records selected skills here", requirement_doc)
            self.assertEqual("requirements", requirement_doc_path.parent.name)
            self.assertEqual("plans", execution_plan_path.parent.name)
            execution_plan = execution_plan_path.read_text(encoding="utf-8")
            self.assertIn("## Execution Summary", execution_plan)
            self.assertIn("## Frozen Inputs", execution_plan)
            self.assertIn("## Module Work Plan", execution_plan)
            self.assertNotIn("## Specialist Consultation", execution_plan)
            self.assertIn("## Code Task TDD Evidence Plan", execution_plan)
            self.assertNotIn("## Skill Execution Decision Plan", execution_plan)
            self.assertNotIn("## Binary Skill Usage Plan", execution_plan)
            self.assertNotIn("## Skill Routing And Usage Evidence", execution_plan)
            self.assertNotIn("## Baseline Document Quality Mapping", execution_plan)
            self.assertNotIn("## Baseline UI Quality Mapping", execution_plan)

            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))
            selected_skill_ids = selected_skill_ids_from_packet(runtime_input_packet)
            candidate_skill_ids = [item["skill_id"] for item in runtime_input_packet["skill_routing"]["candidates"]]
            bound_skill_ids = [item["bound_skill"] for item in runtime_input_packet["module_assignments"]["units"]]
            governance_capsule = json.loads(governance_capsule_path.read_text(encoding="utf-8"))
            stage_lineage = json.loads(stage_lineage_path.read_text(encoding="utf-8"))
            execute_receipt = json.loads(execute_receipt_path.read_text(encoding="utf-8"))
            execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
            agent_execution_handoff = json.loads(
                agent_execution_handoff_path.read_text(encoding="utf-8")
            )

            self.assertEqual("vibe", governance_capsule["runtime_selected_skill"])
            self.assertEqual(summary["run_id"], governance_capsule["run_id"])
            self.assertEqual(EXPECTED_STAGE_IDS[:-1], [item["stage_name"] for item in stage_lineage["stages"]])
            self.assertEqual("runtime_input_freeze", runtime_input_packet["stage"])
            self.assertEqual("interactive_governed", runtime_input_packet["runtime_mode"])
            self.assertFalse(runtime_input_packet["canonical_router"]["unattended"])
            self.assertEqual("structure", runtime_input_packet["provenance"]["proof_class"])
            self.assertEqual("vibe", runtime_input_packet["authority_flags"]["explicit_runtime_skill"])
            self.assertEqual("skill_search_guide_v1", runtime_input_packet["skill_search_guide"]["schema_version"])
            self.assertIn("先拆任务，再拆模块", runtime_input_packet["skill_search_guide"]["search_protocol"])
            self.assertEqual("systematic-debugging", bound_skill_ids[0])
            self.assertEqual(bound_skill_ids, summary["bound_skill_ids"])
            self.assertNotIn("runtime_selected_skill", runtime_input_packet["divergence_shadow"])
            self.assertNotIn("skill_mismatch", runtime_input_packet["divergence_shadow"])
            self.assertNotIn("stage_assistant_hints", runtime_input_packet)
            self.assertNotIn("legacy_skill_routing", runtime_input_packet)
            self.assertGreaterEqual(len(candidate_skill_ids), 1)
            self.assertNotIn("selected", runtime_input_packet["skill_routing"])
            self.assertIn("systematic-debugging", selected_skill_ids)
            self.assertIn("systematic-debugging", bound_skill_ids)
            self.assertIn("systematic-debugging", candidate_skill_ids)
            self.assertEqual("plan_execute", summary["terminal_stage"])
            self.assertEqual("agent_action_required", agent_execution_handoff["status"])
            self.assertEqual("agent", agent_execution_handoff["control_owner"])
            self.assertEqual(
                ["systematic-debugging"],
                [unit["skill_id"] for unit in agent_execution_handoff["units"]],
            )
            self.assertFalse(module_execution_path.exists())
            self.assertEqual(
                ["owner"],
                [unit["role"] for unit in agent_execution_handoff["units"]],
            )
            self.assertEqual("agent_action_required", execute_receipt["status"])
            self.assertEqual("agent_action_required", execution_manifest["status"])
            self.assertEqual(bound_skill_ids, execution_manifest["module_handoff"]["assigned_skill_ids"])
            self.assertEqual("agent", execution_manifest["module_handoff"]["control_owner"])
            self.assertIsNone(artifacts.get("cleanup_receipt"))

    def test_invoke_vibe_canonical_entry_writes_receipt_and_passes_truth_gate(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1"
        truth_gate = REPO_ROOT / "scripts" / "verify" / "vibe-canonical-entry-truth-gate.ps1"
        run_id = "pytest-canonical-bridge"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            completed = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    "-Task",
                    "Plan the migration and freeze the requirement before execution.",
                    "-HostId",
                    "codex",
                    "-EntryId",
                    "vibe",
                    "-RequestedStageStop",
                    "requirement_doc",
                    "-RunId",
                    run_id,
                    "-ArtifactRoot",
                    str(artifact_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                env={**os.environ},
            )

            payload = json.loads(completed.stdout)
            session_root = Path(payload["session_root"])
            receipt_path = Path(payload["host_launch_receipt_path"])

            self.assertEqual(run_id, payload["run_id"])
            self.assertEqual(session_root / "host-launch-receipt.json", receipt_path)
            self.assertTrue(receipt_path.exists())

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual("canonical-entry", receipt["launch_mode"])
            self.assertEqual("verified", receipt["launch_status"])
            self.assertEqual("requirement_doc", receipt["requested_stage_stop"])
            summary = json.loads((session_root / "runtime-summary.json").read_text(encoding="utf-8"))
            self.assertEqual("python", summary["truth_owner"])
            self.assertIsInstance(summary["bound_skill_ids"], list)

            gate = subprocess.run(
                [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(truth_gate),
                    "-SessionRoot",
                    str(session_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(0, gate.returncode, gate.stdout + gate.stderr)
            self.assertIn("[PASS] host-launch-receipt.json exists", gate.stdout)
            self.assertIn("[PASS] host launch receipt launch_status is verified", gate.stdout)

    def test_non_ui_code_diagnosis_does_not_inherit_ui_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=NON_UI_CODE_DIAGNOSIS_TASK,
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
                requested_stage_stop="requirement_doc",
            )
            requirement_doc = Path(payload["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")

        forbidden_fragments = [
            "## Baseline UI Quality Dimensions",
            "Responsive Stability",
            "Open the primary user-facing flow",
            "unhappy-path or validation-path interaction",
        ]
        leaked_fragments = [fragment for fragment in forbidden_fragments if fragment in requirement_doc]

        self.assertEqual(
            [],
            leaked_fragments,
            "A non-UI code diagnosis/TDD task must not inherit UI or responsive acceptance requirements: "
            f"{leaked_fragments}",
        )

    def test_invoke_vibe_runtime_freezes_default_ui_baseline_dimensions_for_ui_task(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-ui"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            host_decision_json = json.dumps(
                {
                    "baseline_ui_quality_dimensions": [
                        "Structure Completeness",
                        "Interaction Feedback",
                        "State Coverage",
                        "Design System Consistency",
                        "Responsive Stability",
                        "Spec Fidelity",
                    ],
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task '{UI_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
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
            host_decision_json = json.dumps(
                {
                    "baseline_document_quality_dimensions": [
                        "Structure Integrity",
                        "Formatting Consistency",
                        "Content Completeness",
                        "Link and Reference Integrity",
                        "Layout and Asset Stability",
                        "Output Fidelity",
                    ],
                    "artifact_review_requirements": [
                        "Review the touched document artifact directly against each frozen baseline document quality dimension.",
                        "Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.",
                        "For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.",
                    ],
                    "code_task_tdd_decision": {"mode": "not_applicable"},
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task '{DOC_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
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
            self.assertNotIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Integrity", requirement_doc)
            self.assertIn("- Formatting Consistency", requirement_doc)
            self.assertIn("- Content Completeness", requirement_doc)
            self.assertIn("- Link and Reference Integrity", requirement_doc)
            self.assertIn("- Layout and Asset Stability", requirement_doc)
            self.assertIn("- Output Fidelity", requirement_doc)
            self.assertNotIn("No baseline document quality dimensions were frozen for this run.", requirement_doc)
            self.assertNotIn("## Baseline UI Quality Dimensions", requirement_doc)

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
                    "baseline_document_quality_dimensions": [],
                    "artifact_review_requirements": [],
                    "code_task_tdd_decision": {
                        "mode": "required",
                        "reason": "The host explicitly classified this as a code change that requires TDD.",
                    },
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task '{DOC_CODE_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            self.assertTrue(requirement_doc_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            self.assertNotIn("## Artifact Review Requirements", requirement_doc)
            self.assertNotIn("No additional artifact review requirements were frozen for this run.", requirement_doc)
            self.assertIn("## Code Task TDD Mode", requirement_doc)
            self.assertIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn(
                "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                requirement_doc,
            )
            self.assertNotIn("## Baseline Document Quality Dimensions", requirement_doc)

    def test_invoke_vibe_runtime_treats_presentation_artifact_tasks_as_non_code_document_work(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-doc-deck"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            host_decision_json = json.dumps(
                {
                    "baseline_document_quality_dimensions": [
                        "Structure Integrity",
                        "Formatting Consistency",
                        "Content Completeness",
                        "Link and Reference Integrity",
                        "Layout and Asset Stability",
                        "Output Fidelity",
                    ],
                    "artifact_review_requirements": [
                        "Review the touched document artifact directly against each frozen baseline document quality dimension.",
                        "Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.",
                        "For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.",
                    ],
                    "code_task_tdd_decision": {"mode": "not_applicable"},
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task '{DOC_DECK_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
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
            self.assertNotIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertIn("- Structure Integrity", requirement_doc)
            self.assertIn("- Output Fidelity", requirement_doc)

    def test_invoke_vibe_runtime_treats_chinese_word_report_as_document_not_ui(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-chinese-word-report"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            host_decision_json = json.dumps(
                {
                    "baseline_document_quality_dimensions": [
                        "Structure Integrity",
                        "Formatting Consistency",
                        "Content Completeness",
                        "Link and Reference Integrity",
                        "Layout and Asset Stability",
                        "Output Fidelity",
                    ],
                    "artifact_review_requirements": [
                        "Review the touched document artifact directly against each frozen baseline document quality dimension.",
                        "Open, render, or export the touched document artifact at least once and confirm the touched scope remains intact.",
                        "For formatting-only or layout-only work, confirm content fidelity explicitly before full completion wording is allowed.",
                    ],
                    "code_task_tdd_decision": {"mode": "not_applicable"},
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task {_ps_single_quote(CHINESE_RESEARCH_DOC_TASK)} "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"]["artifacts_relative"]
            requirement_doc = (artifact_root / Path(relative_artifacts["requirement_doc"])).read_text(
                encoding="utf-8"
            )

            self.assertIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertNotIn("## Baseline UI Quality Dimensions", requirement_doc)
            self.assertNotIn("## Code Task TDD Mode", requirement_doc)
            self.assertNotIn("## Code Task TDD Evidence Requirements", requirement_doc)

    def test_invoke_vibe_runtime_keeps_research_execution_tasks_off_default_code_tdd_path(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
        run_id = "pytest-governed-runtime-research"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            host_decision_json = json.dumps(
                {
                    "code_task_tdd_decision": {"mode": "not_applicable"},
                },
                separators=(",", ":"),
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
                    f"$result = & '{script_path}' "
                    f"-Task '{RESEARCH_EXECUTION_TASK}' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-ArtifactRoot '{artifact_root}' "
                    "-RequestedStageStop requirement_doc "
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
                env={**os.environ},
            )

            payload = json.loads(completed.stdout)
            relative_artifacts = payload["summary"].get("artifacts_relative", {})
            requirement_doc_path = artifact_root / Path(relative_artifacts["requirement_doc"])
            runtime_input_packet_path = artifact_root / Path(relative_artifacts["runtime_input_packet"])
            self.assertTrue(requirement_doc_path.exists())
            self.assertTrue(runtime_input_packet_path.exists())

            requirement_doc = requirement_doc_path.read_text(encoding="utf-8")
            runtime_input_packet = json.loads(runtime_input_packet_path.read_text(encoding="utf-8"))

            self.assertEqual("research", runtime_input_packet["route_snapshot"]["task_type"])
            self.assertNotIn("## Code Task TDD Evidence Requirements", requirement_doc)
            self.assertNotIn("## Code Task TDD Mode", requirement_doc)
            self.assertNotIn(
                "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                requirement_doc,
            )

    def test_write_requirement_doc_preserves_explicit_artifact_review_without_adding_document_dimensions(self) -> None:
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
                "-ExecutionPolicy",
                "Bypass",
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
            self.assertNotIn("## Baseline Document Quality Dimensions", requirement_doc)
            self.assertNotIn("- Structure Integrity", requirement_doc)

    def test_write_requirement_doc_uses_only_explicit_code_task_tdd_decision(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        cases = [
            (
                "pytest-requirement-doc-code-without-tdd-decision",
                "Fix bug in parser module and add targeted verification.",
                None,
                False,
            ),
            (
                "pytest-requirement-doc-explicit-code-tdd-decision",
                "Fix bug in parser module and add targeted verification.",
                {
                    "mode": "required",
                    "source": "host_decision",
                    "reason": "The host explicitly requires TDD for this code change.",
                },
                True,
            ),
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            for run_id, task, tdd_decision, should_require_tdd in cases:
                intent_contract_argument = ""
                if tdd_decision is not None:
                    intent_contract = {
                        "title": "Parser bug correction",
                        "goal": task,
                        "deliverable": "Corrected parser behavior with targeted verification.",
                        "constraints": ["Keep the change scoped to the parser behavior."],
                        "acceptance_criteria": ["The parser regression is covered by targeted verification."],
                        "non_goals": ["Do not refactor unrelated modules."],
                        "autonomy_mode": "interactive_governed",
                        "assumptions": [],
                        "code_task_tdd_decision": tdd_decision,
                    }
                    intent_contract_path = artifact_root / f"{run_id}-intent-contract.json"
                    intent_contract_path.write_text(
                        json.dumps(intent_contract, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    intent_contract_argument = f"-IntentContractPath '{intent_contract_path}' "
                command = [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    (
                        "& { "
                        f"$result = & '{script_path}' "
                        f"-Task {_ps_single_quote(task)} "
                        "-Mode interactive_governed "
                        f"-RunId '{run_id}' "
                        f"{intent_contract_argument}"
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
                    self.assertNotIn("## Code Task TDD Mode", requirement_doc)
                    self.assertNotIn("## Code Task TDD Evidence Requirements", requirement_doc)
                    self.assertNotIn(
                        "- Record failing-first evidence for the changed behavior before implementation or defect correction.",
                        requirement_doc,
                    )

    def test_write_requirement_doc_renders_skill_search_guide_before_workflow_level_confirmation(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        run_id = "pytest-requirement-doc-workflow-level-details"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        intent_contract = {
            "title": "Governed workflow level confirmation",
            "goal": "Clarify which workflow level should run before any execution starts.",
            "deliverable": "A requirement document with explicit L and XL guidance.",
            "constraints": [
                "Do not start execution before the user chooses the workflow level.",
            ],
            "acceptance_criteria": [
                "Both levels explain the workflow, expected skills, and reason for the recommendation.",
            ],
            "non_goals": [
                "Do not auto-continue into execution planning.",
            ],
            "autonomy_mode": "interactive_governed",
            "assumptions": [
                "The user still needs to confirm the workflow level.",
            ],
            "workflow_level_confirmation": {
                "enabled": True,
                "user_visible": True,
                "recommended_level": "L",
                "recommendation_reason": "L keeps the work on one serial governed lane for this scope.",
                "question": "先确认任务级别：这次任务走 L 级还是 XL 级？",
                "decision_importance": "L 和 XL 会直接改变后续协作深度、执行波次和证据压力。",
                "levels": {
                    "L": "L 级保持单主线推进。",
                    "XL": "XL 级进入更重的分波次协作。",
                },
                "level_details": {
                    "L": {
                        "workflow": "冻结需求与计划后，由一个主流程串行推进 Agent 组织出的方案。",
                        "skills": "会先按模块搜索本地 skills、阅读候选 `SKILL.md`，再给出较轻量的 L 级组织方案；如需代码改动，再补充 tdd 这类验证 skill。",
                        "why_this_fit": "适合仍然是一个主交付物、并行收益不高的任务。",
                        "confirm_reply": "如果你认可这个流程，请回复：走 L 级。",
                    },
                    "XL": {
                        "workflow": "冻结需求与计划后，把 Agent 组织出的方案拆成分波次执行，并在依赖安全时做受控并行。",
                        "skills": "会先按模块组织更完整的 skills 覆盖；若任务确实需要多代理，再进入 subagent-driven-development。",
                        "why_this_fit": "适合多技能协作、多产物或高风险任务。",
                        "confirm_reply": "如果你要更重的分波次流程，请回复：走 XL 级。",
                    },
                },
                "selection_prompt": "请根据上面的说明选择并确认这次任务级别。",
            },
        }

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            intent_contract_path = artifact_root / "intent-contract.json"
            runtime_input_packet_path = artifact_root / "runtime-input-packet.json"
            intent_contract_path.write_text(
                json.dumps(intent_contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            runtime_input_packet_path.write_text(
                json.dumps(
                    {
                        "governance_scope": "root",
                        "module_assignments": {
                            "unit_count": 0,
                            "status": "no_bound_skills",
                            "units": [],
                        },
                        "hierarchy": {
                            "root_run_id": run_id,
                        },
                        "authority_flags": {
                            "explicit_runtime_skill": "vibe",
                        },
                        "route_snapshot": {
                            "task_type": "research",
                            "route_mode": "no_local_candidate",
                            "confirm_required": False,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
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
                    f"$result = & '{script_path}' "
                    "-Task 'Clarify the governed workflow level before execution.' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-IntentContractPath '{intent_contract_path}' "
                    f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
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

            self.assertIn("## Skill Search Guide", requirement_doc)
            self.assertIn("先拆任务，再拆模块", requirement_doc)
            self.assertIn("按模块搜索本地 skills", requirement_doc)
            self.assertIn("阅读候选 `SKILL.md`", requirement_doc)
            self.assertIn("给出 `L` / `XL` 两套 skills 组织方案", requirement_doc)
            self.assertIn("明确标出缺口", requirement_doc)
            self.assertNotIn("Screened task-skill shortlist size", requirement_doc)
            self.assertNotIn("shortlist", requirement_doc.lower())
            self.assertNotIn("selected task skills", requirement_doc)
            self.assertIn("## Workflow Level Confirmation", requirement_doc)
            self.assertIn("Recommendation reason: L keeps the work on one serial governed lane for this scope.", requirement_doc)
            self.assertIn("Why this decision matters: L 和 XL 会直接改变后续协作深度、执行波次和证据压力。", requirement_doc)
            self.assertIn("L workflow: 冻结需求与计划后，由一个主流程串行推进 Agent 组织出的方案。", requirement_doc)
            self.assertIn("L skills: 会先按模块搜索本地 skills、阅读候选 `SKILL.md`，再给出较轻量的 L 级组织方案；如需代码改动，再补充 tdd 这类验证 skill。", requirement_doc)
            self.assertIn("XL workflow: 冻结需求与计划后，把 Agent 组织出的方案拆成分波次执行，并在依赖安全时做受控并行。", requirement_doc)
            self.assertIn("XL skills: 会先按模块组织更完整的 skills 覆盖；若任务确实需要多代理，再进入 subagent-driven-development。", requirement_doc)

    def test_write_requirement_doc_uses_skill_search_guide_from_runtime_packet(self) -> None:
        script_path = REPO_ROOT / "scripts" / "runtime" / "Write-RequirementDoc.ps1"
        run_id = "pytest-requirement-doc-skill-search-guide"
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        intent_contract = {
            "title": "Governed workflow level confirmation",
            "goal": "Clarify which workflow level should run before any execution starts.",
            "deliverable": "A requirement document with explicit L and XL guidance.",
            "constraints": [
                "Do not start execution before the user chooses the workflow level.",
            ],
            "acceptance_criteria": [
                "Both levels explain the workflow, expected skills, and reason for the recommendation.",
            ],
            "non_goals": [
                "Do not auto-continue into execution planning.",
            ],
            "autonomy_mode": "interactive_governed",
            "assumptions": [
                "The user still needs to confirm the workflow level.",
            ],
            "workflow_level_confirmation": {
                "enabled": True,
                "user_visible": True,
                "recommended_level": "L",
                "recommendation_reason": "L keeps the work on one serial governed lane for this scope.",
                "question": "先确认任务级别：这次任务走 L 级还是 XL 级？",
                "decision_importance": "L 和 XL 会直接改变后续协作深度、执行波次和证据压力。",
                "levels": {
                    "L": "L 级保持单主线推进。",
                    "XL": "XL 级进入更重的分波次协作。",
                },
                "level_details": {
                    "L": {
                        "workflow": "冻结需求与计划后，由一个主流程串行推进 Agent 组织出的方案。",
                        "skills": "会先按模块搜索本地 skills、阅读候选 `SKILL.md`，再给出较轻量的 L 级组织方案；如需代码改动，再补充 tdd 这类验证 skill。",
                        "why_this_fit": "适合仍然是一个主交付物、并行收益不高的任务。",
                        "confirm_reply": "如果你认可这个流程，请回复：走 L 级。",
                    },
                    "XL": {
                        "workflow": "冻结需求与计划后，把 Agent 组织出的方案拆成分波次执行，并在依赖安全时做受控并行。",
                        "skills": "会先按模块组织更完整的 skills 覆盖；若任务确实需要多代理，再进入 subagent-driven-development。",
                        "why_this_fit": "适合多技能协作、多产物或高风险任务。",
                        "confirm_reply": "如果你要更重的分波次流程，请回复：走 XL 级。",
                    },
                },
                "selection_prompt": "请根据上面的说明选择并确认这次任务级别。",
            },
        }

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            intent_contract_path = artifact_root / "intent-contract.json"
            runtime_input_packet_path = artifact_root / "runtime-input-packet.json"
            intent_contract_path.write_text(
                json.dumps(intent_contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            runtime_input_packet_path.write_text(
                json.dumps(
                    {
                        "governance_scope": "root",
                        "module_assignments": {
                            "unit_count": 0,
                            "status": "no_bound_skills",
                            "units": [],
                        },
                        "hierarchy": {
                            "root_run_id": run_id,
                        },
                        "authority_flags": {
                            "explicit_runtime_skill": "vibe",
                        },
                        "route_snapshot": {
                            "task_type": "research",
                            "route_mode": "candidate_discovery_only",
                            "confirm_required": False,
                        },
                        "skill_search_guide": {
                            "schema_version": "skill_search_guide_v1",
                            "skill_roots": [
                                {"kind": "host_local", "path": "C:/Users/demo/.agents/skills"},
                                {"kind": "repo_bundled", "path": "D:/Documents/vibeskills/Vibe-Skills-main/bundled/skills"},
                            ],
                            "search_protocol": [
                                "先拆任务，再拆模块",
                                "每个模块单独搜索本地 skills",
                                "先看 skill 名、短描述，再打开候选 `SKILL.md`",
                            ],
                            "selection_rules": [
                                "优先选真 owner，不选只沾边的 helper",
                                "没有 owner 时要明确标出缺口",
                            ],
                            "disclosure_rules": [
                                "requirement 阶段只公开搜索办法，不公开程序候选排名或预选结果",
                                "xl_plan 阶段公开模块、候选、最终采用和缺口",
                            ],
                            "workflow_level_contract": {
                                "levels": ["L", "XL"],
                            },
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
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
                    f"$result = & '{script_path}' "
                    "-Task 'Clarify the governed workflow level before execution.' "
                    "-Mode interactive_governed "
                    f"-RunId '{run_id}' "
                    f"-IntentContractPath '{intent_contract_path}' "
                    f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
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

            self.assertIn("## Skill Search Guide", requirement_doc)
            self.assertIn("先拆任务，再拆模块", requirement_doc)
            self.assertIn("按模块搜索本地 skills", requirement_doc)
            self.assertIn("打开候选 `SKILL.md`", requirement_doc)
            self.assertIn("明确标出缺口", requirement_doc)
            self.assertIn("## Workflow Level Confirmation", requirement_doc)
            self.assertNotIn("Screened task-skill shortlist size: `6`", requirement_doc)
            self.assertNotIn("L selected task skills: `research`, `humanizer`, `paper-writer`", requirement_doc)
            self.assertNotIn(
                "XL selected task skills: `research`, `humanizer`, `paper-writer`, `statistical-analysis`, `matplotlib`",
                requirement_doc,
            )
            self.assertNotIn("## Skill Usage", requirement_doc)
            self.assertIn("Selection prompt: 请根据上面的说明选择并确认这次任务级别。", requirement_doc)

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

    def test_installed_freshness_gate_uses_install_receipt_hashes(self) -> None:
        gate_path = REPO_ROOT / "scripts" / "verify" / "vibe-installed-runtime-freshness-gate.ps1"
        content = gate_path.read_text(encoding="utf-8")

        self.assertIn(".vibeskills\\install-receipt.json", content)
        self.assertIn("Get-FileHash", content)
        self.assertNotIn("runtime_neutral\\freshness_gate.py", content)


if __name__ == "__main__":
    unittest.main()
