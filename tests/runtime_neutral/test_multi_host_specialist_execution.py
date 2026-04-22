from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALLER = REPO_ROOT / "scripts" / "install" / "install_vgo_adapter.py"
TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."
HOST_CASES = [
    ("claude-code", "VGO_CLAUDE_CODE_SPECIALIST_WRAPPER", "claude-code-wrapper"),
    ("cursor", "VGO_CURSOR_SPECIALIST_WRAPPER", "cursor-wrapper"),
    ("windsurf", "VGO_WINDSURF_SPECIALIST_WRAPPER", "windsurf-wrapper"),
    ("openclaw", "VGO_OPENCLAW_SPECIALIST_WRAPPER", "openclaw-wrapper"),
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


def run_runtime(task: str, artifact_root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts/runtime/invoke-vibe-runtime.ps1"
    run_id = "pytest-host-exec-" + uuid.uuid4().hex[:10]
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
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_fake_wrapper(directory: Path, name: str, host_id: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    wrapper_path = directory / f"{name}{suffix}"
    if os.name == "nt":
        wrapper_path.write_text(
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
            f"> \"%OUT%\" echo {{\"status\":\"completed\",\"summary\":\"{host_id} wrapper executed specialist\",\"verification_notes\":[\"{host_id} live wrapper ok\"],\"changed_files\":[],\"bounded_output_notes\":[\"{host_id} host-neutral bridge\"]}}\r\n"
            f"echo {host_id} wrapper ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        wrapper_path.write_text(
            "#!/usr/bin/env sh\n"
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
            f"printf '%s' '{{\"status\":\"completed\",\"summary\":\"{host_id} wrapper executed specialist\",\"verification_notes\":[\"{host_id} live wrapper ok\"],\"changed_files\":[],\"bounded_output_notes\":[\"{host_id} host-neutral bridge\"]}}' > \"$OUT\"\n"
            f"printf '{host_id} wrapper ok\\n'\n",
            encoding="utf-8",
        )
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR)
    return wrapper_path


class MultiHostSpecialistExecutionTests(unittest.TestCase):
    def test_runtime_packet_records_requested_and_effective_host_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                TASK,
                artifact_root=Path(tempdir),
                extra_env={"VCO_HOST_ID": "openclaw"},
            )
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            self.assertEqual("openclaw", runtime_input["host_adapter"]["requested_host_id"])
            self.assertEqual("openclaw", runtime_input["host_adapter"]["effective_host_id"])
            self.assertEqual(
                "openclaw",
                execution_manifest["route_runtime_alignment"]["requested_host_adapter_id"],
            )
            self.assertEqual(
                "openclaw",
                execution_manifest["route_runtime_alignment"]["effective_host_adapter_id"],
            )

    def test_non_codex_hosts_route_directly_by_default_even_when_wrapper_is_configured(self) -> None:
        for host_id, env_name, command_name in HOST_CASES:
            with self.subTest(host_id=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    temp_path = Path(tempdir)
                    wrapper = create_fake_wrapper(temp_path, command_name, host_id)
                    payload = run_runtime(
                        TASK,
                        artifact_root=temp_path,
                        extra_env={
                            "VCO_HOST_ID": host_id,
                            "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                            "VGO_SPECIALIST_CONSULTATION_MODE": "",
                            "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                            "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                            env_name: str(wrapper),
                        },
                    )
                    summary = payload["summary"]
                    execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
                    specialist_accounting = execution_manifest["specialist_accounting"]

                    self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
                    self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
                    self.assertEqual(host_id, specialist_accounting["effective_host_adapter_id"])

                    routed_units = list(specialist_accounting["direct_routed_specialist_units"])
                    self.assertGreaterEqual(len(routed_units), 1)
                    for unit in routed_units:
                        result = load_json(unit["result_path"])
                        self.assertEqual("direct_current_session_route", result["execution_driver"])
                        self.assertTrue(bool(result["direct_route"]))
                        self.assertFalse(bool(result["live_native_execution"]))
                        self.assertFalse(bool(result["degraded"]))
                        self.assertFalse(bool(result["blocked"]))

    def test_non_codex_hosts_ignore_legacy_host_subprocess_override_and_route_same_session(self) -> None:
        for host_id, _env_name, _command_name in HOST_CASES:
            with self.subTest(host_id=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    payload = run_runtime(
                        TASK,
                        artifact_root=Path(tempdir),
                        extra_env={
                            "VCO_HOST_ID": host_id,
                            "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                            "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                            "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                            "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                        },
                    )
                    summary = payload["summary"]
                    execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
                    specialist_accounting = execution_manifest["specialist_accounting"]

                    self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
                    self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
                    self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)

                    routed_units = list(specialist_accounting["direct_routed_specialist_units"])
                    self.assertGreaterEqual(len(routed_units), 1)
                    for unit in routed_units:
                        result = load_json(unit["result_path"])
                        self.assertEqual("direct_current_session_route", result["execution_driver"])
                        self.assertTrue(bool(result["direct_route"]))
                        self.assertFalse(bool(result["live_native_execution"]))
                        self.assertFalse(bool(result["degraded"]))

    def test_invalid_specialist_execution_mode_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                TASK,
                artifact_root=Path(tempdir),
                extra_env={
                    "VCO_HOST_ID": "openclaw",
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "typo-mode",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertEqual("explicitly_degraded", specialist_accounting["effective_execution_status"])
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertEqual(0, int(specialist_accounting["direct_routed_specialist_unit_count"]))
            degraded_units = list(specialist_accounting["degraded_specialist_units"])
            self.assertGreaterEqual(len(degraded_units), 1)
            first = load_json(degraded_units[0]["result_path"])
            self.assertEqual(
                "native_specialist_execution_mode_invalid:typo-mode",
                first["degradation_reason"],
            )

    def test_non_codex_hosts_ignore_legacy_subprocess_override_even_when_wrapper_is_configured(self) -> None:
        for host_id, env_name, command_name in HOST_CASES:
            with self.subTest(host_id=host_id):
                with tempfile.TemporaryDirectory() as tempdir:
                    temp_path = Path(tempdir)
                    wrapper = create_fake_wrapper(temp_path, command_name, host_id)
                    payload = run_runtime(
                        TASK,
                        artifact_root=temp_path,
                        extra_env={
                            "VCO_HOST_ID": host_id,
                            "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                            "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                            "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                            "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                            env_name: str(wrapper),
                        },
                    )
                    summary = payload["summary"]
                    execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
                    specialist_accounting = execution_manifest["specialist_accounting"]

                    self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
                    self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
                    self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
                    self.assertEqual(host_id, specialist_accounting["effective_host_adapter_id"])

                    routed_units = list(specialist_accounting["direct_routed_specialist_units"])
                    self.assertGreaterEqual(len(routed_units), 1)
                    for unit in routed_units:
                        result = load_json(unit["result_path"])
                        self.assertEqual("direct_current_session_route", result["execution_driver"])
                        self.assertTrue(bool(result["direct_route"]))
                        self.assertFalse(bool(result["live_native_execution"]))
                        self.assertFalse(bool(result["degraded"]))

    def test_non_codex_hosts_route_same_session_without_wrapper_env(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(
                TASK,
                artifact_root=Path(tempdir),
                extra_env={
                    "VCO_HOST_ID": "windsurf",
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertEqual("windsurf", specialist_accounting["effective_host_adapter_id"])
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            routed_units = list(specialist_accounting["direct_routed_specialist_units"])
            self.assertGreaterEqual(len(routed_units), 1)
            for unit in routed_units:
                result = load_json(unit["result_path"])
                self.assertEqual("direct_current_session_route", result["execution_driver"])
                self.assertTrue(bool(result["direct_route"]))
                self.assertFalse(bool(result["live_native_execution"]))
                self.assertFalse(bool(result["degraded"]))

    def test_runtime_can_use_installed_host_closure_manifest_without_wrapper_env(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            target_root = temp_path / "openclaw-home"
            target_root.mkdir(parents=True, exist_ok=True)

            install_env = dict(os.environ)
            install_env["OPENCLAW_HOME"] = str(target_root)
            install_result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--repo-root",
                    str(REPO_ROOT),
                    "--target-root",
                    str(target_root),
                    "--host",
                    "openclaw",
                    "--profile",
                    "full",
                ],
                capture_output=True,
                text=True,
                check=True,
                env=install_env,
            )
            install_payload = json.loads(install_result.stdout)
            self.assertTrue(install_payload["same_session_specialist_routing"])

            payload = run_runtime(
                TASK,
                artifact_root=temp_path,
                extra_env={
                    "VCO_HOST_ID": "openclaw",
                    "OPENCLAW_HOME": str(target_root),
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
            self.assertEqual("openclaw", specialist_accounting["effective_host_adapter_id"])


if __name__ == "__main__":
    unittest.main()
