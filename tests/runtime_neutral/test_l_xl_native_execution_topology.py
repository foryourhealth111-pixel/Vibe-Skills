from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_EXECUTION_TASK = (
    "Implement a bounded migration with explicit code changes, tests, and verification."
)
DEBUG_EXECUTION_TASK = (
    "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."
)
DEBUG_SPECIALIST_TASK = (
    "I have a failing test and stack trace. Debug systematically and execute specialist workflow."
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


def run_runtime(
    task: str,
    artifact_root: Path,
    *,
    mode: str = "interactive_governed",
    script_relative_path: str = "scripts/runtime/invoke-vibe-runtime.ps1",
    run_id: str | None = None,
    governance_scope: str = "root",
    root_run_id: str = "",
    parent_run_id: str = "",
    parent_unit_id: str = "",
    inherited_requirement_doc_path: Path | None = None,
    inherited_execution_plan_path: Path | None = None,
    approved_specialist_skill_ids: list[str] | None = None,
    entry_intent_id: str = "",
    requested_stage_stop: str = "",
    requested_grade_floor: str = "",
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / script_relative_path
    effective_run_id = run_id or ("pytest-topology-" + uuid.uuid4().hex[:10])
    approved = approved_specialist_skill_ids or []
    delegation_envelope_path: Path | None = None
    if (
        governance_scope == "child"
        and root_run_id
        and parent_run_id
        and parent_unit_id
        and inherited_requirement_doc_path is not None
        and inherited_execution_plan_path is not None
    ):
        delegation_envelope_path = write_delegation_envelope_fixture(
            artifact_root,
            child_run_id=effective_run_id,
            root_run_id=root_run_id,
            parent_run_id=parent_run_id,
            parent_unit_id=parent_unit_id,
            inherited_requirement_doc_path=inherited_requirement_doc_path,
            inherited_execution_plan_path=inherited_execution_plan_path,
            approved_specialists=approved,
        )
    approved_literal = (
        "@(" + ",".join("'" + skill.replace("'", "''") + "'" for skill in approved) + ")"
        if approved
        else "@()"
    )
    inherited_requirement = (
        f"-InheritedRequirementDocPath '{inherited_requirement_doc_path}' "
        if inherited_requirement_doc_path
        else ""
    )
    inherited_plan = (
        f"-InheritedExecutionPlanPath '{inherited_execution_plan_path}' "
        if inherited_execution_plan_path
        else ""
    )
    root_segment = f"-RootRunId '{root_run_id}' " if root_run_id else ""
    parent_segment = f"-ParentRunId '{parent_run_id}' " if parent_run_id else ""
    parent_unit_segment = f"-ParentUnitId '{parent_unit_id}' " if parent_unit_id else ""
    delegation_segment = (
        f"-DelegationEnvelopePath '{delegation_envelope_path}' "
        if delegation_envelope_path is not None
        else ""
    )
    entry_intent_segment = f"-EntryIntentId '{entry_intent_id}' " if entry_intent_id else ""
    requested_stop_segment = f"-RequestedStageStop '{requested_stage_stop}' " if requested_stage_stop else ""
    requested_grade_segment = f"-RequestedGradeFloor '{requested_grade_floor}' " if requested_grade_floor else ""

    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            f"-Mode {mode} "
            f"-GovernanceScope {governance_scope} "
            f"-RunId '{effective_run_id}' "
            f"{root_segment}"
            f"{parent_segment}"
            f"{parent_unit_segment}"
            f"{inherited_requirement}"
            f"{inherited_plan}"
            f"{delegation_segment}"
            f"{entry_intent_segment}"
            f"{requested_stop_segment}"
            f"{requested_grade_segment}"
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
        encoding="utf-8",
        check=True,
        env={**os.environ, "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1", **(extra_env or {})},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def write_delegation_envelope_fixture(
    artifact_root: Path,
    *,
    child_run_id: str,
    root_run_id: str,
    parent_run_id: str,
    parent_unit_id: str,
    inherited_requirement_doc_path: Path,
    inherited_execution_plan_path: Path,
    approved_specialists: list[str] | None = None,
) -> Path:
    approved = approved_specialists or []
    session_root = artifact_root / "outputs" / "runtime" / "vibe-sessions" / child_run_id
    session_root.mkdir(parents=True, exist_ok=True)
    envelope_path = session_root / "delegation-envelope.json"
    envelope = {
        "root_run_id": root_run_id,
        "parent_run_id": parent_run_id,
        "parent_unit_id": parent_unit_id,
        "child_run_id": child_run_id,
        "governance_scope": "child_governed",
        "requirement_doc_path": str(inherited_requirement_doc_path.resolve()),
        "execution_plan_path": str(inherited_execution_plan_path.resolve()),
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


def run_write_xl_plan(
    task: str,
    artifact_root: Path,
    requirement_doc_path: Path,
    runtime_input_packet_path: Path | None = None,
    *,
    run_id: str | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Write-XlPlan.ps1"
    effective_run_id = run_id or ("pytest-write-plan-" + uuid.uuid4().hex[:10])
    ps_command = (
        "& { "
        f"$result = & '{script_path}' "
        f"-Task '{task}' "
        "-Mode interactive_governed "
        f"-RunId '{effective_run_id}' "
        f"-RequirementDocPath '{requirement_doc_path}' "
        f"-ArtifactRoot '{artifact_root}' "
    )
    if runtime_input_packet_path is not None:
        ps_command += f"-RuntimeInputPacketPath '{runtime_input_packet_path}' "
    ps_command += "$result | ConvertTo-Json -Depth 20 }"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        ps_command,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout not in ("", "null"):
        return json.loads(stdout)

    receipt_path = artifact_root / "outputs" / "runtime" / "vibe-sessions" / effective_run_id / "execution-plan-receipt.json"
    if not receipt_path.exists():
        raise AssertionError(
            "Write-XlPlan returned null payload and did not emit a receipt. "
            f"stderr={completed.stderr.strip()}"
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "execution_plan_path": receipt["execution_plan_path"],
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


def run_plan_execute(
    task: str,
    artifact_root: Path,
    requirement_doc_path: Path,
    execution_plan_path: Path,
    runtime_input_packet_path: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
    run_id = "pytest-execute-plan-" + uuid.uuid4().hex[:10]
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
            f"-RunId '{run_id}' "
            f"-RequirementDocPath '{requirement_doc_path}' "
            f"-ExecutionPlanPath '{execution_plan_path}' "
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
        check=True,
        env={**os.environ, **(extra_env or {})},
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def current_selected_dispatch(runtime_input: dict[str, object]) -> list[dict[str, object]]:
    routing = runtime_input.get("skill_routing") or {}
    return list((routing.get("selected") if isinstance(routing, dict) else []) or [])


def parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect_wave_units(execution_manifest: dict[str, object]) -> list[dict[str, object]]:
    units: list[dict[str, object]] = []
    for wave in list(execution_manifest.get("waves") or []):
        units.extend(list((wave or {}).get("units") or []))
    return units


def collect_topology_steps(execution_manifest: dict[str, object]) -> list[dict[str, object]]:
    topology = execution_manifest.get("execution_topology") or {}
    topology_path = topology.get("path")
    if not topology_path:
        return []

    execution_topology = load_json(topology_path)
    steps: list[dict[str, object]] = []
    for wave in list(execution_topology.get("waves") or []):
        steps.extend(list((wave or {}).get("steps") or []))
    return steps


def load_unit_result(unit: dict[str, object]) -> dict[str, object]:
    return load_json(unit["result_path"])


def create_fake_codex_command(directory: Path, *, required_prompt_markers: list[str] | None = None) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex{suffix}"
    markers = required_prompt_markers or []
    if os.name == "nt":
        marker_checks = ""
        for index, marker in enumerate(markers, start=1):
            escaped_marker = marker.replace('"', '""')
            marker_checks += (
                f"echo %* | findstr /C:\"{escaped_marker}\" >nul || exit /b {90 + index}\r\n"
            )
        command_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
            "set RAW_ARGS=%*\r\n"
            "set OUT=\r\n"
            ":loop\r\n"
            "if \"%~1\"==\"\" goto done\r\n"
            "if \"%~1\"==\"-o\" (\r\n"
            "  set OUT=%~2\r\n"
            "  shift\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "shift\r\n"
            "goto loop\r\n"
            ":done\r\n"
            "if \"%OUT%\"==\"\" exit /b 2\r\n"
            "echo %RAW_ARGS% | findstr /C:\"consultation_role:\" >nul\r\n"
            "if %errorlevel%==0 (\r\n"
            "  > \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"fake codex consultation executed\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the consultation guidance to shape the next frozen artifact.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}\r\n"
            "  echo fake codex consultation ok\r\n"
            "  exit /b 0\r\n"
            ")\r\n"
            f"{marker_checks}"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}\r\n"
            "echo fake codex ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        marker_checks = ""
        for index, marker in enumerate(markers, start=1):
            escaped_marker = marker.replace("\\", "\\\\").replace('"', '\\"')
            marker_checks += (
                f'printf "%s" "$RAW_ARGS" | grep -F "{escaped_marker}" >/dev/null || exit {90 + index}\n'
            )
        command_path.write_text(
            "#!/usr/bin/env sh\n"
            "RAW_ARGS=\"$*\"\n"
            "IS_CONSULTATION=0\n"
            "printf '%s' \"$RAW_ARGS\" | grep -F \"consultation_role:\" >/dev/null && IS_CONSULTATION=1\n"
            "OUT=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -o)\n"
            "      OUT=\"$2\"\n"
            "      shift 2\n"
            "      ;;\n"
            "    *)\n"
            "      shift\n"
            "      ;;\n"
            "  esac\n"
            "done\n"
            "if [ -z \"$OUT\" ]; then\n"
            "  exit 2\n"
            "fi\n"
            "if [ \"$IS_CONSULTATION\" -eq 1 ]; then\n"
            "  printf '%s' '{\"status\":\"completed\",\"summary\":\"fake codex consultation executed\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the consultation guidance to shape the next frozen artifact.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}' > \"$OUT\"\n"
            "  printf 'fake codex consultation ok\\n'\n"
            "  exit 0\n"
            "fi\n"
            f"{marker_checks}"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}' > \"$OUT\"\n"
            "printf 'fake codex ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


class NativeExecutionTopologyTests(unittest.TestCase):
    def test_public_vibe_defaults_to_requirement_confirmation_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Implement the runtime hardening after confirming scope and plan.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertEqual("vibe", runtime_input["entry_intent_id"])
            self.assertEqual("requirement_doc", runtime_input["requested_stage_stop"])
            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("requirement_doc", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual("xl_plan", summary["bounded_return_control"]["next_stage"])
            self.assertEqual("requirement_confirmation", summary["bounded_return_control"]["approval_kind"])
            self.assertIn(
                "revise_requirement",
                summary["bounded_return_control"]["host_decision_contract"]["allowed_decision_actions"],
            )
            self.assertEqual(["vibe"], list(summary["bounded_return_control"]["allowed_followup_entry_ids"]))
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_new_user_message_required"]))
            self.assertIn("Do not auto-continue into `xl_plan`", summary["bounded_return_control"]["approval_prompt"])
            self.assertIn("wait for a new user message", summary["host_user_briefing"]["rendered_text"])
            self.assertFalse(summary["artifacts"]["execution_plan"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_vibe_what_do_i_want_shortcut_stops_after_requirement_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Clarify the project goal before any implementation starts.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe-what-do-i-want",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertEqual("vibe-what-do-i-want", runtime_input["entry_intent_id"])
            self.assertIsNone(runtime_input["canonical_router"]["requested_skill"])
            self.assertEqual("requirement_doc", runtime_input["requested_stage_stop"])
            self.assertIsNone(runtime_input["requested_grade_floor"])
            self.assertEqual("requirement_doc", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("requirement_doc", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual(payload["run_id"], summary["bounded_return_control"]["source_run_id"])
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_user_reentry_required"]))
            self.assertEqual(
                ["vibe", "vibe-how-do-we-do", "vibe-do-it"],
                list(summary["bounded_return_control"]["allowed_followup_entry_ids"]),
            )
            self.assertTrue(summary["artifacts"]["host_user_briefing"])
            self.assertIn("--continue-from-run-id", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("--bounded-reentry-token", summary["host_user_briefing"]["rendered_text"])
            self.assertTrue(summary["artifacts"]["requirement_doc"])
            self.assertFalse(summary["artifacts"]["execution_plan"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_vibe_how_do_we_do_shortcut_freezes_requirement_and_plan_then_stops_before_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Plan the migration and freeze the requirement before execution.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe-how-do-we-do",
                requested_grade_floor="XL",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])
            requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            plan_receipt = load_json(summary["artifacts"]["execution_plan_receipt"])

            self.assertEqual("vibe-how-do-we-do", runtime_input["entry_intent_id"])
            self.assertIsNone(runtime_input["canonical_router"]["requested_skill"])
            self.assertEqual("xl_plan", runtime_input["requested_stage_stop"])
            self.assertEqual("XL", runtime_input["requested_grade_floor"])
            self.assertEqual("xl_plan", summary["terminal_stage"])
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan"],
                list(summary["executed_stage_order"]),
            )
            self.assertEqual(
                ["skeleton_check", "deep_interview", "requirement_doc", "xl_plan"],
                [item["stage_name"] for item in stage_lineage["stages"]],
            )
            self.assertEqual("xl_plan", summary["bounded_return_control"]["terminal_stage"])
            self.assertEqual(payload["run_id"], summary["bounded_return_control"]["source_run_id"])
            self.assertTrue(bool(summary["bounded_return_control"]["explicit_user_reentry_required"]))
            self.assertIn(
                "revise_plan",
                summary["bounded_return_control"]["host_decision_contract"]["allowed_decision_actions"],
            )
            self.assertEqual(
                ["vibe", "vibe-do-it"],
                list(summary["bounded_return_control"]["allowed_followup_entry_ids"]),
            )
            self.assertTrue(summary["artifacts"]["host_user_briefing"])
            self.assertIn("--continue-from-run-id", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("--bounded-reentry-token", summary["host_user_briefing"]["rendered_text"])
            self.assertIn("Entry intent", requirement_doc)
            self.assertIn("Requested stop stage", requirement_doc)
            self.assertIn("Requested grade floor", execution_plan)
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertFalse(summary["artifacts"]["execute_receipt"])
            self.assertFalse(summary["artifacts"]["execution_manifest"])
            self.assertFalse(summary["artifacts"]["cleanup_receipt"])

    def test_requested_xl_grade_floor_clamps_governed_runtime_execution_grade(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Implement the migration with explicit code changes, tests, and verification.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe-do-it",
                requested_grade_floor="XL",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            plan_receipt = load_json(summary["artifacts"]["execution_plan_receipt"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual("vibe-do-it", runtime_input["entry_intent_id"])
            self.assertIsNone(runtime_input["canonical_router"]["requested_skill"])
            self.assertEqual("phase_cleanup", runtime_input["requested_stage_stop"])
            self.assertEqual("XL", runtime_input["requested_grade_floor"])
            self.assertEqual("XL", runtime_input["internal_grade"])
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertEqual("XL", execution_manifest["internal_grade"])

    def test_confirm_required_stops_at_skeleton_before_wrapper_stage_target(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Design architecture migration with staged review and planning gates.",
                artifact_root=Path(tempdir),
                governance_scope="root",
                entry_intent_id="vibe-what-do-i-want",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            stage_lineage = load_json(summary["artifacts"]["stage_lineage"])

            self.assertTrue(bool(runtime_input["route_snapshot"]["confirm_required"]))
            self.assertEqual("skeleton_check", summary["terminal_stage"])
            self.assertEqual(["skeleton_check"], list(summary["executed_stage_order"]))
            self.assertEqual(["skeleton_check"], [item["stage_name"] for item in stage_lineage["stages"]])
            self.assertFalse(summary["artifacts"]["requirement_doc"])
            self.assertTrue(summary["artifacts"]["host_user_briefing"])

    def test_direct_plan_and_execute_scripts_do_not_let_stale_packet_grade_undercut_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
                entry_intent_id="vibe",
                requested_grade_floor="XL",
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)
            runtime_input_packet["internal_grade"] = "L"
            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            plan_payload = run_write_xl_plan(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            plan_receipt = load_json(plan_payload["receipt_path"])
            execution_payload = run_plan_execute(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=Path(plan_payload["execution_plan_path"]),
                runtime_input_packet_path=runtime_input_packet_path,
            )
            execution_receipt = load_json(execution_payload["receipt_path"])
            execution_manifest = load_json(execution_receipt["execution_manifest_path"])

            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertEqual("XL", execution_receipt["internal_grade"])
            self.assertEqual("XL", execution_manifest["internal_grade"])

    def test_write_xl_plan_uses_session_runtime_input_packet_when_path_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task="Plan a small bounded migration.",
                artifact_root=artifact_root,
                governance_scope="root",
                entry_intent_id="vibe-how-do-we-do",
                requested_grade_floor="XL",
            )
            initial_summary = initial_payload["summary"]
            run_id = str(initial_payload["run_id"])
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])

            plan_payload = run_write_xl_plan(
                task="Plan a small bounded migration.",
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                run_id=run_id,
            )
            plan_receipt = load_json(plan_payload["receipt_path"])
            execution_plan = Path(plan_payload["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertEqual(str(runtime_input_packet_path), plan_receipt["runtime_input_packet_path"])
            self.assertEqual("XL", plan_receipt["internal_grade"])
            self.assertIn("Entry intent: vibe-how-do-we-do", execution_plan)
            self.assertIn("Requested stop stage: xl_plan", execution_plan)
            self.assertIn("Requested grade floor: XL", execution_plan)

    def test_write_xl_plan_keeps_unknown_phase_dispatches_and_suggestions_in_ungrouped_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)

            approved_dispatch = current_selected_dispatch(runtime_input_packet)
            self.assertGreaterEqual(len(approved_dispatch), 1)
            unknown_dispatch_skill_id = str(approved_dispatch[0]["skill_id"])
            runtime_input_packet["skill_routing"]["selected"][0]["phase_id"] = "missing-phase"
            runtime_input_packet["execution_phase_decomposition"] = {
                "phases": [
                    {
                        "phase_id": "phase-1",
                        "stage_type": "implementation",
                        "dispatch_phase": "in_execution",
                        "stage_order": 1,
                        "stage_label": "Implementation",
                        "goal": "Exercise ungrouped specialist rendering.",
                        "depends_on": [],
                        "artifacts_in": [],
                        "artifacts_out": [],
                        "acceptance_checks": [],
                    }
                ]
            }

            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            plan_payload = run_write_xl_plan(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            execution_plan = Path(plan_payload["execution_plan_path"]).read_text(encoding="utf-8")

            self.assertIn("### Phase `ungrouped`: fallback specialist dispatch", execution_plan)
            self.assertIn(f"- Dispatch {unknown_dispatch_skill_id} as", execution_plan)
            self.assertNotIn("- Suggest pytest-ungrouped-suggestion.", execution_plan)

    def test_plan_execute_marks_current_selected_dispatch_packets_incomplete_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            initial_payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            execution_plan_path = Path(initial_summary["artifacts"]["execution_plan"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)

            approved_dispatch = current_selected_dispatch(runtime_input_packet)
            self.assertGreaterEqual(len(approved_dispatch), 1)
            selected_skill_id = str(approved_dispatch[0]["skill_id"])
            runtime_input_packet["skill_routing"]["selected"][0].pop("skill_root", None)
            runtime_input_packet["skill_routing"]["selected"][0].pop("usage_required", None)
            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            execution_payload = run_plan_execute(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=execution_plan_path,
                runtime_input_packet_path=runtime_input_packet_path,
            )
            execution_receipt = load_json(execution_payload["receipt_path"])
            execution_manifest = load_json(execution_receipt["execution_manifest_path"])
            execution_proof = load_json(execution_receipt["execution_proof_manifest_path"])

            self.assertIn(
                selected_skill_id,
                list(execution_manifest["dispatch_integrity"]["dispatch_contract_incomplete_skill_ids"]),
            )
            self.assertFalse(bool(execution_manifest["dispatch_integrity"]["proof_passed"]))
            self.assertFalse(bool(execution_proof["dispatch_integrity_proof_passed"]))
            self.assertFalse(bool(execution_proof["proof_passed"]))

    def test_plan_execute_accepts_current_usage_required_only_dispatch_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_fake_codex_command(
                artifact_root,
                required_prompt_markers=[
                    "native_skill_entrypoint:",
                    "skill_root:",
                    "usage_required: true",
                    "must_preserve_workflow: true",
                ],
            )
            initial_payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                governance_scope="root",
            )
            initial_summary = initial_payload["summary"]
            requirement_doc_path = Path(initial_summary["artifacts"]["requirement_doc"])
            execution_plan_path = Path(initial_summary["artifacts"]["execution_plan"])
            runtime_input_packet_path = Path(initial_summary["artifacts"]["runtime_input_packet"])
            runtime_input_packet = load_json(runtime_input_packet_path)

            approved_dispatch = current_selected_dispatch(runtime_input_packet)
            self.assertGreaterEqual(len(approved_dispatch), 1)
            selected_skill_id = str(approved_dispatch[0]["skill_id"])
            runtime_input_packet["skill_routing"]["selected"][0].pop("native_usage_required", None)
            runtime_input_packet["skill_routing"]["selected"][0]["usage_required"] = True
            runtime_input_packet_path.write_text(
                json.dumps(runtime_input_packet, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            execution_payload = run_plan_execute(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=execution_plan_path,
                runtime_input_packet_path=runtime_input_packet_path,
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            execution_receipt = load_json(execution_payload["receipt_path"])
            execution_manifest = load_json(execution_receipt["execution_manifest_path"])

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            selected_units = [
                unit
                for unit in list(specialist_accounting["specialist_dispatch_outcomes"])
                if str(unit.get("skill_id")) == selected_skill_id
            ]
            self.assertGreaterEqual(len(selected_units), 1)

            result = load_json(selected_units[0]["result_path"])
            self.assertFalse(bool(result["live_native_execution"]))
            self.assertTrue(bool(result["verification_passed"]))
            self.assertTrue(bool(result["native_usage_required"]))
            self.assertTrue(bool(result["usage_required"]))
            self.assertTrue(bool(result["direct_route"]))
            self.assertEqual("direct_current_session_route", result["execution_driver"])

    def test_specialist_binding_metadata_is_frozen_into_runtime_requirement_and_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=DEBUG_EXECUTION_TASK,
                artifact_root=Path(tempdir),
                governance_scope="root",
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            requirement_doc = Path(summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            approved_dispatch = list(runtime_input["skill_routing"]["selected"])
            self.assertGreaterEqual(len(approved_dispatch), 1)

            dispatch = approved_dispatch[0]
            for field in (
                "binding_profile",
                "dispatch_phase",
                "execution_priority",
                "lane_policy",
                "parallelizable_in_root_xl",
                "write_scope",
                "review_mode",
            ):
                with self.subTest(field=field):
                    self.assertIn(field, dispatch)

            self.assertIn("## Selected Skill", requirement_doc)
            self.assertIn("Binding: profile=", requirement_doc)
            self.assertNotIn("## Specialist Consultation", execution_plan)
            self.assertIn("## Binary Skill Usage Plan", execution_plan)
            self.assertIn("## Skill Routing And Usage Evidence", execution_plan)
            self.assertIn("Binding profile:", execution_plan)

            specialist_phase_bindings = execution_manifest["execution_topology"]["specialist_phase_bindings"]
            self.assertIsNotNone(specialist_phase_bindings)
            self.assertGreaterEqual(
                sum(len(list(specialist_phase_bindings.get(phase) or [])) for phase in specialist_phase_bindings),
                len(approved_dispatch),
            )

    def test_plan_shadow_recognizes_specialist_lifecycle_headers_without_legacy_dispatch_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_fake_codex_command(artifact_root)
            payload = run_runtime(
                task="I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
                artifact_root=artifact_root,
                governance_scope="root",
            )
            summary = payload["summary"]
            requirement_doc_path = Path(summary["artifacts"]["requirement_doc"])
            execution_plan_path = Path(summary["artifacts"]["execution_plan"])
            runtime_input_packet_path = Path(summary["artifacts"]["runtime_input_packet"])

            execution_plan = execution_plan_path.read_text(encoding="utf-8")
            self.assertIn("## Specialist Skill Dispatch Plan", execution_plan)
            self.assertNotIn("## Specialist Consultation", execution_plan)
            self.assertIn("## Binary Skill Usage Plan", execution_plan)
            self.assertIn("## Skill Routing And Usage Evidence", execution_plan)
            rewritten_plan = (
                execution_plan.replace(
                    "## Skill Routing And Usage Evidence",
                    "## Lifecycle Notes",
                    1,
                )
                .replace(
                    "## Specialist Skill Dispatch Plan",
                    "## Skill Routing And Usage Evidence",
                    1,
                )
            )
            self.assertEqual(1, rewritten_plan.count("## Skill Routing And Usage Evidence"))
            self.assertNotIn("## Specialist Skill Dispatch Plan", rewritten_plan)
            self.assertNotIn("## Specialist Consultation", rewritten_plan)
            execution_plan_path.write_text(
                rewritten_plan,
                encoding="utf-8",
            )

            execution_payload = run_plan_execute(
                task="I have a failing test and a stack trace. Help me debug systematically before proposing fixes.",
                artifact_root=artifact_root,
                requirement_doc_path=requirement_doc_path,
                execution_plan_path=execution_plan_path,
                runtime_input_packet_path=runtime_input_packet_path,
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            execution_manifest = load_json(execution_payload["execution_manifest_path"])
            plan_shadow = load_json(execution_manifest["plan_shadow"]["path"])

            specialist_units = [
                unit
                for unit in plan_shadow["units"]
                if unit["classification"] == "specialist_dispatch_unit"
            ]

            self.assertGreaterEqual(len(specialist_units), 1)
            self.assertEqual(
                {"Skill Routing And Usage Evidence"},
                {unit["source_section"] for unit in specialist_units},
            )
            self.assertGreaterEqual(execution_manifest["plan_shadow"]["candidate_unit_count"], 1)

    def test_l_grade_requires_native_serial_child_lane_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=Path(tempdir),
                governance_scope="root",
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual("L", execution_manifest["internal_grade"])
            self.assertIn("execution_topology", execution_manifest)

            topology = execution_manifest["execution_topology"]
            self.assertEqual("serial_child_lanes", topology["delegation_mode"])
            self.assertEqual("sequential", topology["wave_execution"])
            self.assertEqual("sequential", topology["step_execution"])
            self.assertEqual("sequential", topology["unit_execution"])
            self.assertEqual(1, int(topology["max_parallel_units"]))
            self.assertGreaterEqual(int(topology["child_lane_unit_count"]), 1)
            self.assertEqual(0, int(topology["parallel_units_executed_count"]))
            self.assertIn("two_stage_review", topology)
            self.assertTrue(bool(topology["two_stage_review"]["enabled"]))
            self.assertEqual([], list(topology.get("parallel_executed_unit_ids") or []))

            executed_units = collect_wave_units(execution_manifest)
            self.assertEqual(int(execution_manifest["executed_unit_count"]), len(executed_units))
            self.assertGreaterEqual(len(executed_units), 1)
            for unit in executed_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    result = load_unit_result(unit)
                    self.assertEqual(0, int(result["exit_code"]))
                    self.assertTrue(Path(result["stdout_path"]).exists())
                    self.assertTrue(Path(result["stderr_path"]).exists())
                    if result["kind"] == "specialist_dispatch":
                        self.assertEqual("completed", result["status"])
                        self.assertTrue(bool(result["verification_passed"]))
                        self.assertFalse(bool(result["degraded"]))
                        self.assertFalse(bool(result["live_native_execution"]))
                        self.assertEqual("direct_current_session_route", result["execution_driver"])
                        self.assertTrue(bool(result["direct_route"]))
                    else:
                        self.assertEqual("completed", result["status"])
                        self.assertTrue(bool(result["verification_passed"]))

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)

            serial_order = list(topology.get("serial_execution_order") or [])
            self.assertEqual(
                [str(unit["unit_id"]) for unit in executed_units],
                [str(unit_id) for unit_id in serial_order],
            )

    def test_xl_grade_requires_selective_parallel_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=IMPLEMENTATION_EXECUTION_TASK,
                artifact_root=Path(tempdir),
                governance_scope="root",
                requested_grade_floor="XL",
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual("XL", execution_manifest["internal_grade"])
            self.assertIn("execution_topology", execution_manifest)

            topology = execution_manifest["execution_topology"]
            self.assertEqual("selective_parallel_child_lanes", topology["delegation_mode"])
            self.assertEqual("sequential", topology["wave_execution"])
            self.assertEqual("sequential", topology["step_execution"])
            self.assertIn(topology["unit_execution"], ("bounded_parallel", "mixed"))
            self.assertGreaterEqual(int(topology["max_parallel_units"]), 2)
            self.assertGreaterEqual(int(topology["parallel_candidate_unit_count"]), 1)
            self.assertGreaterEqual(int(topology["parallel_units_executed_count"]), 1)
            self.assertGreaterEqual(
                int(execution_manifest["executed_unit_count"]),
                int(topology["parallel_units_executed_count"]),
            )

            executed_units = collect_wave_units(execution_manifest)
            self.assertEqual(int(execution_manifest["executed_unit_count"]), len(executed_units))
            executed_by_id = {str(unit["unit_id"]): unit for unit in executed_units}
            parallel_unit_ids = [str(unit_id) for unit_id in list(topology.get("parallel_executed_unit_ids") or [])]
            self.assertGreaterEqual(len(parallel_unit_ids), int(topology["parallel_units_executed_count"]))
            for unit_id in parallel_unit_ids:
                with self.subTest(parallel_unit_id=unit_id):
                    self.assertIn(unit_id, executed_by_id)

            parallel_windows = list(topology.get("parallel_execution_windows") or [])
            self.assertGreaterEqual(len(parallel_windows), 1)
            self.assertTrue(any(len(list(window.get("unit_ids") or [])) >= 2 for window in parallel_windows))
            for window in parallel_windows:
                window_unit_ids = [str(unit_id) for unit_id in list(window.get("unit_ids") or [])]
                if not window_unit_ids:
                    continue
                spans: list[tuple[datetime, datetime]] = []
                window_results: list[dict[str, object]] = []
                for unit_id in window_unit_ids:
                    with self.subTest(window_unit_id=unit_id):
                        self.assertIn(unit_id, executed_by_id)
                        result = load_unit_result(executed_by_id[unit_id])
                        self.assertEqual("completed", result["status"])
                        self.assertEqual(0, int(result["exit_code"]))
                        self.assertTrue(bool(result["verification_passed"]))
                        self.assertTrue(Path(result["stdout_path"]).exists())
                        self.assertTrue(Path(result["stderr_path"]).exists())
                        window_results.append(result)
                        spans.append(
                            (
                                parse_utc_timestamp(str(result["started_at"])),
                                parse_utc_timestamp(str(result["finished_at"])),
                            )
                        )
                # Direct current-session specialist routes are grouped as bounded-parallel
                # windows for topology accounting, but they do not claim wall-clock overlap.
                if len(spans) >= 2 and not all(bool(result.get("direct_route")) for result in window_results):
                    latest_start = max(start for start, _ in spans)
                    earliest_finish = min(finish for _, finish in spans)
                    self.assertLess(latest_start, earliest_finish)

    def test_approved_specialist_dispatch_requires_executable_native_units(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=DEBUG_SPECIALIST_TASK,
                artifact_root=Path(tempdir),
                governance_scope="root",
                extra_env={
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])

            approved_dispatch = current_selected_dispatch(runtime_input)
            self.assertGreaterEqual(len(approved_dispatch), 1)

            self.assertIn("specialist_accounting", execution_manifest)
            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertIn("skill_execution_unit_count", specialist_accounting)
            self.assertIn("execution_skill_outcome_count", specialist_accounting)
            self.assertIn("execution_skill_outcomes", specialist_accounting)
            self.assertEqual(
                int(specialist_accounting["dispatch_unit_count"]),
                int(specialist_accounting["skill_execution_unit_count"]),
            )
            self.assertEqual(
                len(list(specialist_accounting["specialist_dispatch_outcomes"])),
                len(list(specialist_accounting["execution_skill_outcomes"])),
            )
            self.assertEqual(
                int(specialist_accounting["execution_skill_outcome_count"]),
                len(list(specialist_accounting["execution_skill_outcomes"])),
            )
            self.assertEqual("native_bounded_units", specialist_accounting["execution_mode"])
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
            self.assertEqual("completed", execution_manifest["status"])
            self.assertEqual(0, int(execution_manifest["failed_unit_count"]))

            routed_units = list(specialist_accounting["direct_routed_specialist_units"])
            self.assertGreaterEqual(len(routed_units), 1)
            for unit in routed_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertTrue(bool(unit["verification_passed"]))
                    self.assertFalse(bool(unit["degraded"]))
                    self.assertFalse(bool(unit["live_native_execution"]))
                    self.assertTrue(Path(unit["result_path"]).exists())
                    self.assertIn("skill_id", unit)
                    self.assertNotEqual("", str(unit["skill_id"]).strip())
                    result = load_json(unit["result_path"])
                    self.assertEqual("completed", result["status"])
                    self.assertEqual(0, int(result["exit_code"]))
                    self.assertTrue(bool(result["verification_passed"]))
                    self.assertEqual("direct_current_session_route", result["execution_driver"])
                    self.assertFalse(bool(result["degraded"]))
                    self.assertFalse(bool(result["live_native_execution"]))
                    self.assertTrue(bool(result["direct_route"]))
                    self.assertTrue(Path(result["stdout_path"]).exists())
                    self.assertTrue(Path(result["stderr_path"]).exists())

    def test_approved_specialist_dispatch_routes_directly_in_current_session_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            payload = run_runtime(
                task=DEBUG_SPECIALIST_TASK,
                artifact_root=temp_path,
                governance_scope="root",
                extra_env={
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "",
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("native_bounded_units", specialist_accounting["execution_mode"])
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
            self.assertEqual("completed", execution_manifest["status"])

            routed_units = list(specialist_accounting["direct_routed_specialist_units"])
            self.assertGreaterEqual(len(routed_units), 1)
            for unit in routed_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertTrue(bool(unit["verification_passed"]))
                    self.assertFalse(bool(unit["degraded"]))
                    self.assertFalse(bool(unit["live_native_execution"]))
                    self.assertEqual("direct_current_session_route", unit["execution_driver"])
                    result = load_json(unit["result_path"])
                    self.assertEqual("completed", result["status"])
                    self.assertTrue(bool(result["verification_passed"]))
                    self.assertTrue(bool(result["direct_route"]))
                    self.assertEqual("direct_current_session_route", result["execution_driver"])
                    self.assertFalse(bool(result["live_native_execution"]))
                    self.assertFalse(bool(result.get("host_adapter_id")))
                    self.assertFalse(bool(result["degraded"]))
                    self.assertFalse(bool(result["blocked"]))
                    self.assertFalse(bool(result.get("prompt_path")))

    def test_approved_specialist_dispatch_can_execute_live_native_lane_when_adapter_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_fake_codex_command(
                temp_path,
                required_prompt_markers=[
                    "native_skill_entrypoint:",
                    "skill_root:",
                    "usage_required: true",
                    "must_preserve_workflow: true",
                ],
            )
            payload = run_runtime(
                task=DEBUG_SPECIALIST_TASK,
                artifact_root=temp_path,
                governance_scope="root",
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("native_bounded_units", specialist_accounting["execution_mode"])
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
            self.assertEqual("completed", execution_manifest["status"])

            routed_units = list(specialist_accounting["direct_routed_specialist_units"])
            self.assertGreaterEqual(len(routed_units), 1)
            for unit in routed_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertTrue(bool(unit["verification_passed"]))
                    self.assertFalse(bool(unit["degraded"]))
                    self.assertFalse(bool(unit["live_native_execution"]))
                    self.assertEqual("direct_current_session_route", unit["execution_driver"])
                    self.assertTrue(Path(unit["result_path"]).exists())
                    result = load_json(unit["result_path"])
                    self.assertEqual("completed", result["status"])
                    self.assertEqual(0, int(result["exit_code"]))
                    self.assertTrue(bool(result["verification_passed"]))
                    self.assertFalse(bool(result["live_native_execution"]))
                    self.assertFalse(bool(result["degraded"]))
                    self.assertEqual("direct_current_session_route", result["execution_driver"])
                    self.assertTrue(bool(result["direct_route"]))
                    self.assertFalse(bool(result.get("host_adapter_id")))
                    self.assertFalse(bool(result.get("prompt_path")))
                    self.assertTrue(Path(result["stdout_path"]).exists())
                    self.assertTrue(Path(result["stderr_path"]).exists())
                    self.assertTrue(bool(result["native_skill_entrypoint"]))
                    self.assertTrue(bool(result["skill_root"]))
                    self.assertEqual(result["native_skill_entrypoint"], result["direct_route_entrypoint"])

    def test_path_resolved_specialist_prompt_uses_entrypoint_and_root_as_source_of_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_fake_codex_command(temp_path)
            payload = run_runtime(
                task=(
                    "Analyze biological sequences with Python, draft a scientific report, "
                    "and prepare the execution planning notes."
                ),
                artifact_root=temp_path,
                governance_scope="root",
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            specialist_outcomes = list(execution_manifest["specialist_accounting"]["specialist_dispatch_outcomes"])
            self.assertGreaterEqual(len(specialist_outcomes), 1)

            path_resolved_prompt_verified = False
            for unit in specialist_outcomes:
                result = load_json(unit["result_path"])
                if bool(result.get("blocked")) or bool(result.get("degraded")):
                    continue
                dispatch = next(
                    (
                        entry
                        for entry in execution_manifest["specialist_accounting"]["approved_dispatch"]
                        if str(entry.get("skill_id", "")).strip() == str(result["specialist_skill_id"]).strip()
                    ),
                    None,
                )
                self.assertIsNotNone(dispatch)
                native_entrypoint = str((dispatch or {}).get("native_skill_entrypoint") or "").strip()
                normalized_entrypoint = native_entrypoint.replace("\\", "/")
                if "/bundled/skills/" not in normalized_entrypoint:
                    continue
                skill_root = str((dispatch or {}).get("skill_root") or "").strip()
                self.assertTrue(skill_root)
                self.assertEqual(native_entrypoint, str(result.get("native_skill_entrypoint") or "").strip())
                self.assertEqual(skill_root, str(result.get("skill_root") or "").strip())
                self.assertEqual(native_entrypoint, str(result.get("direct_route_entrypoint") or "").strip())
                self.assertFalse(bool(result.get("prompt_path")))
                self.assertIn(
                    f"native_skill_entrypoint:{native_entrypoint}",
                    "".join(str(note) for note in list(result.get("verification_notes") or [])),
                )
                path_resolved_prompt_verified = True

            self.assertTrue(path_resolved_prompt_verified)

    def test_child_escalation_remains_advisory_and_blocks_unapproved_specialist_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            composite_task = (
                "Analyze biological sequences with Python, draft a scientific report, "
                "and prepare the execution planning notes."
            )
            root_payload = run_runtime(
                task=composite_task,
                artifact_root=artifact_root,
                governance_scope="root",
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_approved_dispatch = current_selected_dispatch(root_runtime_input)
            approved_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_approved_dispatch
                if str(item.get("skill_id", "")).strip()
            ]
            if not approved_skill_ids:
                self.skipTest("Root run did not expose approved specialist dispatch skill ids")

            parent_unit_id = "pytest-child-topology-unit"
            child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
            child_payload = run_runtime(
                task=composite_task + " Child lane requests extra specialist help beyond approved dispatch.",
                artifact_root=artifact_root,
                run_id=child_run_id,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id=parent_unit_id,
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                approved_specialist_skill_ids=approved_skill_ids[:1],
            )
            child_summary = child_payload["summary"]
            child_runtime_input = load_json(child_summary["artifacts"]["runtime_input_packet"])
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

            specialist_accounting = child_execution_manifest["specialist_accounting"]
            approved_child_dispatch = list(specialist_accounting["approved_dispatch"])
            approved_child_ids = {
                str(entry.get("skill_id", "")).strip() for entry in approved_child_dispatch if str(entry.get("skill_id", "")).strip()
            }
            self.assertEqual(1, int(specialist_accounting["frozen_approved_dispatch_count"]))
            self.assertTrue(set(approved_skill_ids[:1]).issubset(approved_child_ids))
            self.assertEqual(int(specialist_accounting["approved_dispatch_count"]), len(approved_child_ids))
            self.assertLessEqual(
                int(specialist_accounting["executed_specialist_unit_count"]),
                int(specialist_accounting["approved_dispatch_count"]),
            )
            self.assertGreaterEqual(int(specialist_accounting["degraded_specialist_unit_count"]), 0)
            auto_absorb_gate = specialist_accounting["auto_absorb_gate"]
            self.assertFalse(bool(auto_absorb_gate["enabled"]))
            self.assertEqual([], list(auto_absorb_gate.get("auto_approved_skill_ids") or []))

            specialist_outcomes = list(specialist_accounting["specialist_dispatch_outcomes"])
            for unit in specialist_outcomes:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertIn(str(unit["skill_id"]), approved_child_ids)
                    self.assertTrue(Path(unit["result_path"]).exists())
                    result = load_json(unit["result_path"])
                    self.assertIn(
                        str(result["status"]),
                        {"completed", "degraded_non_authoritative"},
                    )

            escalation_request_path = specialist_accounting.get("escalation_request_path")
            if specialist_accounting["local_suggestion_count"]:
                self.assertTrue(escalation_request_path)
                self.assertTrue(Path(escalation_request_path).exists())
            else:
                self.assertFalse(bool(escalation_request_path))
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

            child_session_root = Path(child_payload["session_root"])
            specialist_result_files = list(child_session_root.glob("execution-results/*specialist*.json"))
            self.assertLessEqual(len(specialist_result_files), len(specialist_outcomes))

    def test_child_auto_absorb_can_fallback_to_root_escalation_when_gate_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            composite_task = (
                "Analyze biological sequences with Python, draft a scientific report, "
                "and prepare the execution planning notes."
            )
            root_payload = run_runtime(
                task=composite_task,
                artifact_root=artifact_root,
                governance_scope="root",
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_approved_dispatch = current_selected_dispatch(root_runtime_input)
            approved_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_approved_dispatch
                if str(item.get("skill_id", "")).strip()
            ]
            if len(approved_skill_ids) < 1:
                self.skipTest("Root run did not expose approved specialist dispatch skill ids")

            parent_unit_id = "pytest-child-topology-fallback-unit"
            child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
            child_payload = run_runtime(
                task=composite_task + " Child lane requests extra specialist help beyond approved dispatch.",
                artifact_root=artifact_root,
                run_id=child_run_id,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id=parent_unit_id,
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                approved_specialist_skill_ids=approved_skill_ids[:1],
                extra_env={"VGO_DISABLE_CHILD_SPECIALIST_AUTO_ABSORB": "1"},
            )
            child_summary = child_payload["summary"]
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

            specialist_accounting = child_execution_manifest["specialist_accounting"]
            approved_child_ids = {
                str(entry.get("skill_id", "")).strip()
                for entry in list(specialist_accounting["approved_dispatch"])
                if str(entry.get("skill_id", "")).strip()
            }
            self.assertEqual(set(approved_skill_ids[:1]), approved_child_ids)
            self.assertEqual(0, int(specialist_accounting["local_suggestion_count"]))
            self.assertFalse(bool(specialist_accounting["escalation_required"]))
            self.assertFalse(bool(specialist_accounting.get("escalation_request_path")))
            self.assertFalse(bool(specialist_accounting["auto_absorb_gate"]["enabled"]))
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_child_auto_absorbed_specialist_dispatch_can_execute_live_native_lane_when_adapter_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_fake_codex_command(temp_path)
            composite_task = (
                "Analyze biological sequences with Python, draft a scientific report, "
                "and prepare the execution planning notes."
            )
            root_payload = run_runtime(
                task=composite_task,
                artifact_root=temp_path,
                governance_scope="root",
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_approved_dispatch = current_selected_dispatch(root_runtime_input)
            approved_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_approved_dispatch
                if str(item.get("skill_id", "")).strip()
            ]
            if len(approved_skill_ids) < 1:
                self.skipTest("Root run did not expose approved specialist dispatch skill ids")

            parent_unit_id = "pytest-child-topology-live-native-unit"
            child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
            child_payload = run_runtime(
                task=composite_task + " Child lane requests extra specialist help beyond approved dispatch.",
                artifact_root=temp_path,
                run_id=child_run_id,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id=parent_unit_id,
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                approved_specialist_skill_ids=approved_skill_ids[:1],
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            child_summary = child_payload["summary"]
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

            specialist_accounting = child_execution_manifest["specialist_accounting"]
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertEqual(0, int(specialist_accounting["auto_approved_dispatch_count"]))
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))
            self.assertFalse(bool(specialist_accounting["auto_absorb_gate"]["enabled"]))

    def test_child_divergent_specialist_request_without_overlap_auto_promotes_when_safe(self) -> None:
        cases = [
            (
                "L",
                IMPLEMENTATION_EXECUTION_TASK,
                "serial_child_lanes",
                "",
            ),
            (
                "XL",
                IMPLEMENTATION_EXECUTION_TASK,
                "selective_parallel_child_lanes",
                "XL",
            ),
        ]

        for expected_grade, root_task, expected_delegation_mode, requested_grade_floor in cases:
            with self.subTest(expected_grade=expected_grade):
                with tempfile.TemporaryDirectory() as tempdir:
                    artifact_root = Path(tempdir)
                    root_payload = run_runtime(
                        task=root_task,
                        artifact_root=artifact_root,
                        governance_scope="root",
                        requested_grade_floor=requested_grade_floor,
                    )
                    root_summary = root_payload["summary"]
                    parent_unit_id = f"pytest-{expected_grade.lower()}-divergent-child-unit"
                    child_run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
                    child_payload = run_runtime(
                        task=root_task + " Child lane divergence into a new specialist demand set.",
                        artifact_root=artifact_root,
                        run_id=child_run_id,
                        governance_scope="child",
                        root_run_id=str(root_summary["run_id"]),
                        parent_run_id=str(root_summary["run_id"]),
                        parent_unit_id=parent_unit_id,
                        inherited_requirement_doc_path=Path(root_summary["artifacts"]["requirement_doc"]),
                        inherited_execution_plan_path=Path(root_summary["artifacts"]["execution_plan"]),
                        approved_specialist_skill_ids=["totally-non-overlap-skill-id"],
                        requested_grade_floor=requested_grade_floor,
                    )

                    child_summary = child_payload["summary"]
                    child_runtime_input = load_json(child_summary["artifacts"]["runtime_input_packet"])
                    child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

                    self.assertEqual(expected_grade, child_execution_manifest["internal_grade"])
                    self.assertEqual(
                        expected_delegation_mode,
                        child_execution_manifest["execution_topology"]["delegation_mode"],
                    )

                    self.assertNotIn("specialist_dispatch", child_runtime_input)
                    child_selected_ids = {
                        str(entry.get("skill_id", "")).strip()
                        for entry in current_selected_dispatch(child_runtime_input)
                        if str(entry.get("skill_id", "")).strip()
                    }
                    self.assertGreaterEqual(len(child_selected_ids), 1)

                    specialist_accounting = child_execution_manifest["specialist_accounting"]
                    self.assertGreaterEqual(int(specialist_accounting["approved_dispatch_count"]), 1)
                    self.assertGreaterEqual(int(specialist_accounting["specialist_skill_count"]), 1)
                    self.assertFalse(bool(specialist_accounting["escalation_required"]))
                    self.assertGreaterEqual(len(list(specialist_accounting["specialist_dispatch_outcomes"])), 1)
                    self.assertEqual("completed_local_scope", child_execution_manifest["status"])
                    self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_xl_can_build_specialist_steps_from_current_selected_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            fake_bin_dir = Path(tempdir) / "fake-bin"
            fake_bin_dir.mkdir(parents=True, exist_ok=True)
            fake_codex = create_fake_codex_command(fake_bin_dir)

            payload = run_runtime(
                task=(
                    "Run an XL multi-agent wave to draft a scientific manuscript, prepare scientific "
                    "reporting artifacts, and publish-ready writing deliverables with independent lanes "
                    "and staged verification."
                ),
                artifact_root=Path(tempdir),
                governance_scope="root",
                extra_env={
                    "PATH": str(fake_bin_dir) + os.pathsep + os.environ.get("PATH", ""),
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            topology_steps = collect_topology_steps(execution_manifest)
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertEqual("XL", execution_manifest["internal_grade"])
            self.assertGreaterEqual(int(specialist_accounting["approved_dispatch_count"]), 1)
            self.assertGreaterEqual(
                int(specialist_accounting["phase_binding_counts"]["post_execution"]),
                1,
            )

            specialist_steps = [
                step
                for step in topology_steps
                if "specialist-" in str(step.get("step_id", ""))
            ]
            self.assertGreaterEqual(len(specialist_steps), 1)
            self.assertTrue(
                any(len(list(step.get("units") or [])) >= 1 for step in specialist_steps)
            )

    def test_runtime_packaging_uses_canonical_sources_and_install_only_generated_compatibility(self) -> None:
        governance = json.loads((REPO_ROOT / "config" / "version-governance.json").read_text(encoding="utf-8"))
        generated_compat = governance["packaging"]["generated_compatibility"]["nested_runtime_root"]
        canonical_runtime_root = REPO_ROOT / "scripts" / "runtime"
        bundled_runtime_roots = [
            REPO_ROOT / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
            REPO_ROOT / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
        ]

        self.assertEqual("bundled/skills/vibe", generated_compat["relative_path"])
        self.assertEqual("install_only", generated_compat["materialization_mode"])
        self.assertTrue(canonical_runtime_root.exists())
        for bundled_runtime in bundled_runtime_roots:
            with self.subTest(bundled_runtime=str(bundled_runtime)):
                self.assertFalse(bundled_runtime.exists())


if __name__ == "__main__":
    unittest.main()
