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
    mode: str = "benchmark_autonomous",
    script_relative_path: str = "scripts/runtime/invoke-vibe-runtime.ps1",
    governance_scope: str = "root",
    root_run_id: str = "",
    parent_run_id: str = "",
    parent_unit_id: str = "",
    inherited_requirement_doc_path: Path | None = None,
    inherited_execution_plan_path: Path | None = None,
    approved_specialist_skill_ids: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / script_relative_path
    run_id = "pytest-topology-" + uuid.uuid4().hex[:10]
    approved = approved_specialist_skill_ids or []
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
            f"-RunId '{run_id}' "
            f"{root_segment}"
            f"{parent_segment}"
            f"{parent_unit_segment}"
            f"{inherited_requirement}"
            f"{inherited_plan}"
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
        env={**os.environ, **(extra_env or {})},
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect_wave_units(execution_manifest: dict[str, object]) -> list[dict[str, object]]:
    units: list[dict[str, object]] = []
    for wave in list(execution_manifest.get("waves") or []):
        units.extend(list((wave or {}).get("units") or []))
    return units


def load_unit_result(unit: dict[str, object]) -> dict[str, object]:
    return load_json(unit["result_path"])


def create_fake_codex_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex{suffix}"
    if os.name == "nt":
        command_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
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
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}\r\n"
            "echo fake codex ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        command_path.write_text(
            "#!/usr/bin/env sh\n"
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
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}' > \"$OUT\"\n"
            "printf 'fake codex ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


class NativeExecutionTopologyTests(unittest.TestCase):
    def test_l_grade_requires_native_serial_child_lane_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="Design architecture migration with staged review and planning gates.",
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
                        self.assertEqual("degraded_non_authoritative", result["status"])
                        self.assertFalse(bool(result["verification_passed"]))
                        self.assertTrue(bool(result["degraded"]))
                        self.assertFalse(bool(result["live_native_execution"]))
                    else:
                        self.assertEqual("completed", result["status"])
                        self.assertTrue(bool(result["verification_passed"]))

            serial_order = list(topology.get("serial_execution_order") or [])
            self.assertEqual(
                [str(unit["unit_id"]) for unit in executed_units],
                [str(unit_id) for unit_id in serial_order],
            )

    def test_xl_grade_requires_selective_parallel_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task=(
                    "Run an XL multi-agent wave with parallelizable independent units, "
                    "then reconcile in sequence."
                ),
                artifact_root=Path(tempdir),
                governance_scope="root",
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
                for unit_id in window_unit_ids:
                    with self.subTest(window_unit_id=unit_id):
                        self.assertIn(unit_id, executed_by_id)
                        result = load_unit_result(executed_by_id[unit_id])
                        self.assertEqual("completed", result["status"])
                        self.assertEqual(0, int(result["exit_code"]))
                        self.assertTrue(bool(result["verification_passed"]))
                        self.assertTrue(Path(result["stdout_path"]).exists())
                        self.assertTrue(Path(result["stderr_path"]).exists())
                        spans.append(
                            (
                                parse_utc_timestamp(str(result["started_at"])),
                                parse_utc_timestamp(str(result["finished_at"])),
                            )
                        )
                if len(spans) >= 2:
                    latest_start = max(start for start, _ in spans)
                    earliest_finish = min(finish for _, finish in spans)
                    self.assertLess(latest_start, earliest_finish)

    def test_approved_specialist_dispatch_requires_executable_native_units(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                task="I have a failing test and stack trace. Debug systematically and execute specialist workflow.",
                artifact_root=Path(tempdir),
                governance_scope="root",
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])

            approved_dispatch = list(
                (runtime_input.get("specialist_dispatch") or {}).get("approved_dispatch") or []
            )
            self.assertGreaterEqual(len(approved_dispatch), 1)

            self.assertIn("specialist_accounting", execution_manifest)
            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("native_bounded_units", specialist_accounting["execution_mode"])
            self.assertEqual("explicitly_degraded", specialist_accounting["effective_execution_status"])
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertGreaterEqual(int(specialist_accounting["degraded_specialist_unit_count"]), 1)
            self.assertEqual("completed_with_failures", execution_manifest["status"])
            self.assertGreaterEqual(int(execution_manifest["failed_unit_count"]), 1)

            degraded_units = list(specialist_accounting["degraded_specialist_units"])
            self.assertGreaterEqual(len(degraded_units), 1)
            for unit in degraded_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertFalse(bool(unit["verification_passed"]))
                    self.assertTrue(bool(unit["degraded"]))
                    self.assertFalse(bool(unit["live_native_execution"]))
                    self.assertTrue(Path(unit["result_path"]).exists())
                    self.assertIn("skill_id", unit)
                    self.assertNotEqual("", str(unit["skill_id"]).strip())
                    result = load_json(unit["result_path"])
                    self.assertEqual("degraded_non_authoritative", result["status"])
                    self.assertEqual(0, int(result["exit_code"]))
                    self.assertFalse(bool(result["verification_passed"]))
                    self.assertEqual("degraded_specialist_contract_receipt", result["execution_driver"])
                    self.assertTrue(bool(result["degraded"]))
                    self.assertFalse(bool(result["live_native_execution"]))
                    self.assertTrue(Path(result["stdout_path"]).exists())
                    self.assertTrue(Path(result["stderr_path"]).exists())

    def test_approved_specialist_dispatch_can_execute_live_native_lane_when_adapter_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_fake_codex_command(temp_path)
            payload = run_runtime(
                task="I have a failing test and stack trace. Debug systematically and execute specialist workflow.",
                artifact_root=temp_path,
                governance_scope="root",
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertEqual("native_bounded_units", specialist_accounting["execution_mode"])
            self.assertEqual("live_native_executed", specialist_accounting["effective_execution_status"])
            self.assertGreaterEqual(int(specialist_accounting["executed_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
            self.assertEqual("completed", execution_manifest["status"])

            executed_units = list(specialist_accounting["executed_specialist_units"])
            self.assertGreaterEqual(len(executed_units), 1)
            for unit in executed_units:
                with self.subTest(unit_id=unit.get("unit_id", "")):
                    self.assertTrue(bool(unit["verification_passed"]))
                    self.assertFalse(bool(unit["degraded"]))
                    self.assertTrue(bool(unit["live_native_execution"]))
                    self.assertEqual("codex_exec_native_specialist", unit["execution_driver"])
                    self.assertTrue(Path(unit["result_path"]).exists())
                    result = load_json(unit["result_path"])
                    self.assertEqual("completed", result["status"])
                    self.assertEqual(0, int(result["exit_code"]))
                    self.assertTrue(bool(result["verification_passed"]))
                    self.assertTrue(bool(result["live_native_execution"]))
                    self.assertFalse(bool(result["degraded"]))
                    self.assertEqual("codex_exec_native_specialist", result["execution_driver"])
                    self.assertEqual("codex", result["host_adapter_id"])
                    self.assertTrue(Path(result["response_json_path"]).exists())
                    self.assertTrue(Path(result["prompt_path"]).exists())
                    self.assertTrue(Path(result["schema_path"]).exists())
                    self.assertTrue(Path(result["git_status_before_path"]).exists())
                    self.assertTrue(Path(result["git_status_after_path"]).exists())
                    self.assertTrue(Path(result["stdout_path"]).exists())
                    self.assertTrue(Path(result["stderr_path"]).exists())

    def test_child_escalation_remains_advisory_and_blocks_unapproved_specialist_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            root_payload = run_runtime(
                task="Root run prepares specialist dispatch and child escalation baseline.",
                artifact_root=artifact_root,
                governance_scope="root",
            )
            root_summary = root_payload["summary"]
            root_artifacts = root_summary["artifacts"]
            root_runtime_input = load_json(root_artifacts["runtime_input_packet"])
            root_approved_dispatch = list(
                (root_runtime_input.get("specialist_dispatch") or {}).get("approved_dispatch") or []
            )
            approved_skill_ids = [
                str(item.get("skill_id", "")).strip()
                for item in root_approved_dispatch
                if str(item.get("skill_id", "")).strip()
            ]
            if not approved_skill_ids:
                self.skipTest("Root run did not expose approved specialist dispatch skill ids")

            child_payload = run_runtime(
                task="Child lane requests extra specialist help beyond approved dispatch.",
                artifact_root=artifact_root,
                governance_scope="child",
                root_run_id=str(root_summary["run_id"]),
                parent_run_id=str(root_summary["run_id"]),
                parent_unit_id="pytest-child-topology-unit",
                inherited_requirement_doc_path=Path(root_artifacts["requirement_doc"]),
                inherited_execution_plan_path=Path(root_artifacts["execution_plan"]),
                approved_specialist_skill_ids=approved_skill_ids[:1],
            )
            child_summary = child_payload["summary"]
            child_runtime_input = load_json(child_summary["artifacts"]["runtime_input_packet"])
            child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

            specialist_dispatch = child_runtime_input["specialist_dispatch"]
            self.assertEqual("advisory_until_root_approval", str(specialist_dispatch["status"]))
            self.assertTrue(bool(specialist_dispatch["escalation_required"]))
            self.assertEqual("root_approval_required", str(specialist_dispatch["escalation_status"]))

            specialist_accounting = child_execution_manifest["specialist_accounting"]
            approved_child_dispatch = list(specialist_accounting["approved_dispatch"])
            approved_child_ids = {
                str(entry.get("skill_id", "")).strip() for entry in approved_child_dispatch if str(entry.get("skill_id", "")).strip()
            }
            self.assertEqual(1, int(specialist_accounting["approved_dispatch_count"]))
            self.assertEqual(1, len(approved_child_ids))
            self.assertEqual(set(approved_skill_ids[:1]), approved_child_ids)
            self.assertLessEqual(
                int(specialist_accounting["executed_specialist_unit_count"]),
                int(specialist_accounting["approved_dispatch_count"]),
            )
            self.assertGreaterEqual(int(specialist_accounting["degraded_specialist_unit_count"]), 0)

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
            if escalation_request_path:
                self.assertTrue(Path(escalation_request_path).exists())
            self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

            child_session_root = Path(child_payload["session_root"])
            specialist_result_files = list(child_session_root.glob("execution-results/*specialist*.json"))
            self.assertLessEqual(len(specialist_result_files), len(specialist_outcomes))

    def test_child_divergent_specialist_request_without_overlap_escalates_without_crashing(self) -> None:
        cases = [
            (
                "L",
                "Design architecture migration with staged review and planning gates.",
                "serial_child_lanes",
            ),
            (
                "XL",
                "Run an XL multi-agent wave with parallelizable independent units, then reconcile in sequence.",
                "selective_parallel_child_lanes",
            ),
        ]

        for expected_grade, root_task, expected_delegation_mode in cases:
            with self.subTest(expected_grade=expected_grade):
                with tempfile.TemporaryDirectory() as tempdir:
                    artifact_root = Path(tempdir)
                    root_payload = run_runtime(
                        task=root_task,
                        artifact_root=artifact_root,
                        governance_scope="root",
                    )
                    root_summary = root_payload["summary"]

                    child_payload = run_runtime(
                        task=root_task + " Child lane divergence into a new specialist demand set.",
                        artifact_root=artifact_root,
                        governance_scope="child",
                        root_run_id=str(root_summary["run_id"]),
                        parent_run_id=str(root_summary["run_id"]),
                        parent_unit_id=f"pytest-{expected_grade.lower()}-divergent-child-unit",
                        inherited_requirement_doc_path=Path(root_summary["artifacts"]["requirement_doc"]),
                        inherited_execution_plan_path=Path(root_summary["artifacts"]["execution_plan"]),
                        approved_specialist_skill_ids=["totally-non-overlap-skill-id"],
                    )

                    child_summary = child_payload["summary"]
                    child_runtime_input = load_json(child_summary["artifacts"]["runtime_input_packet"])
                    child_execution_manifest = load_json(child_summary["artifacts"]["execution_manifest"])

                    self.assertEqual(expected_grade, child_execution_manifest["internal_grade"])
                    self.assertEqual(
                        expected_delegation_mode,
                        child_execution_manifest["execution_topology"]["delegation_mode"],
                    )

                    specialist_dispatch = child_runtime_input["specialist_dispatch"]
                    self.assertEqual([], list(specialist_dispatch["approved_dispatch"]))
                    self.assertEqual([], list(specialist_dispatch["approved_skill_ids"]))
                    self.assertGreaterEqual(len(list(specialist_dispatch["local_specialist_suggestions"])), 1)
                    self.assertTrue(bool(specialist_dispatch["escalation_required"]))
                    self.assertEqual("root_approval_required", str(specialist_dispatch["escalation_status"]))

                    specialist_accounting = child_execution_manifest["specialist_accounting"]
                    self.assertEqual(0, int(specialist_accounting["approved_dispatch_count"]))
                    self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
                    self.assertEqual(0, int(specialist_accounting["degraded_specialist_unit_count"]))
                    self.assertEqual(0, int(specialist_accounting["specialist_skill_count"]))
                    self.assertEqual([], list(specialist_accounting["specialist_dispatch_outcomes"]))
                    self.assertGreaterEqual(int(specialist_accounting["local_suggestion_count"]), 1)
                    self.assertTrue(bool(specialist_accounting["escalation_required"]))

                    escalation_request_path = specialist_accounting.get("escalation_request_path")
                    self.assertTrue(escalation_request_path)
                    self.assertTrue(Path(escalation_request_path).exists())
                    self.assertEqual("completed_local_scope", child_execution_manifest["status"])
                    self.assertFalse(bool(child_execution_manifest["authority"]["completion_claim_allowed"]))

    def test_bundled_runtime_mirror_matches_primary_runtime_sources(self) -> None:
        primary_runtime = REPO_ROOT / "scripts" / "runtime"
        bundled_runtime_roots = [
            REPO_ROOT / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
            REPO_ROOT / "bundled" / "skills" / "vibe" / "bundled" / "skills" / "vibe" / "scripts" / "runtime",
        ]

        primary_files = sorted(path.name for path in primary_runtime.glob("*.ps1"))
        self.assertGreaterEqual(len(primary_files), 1)

        for bundled_runtime in bundled_runtime_roots:
            with self.subTest(bundled_runtime=str(bundled_runtime)):
                bundled_files = sorted(path.name for path in bundled_runtime.glob("*.ps1"))
                self.assertEqual(primary_files, bundled_files)
                for file_name in primary_files:
                    self.assertEqual(
                        (primary_runtime / file_name).read_text(encoding="utf-8"),
                        (bundled_runtime / file_name).read_text(encoding="utf-8"),
                    )


if __name__ == "__main__":
    unittest.main()
