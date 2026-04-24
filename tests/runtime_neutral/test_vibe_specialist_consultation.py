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
FREEZE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
CONSULTATION_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "VibeConsultation.Common.ps1"
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
EXECUTION_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
SPECIALIST_TASK = "I have a failing test and a stack trace. Help me debug systematically before proposing fixes."


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


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_preview_line(preview_lines: object, prefix: str) -> str:
    normalized = [str(line) for line in list(preview_lines)]
    line = next((line for line in normalized if line.startswith(prefix)), None)
    if line is None:
        raise AssertionError(f"{prefix} line not found in preview: {normalized}")
    return line


def require_skill_entry(entries: object, skill_id: str) -> dict[str, object]:
    normalized = list(entries)
    entry = next((item for item in normalized if item["skill_id"] == skill_id), None)
    if entry is None:
        raise AssertionError(f"{skill_id} entry not found in entries: {normalized}")
    return entry


def assert_direct_routed_result(
    test_case: unittest.TestCase,
    result: dict[str, object],
    *,
    skill_id: str = "systematic-debugging",
    entrypoint_path: Path | None = None,
    require_receipt_metadata: bool = True,
) -> None:
    if require_receipt_metadata:
        test_case.assertEqual(skill_id, result["skill_id"])
        test_case.assertEqual("routed_pending_current_session", result["status"])
        test_case.assertFalse(bool(result["verification_passed"]))
        test_case.assertFalse(bool(result["live_native_execution"]))
        test_case.assertFalse(bool(result["degraded"]))
    test_case.assertFalse(bool(result["blocked"]))
    test_case.assertTrue(bool(result["direct_route"]))
    test_case.assertEqual("direct_current_session_route", result["consultation_mode"])
    test_case.assertEqual("pending_direct_current_session_route", result["result_reason"])
    test_case.assertEqual([], list(result["observed_changed_files"]))
    test_case.assertGreaterEqual(len(list(result["consultation_notes"])), 1)
    test_case.assertGreaterEqual(len(list(result["adoption_notes"])), 1)
    test_case.assertGreaterEqual(len(list(result["verification_notes"])), 1)
    test_case.assertIsNone(result.get("response_json_path"))
    test_case.assertIsNone(result.get("prompt_path"))
    test_case.assertIsNone(result.get("schema_path"))

    native_entrypoint = Path(str(result["native_skill_entrypoint"]))
    test_case.assertTrue(native_entrypoint.is_absolute())
    test_case.assertTrue(native_entrypoint.exists())
    if entrypoint_path is not None:
        test_case.assertEqual(entrypoint_path.resolve(), native_entrypoint.resolve())

    result_path = result.get("result_path")
    if result_path is not None:
        test_case.assertTrue(Path(str(result_path)).exists())


def assert_live_consultation_result(
    test_case: unittest.TestCase,
    result: dict[str, object],
    *,
    skill_id: str = "systematic-debugging",
    entrypoint_path: Path | None = None,
    expected_status: str = "completed",
    expected_verification_passed: bool = True,
    expected_degraded: bool = False,
    expected_cwd: Path | None = None,
) -> None:
    test_case.assertEqual(skill_id, result["skill_id"])
    test_case.assertEqual(expected_status, result["status"])
    test_case.assertEqual(expected_verification_passed, bool(result["verification_passed"]))
    test_case.assertTrue(bool(result["live_native_execution"]))
    test_case.assertEqual(expected_degraded, bool(result["degraded"]))
    test_case.assertFalse(bool(result["blocked"]))
    test_case.assertTrue(Path(str(result["response_json_path"])).exists())
    test_case.assertTrue(Path(str(result["prompt_path"])).exists())
    test_case.assertTrue(Path(str(result["schema_path"])).exists())
    test_case.assertTrue(Path(str(result["stdout_path"])).exists())
    test_case.assertTrue(Path(str(result["stderr_path"])).exists())

    native_entrypoint = Path(str(result["native_skill_entrypoint"]))
    test_case.assertTrue(native_entrypoint.is_absolute())
    test_case.assertTrue(native_entrypoint.exists())
    if entrypoint_path is not None:
        test_case.assertEqual(entrypoint_path.resolve(), native_entrypoint.resolve())

    if expected_cwd is not None:
        test_case.assertEqual(expected_cwd.resolve(), Path(str(result["cwd"])).resolve())

    result_path = result.get("result_path")
    if result_path is not None:
        test_case.assertTrue(Path(str(result_path)).exists())


def consultation_native_subprocess_test_overrides(timeout_seconds: int = 30) -> str:
    return (
        "$script:OriginalGetVibeSpecialistConsultationPolicy = ${function:Get-VibeSpecialistConsultationPolicy}; "
        "function Get-VibeSpecialistConsultationPolicy { "
        "param([AllowNull()] [object]$Policy = $null) "
        "$resolved = & $script:OriginalGetVibeSpecialistConsultationPolicy -Policy $Policy; "
        "$resolved | Add-Member -NotePropertyName mode -NotePropertyValue 'native_subprocess_test' -Force; "
        "return $resolved "
        "}; "
        "function Resolve-VibeNativeSpecialistAdapter { "
        "param([Parameter(Mandatory)] [string]$ScriptPath) "
        "$commandPath = [Environment]::GetEnvironmentVariable('VGO_CODEX_EXECUTABLE'); "
        "if ([string]::IsNullOrWhiteSpace($commandPath)) { "
        "  throw 'VGO_CODEX_EXECUTABLE missing for specialist consultation subprocess test.' "
        "} "
        "return [pscustomobject]@{ "
        "  enabled = $true; "
        "  live_execution_allowed = $true; "
        "  reason = 'native_specialist_bridge_ready'; "
        f"  policy = [pscustomobject]@{{ default_timeout_seconds = {timeout_seconds} }}; "
        "  runtime = $null; "
        "  adapter = [pscustomobject]@{ id = 'codex'; arguments_prefix = @() }; "
        "  requested_host_adapter_id = 'codex'; "
        "  effective_host_adapter_id = 'codex'; "
        "  command_path = [System.IO.Path]::GetFullPath($commandPath); "
        "  invocation_arguments_prefix = @(); "
        "  legacy_removed_mode = $null "
        "} "
        "}; "
    )


def freeze_runtime_packet(task: str, artifact_root: Path) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-consult-freeze-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{FREEZE_SCRIPT}' "
                f"-Task '{task}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=dict(os.environ),
    )
    return json.loads(completed.stdout)


def run_runtime(
    task: str,
    artifact_root: Path,
    *,
    extra_env: dict[str, str] | None = None,
    check: bool = True,
) -> dict[str, object] | subprocess.CompletedProcess[str]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-consult-runtime-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{RUNTIME_SCRIPT}' "
                f"-Task '{task}' "
                "-Mode interactive_governed "
                f"-RunId '{run_id}' "
                f"-ArtifactRoot '{artifact_root}'; "
                "$result | ConvertTo-Json -Depth 20 }"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
        env={**os.environ, **(extra_env or {})},
    )
    if check:
        return json.loads(completed.stdout)
    return completed


def run_runtime_common_json(command_body: str, *, check: bool = True) -> object | subprocess.CompletedProcess[str]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            f"& {{ . {_ps_single_quote(str(RUNTIME_COMMON))}; {command_body} }}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
        env=dict(os.environ),
    )
    if not check:
        return completed

    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        return None
    return json.loads(stdout)


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
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Consulted specialist and produced bounded guidance.\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the systematic-debugging workflow to shape requirement and plan wording.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}\r\n"
            "echo fake codex consultation ok\r\n"
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
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Consulted specialist and produced bounded guidance.\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the systematic-debugging workflow to shape requirement and plan wording.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}' > \"$OUT\"\n"
            "printf 'fake codex consultation ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_codex_home_verifying_fake_consultation_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-home-check{suffix}"
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
            "if \"%CODEX_HOME%\"==\"\" (\r\n"
            "  >&2 echo CODEX_HOME missing\r\n"
            "  exit /b 3\r\n"
            ")\r\n"
            "if not exist \"%CODEX_HOME%\\skills\\systematic-debugging\\SKILL.md\" (\r\n"
            "  >&2 echo skill surface missing\r\n"
            "  exit /b 4\r\n"
            ")\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Consulted specialist and produced bounded guidance.\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the systematic-debugging workflow to shape requirement and plan wording.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}\r\n"
            "echo CODEX_HOME=%CODEX_HOME%\r\n"
            "echo SKILL_SURFACE=%CODEX_HOME%\\skills\\systematic-debugging\\SKILL.md\r\n"
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
            "if [ -z \"$CODEX_HOME\" ]; then\n"
            "  printf 'CODEX_HOME missing\\n' >&2\n"
            "  exit 3\n"
            "fi\n"
            "if [ ! -f \"$CODEX_HOME/skills/systematic-debugging/SKILL.md\" ]; then\n"
            "  printf 'skill surface missing\\n' >&2\n"
            "  exit 4\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Consulted specialist and produced bounded guidance.\",\"consultation_notes\":[\"Validate the failing path before proposing a fix.\"],\"adoption_notes\":[\"Use the systematic-debugging workflow to shape requirement and plan wording.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}' > \"$OUT\"\n"
            "printf 'CODEX_HOME=%s\\n' \"$CODEX_HOME\"\n"
            "printf 'SKILL_SURFACE=%s\\n' \"$CODEX_HOME/skills/systematic-debugging/SKILL.md\"\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_codex_home_seed_verifying_fake_consultation_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-home-seed-check{suffix}"
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
            "if \"%CODEX_HOME%\"==\"\" (\r\n"
            "  >&2 echo CODEX_HOME missing\r\n"
            "  exit /b 3\r\n"
            ")\r\n"
            "if not exist \"%CODEX_HOME%\\config.toml\" (\r\n"
            "  >&2 echo config missing\r\n"
            "  exit /b 4\r\n"
            ")\r\n"
            "findstr /c:\"config-seed-marker\" \"%CODEX_HOME%\\config.toml\" >nul || exit /b 5\r\n"
            "if not exist \"%CODEX_HOME%\\auth.json\" (\r\n"
            "  >&2 echo auth missing\r\n"
            "  exit /b 6\r\n"
            ")\r\n"
            "findstr /c:\"auth-seed-marker\" \"%CODEX_HOME%\\auth.json\" >nul || exit /b 7\r\n"
            "if not exist \"%CODEX_HOME%\\config\\seed.json\" exit /b 8\r\n"
            "if not exist \"%CODEX_HOME%\\mcp\\seed.json\" exit /b 9\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Consulted specialist from a seeded codex home.\",\"consultation_notes\":[\"Baseline codex config was copied into the sidecar.\"],\"adoption_notes\":[\"Keep user auth and config available to native specialist subprocesses.\"],\"verification_notes\":[\"Consultation used a seeded CODEX_HOME sidecar.\"]}\r\n"
            "echo CODEX_HOME=%CODEX_HOME%\r\n"
            "echo CODEX_HOME_SEEDED=1\r\n"
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
            "if [ -z \"$CODEX_HOME\" ]; then\n"
            "  printf 'CODEX_HOME missing\\n' >&2\n"
            "  exit 3\n"
            "fi\n"
            "if [ ! -f \"$CODEX_HOME/config.toml\" ]; then\n"
            "  printf 'config missing\\n' >&2\n"
            "  exit 4\n"
            "fi\n"
            "grep -q 'config-seed-marker' \"$CODEX_HOME/config.toml\" || exit 5\n"
            "if [ ! -f \"$CODEX_HOME/auth.json\" ]; then\n"
            "  printf 'auth missing\\n' >&2\n"
            "  exit 6\n"
            "fi\n"
            "grep -q 'auth-seed-marker' \"$CODEX_HOME/auth.json\" || exit 7\n"
            "if [ ! -f \"$CODEX_HOME/config/seed.json\" ]; then\n"
            "  exit 8\n"
            "fi\n"
            "if [ ! -f \"$CODEX_HOME/mcp/seed.json\" ]; then\n"
            "  exit 9\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Consulted specialist from a seeded codex home.\",\"consultation_notes\":[\"Baseline codex config was copied into the sidecar.\"],\"adoption_notes\":[\"Keep user auth and config available to native specialist subprocesses.\"],\"verification_notes\":[\"Consultation used a seeded CODEX_HOME sidecar.\"]}' > \"$OUT\"\n"
            "printf 'CODEX_HOME=%s\\n' \"$CODEX_HOME\"\n"
            "printf 'CODEX_HOME_SEEDED=1\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_incomplete_fake_codex_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-incomplete{suffix}"
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
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"\",\"consultation_notes\":[],\"adoption_notes\":[],\"verification_notes\":[]}\r\n"
            "echo fake codex incomplete consultation\r\n"
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
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"\",\"consultation_notes\":[],\"adoption_notes\":[],\"verification_notes\":[]}' > \"$OUT\"\n"
            "printf 'fake codex incomplete consultation\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_repo_check_fake_codex_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-repo-check{suffix}"
    if os.name == "nt":
        command_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
            "set OUT=\r\n"
            "set HAS_SKIP=0\r\n"
            ":loop\r\n"
            "if \"%~1\"==\"\" goto done\r\n"
            "if /I \"%~1\"==\"-o\" (\r\n"
            "  set OUT=%~2\r\n"
            "  shift\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "if /I \"%~1\"==\"--skip-git-repo-check\" (\r\n"
            "  set HAS_SKIP=1\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "shift\r\n"
            "goto loop\r\n"
            ":done\r\n"
            "if \"%HAS_SKIP%\"==\"0\" (\r\n"
            "  >&2 echo Not inside a trusted directory and --skip-git-repo-check was not specified.\r\n"
            "  exit /b 1\r\n"
            ")\r\n"
            "if \"%OUT%\"==\"\" exit /b 2\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Consulted specialist from a non-git workspace.\",\"consultation_notes\":[\"Repo-check bypass was applied only for this codex exec.\"],\"adoption_notes\":[\"Keep the bypass scoped to native codex subprocesses.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}\r\n"
            "echo fake codex repo-check ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        command_path.write_text(
            "#!/usr/bin/env sh\n"
            "OUT=''\n"
            "HAS_SKIP=0\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -o)\n"
            "      OUT=\"$2\"\n"
            "      shift 2\n"
            "      ;;\n"
            "    --skip-git-repo-check)\n"
            "      HAS_SKIP=1\n"
            "      shift\n"
            "      ;;\n"
            "    *)\n"
            "      shift\n"
            "      ;;\n"
            "  esac\n"
            "done\n"
            "if [ \"$HAS_SKIP\" != \"1\" ]; then\n"
            "  printf 'Not inside a trusted directory and --skip-git-repo-check was not specified.\\n' >&2\n"
            "  exit 1\n"
            "fi\n"
            "if [ -z \"$OUT\" ]; then\n"
            "  exit 2\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Consulted specialist from a non-git workspace.\",\"consultation_notes\":[\"Repo-check bypass was applied only for this codex exec.\"],\"adoption_notes\":[\"Keep the bypass scoped to native codex subprocesses.\"],\"verification_notes\":[\"Consultation stayed read-only and returned structured guidance.\"]}' > \"$OUT\"\n"
            "printf 'fake codex repo-check ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_write_attempt_fake_consultation_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-write-attempt{suffix}"
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
            "> wrote-by-fake.txt echo hi\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Consultation attempted a write.\",\"consultation_notes\":[\"A write was attempted in the working directory.\"],\"adoption_notes\":[\"Read-only verification should reject this run.\"],\"verification_notes\":[\"The fake codex created wrote-by-fake.txt.\"]}\r\n"
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
            "printf 'hi' > wrote-by-fake.txt\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Consultation attempted a write.\",\"consultation_notes\":[\"A write was attempted in the working directory.\"],\"adoption_notes\":[\"Read-only verification should reject this run.\"],\"verification_notes\":[\"The fake codex created wrote-by-fake.txt.\"]}' > \"$OUT\"\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def set_directory_read_only(path: Path) -> None:
    if os.name == "nt":
        path.chmod(stat.S_IREAD | stat.S_IEXEC)
    else:
        path.chmod(0o555)


def set_directory_writable(path: Path) -> None:
    if os.name == "nt":
        path.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    else:
        path.chmod(0o755)


class VibeSpecialistConsultationTests(unittest.TestCase):
    def test_bucketed_consultation_selection_keeps_stage_assistant_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            primary_one = temp_root / "primary-one" / "SKILL.md"
            primary_two = temp_root / "primary-two" / "SKILL.md"
            stage_one = temp_root / "stage-one" / "SKILL.md"
            stage_two = temp_root / "stage-two" / "SKILL.md"
            for path in (primary_one, primary_two, stage_one, stage_two):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Skill\n", encoding="utf-8")

            result = run_runtime_common_json(
                f"""
                . {_ps_single_quote(str(CONSULTATION_SCRIPT))}
                $policy = [pscustomobject]@{{
                    enabled = $true
                    mode = 'direct_current_session_route'
                    max_consults_per_window = 3
                    selection_mode = 'bucketed_with_backfill'
                    bucket_limits = [pscustomobject]@{{
                        primary = 2
                        stage_assistant = 1
                    }}
                    allowed_windows = @('discussion', 'planning')
                    require_contract_complete = $true
                    require_native_workflow = $true
                    require_native_usage_required = $true
                    require_entrypoint_path = $true
                }}
                $recommendations = @(
                    [pscustomobject]@{{
                        skill_id = 'ml-expert'
                        source = 'route_ranked'
                        native_skill_entrypoint = {_ps_single_quote(primary_one.as_posix())}
                        reason = 'primary specialist one'
                        contract_complete = $true
                        must_preserve_workflow = $true
                        native_usage_required = $true
                        rank = 1
                        confidence = 0.99
                    }},
                    [pscustomobject]@{{
                        skill_id = 'science-plotting'
                        source = 'route_ranked'
                        native_skill_entrypoint = {_ps_single_quote(primary_two.as_posix())}
                        reason = 'primary specialist two'
                        contract_complete = $true
                        must_preserve_workflow = $true
                        native_usage_required = $true
                        rank = 2
                        confidence = 0.98
                    }},
                    [pscustomobject]@{{
                        skill_id = 'brainstorming'
                        source = 'route_stage_assistant'
                        native_skill_entrypoint = {_ps_single_quote(stage_one.as_posix())}
                        reason = 'stage assistant one'
                        contract_complete = $true
                        must_preserve_workflow = $true
                        native_usage_required = $true
                        rank = 3
                        confidence = 0.70
                    }},
                    [pscustomobject]@{{
                        skill_id = 'writing-plans'
                        source = 'route_stage_assistant'
                        native_skill_entrypoint = {_ps_single_quote(stage_two.as_posix())}
                        reason = 'stage assistant two'
                        contract_complete = $true
                        must_preserve_workflow = $true
                        native_usage_required = $true
                        rank = 4
                        confidence = 0.60
                    }}
                )
                $result = Split-VibeSpecialistConsultationCandidates -Recommendations $recommendations -WindowId 'discussion' -Stage 'deep_interview' -Policy $policy
                $result | ConvertTo-Json -Depth 20
                """
            )

            assert isinstance(result, dict)
            approved = list(result["approved_consultation"])
            deferred = list(result["deferred_to_execution"])
            self.assertEqual(
                ["ml-expert", "science-plotting", "brainstorming"],
                [item["skill_id"] for item in approved],
            )
            self.assertEqual(
                ["primary", "primary", "stage_assistant"],
                [item["consultation_bucket"] for item in approved],
            )
            self.assertEqual(1, len(deferred))
            self.assertEqual("writing-plans", deferred[0]["skill_id"])
            self.assertEqual("max_consults_per_window_reached", deferred[0]["reason"])
            self.assertEqual("stage_assistant", deferred[0]["consultation_bucket"])

    def test_user_disclosure_projection_retains_entries_with_missing_or_invalid_entrypoints(self) -> None:
        result = run_runtime_common_json(
            """
            $policy = [pscustomobject]@{
                enabled = $true
                stage = 'plan_execute'
                mode = 'approved_dispatch_pre_execution_unified_once'
                timing = 'before_execution'
                scope = 'approved_dispatch_only'
                aggregation = 'unified_once'
                path_source = 'native_skill_entrypoint'
                require_entrypoint_path = $true
                include_description = $true
                header = 'Pre-dispatch specialist disclosure:'
            }
            $approvedDispatch = @(
                [pscustomobject]@{
                    skill_id = 'systematic-debugging'
                    native_skill_entrypoint = 'bundled/skills/systematic-debugging/SKILL.md'
                    native_skill_description = 'debug'
                    dispatch_phase = 'plan_execute'
                    write_scope = 'read_only'
                    review_mode = 'consultation_only'
                },
                [pscustomobject]@{
                    skill_id = 'brainstorming'
                    native_skill_description = 'plan'
                    dispatch_phase = 'plan_execute'
                    write_scope = 'read_only'
                    review_mode = 'consultation_only'
                }
            )
            $result = New-VibeSpecialistUserDisclosureProjection -ApprovedDispatch $approvedDispatch -Policy $policy
            $result | ConvertTo-Json -Depth 20
            """
        )

        assert isinstance(result, dict)
        self.assertEqual(2, result["routed_skill_count"])
        entries = {item["skill_id"]: item for item in list(result["routed_skills"])}
        self.assertEqual({"systematic-debugging", "brainstorming"}, set(entries))

        invalid_entry = entries["systematic-debugging"]
        self.assertIsNone(invalid_entry["native_skill_entrypoint"])
        self.assertEqual("bundled/skills/systematic-debugging/SKILL.md", invalid_entry["native_skill_entrypoint_raw"])
        self.assertEqual("invalid", invalid_entry["entrypoint_path_state"])
        self.assertFalse(bool(invalid_entry["entrypoint_missing"]))
        self.assertTrue(bool(invalid_entry["entrypoint_path_invalid"]))
        self.assertFalse(bool(invalid_entry["entrypoint_requirement_satisfied"]))

        missing_entry = entries["brainstorming"]
        self.assertIsNone(missing_entry["native_skill_entrypoint"])
        self.assertIsNone(missing_entry["native_skill_entrypoint_raw"])
        self.assertEqual("missing", missing_entry["entrypoint_path_state"])
        self.assertTrue(bool(missing_entry["entrypoint_missing"]))
        self.assertFalse(bool(missing_entry["entrypoint_path_invalid"]))
        self.assertFalse(bool(missing_entry["entrypoint_requirement_satisfied"]))

        self.assertIn(
            "systematic-debugging -> bundled/skills/systematic-debugging/SKILL.md (invalid entrypoint path)",
            result["rendered_text"],
        )
        self.assertIn(
            "brainstorming -> path unavailable (missing entrypoint path)",
            result["rendered_text"],
        )

    def test_observed_changed_paths_ignores_snapshot_root_when_explicitly_ignored(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            snapshot_root = Path(tempdir) / "snapshot-root"
            snapshot_root.mkdir(parents=True, exist_ok=True)

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f"$root = {_ps_single_quote(str(snapshot_root))}; "
                "$before = Get-VibePathStatusSnapshot -RootPath $root; "
                "Set-Content -LiteralPath (Join-Path $root 'foo.txt') -Value 'x' -Encoding utf8; "
                "$after = Get-VibePathStatusSnapshot -RootPath $root; "
                "$changed = Get-VibeObservedChangedPaths -BeforeSnapshot $before -AfterSnapshot $after -SnapshotRoot $root -IgnoredPaths @($root); "
                "[pscustomobject]@{ changed = @($changed) } | ConvertTo-Json -Depth 5 -Compress }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env=dict(os.environ),
            )

            payload = json.loads(completed.stdout)
            self.assertEqual([], list(payload["changed"]))

    def test_consultation_lifecycle_projection_rejects_missing_window_id(self) -> None:
        completed = run_runtime_common_json(
            """
            $receipt = [pscustomobject]@{
                enabled = $true
                stage = 'requirement_doc'
                user_disclosures = @(
                    [pscustomobject]@{
                        skill_id = 'systematic-debugging'
                        why_now = 'need debugging guidance before requirement freeze'
                        native_skill_entrypoint = 'scripts/runtime/systematic-debugging/SKILL.md'
                    }
                )
                consulted_units = @()
            }
            $result = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt
            $result | ConvertTo-Json -Depth 20
            """,
            check=False,
        )

        assert isinstance(completed, subprocess.CompletedProcess)
        self.assertNotEqual(0, completed.returncode)
        self.assertIn(
            "Enabled specialist consultation receipts must declare window_id as",
            completed.stderr,
        )

    def test_consultation_unit_ignores_session_root_artifacts_when_working_root_matches_session_root(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_fake_codex_command(artifact_root)
            session_root = artifact_root / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            skill_root = artifact_root / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")
            source_artifact = session_root / "discussion-seed.md"
            source_artifact.write_text("# Intent\nNeed session-root consultation coverage.\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                "$consultation = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                f"native_skill_entrypoint = {_ps_single_quote(entrypoint_path.as_posix())}; "
                f"skill_root = {_ps_single_quote(skill_root.as_posix())}; "
                "consultation_reason = 'verify session-root ignore coverage'; "
                "consultation_scope = 'bounded consultation'; "
                "consultation_role = 'discussion_consultant'; "
                "required_inputs = @('source_artifact'); "
                "expected_outputs = @('consultation_notes'); "
                "verification_expectation = 'Return structured consultation output.' "
                "}; "
                f"$result = Invoke-VibeSpecialistConsultationUnit -UnitId 'consult-session-root' -Consultation $consultation -SessionRoot {_ps_single_quote(session_root.as_posix())} -RepoRoot $runtime.repo_root -Task 'debug this workflow' -RunId 'run-session-root' -WindowId 'discussion' -Stage 'deep_interview' -SourceArtifactPath {_ps_single_quote(source_artifact.as_posix())} -Policy $runtime.specialist_consultation_policy; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            assert_live_consultation_result(
                self,
                result,
                entrypoint_path=entrypoint_path,
                expected_cwd=session_root,
            )
            self.assertIn("fake codex consultation ok", list(result["stdout_preview"]))
            self.assertTrue(source_artifact.exists())

    def test_consultation_lifecycle_projection_handles_summary_only_receipt(self) -> None:
        result = run_runtime_common_json(
            """
            $receipt = [pscustomobject]@{
                enabled = $true
                window_id = 'discussion'
                stage = 'requirement_doc'
                summary = [pscustomobject]@{
                    consulted_unit_count = 0
                    routed_unit_count = 1
                }
                user_disclosures = @(
                    [pscustomobject]@{
                        skill_id = 'systematic-debugging'
                        why_now = 'need debugging guidance before requirement freeze'
                        native_skill_entrypoint = 'scripts/runtime/systematic-debugging/SKILL.md'
                    }
                )
            }
            $result = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt
            $result | ConvertTo-Json -Depth 20
            """
        )

        self.assertEqual("discussion_consultation", result["layer_id"])
        self.assertEqual(1, int(result["skill_count"]))
        self.assertIn("Specialist consultation routing during discussion:", result["rendered_text"])
        skill = list(result["skills"])[0]
        self.assertEqual("systematic-debugging", skill["skill_id"])
        self.assertEqual("consultation_disclosed", skill["state"])

    def test_consultation_lifecycle_projection_uses_chain_header_for_mixed_consultation_state(self) -> None:
        result = run_runtime_common_json(
            """
            $receipt = [pscustomobject]@{
                enabled = $true
                window_id = 'discussion'
                stage = 'requirement_doc'
                summary = [pscustomobject]@{
                    consulted_unit_count = 1
                    routed_unit_count = 1
                }
                user_disclosures = @(
                    [pscustomobject]@{
                        skill_id = 'systematic-debugging'
                        why_now = 'need debugging guidance before requirement freeze'
                        native_skill_entrypoint = 'scripts/runtime/systematic-debugging/SKILL.md'
                    }
                )
            }
            $result = New-VibeSpecialistConsultationLifecycleLayerProjection -ConsultationReceipt $receipt
            $result | ConvertTo-Json -Depth 20
            """
        )

        self.assertIn("Recorded specialist consultation chain during discussion:", result["rendered_text"])

    def test_host_stage_disclosure_treats_suffix_routed_states_as_routed(self) -> None:
        result = run_runtime_common_json(
            """
            $segment = [pscustomobject]@{
                segment_id = 'discussion_consultation'
                stage = 'deep_interview'
                skills = @(
                    [pscustomobject]@{
                        skill_id = 'systematic-debugging'
                        state = 'direct_current_session_routed'
                    }
                )
            }
            $result = New-VibeHostStageDisclosureEventProjection -Segment $segment
            $result | ConvertTo-Json -Depth 20
            """
        )

        self.assertEqual("discussion_consultation_routed", result["event_id"])

    def test_invalid_specialist_consultation_mode_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            completed = run_runtime(
                SPECIALIST_TASK,
                Path(tempdir),
                extra_env={
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "typo-mode",
                },
                check=False,
            )

        assert isinstance(completed, subprocess.CompletedProcess)
        self.assertNotEqual(0, completed.returncode)
        self.assertIn(
            "Unsupported specialist consultation mode: typo-mode",
            "\n".join([completed.stdout, completed.stderr]),
        )

    def test_consultation_unit_treats_direct_current_session_adapter_reason_as_direct_route(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            session_root = artifact_root / "session-root"
            session_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = REPO_ROOT / "bundled" / "skills" / "systematic-debugging" / "SKILL.md"
            source_artifact_path = artifact_root / "source.md"
            source_artifact_path.write_text("# source\n", encoding="utf-8")

            result = run_runtime_common_json(
                f"""
                . {_ps_single_quote(str(EXECUTION_COMMON))}
                . {_ps_single_quote(str(CONSULTATION_SCRIPT))}
                function Get-VibeSpecialistConsultationPolicy {{
                    param([object]$Policy)
                    return [pscustomobject]@{{
                        mode = 'native_bridge'
                    }}
                }}
                function Resolve-VibeNativeSpecialistAdapter {{
                    param([string]$ScriptPath)
                    return [pscustomobject]@{{
                        enabled = $true
                        live_execution_allowed = $false
                        reason = 'direct_current_session_route'
                        policy = [pscustomobject]@{{}}
                        adapter = $null
                    }}
                }}
                $consultation = [pscustomobject]@{{
                    skill_id = 'systematic-debugging'
                    native_skill_entrypoint = {_ps_single_quote(str(entrypoint_path))}
                    reason = 'Need same-session debugging guidance.'
                    required_inputs = @('task')
                    expected_outputs = @('guidance')
                    verification_expectation = 'host should keep governance'
                }}
                $result = Invoke-VibeSpecialistConsultationUnit `
                    -UnitId 'unit-1' `
                    -Consultation $consultation `
                    -SessionRoot {_ps_single_quote(str(session_root))} `
                    -RepoRoot {_ps_single_quote(str(REPO_ROOT))} `
                    -Task 'Need debugging guidance.' `
                    -RunId 'pytest-consult-direct-route' `
                    -WindowId 'discussion' `
                    -Stage 'deep_interview' `
                    -SourceArtifactPath {_ps_single_quote(str(source_artifact_path))} `
                    -Policy ([pscustomobject]@{{}})
                $result | ConvertTo-Json -Depth 20
                """
            )

            assert isinstance(result, dict)
            self.assertEqual("routed", result["category"])
            self.assertTrue(Path(str(result["result_path"])).exists())
            assert_direct_routed_result(self, result["result"], entrypoint_path=entrypoint_path)

    def test_host_user_briefing_segment_handles_missing_consultation_receipt(self) -> None:
        result = run_runtime_common_json(
            """
            $layer = [pscustomobject]@{
                layer_id = 'discussion_consultation'
                stage = 'deep_interview'
                truth_layer = 'consultation'
                skills = @(
                    [pscustomobject]@{
                        skill_id = 'systematic-debugging'
                        state = 'direct_current_session_routed'
                        why_now = 'need debugging guidance before requirement freeze'
                        native_skill_entrypoint = 'scripts/runtime/systematic-debugging/SKILL.md'
                    }
                )
            }
            $result = New-VibeHostUserBriefingSegmentProjection -LifecycleLayer $layer -ConsultationReceipt $null
            $result | ConvertTo-Json -Depth 20
            """
        )

        self.assertEqual("consultation", result["category"])
        self.assertEqual("gate_unknown", result["status"])
        self.assertIn(
            "Vibe recorded these Skills in the discussion consultation chain; freeze gate: not_applicable.",
            result["rendered_text"],
        )

    def test_host_user_briefing_uses_execution_handoff_mode_without_lifecycle_or_bounded_return(self) -> None:
        result = run_runtime_common_json(
            """
            $deliveryAcceptanceReport = [pscustomobject]@{
                summary = [pscustomobject]@{
                    gate_result = 'MANUAL_REVIEW_REQUIRED'
                    readiness_state = 'manual_review_required'
                    completion_language_allowed = $false
                    incomplete_layers = @('workflow_completion_truth')
                }
                execution_context = [pscustomobject]@{
                    run_id = 'pytest-host-specialist-handoff'
                    session_root = 'F:\\repo\\outputs\\runtime\\vibe-sessions\\pytest-host-specialist-handoff'
                    specialist_host_continuation_pending = $true
                    specialist_effective_execution_status = 'direct_current_session_routed'
                    direct_routed_specialist_unit_ids = @('unit-1')
                    direct_routed_specialist_skill_ids = @('systematic-debugging')
                    direct_routed_specialist_units = @(
                        [pscustomobject]@{
                            unit_id = 'unit-1'
                            skill_id = 'systematic-debugging'
                            native_skill_entrypoint = 'C:\\skills\\systematic-debugging\\SKILL.md'
                            result_path = 'F:\\repo\\outputs\\runtime\\vibe-sessions\\pytest-host-specialist-handoff\\specialist-results\\unit-1.json'
                        }
                    )
                }
            }
            $result = New-VibeHostUserBriefingProjection -DeliveryAcceptanceReport $deliveryAcceptanceReport
            $result | ConvertTo-Json -Depth 20
            """
        )

        self.assertEqual("execution_handoff_host_briefing", result["mode"])
        self.assertEqual(["execution_handoff"], [str(segment["segment_id"]) for segment in list(result["segments"])])
        self.assertIn("Execution handoff is still pending under governed vibe.", result["rendered_text"])
        segment = list(result["segments"])[0]
        self.assertEqual(1, segment["skill_count"])
        self.assertEqual(["systematic-debugging"], list(segment["skills"]))
        self.assertIn("specialist-execution.json", segment["rendered_text"])
        self.assertIn("runtime_delivery_acceptance.py", segment["rendered_text"])
        contract = segment["host_decision_contract"]
        self.assertEqual("specialist_execution_resolution", contract["decision_kind"])
        self.assertEqual("execution_handoff", contract["decision_context"])
        self.assertEqual(
            "F:\\repo\\outputs\\runtime\\vibe-sessions\\pytest-host-specialist-handoff\\specialist-execution.json",
            contract["sidecar_path"],
        )
        self.assertEqual(["executed", "degraded", "blocked"], list(contract["allowed_resolution_states"]))
        self.assertEqual(["unit-1"], list(contract["direct_routed_unit_ids"]))
        self.assertEqual(["systematic-debugging"], list(contract["direct_routed_skill_ids"]))
        self.assertEqual("unit-1", contract["required_units"][0]["unit_id"])
        self.assertEqual("executed", contract["preferred_payload"]["units"][0]["resolution_state"])

    def test_consultation_window_invokes_specialist_and_emits_progressive_disclosure(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_fake_codex_command(artifact_root)
            freeze_payload = freeze_runtime_packet(SPECIALIST_TASK, artifact_root)
            packet_path = Path(freeze_payload["packet_path"])
            run_id = "pytest-consult-window-" + uuid.uuid4().hex[:10]
            prompt_seed_path = artifact_root / "discussion-seed.md"
            prompt_seed_path.write_text("# Intent\nNeed systematic debugging guidance before freezing requirements.\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$packet = Get-Content -LiteralPath {_ps_single_quote(str(packet_path))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                f"$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId {_ps_single_quote(run_id)} -Runtime $runtime -ArtifactRoot {_ps_single_quote(str(artifact_root))}; "
                f"$result = Invoke-VibeSpecialistConsultationWindow "
                f"-Task {_ps_single_quote(SPECIALIST_TASK)} "
                f"-RunId {_ps_single_quote(run_id)} "
                f"-SessionRoot $sessionRoot "
                f"-RepoRoot $runtime.repo_root "
                f"-WindowId 'discussion' "
                f"-Stage 'deep_interview' "
                f"-SourceArtifactPath {_ps_single_quote(str(prompt_seed_path))} "
                f"-Recommendations @($packet.specialist_recommendations | Where-Object {{ [string]$_.skill_id -eq 'systematic-debugging' }}) "
                f"-Policy $runtime.specialist_consultation_policy; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            payload = json.loads(completed.stdout)
            receipt = load_json(payload["receipt_path"])

            self.assertEqual("discussion", receipt["window_id"])
            self.assertEqual("deep_interview", receipt["stage"])
            self.assertGreaterEqual(len(list(receipt["approved_consultation"])), 1)
            self.assertGreaterEqual(len(list(receipt["consulted_units"])), 1)
            self.assertEqual([], list(receipt["degraded"]))
            self.assertEqual([], list(receipt["routed_units"]))
            self.assertGreaterEqual(len(list(receipt["user_disclosures"])), 1)
            self.assertTrue(bool(receipt["freeze_gate"]["passed"]))

            disclosure = require_skill_entry(receipt["user_disclosures"], "systematic-debugging")
            self.assertTrue(disclosure["why_now"])
            self.assertTrue(Path(disclosure["native_skill_entrypoint"]).is_absolute())
            self.assertTrue(Path(disclosure["native_skill_entrypoint"]).exists())
            self.assertIn("systematic-debugging", disclosure["rendered_text"])
            self.assertIn(disclosure["native_skill_entrypoint"], disclosure["rendered_text"])

            consulted = require_skill_entry(receipt["consulted_units"], "systematic-debugging")
            assert_live_consultation_result(self, consulted)
            self.assertIn("fake codex consultation ok", list(consulted["stdout_preview"]))

    def test_consultation_window_bypasses_codex_repo_check_for_non_git_roots(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_repo_check_fake_codex_command(artifact_root)
            freeze_payload = freeze_runtime_packet(SPECIALIST_TASK, artifact_root)
            packet_path = Path(freeze_payload["packet_path"])
            non_git_root = artifact_root / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            run_id = "pytest-consult-non-git-" + uuid.uuid4().hex[:10]
            prompt_seed_path = artifact_root / "discussion-seed.md"
            prompt_seed_path.write_text("# Intent\nNeed consultation from a non-git workspace.\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$packet = Get-Content -LiteralPath {_ps_single_quote(str(packet_path))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                f"$sessionRoot = Ensure-VibeSessionRoot -RepoRoot {_ps_single_quote(str(non_git_root))} -RunId {_ps_single_quote(run_id)} -Runtime $runtime -ArtifactRoot {_ps_single_quote(str(artifact_root))}; "
                f"$result = Invoke-VibeSpecialistConsultationWindow "
                f"-Task {_ps_single_quote(SPECIALIST_TASK)} "
                f"-RunId {_ps_single_quote(run_id)} "
                f"-SessionRoot $sessionRoot "
                f"-RepoRoot {_ps_single_quote(str(non_git_root))} "
                f"-WindowId 'discussion' "
                f"-Stage 'deep_interview' "
                f"-SourceArtifactPath {_ps_single_quote(str(prompt_seed_path))} "
                f"-Recommendations @($packet.specialist_recommendations | Where-Object {{ [string]$_.skill_id -eq 'systematic-debugging' }}) "
                f"-Policy $runtime.specialist_consultation_policy; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            payload = json.loads(completed.stdout)
            receipt = load_json(payload["receipt_path"])

            self.assertGreaterEqual(len(list(receipt["consulted_units"])), 1)
            self.assertEqual([], list(receipt["degraded"]))
            self.assertTrue(bool(receipt["freeze_gate"]["passed"]))
            self.assertEqual([], list(receipt["routed_units"]))
            consulted = require_skill_entry(receipt["consulted_units"], "systematic-debugging")
            assert_live_consultation_result(self, consulted, expected_cwd=non_git_root)
            self.assertIn("--skip-git-repo-check", list(consulted["arguments"]))
            self.assertIn("fake codex repo-check ok", list(consulted["stdout_preview"]))

    def test_consultation_window_fails_verification_when_non_git_working_root_is_modified(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_write_attempt_fake_consultation_command(artifact_root)
            freeze_payload = freeze_runtime_packet(SPECIALIST_TASK, artifact_root)
            packet_path = Path(freeze_payload["packet_path"])
            non_git_root = artifact_root / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            run_id = "pytest-consult-write-attempt-" + uuid.uuid4().hex[:10]
            prompt_seed_path = artifact_root / "discussion-seed.md"
            prompt_seed_path.write_text("# Intent\nDetect writes inside a non-git consultation workspace.\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$packet = Get-Content -LiteralPath {_ps_single_quote(str(packet_path))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                f"$sessionRoot = Ensure-VibeSessionRoot -RepoRoot {_ps_single_quote(str(non_git_root))} -RunId {_ps_single_quote(run_id)} -Runtime $runtime -ArtifactRoot {_ps_single_quote(str(artifact_root))}; "
                f"$result = Invoke-VibeSpecialistConsultationWindow "
                f"-Task {_ps_single_quote(SPECIALIST_TASK)} "
                f"-RunId {_ps_single_quote(run_id)} "
                f"-SessionRoot $sessionRoot "
                f"-RepoRoot {_ps_single_quote(str(non_git_root))} "
                f"-WindowId 'discussion' "
                f"-Stage 'deep_interview' "
                f"-SourceArtifactPath {_ps_single_quote(str(prompt_seed_path))} "
                f"-Recommendations @($packet.specialist_recommendations | Where-Object {{ [string]$_.skill_id -eq 'systematic-debugging' }}) "
                f"-Policy $runtime.specialist_consultation_policy; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            payload = json.loads(completed.stdout)
            receipt = load_json(payload["receipt_path"])
            self.assertEqual([], list(receipt["consulted_units"]))
            self.assertGreaterEqual(len(list(receipt["degraded"])), 1)
            self.assertFalse(bool(receipt["freeze_gate"]["passed"]))
            self.assertEqual([], list(receipt["routed_units"]))
            degraded = require_skill_entry(receipt["degraded"], "systematic-debugging")
            assert_live_consultation_result(
                self,
                degraded,
                expected_status="failed",
                expected_verification_passed=False,
                expected_degraded=True,
                expected_cwd=non_git_root,
            )
            self.assertIn("--skip-git-repo-check", list(degraded["arguments"]))
            self.assertEqual(["wrote-by-fake.txt"], list(degraded["observed_changed_files"]))
            self.assertIn("live_degraded_result:systematic-debugging", list(receipt["freeze_gate"]["errors"]))

    def test_consultation_window_falls_back_to_writable_artifact_root_when_repo_root_is_read_only(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_fake_codex_command(artifact_root)
            freeze_payload = freeze_runtime_packet(SPECIALIST_TASK, artifact_root)
            packet_path = Path(freeze_payload["packet_path"])
            read_only_root = artifact_root / "read-only-install-root"
            read_only_root.mkdir(parents=True, exist_ok=True)
            run_id = "pytest-consult-readonly-" + uuid.uuid4().hex[:10]
            prompt_seed_path = artifact_root / "discussion-seed.md"
            prompt_seed_path.write_text("# Intent\nNeed consultation from a writable artifact root.\n", encoding="utf-8")

            try:
                set_directory_read_only(read_only_root)

                ps_script = (
                    "& { "
                    f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                    f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                    f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                    f"{consultation_native_subprocess_test_overrides()}"
                    f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                    f"$packet = Get-Content -LiteralPath {_ps_single_quote(str(packet_path))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                    f"$sessionRoot = Ensure-VibeSessionRoot -RepoRoot {_ps_single_quote(str(read_only_root))} -RunId {_ps_single_quote(run_id)} -Runtime $runtime -ArtifactRoot {_ps_single_quote(str(artifact_root))}; "
                    f"$result = Invoke-VibeSpecialistConsultationWindow "
                    f"-Task {_ps_single_quote(SPECIALIST_TASK)} "
                    f"-RunId {_ps_single_quote(run_id)} "
                    f"-SessionRoot $sessionRoot "
                    f"-RepoRoot {_ps_single_quote(str(read_only_root))} "
                    f"-WindowId 'discussion' "
                    f"-Stage 'deep_interview' "
                    f"-SourceArtifactPath {_ps_single_quote(str(prompt_seed_path))} "
                    f"-Recommendations @($packet.specialist_recommendations) "
                    f"-Policy $runtime.specialist_consultation_policy; "
                    "$result | ConvertTo-Json -Depth 20 }"
                )
                completed = subprocess.run(
                    [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=True,
                    env={
                        **os.environ,
                        "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                        "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                        "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                        "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                        "VGO_CODEX_EXECUTABLE": str(fake_codex),
                    },
                )
            finally:
                set_directory_writable(read_only_root)

            payload = json.loads(completed.stdout)
            receipt = load_json(payload["receipt_path"])
            self.assertGreaterEqual(len(list(receipt["consulted_units"])), 1)
            self.assertEqual([], list(receipt["degraded"]))
            self.assertTrue(bool(receipt["freeze_gate"]["passed"]))
            self.assertEqual([], list(receipt["routed_units"]))
            consulted = require_skill_entry(receipt["consulted_units"], "systematic-debugging")
            assert_live_consultation_result(self, consulted)
            resolved_cwd = Path(str(consulted["cwd"])).resolve()
            if os.name == "nt":
                self.assertIn(resolved_cwd, {artifact_root.resolve(), read_only_root.resolve()})
            else:
                self.assertEqual(artifact_root.resolve(), resolved_cwd)
            self.assertIn("fake codex consultation ok", list(consulted["stdout_preview"]))

    def test_specialist_consultation_unit_uses_sidecar_codex_home_with_materialized_skill_surface(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_codex_home_verifying_fake_consultation_command(artifact_root)
            non_git_root = artifact_root / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            session_root = artifact_root / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            skill_root = artifact_root / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            source_artifact = artifact_root / "intent-contract.json"
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")
            source_artifact.write_text("{\"goal\":\"demo\"}\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                "$consultation = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                f"skill_root = '{skill_root.as_posix()}'; "
                "consultation_reason = 'verify codex sidecar home'; "
                "consultation_scope = 'bounded consultation'; "
                "consultation_role = 'discussion_consultant'; "
                "required_inputs = @('source_artifact'); "
                "expected_outputs = @('consultation_notes'); "
                "verification_expectation = 'Return structured consultation output.' "
                "}; "
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$result = Invoke-VibeSpecialistConsultationUnit -UnitId 'consult-unit' -Consultation $consultation -SessionRoot '{session_root.as_posix()}' -RepoRoot '{non_git_root.as_posix()}' -Task 'debug this workflow' -RunId 'run-sidecar' -WindowId 'discussion' -Stage 'deep_interview' -SourceArtifactPath '{source_artifact.as_posix()}' -Policy $runtime.specialist_consultation_policy; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )

            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            assert_live_consultation_result(self, result, entrypoint_path=entrypoint_path, expected_cwd=non_git_root)
            codex_home_line = require_preview_line(result["stdout_preview"], "CODEX_HOME=")
            codex_home = codex_home_line.split("=", 1)[1]
            self.assertNotIn(str(session_root), codex_home)
            self.assertNotIn(str(artifact_root), codex_home)
            self.assertFalse(Path(codex_home).exists())
            skill_surface_line = require_preview_line(result["stdout_preview"], "SKILL_SURFACE=")
            skill_surface = skill_surface_line.split("=", 1)[1]
            self.assertFalse(Path(skill_surface).exists())
            self.assertEqual("SKILL.md", Path(skill_surface).name)

    def test_specialist_consultation_unit_seeds_sidecar_codex_home_from_current_host(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            fake_codex = create_codex_home_seed_verifying_fake_consultation_command(artifact_root)
            source_codex_home = artifact_root / "source-codex-home"
            (source_codex_home / "config").mkdir(parents=True, exist_ok=True)
            (source_codex_home / "mcp").mkdir(parents=True, exist_ok=True)
            (source_codex_home / "config.toml").write_text("# config-seed-marker\n", encoding="utf-8")
            (source_codex_home / "auth.json").write_text("{\"marker\":\"auth-seed-marker\"}\n", encoding="utf-8")
            (source_codex_home / "config" / "seed.json").write_text("{\"marker\":\"config-dir\"}\n", encoding="utf-8")
            (source_codex_home / "mcp" / "seed.json").write_text("{\"marker\":\"mcp-dir\"}\n", encoding="utf-8")
            non_git_root = artifact_root / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            session_root = artifact_root / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            skill_root = artifact_root / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            source_artifact = artifact_root / "intent-contract.json"
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")
            source_artifact.write_text("{\"goal\":\"demo\"}\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"{consultation_native_subprocess_test_overrides()}"
                "$consultation = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                f"skill_root = '{skill_root.as_posix()}'; "
                "consultation_reason = 'verify codex sidecar home seed'; "
                "consultation_scope = 'bounded consultation'; "
                "consultation_role = 'discussion_consultant'; "
                "required_inputs = @('source_artifact'); "
                "expected_outputs = @('consultation_notes'); "
                "verification_expectation = 'Return structured consultation output.' "
                "}; "
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$result = Invoke-VibeSpecialistConsultationUnit -UnitId 'consult-seed-unit' -Consultation $consultation -SessionRoot '{session_root.as_posix()}' -RepoRoot '{non_git_root.as_posix()}' -Task 'debug this workflow' -RunId 'run-seed' -WindowId 'discussion' -Stage 'deep_interview' -SourceArtifactPath '{source_artifact.as_posix()}' -Policy $runtime.specialist_consultation_policy; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )

            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "CODEX_HOME": str(source_codex_home),
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            assert_live_consultation_result(self, result, entrypoint_path=entrypoint_path, expected_cwd=non_git_root)
            codex_home_line = require_preview_line(result["stdout_preview"], "CODEX_HOME=")
            codex_home = codex_home_line.split("=", 1)[1]
            self.assertIn("CODEX_HOME_SEEDED=1", list(result["stdout_preview"]))
            self.assertFalse(Path(codex_home).exists())

    def test_runtime_projects_consultation_truth_into_summary_requirement_and_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            payload = run_runtime(
                SPECIALIST_TASK,
                artifact_root,
                extra_env={
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                },
            )
            summary = payload["summary"]
            artifacts = summary["artifacts"]

            self.assertIn("discussion_specialist_consultation", artifacts)
            self.assertIn("planning_specialist_consultation", artifacts)
            self.assertIn("specialist_lifecycle_disclosure", artifacts)

            discussion_receipt = load_json(artifacts["discussion_specialist_consultation"])
            planning_receipt = load_json(artifacts["planning_specialist_consultation"])
            lifecycle_disclosure = load_json(artifacts["specialist_lifecycle_disclosure"])
            requirement_receipt = load_json(artifacts["requirement_receipt"])
            plan_receipt = load_json(artifacts["execution_plan_receipt"])
            requirement_doc = Path(artifacts["requirement_doc"]).read_text(encoding="utf-8")
            execution_plan = Path(artifacts["execution_plan"]).read_text(encoding="utf-8")

            for receipt in (discussion_receipt, planning_receipt):
                self.assertTrue(bool(receipt["enabled"]))
                self.assertGreaterEqual(len(list(receipt["approved_consultation"])), 1)
                self.assertEqual([], list(receipt["consulted_units"]))
                self.assertGreaterEqual(len(list(receipt["routed_units"])), 1)
                self.assertGreaterEqual(len(list(receipt["user_disclosures"])), 1)
                disclosure = next(
                    item for item in list(receipt["user_disclosures"]) if item["skill_id"] == "systematic-debugging"
                )
                self.assertTrue(disclosure["why_now"])
                self.assertTrue(Path(disclosure["native_skill_entrypoint"]).is_absolute())
                self.assertTrue(Path(disclosure["native_skill_entrypoint"]).exists())

            specialist_consultation = summary["specialist_consultation"]
            self.assertTrue(bool(specialist_consultation["enabled"]))
            self.assertEqual(2, int(specialist_consultation["window_count"]))
            self.assertEqual(
                ["discussion", "planning"],
                [str(window["window_id"]) for window in list(specialist_consultation["windows"])],
            )
            self.assertEqual(0, int(specialist_consultation["consulted_unit_count"]))
            self.assertGreaterEqual(int(specialist_consultation["routed_unit_count"]), 2)
            self.assertGreaterEqual(int(specialist_consultation["user_disclosure_count"]), 2)
            self.assertNotIn("specialist_consultation", summary["specialist_user_disclosure"])

            specialist_lifecycle = summary["specialist_lifecycle_disclosure"]
            self.assertTrue(bool(specialist_lifecycle["enabled"]))
            self.assertEqual("routing_consultation_execution_separated", specialist_lifecycle["truth_model"])
            self.assertEqual(
                ["discussion_routing", "discussion_consultation", "planning_consultation", "execution_dispatch"],
                [str(layer["layer_id"]) for layer in list(specialist_lifecycle["layers"])],
            )
            self.assertGreaterEqual(int(specialist_lifecycle["skill_count"]), 1)
            self.assertIn("systematic-debugging", specialist_lifecycle["rendered_text"])
            self.assertEqual("routing_consultation_execution_separated", lifecycle_disclosure["truth_model"])
            routing_layer = next(
                item for item in list(lifecycle_disclosure["layers"]) if item["layer_id"] == "discussion_routing"
            )
            routed_entry = next(
                item for item in list(routing_layer["skills"]) if item["skill_id"] == "systematic-debugging"
            )
            self.assertTrue(routed_entry["why_now"])
            self.assertTrue(Path(routed_entry["native_skill_entrypoint"]).is_absolute())
            self.assertTrue(Path(routed_entry["native_skill_entrypoint"]).exists())

            self.assertEqual(artifacts["discussion_specialist_consultation"], requirement_receipt["discussion_consultation_path"])
            self.assertEqual(artifacts["planning_specialist_consultation"], plan_receipt["planning_consultation_path"])
            self.assertEqual(artifacts["specialist_lifecycle_disclosure"], requirement_receipt["specialist_lifecycle_disclosure_path"])
            self.assertEqual(artifacts["specialist_lifecycle_disclosure"], plan_receipt["specialist_lifecycle_disclosure_path"])
            self.assertIn("host_stage_disclosure", artifacts)
            host_stage_disclosure = load_json(artifacts["host_stage_disclosure"])
            self.assertTrue(bool(host_stage_disclosure["enabled"]))
            self.assertEqual("progressive_host_stage_disclosure", host_stage_disclosure["mode"])
            self.assertEqual(4, int(host_stage_disclosure["event_count"]))
            self.assertEqual(4, int(host_stage_disclosure["last_sequence"]))
            self.assertEqual(
                [
                    "discussion_routing_frozen",
                    "discussion_consultation_routed",
                    "planning_consultation_routed",
                    "execution_dispatch_confirmed",
                ],
                [str(event["event_id"]) for event in list(host_stage_disclosure["events"])],
            )
            self.assertEqual(
                ["discussion_routing", "discussion_consultation", "planning_consultation", "execution_dispatch"],
                [str(event["segment_id"]) for event in list(host_stage_disclosure["events"])],
            )
            self.assertEqual([1, 2, 3, 4], [int(event["sequence"]) for event in list(host_stage_disclosure["events"])])
            self.assertIn("Vibe routed these Skills", host_stage_disclosure["rendered_text"])
            self.assertIn("Vibe approved these Skills for execution", host_stage_disclosure["rendered_text"])
            execution_event = next(
                item for item in list(host_stage_disclosure["events"]) if item["segment_id"] == "execution_dispatch"
            )
            routed_skill = next(item for item in list(execution_event["skills"]) if item["skill_id"] == "systematic-debugging")
            self.assertTrue(Path(routed_skill["native_skill_entrypoint"]).is_absolute())
            self.assertTrue(Path(routed_skill["native_skill_entrypoint"]).exists())
            self.assertEqual(host_stage_disclosure, summary["host_stage_disclosure"])
            self.assertIn("host_user_briefing", artifacts)
            host_user_briefing_doc = Path(artifacts["host_user_briefing"]).read_text(encoding="utf-8")
            host_user_briefing = summary["host_user_briefing"]
            self.assertTrue(bool(host_user_briefing["enabled"]))
            self.assertTrue(bool(host_user_briefing["freeze_gate_passed"]))
            self.assertEqual(
                ["execution_handoff", "discussion_routing", "discussion_consultation", "planning_consultation", "execution_dispatch"],
                [str(segment["segment_id"]) for segment in list(host_user_briefing["segments"])],
            )
            self.assertIn("Execution handoff is still pending under governed vibe.", host_user_briefing["rendered_text"])
            self.assertIn("Vibe routed these Skills", host_user_briefing["rendered_text"])
            self.assertIn(
                "Vibe routed these Skills for direct current-session consultation during discussion",
                host_user_briefing["rendered_text"],
            )
            self.assertIn(
                "Do not replace this path with Skill(systematic-debugging) unless that skill name is explicitly visible in the host registry.",
                host_user_briefing["rendered_text"],
            )
            self.assertIn("freeze gate: passed", host_user_briefing["rendered_text"])
            self.assertIn("Vibe approved these Skills for execution", host_user_briefing["rendered_text"])
            self.assertIn("systematic-debugging", host_user_briefing["rendered_text"])
            self.assertIn(host_user_briefing["rendered_text"], host_user_briefing_doc)
            self.assertEqual(artifacts["host_user_briefing"], payload["host_user_briefing_path"])
            self.assertEqual(host_user_briefing, payload["host_user_briefing"])
            self.assertIn("## Specialist Consultation", requirement_doc)
            self.assertIn("## Specialist Consultation", execution_plan)
            self.assertIn("## Unified Specialist Lifecycle Disclosure", requirement_doc)
            self.assertIn("## Unified Specialist Lifecycle Disclosure", execution_plan)
            self.assertIn("systematic-debugging", requirement_doc)
            self.assertIn("systematic-debugging", execution_plan)

    def test_live_consultation_with_empty_guidance_routes_directly_and_keeps_freeze_gate_green(self) -> None:
        shell = resolve_powershell()
        if shell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            freeze_payload = freeze_runtime_packet(SPECIALIST_TASK, artifact_root)
            packet_path = Path(freeze_payload["packet_path"])
            run_id = "pytest-consult-window-invalid-" + uuid.uuid4().hex[:10]
            prompt_seed_path = artifact_root / "discussion-seed.md"
            prompt_seed_path.write_text("# Intent\nNeed systematic debugging guidance before freezing requirements.\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". {_ps_single_quote(str(RUNTIME_COMMON))}; "
                f". {_ps_single_quote(str(EXECUTION_COMMON))}; "
                f". {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$runtime = Get-VibeRuntimeContext -ScriptPath {_ps_single_quote(str(CONSULTATION_SCRIPT))}; "
                f"$packet = Get-Content -LiteralPath {_ps_single_quote(str(packet_path))} -Raw -Encoding UTF8 | ConvertFrom-Json; "
                f"$sessionRoot = Ensure-VibeSessionRoot -RepoRoot $runtime.repo_root -RunId {_ps_single_quote(run_id)} -Runtime $runtime -ArtifactRoot {_ps_single_quote(str(artifact_root))}; "
                f"$result = Invoke-VibeSpecialistConsultationWindow "
                f"-Task {_ps_single_quote(SPECIALIST_TASK)} "
                f"-RunId {_ps_single_quote(run_id)} "
                f"-SessionRoot $sessionRoot "
                f"-RepoRoot $runtime.repo_root "
                f"-WindowId 'discussion' "
                f"-Stage 'deep_interview' "
                f"-SourceArtifactPath {_ps_single_quote(str(prompt_seed_path))} "
                f"-Recommendations @($packet.specialist_recommendations | Where-Object {{ [string]$_.skill_id -eq 'systematic-debugging' }}) "
                f"-Policy $runtime.specialist_consultation_policy; "
                "$result | ConvertTo-Json -Depth 20 }"
            )
            completed = subprocess.run(
                [shell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                },
            )
            payload = json.loads(completed.stdout)
            receipt = load_json(payload["receipt_path"])

            self.assertEqual([], list(receipt["consulted_units"]))
            self.assertEqual([], list(receipt["degraded"]))
            self.assertGreaterEqual(len(list(receipt["routed_units"])), 1)
            routed = require_skill_entry(receipt["routed_units"], "systematic-debugging")
            assert_direct_routed_result(self, routed)
            self.assertIn("freeze_gate", receipt)
            self.assertTrue(bool(receipt["freeze_gate"]["passed"]))
            self.assertEqual([], list(receipt["freeze_gate"]["errors"]))

    def test_runtime_keeps_freeze_green_when_live_consultation_routes_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_root = Path(tempdir)
            completed = run_runtime(
                SPECIALIST_TASK,
                artifact_root,
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "host_subprocess",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                },
                check=False,
            )

            self.assertEqual(0, completed.returncode)
            payload = json.loads(completed.stdout)
            discussion_receipt = load_json(payload["summary"]["artifacts"]["discussion_specialist_consultation"])
            self.assertEqual([], list(discussion_receipt["consulted_units"]))
            self.assertEqual([], list(discussion_receipt["degraded"]))
            self.assertTrue(bool(discussion_receipt["freeze_gate"]["passed"]))
            routed = require_skill_entry(discussion_receipt["routed_units"], "systematic-debugging")
            assert_direct_routed_result(self, routed)
            combined_output = f"{completed.stdout}\n{completed.stderr}"
            self.assertNotIn("specialist consultation freeze gate failed", combined_output)
