from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
PLANNING_TASK = "Create a PRD and backlog for a small feature with quality gate requirements $vibe"
DEBUG_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes. $vibe"
EXECUTION_TASK = "Implement a bounded runtime enhancement with verification and cleanup $vibe"
MEMORY_TASK_FIRST = "Record that hidden skill topology must stay under vibe and planner depends on this decision. $vibe"
MEMORY_TASK_SECOND = "Follow up on the hidden skill topology decision and recall planner dependency before proposing the next step. $vibe"
HOSTS = ("codex", "claude-code", "cursor", "windsurf", "openclaw", "opencode")
INSTALLED_RUNTIME_ADVISORY_FAILURE_UNITS = {
    "runtime-neutral-freshness-gate-tests",
    "version-consistency-gate",
}
HOST_BRIDGE_ENV = {
    "claude-code": "VGO_CLAUDE_CODE_SPECIALIST_BRIDGE_COMMAND",
    "cursor": "VGO_CURSOR_SPECIALIST_BRIDGE_COMMAND",
    "windsurf": "VGO_WINDSURF_SPECIALIST_BRIDGE_COMMAND",
    "openclaw": "VGO_OPENCLAW_SPECIALIST_BRIDGE_COMMAND",
    "opencode": "VGO_OPENCODE_SPECIALIST_BRIDGE_COMMAND",
}
HOST_HOME_ENV = {
    "codex": "CODEX_HOME",
    "claude-code": "CLAUDE_HOME",
    "cursor": "CURSOR_HOME",
    "windsurf": "WINDSURF_HOME",
    "openclaw": "OPENCLAW_HOME",
    "opencode": "OPENCODE_HOME",
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


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_fake_bridge(directory: Path, host_id: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    bridge_path = directory / f"{host_id}-bridge{suffix}"
    if os.name == "nt":
        bridge_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
            "set OUT=\r\n"
            ":loop\r\n"
            "if \"%~1\"==\"\" goto done\r\n"
            "if /I \"%~1\"==\"--output\" (\r\n"
            "  set OUT=%~2\r\n"
            "  shift\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "shift\r\n"
            "goto loop\r\n"
            ":done\r\n"
            "if \"%OUT%\"==\"\" exit /b 2\r\n"
            f"> \"%OUT%\" echo {{\"status\":\"completed\",\"summary\":\"{host_id} bridge executed specialist\",\"verification_notes\":[\"{host_id} simulated bridge ok\"],\"changed_files\":[],\"bounded_output_notes\":[\"{host_id} simulated host specialist\"]}}\r\n"
            f"echo {host_id} bridge ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        bridge_path.write_text(
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            "OUT=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    --output)\n"
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
            f"printf '%s' '{{\"status\":\"completed\",\"summary\":\"{host_id} bridge executed specialist\",\"verification_notes\":[\"{host_id} simulated bridge ok\"],\"changed_files\":[],\"bounded_output_notes\":[\"{host_id} simulated host specialist\"]}}' > \"$OUT\"\n"
            f"printf '{host_id} bridge ok\\n'\n",
            encoding="utf-8",
        )
        bridge_path.chmod(bridge_path.stat().st_mode | stat.S_IXUSR)
    return bridge_path


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
            "if /I \"%~1\"==\"-o\" (\r\n"
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


def install_host(target_root: Path, host_id: str, *, env: dict[str, str]) -> None:
    command = [
        "bash",
        str(INSTALL_SCRIPT),
        "--host",
        host_id,
        "--profile",
        "full",
        "--target-root",
        str(target_root),
    ]
    if host_id in HOST_BRIDGE_ENV:
        command.append("--require-closed-ready")
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


def run_installed_runtime(
    installed_root: Path,
    *,
    host_id: str,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-installed-host-{host_id}-{uuid.uuid4().hex[:8]}"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1'}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "installed invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


class InstalledHostRuntimeSimulationTests(unittest.TestCase):
    def _install_context(self, host_id: str) -> tuple[Path, Path, dict[str, str]]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        target_root = root / "target"
        bridge_root = root / "bridges"
        target_root.mkdir(parents=True, exist_ok=True)
        bridge_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env[HOST_HOME_ENV[host_id]] = str(target_root)
        fake_codex = create_fake_codex_command(bridge_root)
        env["VGO_CODEX_EXECUTABLE"] = str(fake_codex)
        if host_id in HOST_BRIDGE_ENV:
            bridge = create_fake_bridge(bridge_root, host_id)
            env[HOST_BRIDGE_ENV[host_id]] = str(bridge)
        install_host(target_root, host_id, env=env)
        installed_root = target_root / "skills" / "vibe"
        self.assertTrue(installed_root.exists(), host_id)
        return target_root, installed_root, env

    def _assert_common_governed_outputs(
        self,
        payload: dict[str, object],
        *,
        host_id: str,
        allowed_execution_statuses: set[str] | None = None,
    ) -> dict[str, object]:
        summary = payload["summary"]
        artifacts = summary["artifacts"]
        runtime_input = load_json(artifacts["runtime_input_packet"])
        cleanup = load_json(artifacts["cleanup_receipt"])
        execution_manifest = load_json(artifacts["execution_manifest"])

        self.assertEqual("vibe", runtime_input["authority_flags"]["explicit_runtime_skill"], host_id)
        self.assertEqual("vibe", runtime_input["route_snapshot"]["selected_skill"], host_id)
        self.assertTrue(Path(artifacts["requirement_doc"]).exists(), host_id)
        self.assertTrue(Path(artifacts["execution_plan"]).exists(), host_id)
        self.assertTrue(Path(artifacts["cleanup_receipt"]).exists(), host_id)
        allowed_statuses = allowed_execution_statuses or {"completed", "completed_with_failures"}
        self.assertIn(execution_manifest["status"], allowed_statuses, host_id)
        if execution_manifest["status"] == "completed_with_failures":
            failed_unit_ids = {
                str(unit["unit_id"])
                for wave in execution_manifest.get("waves") or []
                for unit in wave.get("units") or []
                if str(unit.get("status")) == "failed"
            }
            self.assertTrue(failed_unit_ids, host_id)
            self.assertTrue(
                failed_unit_ids.issubset(INSTALLED_RUNTIME_ADVISORY_FAILURE_UNITS),
                host_id,
            )
        self.assertIn(cleanup["cleanup_mode"], {"receipt_only", "bounded_cleanup_executed"}, host_id)
        return {
            "summary": summary,
            "artifacts": artifacts,
            "runtime_input": runtime_input,
            "cleanup": cleanup,
            "execution_manifest": execution_manifest,
        }

    def test_installed_hosts_support_high_fidelity_planning_debug_and_execution_tasks(self) -> None:
        for host_id in HOSTS:
            with self.subTest(host=host_id):
                target_root, installed_root, base_env = self._install_context(host_id)
                runtime_env = {
                    **base_env,
                    "VCO_HOST_ID": host_id,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                }

                planning = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=PLANNING_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-planning",
                    env=runtime_env,
                )
                planning_state = self._assert_common_governed_outputs(
                    planning,
                    host_id=host_id,
                    allowed_execution_statuses={"completed", "completed_with_failures"},
                )
                planning_requirement = Path(planning_state["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
                self.assertIn("## Runtime Input Truth", planning_requirement, host_id)
                self.assertIn("## Acceptance Criteria", planning_requirement, host_id)

                debug = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=DEBUG_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-debug",
                    env=runtime_env,
                )
                debug_state = self._assert_common_governed_outputs(debug, host_id=host_id)
                specialist_ids = [item["skill_id"] for item in debug_state["runtime_input"]["specialist_recommendations"]]
                self.assertIn("systematic-debugging", specialist_ids, host_id)
                self.assertGreaterEqual(
                    debug_state["execution_manifest"]["specialist_accounting"]["recommendation_count"],
                    1,
                    host_id,
                )
                if host_id == "codex" or host_id in HOST_BRIDGE_ENV:
                    self.assertEqual(
                        "live_native_executed",
                        debug_state["execution_manifest"]["specialist_accounting"]["effective_execution_status"],
                        host_id,
                    )
                    self.assertGreaterEqual(
                        int(debug_state["execution_manifest"]["specialist_accounting"]["executed_specialist_unit_count"]),
                        1,
                        host_id,
                    )

                execution = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=EXECUTION_TASK,
                    artifact_root=target_root / ".vibeskills" / "simulated-execution",
                    env=runtime_env,
                )
                execution_state = self._assert_common_governed_outputs(execution, host_id=host_id)
                execute_receipt = load_json(execution_state["artifacts"]["execute_receipt"])
                self.assertGreaterEqual(int(execute_receipt["executed_unit_count"]), 1, host_id)
                self.assertTrue(Path(execute_receipt["plan_shadow_path"]).exists(), host_id)

    def test_installed_hosts_support_high_fidelity_memory_continuity(self) -> None:
        for host_id in HOSTS:
            with self.subTest(host=host_id):
                target_root, installed_root, base_env = self._install_context(host_id)
                backend_root = target_root / ".vibeskills" / "memory-backend"
                runtime_env = {
                    **base_env,
                    "VCO_HOST_ID": host_id,
                    "SERENA_PROJECT_KEY": f"pytest-installed-{host_id}",
                    "VIBE_MEMORY_BACKEND_ROOT": str(backend_root),
                }

                first = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=MEMORY_TASK_FIRST,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-1",
                    env=runtime_env,
                )
                first_report = load_json(first["summary"]["artifacts"]["memory_activation_report"])
                self.assertGreaterEqual(len(first_report["stages"]), 5, host_id)
                self.assertTrue(first_report["stages"][4]["write_actions"], host_id)
                self.assertIn(
                    first_report["stages"][4]["write_actions"][0]["status"],
                    {"fallback_local_artifact", "backend_write"},
                    host_id,
                )

                second = run_installed_runtime(
                    installed_root,
                    host_id=host_id,
                    task=MEMORY_TASK_SECOND,
                    artifact_root=target_root / ".vibeskills" / "simulated-memory-run-2",
                    env=runtime_env,
                )
                second_summary = second["summary"]
                second_report = load_json(second_summary["artifacts"]["memory_activation_report"])
                self.assertGreaterEqual(len(second_report["stages"]), 2, host_id)
                skeleton_reads = second_report["stages"][0]["read_actions"]
                deep_interview_reads = second_report["stages"][1]["read_actions"]
                later_reads = [
                    action
                    for stage in second_report["stages"][1:]
                    for action in stage.get("read_actions", [])
                ]
                self.assertTrue(any(action["status"] == "backend_read" for action in skeleton_reads), host_id)
                self.assertTrue(
                    any(action["status"] in {"backend_read", "backend_read_empty"} for action in deep_interview_reads),
                    host_id,
                )
                self.assertTrue(any(action["status"] == "backend_read" for action in later_reads), host_id)

                requirement_text = Path(second_summary["artifacts"]["requirement_doc"]).read_text(encoding="utf-8")
                plan_text = Path(second_summary["artifacts"]["execution_plan"]).read_text(encoding="utf-8")
                self.assertIn("## Memory Context", requirement_text, host_id)
                self.assertIn("## Memory Context", plan_text, host_id)


if __name__ == "__main__":
    unittest.main()
