from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
import uuid
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


def extract_powershell_function(script_path: Path, function_name: str) -> str:
    text = script_path.read_text(encoding="utf-8")
    match = re.search(rf"function\s+{re.escape(function_name)}\s*\{{", text)
    if match is None:
        raise AssertionError(f"Function {function_name} not found in {script_path}")

    start = match.start()
    index = match.end() - 1
    depth = 0
    while index < len(text):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                index += 1
                break
        index += 1
    return text[start:index]


def require_preview_line(preview_lines: object, prefix: str) -> str:
    normalized = [str(line) for line in list(preview_lines)]
    line = next((line for line in normalized if line.startswith(prefix)), None)
    if line is None:
        raise AssertionError(f"{prefix} line not found in preview: {normalized}")
    return line


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
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Executed specialist from a non-git workspace.\",\"verification_notes\":[\"Repo-check bypass was applied only for this codex exec.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Execution stayed bounded to the provided artifacts.\"]}\r\n"
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
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Executed specialist from a non-git workspace.\",\"verification_notes\":[\"Repo-check bypass was applied only for this codex exec.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Execution stayed bounded to the provided artifacts.\"]}' > \"$OUT\"\n"
            "printf 'fake codex repo-check ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_codex_home_verifying_fake_dispatch_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-home-dispatch{suffix}"
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
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Executed specialist from a bounded sidecar home.\",\"verification_notes\":[\"Execution used a writable CODEX_HOME sidecar.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Specialist skill surface was materialized before launch.\"]}\r\n"
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
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Executed specialist from a bounded sidecar home.\",\"verification_notes\":[\"Execution used a writable CODEX_HOME sidecar.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Specialist skill surface was materialized before launch.\"]}' > \"$OUT\"\n"
            "printf 'CODEX_HOME=%s\\n' \"$CODEX_HOME\"\n"
            "printf 'SKILL_SURFACE=%s\\n' \"$CODEX_HOME/skills/systematic-debugging/SKILL.md\"\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def create_codex_home_seed_verifying_fake_dispatch_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex-home-seed-dispatch{suffix}"
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
            "if not exist \"%CODEX_HOME%\\config.toml\" exit /b 4\r\n"
            "findstr /c:\"config-seed-marker\" \"%CODEX_HOME%\\config.toml\" >nul || exit /b 5\r\n"
            "if not exist \"%CODEX_HOME%\\auth.json\" exit /b 6\r\n"
            "findstr /c:\"auth-seed-marker\" \"%CODEX_HOME%\\auth.json\" >nul || exit /b 7\r\n"
            "if not exist \"%CODEX_HOME%\\config\\seed.json\" exit /b 8\r\n"
            "if not exist \"%CODEX_HOME%\\mcp\\seed.json\" exit /b 9\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"Executed specialist from a seeded codex home.\",\"verification_notes\":[\"Execution used copied auth and config in the sidecar.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Sidecar was seeded from the current host codex home before launch.\"]}\r\n"
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
            "  exit 4\n"
            "fi\n"
            "grep -q 'config-seed-marker' \"$CODEX_HOME/config.toml\" || exit 5\n"
            "if [ ! -f \"$CODEX_HOME/auth.json\" ]; then\n"
            "  exit 6\n"
            "fi\n"
            "grep -q 'auth-seed-marker' \"$CODEX_HOME/auth.json\" || exit 7\n"
            "if [ ! -f \"$CODEX_HOME/config/seed.json\" ]; then\n"
            "  exit 8\n"
            "fi\n"
            "if [ ! -f \"$CODEX_HOME/mcp/seed.json\" ]; then\n"
            "  exit 9\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"Executed specialist from a seeded codex home.\",\"verification_notes\":[\"Execution used copied auth and config in the sidecar.\"],\"changed_files\":[],\"bounded_output_notes\":[\"Sidecar was seeded from the current host codex home before launch.\"]}' > \"$OUT\"\n"
            "printf 'CODEX_HOME=%s\\n' \"$CODEX_HOME\"\n"
            "printf 'CODEX_HOME_SEEDED=1\\n'\n",
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


class PlanExecuteReceiptTests(unittest.TestCase):
    def test_native_specialist_prompt_references_declared_entrypoint_rule(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
        function_body = extract_powershell_function(common_path, "New-VibeNativeSpecialistPrompt")

        ps_script = (
            "& { "
            f". '{common_path}'; "
            f"{function_body} "
            "$dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "bounded_role = 'specialist_assist'; "
            "native_skill_entrypoint = '/tmp/demo/SKILL.runtime-mirror.md'; "
            "skill_root = '/tmp/demo'; "
            "visibility_class = 'path_resolved'; "
            "native_usage_required = $true; "
            "usage_required = $true; "
            "must_preserve_workflow = $true; "
            "required_inputs = @('input'); "
            "expected_outputs = @('output'); "
            "verification_expectation = 'verify'; "
            "progressive_load_policy = @('Open the specialist /tmp/demo/SKILL.runtime-mirror.md entrypoint first.') "
            "}; "
            "$prompt = New-VibeNativeSpecialistPrompt "
            "-Dispatch $dispatch "
            "-RequirementDocPath 'req.md' "
            "-ExecutionPlanPath 'plan.md' "
            "-GovernanceScope 'root' "
            "-WriteScope 'scope' "
            "-RunId 'run-1'; "
            "$prompt }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        prompt = completed.stdout
        self.assertIn(
            "- Open the declared native_skill_entrypoint before doing bounded specialist work.",
            prompt,
        )
        self.assertNotIn("- Open the specialist SKILL.md entrypoint before doing bounded specialist work.", prompt)

    def test_convert_to_vibe_executed_unit_receipt_preserves_prompt_injection_fields(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        helper_path = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"
        script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
        function_body = extract_powershell_function(script_path, "ConvertTo-VibeExecutedUnitReceipt")

        ps_script = (
            "& { "
            f". '{helper_path}'; "
            f". '{common_path}'; "
            f"{function_body} "
            "$outcome = [pscustomobject]@{ "
            "lane_id = 'lane-1'; "
            "lane_entry = [pscustomobject]@{ "
            "lane_kind = 'specialist_dispatch'; "
            "source_unit_id = 'unit-1'; "
            "write_scope = 'read_only'; "
            "dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "dispatch_phase = 'plan_execute'; "
            "binding_profile = 'native'; "
            "lane_policy = 'bounded_native' "
            "} "
            "}; "
            "lane_result = [pscustomobject]@{ "
            "unit_id = 'unit-1'; "
            "status = 'degraded_non_authoritative'; "
            "exit_code = 0; "
            "timed_out = $false; "
            "verification_passed = $false; "
            "execution_driver = 'codex-cli'; "
            "live_native_execution = $false; "
            "degraded = $true; "
            "prompt_path = 'prompt.md'; "
            "prompt_injection_complete = $false; "
            "missing_prompt_injection_fields = @('skill_root', 'usage_required') "
            "}; "
            "lane_result_path = 'result.json'; "
            "lane_receipt_path = 'receipt.json' "
            "}; "
            "$receipt = ConvertTo-VibeExecutedUnitReceipt -WaveId 'wave-1' -StepId 'step-1' -Outcome $outcome; "
            "$receipt | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        receipt = json.loads(completed.stdout)
        self.assertEqual("prompt.md", receipt["prompt_path"])
        self.assertFalse(receipt["prompt_injection_complete"])
        self.assertEqual(["skill_root", "usage_required"], receipt["missing_prompt_injection_fields"])

    def test_specialist_summary_preserves_prompt_injection_fields(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        ps_script = (
            "& { "
            f". '{common_path}'; "
            "$unitReceipt = [pscustomobject]@{ "
            "unit_id = 'unit-1'; "
            "skill_id = 'systematic-debugging'; "
            "dispatch_phase = 'plan_execute'; "
            "binding_profile = 'native'; "
            "lane_policy = 'bounded_native'; "
            "result_path = 'result.json'; "
            "verification_passed = $false; "
            "execution_driver = 'codex-cli'; "
            "live_native_execution = $false; "
            "degraded = $true; "
            "prompt_path = 'prompt.md'; "
            "prompt_injection_complete = $false; "
            "missing_prompt_injection_fields = @('skill_root', 'usage_required'); "
            "lane_receipt_path = 'receipt.json' "
            "}; "
            "$laneEntry = [pscustomobject]@{ parallelizable = $true }; "
            "$summary = New-VibeExecutedSpecialistUnitSummary -UnitReceipt $unitReceipt -LaneEntry $laneEntry; "
            "$summary | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        summary = json.loads(completed.stdout)
        self.assertEqual("prompt.md", summary["prompt_path"])
        self.assertFalse(summary["prompt_injection_complete"])
        self.assertEqual(["skill_root", "usage_required"], summary["missing_prompt_injection_fields"])
        self.assertTrue(summary["parallelizable"])

    def test_degraded_specialist_without_prompt_does_not_claim_prompt_injection_complete(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        ps_script = (
            "& { "
            f". '{common_path}'; "
            "$policy = [pscustomobject]@{ "
            "degrade_contract = [pscustomobject]@{ status = 'degraded_non_authoritative'; verification_passed = $false; execution_driver = 'degraded_contract' ; hazard_alert = 'alert' } "
            "}; "
            "$dispatch = [pscustomobject]@{ "
            "skill_id = 'systematic-debugging'; "
            "bounded_role = 'specialist_assist'; "
            "native_usage_required = $true; "
            "usage_required = $true; "
            "must_preserve_workflow = $true "
            "}; "
            "$result = New-VibeDegradedSpecialistDispatchResult -UnitId 'unit-1' -Dispatch $dispatch -SessionRoot ([System.IO.Path]::GetTempPath()) -Policy $policy -Reason 'adapter_unavailable'; "
            "$result.result | ConvertTo-Json -Depth 10 }"
        )

        completed = subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        result = json.loads(completed.stdout)
        self.assertIsNone(result["prompt_path"])
        self.assertFalse(result["prompt_injection_complete"])
        self.assertEqual([], result["missing_prompt_injection_fields"])

    def test_specialist_dispatch_bypasses_codex_repo_check_for_non_git_roots(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_repo_check_fake_codex_command(temp_path)
            non_git_root = temp_path / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            session_root = temp_path / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            requirement_doc = temp_path / "requirement.md"
            execution_plan = temp_path / "plan.md"
            skill_root = temp_path / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            requirement_doc.write_text("# Requirement\n", encoding="utf-8")
            execution_plan.write_text("# Plan\n", encoding="utf-8")
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". '{common_path}'; "
                "$dispatch = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                "bounded_role = 'specialist_assist'; "
                f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                f"skill_root = '{skill_root.as_posix()}'; "
                "visibility_class = 'path_resolved'; "
                "native_usage_required = $true; "
                "usage_required = $true; "
                "must_preserve_workflow = $true; "
                "required_inputs = @('requirement_doc', 'execution_plan'); "
                "expected_outputs = @('verification_notes', 'changed_files'); "
                "verification_expectation = 'Return bounded execution guidance.'; "
                "progressive_load_policy = @('Open the declared specialist entrypoint before executing.') "
                "}; "
                f"$result = Invoke-VibeSpecialistDispatchUnit -UnitId 'unit-{uuid.uuid4().hex[:8]}' -Dispatch $dispatch -SessionRoot '{session_root.as_posix()}' -RepoRoot '{non_git_root.as_posix()}' -RequirementDocPath '{requirement_doc.as_posix()}' -ExecutionPlanPath '{execution_plan.as_posix()}' -RunId 'run-1' -GovernanceScope 'root' -WriteScope 'read_only'; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            self.assertEqual("completed", result["status"])
            self.assertTrue(result["live_native_execution"])
            self.assertEqual(non_git_root.resolve(), Path(result["cwd"]).resolve())
            self.assertIn("--skip-git-repo-check", list(result["arguments"]))
            self.assertTrue(Path(result["response_json_path"]).exists())
            self.assertEqual([], list(result["observed_changed_files"]))

    def test_delegated_lane_receipt_normalizes_legacy_usage_required_dispatch(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell not available")

        script_path = REPO_ROOT / "scripts" / "runtime" / "Invoke-DelegatedLaneUnit.ps1"

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_repo_check_fake_codex_command(temp_path)
            non_git_root = temp_path / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            lane_root = temp_path / "lane-root"
            requirement_doc = temp_path / "requirement.md"
            execution_plan = temp_path / "plan.md"
            skill_root = temp_path / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            requirement_doc.write_text("# Requirement\n", encoding="utf-8")
            execution_plan.write_text("# Plan\n", encoding="utf-8")
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")

            lane_id = "lane-" + uuid.uuid4().hex[:8]
            envelope_path = temp_path / "delegation-envelope.json"
            envelope_path.write_text(
                json.dumps(
                    {
                        "root_run_id": "root-run-1",
                        "parent_run_id": "parent-run-1",
                        "parent_unit_id": "parent-unit-1",
                        "child_run_id": lane_id,
                        "governance_scope": "child_governed",
                        "requirement_doc_path": str(requirement_doc.resolve()),
                        "execution_plan_path": str(execution_plan.resolve()),
                        "write_scope": "read_only",
                        "approved_specialists": ["systematic-debugging"],
                        "review_mode": "native_contract",
                        "prompt_tail_required": "$vibe",
                        "allow_requirement_freeze": False,
                        "allow_plan_freeze": False,
                        "allow_root_completion_claim": False,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            lane_spec_path = temp_path / "lane-spec.json"
            lane_spec_path.write_text(
                json.dumps(
                    {
                        "lane_id": lane_id,
                        "lane_kind": "specialist_dispatch",
                        "lane_root": str(lane_root.resolve()),
                        "run_id": lane_id,
                        "mode": "interactive_governed",
                        "governance_scope": "child",
                        "root_run_id": "root-run-1",
                        "parent_run_id": "parent-run-1",
                        "parent_unit_id": "parent-unit-1",
                        "requirement_doc_path": str(requirement_doc.resolve()),
                        "execution_plan_path": str(execution_plan.resolve()),
                        "repo_root": str(non_git_root.resolve()),
                        "default_timeout_seconds": 120,
                        "parallelizable": False,
                        "write_scope": "read_only",
                        "review_mode": "native_contract",
                        "delegation_envelope_path": str(envelope_path.resolve()),
                        "tokens": {},
                        "dispatch": {
                            "skill_id": "systematic-debugging",
                            "bounded_role": "specialist_assist",
                            "native_skill_entrypoint": str(entrypoint_path.resolve()),
                            "skill_root": str(skill_root.resolve()),
                            "visibility_class": "path_resolved",
                            "usage_required": True,
                            "must_preserve_workflow": True,
                            "required_inputs": ["requirement_doc", "execution_plan"],
                            "expected_outputs": ["verification_notes", "changed_files"],
                            "verification_expectation": "Return bounded execution guidance.",
                            "progressive_load_policy": [
                                "Open the declared specialist entrypoint before executing."
                            ],
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    powershell,
                    "-NoLogo",
                    "-NoProfile",
                    "-Command",
                    f"& '{script_path.as_posix()}' -LaneSpecPath '{lane_spec_path.as_posix()}'",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            payload = json.loads(completed.stdout)
            receipt = payload["receipt"]
            self.assertTrue(bool(receipt["native_usage_required"]))
            self.assertTrue(bool(receipt["usage_required"]))
            notes = Path(payload["lane_notes_path"]).read_text(encoding="utf-8")
            self.assertIn("native_usage_required: True", notes)
            self.assertIn("usage_required: True", notes)

    def test_specialist_dispatch_falls_back_to_requirement_workspace_when_repo_root_is_read_only(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_repo_check_fake_codex_command(temp_path)
            read_only_root = temp_path / "read-only-install-root"
            read_only_root.mkdir(parents=True, exist_ok=True)
            session_root = temp_path / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            requirement_doc = temp_path / "docs" / "requirements" / "requirement.md"
            execution_plan = temp_path / "docs" / "plans" / "plan.md"
            requirement_doc.parent.mkdir(parents=True, exist_ok=True)
            execution_plan.parent.mkdir(parents=True, exist_ok=True)
            skill_root = temp_path / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            requirement_doc.write_text("# Requirement\n", encoding="utf-8")
            execution_plan.write_text("# Plan\n", encoding="utf-8")
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")

            try:
                set_directory_read_only(read_only_root)

                ps_script = (
                    "& { "
                    f". '{common_path}'; "
                    "$dispatch = [pscustomobject]@{ "
                    "skill_id = 'systematic-debugging'; "
                    "bounded_role = 'specialist_assist'; "
                    f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                    f"skill_root = '{skill_root.as_posix()}'; "
                    "visibility_class = 'path_resolved'; "
                    "native_usage_required = $true; "
                    "usage_required = $true; "
                    "must_preserve_workflow = $true; "
                    "required_inputs = @('requirement_doc', 'execution_plan'); "
                    "expected_outputs = @('verification_notes', 'changed_files'); "
                    "verification_expectation = 'Return bounded execution guidance.'; "
                    "progressive_load_policy = @('Open the declared specialist entrypoint before executing.') "
                    "}; "
                    f"$result = Invoke-VibeSpecialistDispatchUnit -UnitId 'unit-{uuid.uuid4().hex[:8]}' -Dispatch $dispatch -SessionRoot '{session_root.as_posix()}' -RepoRoot '{read_only_root.as_posix()}' -RequirementDocPath '{requirement_doc.as_posix()}' -ExecutionPlanPath '{execution_plan.as_posix()}' -RunId 'run-1' -GovernanceScope 'root' -WriteScope 'read_only'; "
                    "$result.result | ConvertTo-Json -Depth 20 }"
                )

                completed = subprocess.run(
                    [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                    env={
                        **os.environ,
                        "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                        "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                        "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                        "VGO_CODEX_EXECUTABLE": str(fake_codex),
                    },
                )
            finally:
                set_directory_writable(read_only_root)

            result = json.loads(completed.stdout)
            self.assertEqual("completed", result["status"])
            self.assertEqual(temp_path.resolve(), Path(result["cwd"]).resolve())
            self.assertIn("--skip-git-repo-check", list(result["arguments"]))
            self.assertTrue(Path(result["response_json_path"]).exists())

    def test_specialist_dispatch_uses_sidecar_codex_home_with_materialized_skill_surface(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_codex_home_verifying_fake_dispatch_command(temp_path)
            non_git_root = temp_path / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            session_root = temp_path / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            requirement_doc = temp_path / "requirement.md"
            execution_plan = temp_path / "plan.md"
            skill_root = temp_path / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            requirement_doc.write_text("# Requirement\n", encoding="utf-8")
            execution_plan.write_text("# Plan\n", encoding="utf-8")
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". '{common_path}'; "
                "$dispatch = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                "bounded_role = 'specialist_assist'; "
                f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                f"skill_root = '{skill_root.as_posix()}'; "
                "visibility_class = 'path_resolved'; "
                "native_usage_required = $true; "
                "usage_required = $true; "
                "must_preserve_workflow = $true; "
                "required_inputs = @('requirement_doc', 'execution_plan'); "
                "expected_outputs = @('verification_notes', 'changed_files'); "
                "verification_expectation = 'Return bounded execution guidance.'; "
                "progressive_load_policy = @('Open the declared specialist entrypoint before executing.') "
                "}; "
                f"$result = Invoke-VibeSpecialistDispatchUnit -UnitId 'unit-sidecar' -Dispatch $dispatch -SessionRoot '{session_root.as_posix()}' -RepoRoot '{non_git_root.as_posix()}' -RequirementDocPath '{requirement_doc.as_posix()}' -ExecutionPlanPath '{execution_plan.as_posix()}' -RunId 'run-sidecar' -GovernanceScope 'root' -WriteScope 'read_only'; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={
                    **os.environ,
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            self.assertEqual("completed", result["status"])
            self.assertTrue(result["live_native_execution"])
            self.assertEqual(non_git_root.resolve(), Path(result["cwd"]).resolve())
            codex_home_line = require_preview_line(result["stdout_preview"], "CODEX_HOME=")
            codex_home = codex_home_line.split("=", 1)[1]
            self.assertNotIn(str(session_root), codex_home)
            self.assertNotIn(str(temp_path), codex_home)
            self.assertFalse(Path(codex_home).exists())
            skill_surface_line = require_preview_line(result["stdout_preview"], "SKILL_SURFACE=")
            skill_surface = skill_surface_line.split("=", 1)[1]
            self.assertFalse(Path(skill_surface).exists())
            self.assertEqual("SKILL.md", Path(skill_surface).name)

    def test_specialist_dispatch_seeds_sidecar_codex_home_from_current_host(self) -> None:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        common_path = REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1"

        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_codex_home_seed_verifying_fake_dispatch_command(temp_path)
            source_codex_home = temp_path / "source-codex-home"
            (source_codex_home / "config").mkdir(parents=True, exist_ok=True)
            (source_codex_home / "mcp").mkdir(parents=True, exist_ok=True)
            (source_codex_home / "config.toml").write_text("# config-seed-marker\n", encoding="utf-8")
            (source_codex_home / "auth.json").write_text("{\"marker\":\"auth-seed-marker\"}\n", encoding="utf-8")
            (source_codex_home / "config" / "seed.json").write_text("{\"marker\":\"config-dir\"}\n", encoding="utf-8")
            (source_codex_home / "mcp" / "seed.json").write_text("{\"marker\":\"mcp-dir\"}\n", encoding="utf-8")
            non_git_root = temp_path / "non-git-workspace"
            non_git_root.mkdir(parents=True, exist_ok=True)
            session_root = temp_path / "session"
            session_root.mkdir(parents=True, exist_ok=True)
            requirement_doc = temp_path / "requirement.md"
            execution_plan = temp_path / "plan.md"
            skill_root = temp_path / "skills" / "systematic-debugging"
            skill_root.mkdir(parents=True, exist_ok=True)
            entrypoint_path = skill_root / "SKILL.runtime-mirror.md"
            requirement_doc.write_text("# Requirement\n", encoding="utf-8")
            execution_plan.write_text("# Plan\n", encoding="utf-8")
            entrypoint_path.write_text("# Specialist\n", encoding="utf-8")

            ps_script = (
                "& { "
                f". '{common_path}'; "
                "$dispatch = [pscustomobject]@{ "
                "skill_id = 'systematic-debugging'; "
                "bounded_role = 'specialist_assist'; "
                f"native_skill_entrypoint = '{entrypoint_path.as_posix()}'; "
                f"skill_root = '{skill_root.as_posix()}'; "
                "visibility_class = 'path_resolved'; "
                "native_usage_required = $true; "
                "usage_required = $true; "
                "must_preserve_workflow = $true; "
                "required_inputs = @('requirement_doc', 'execution_plan'); "
                "expected_outputs = @('verification_notes', 'changed_files'); "
                "verification_expectation = 'Return bounded execution guidance.'; "
                "progressive_load_policy = @('Open the declared specialist entrypoint before executing.') "
                "}; "
                f"$result = Invoke-VibeSpecialistDispatchUnit -UnitId 'unit-seed' -Dispatch $dispatch -SessionRoot '{session_root.as_posix()}' -RepoRoot '{non_git_root.as_posix()}' -RequirementDocPath '{requirement_doc.as_posix()}' -ExecutionPlanPath '{execution_plan.as_posix()}' -RunId 'run-seed' -GovernanceScope 'root' -WriteScope 'read_only'; "
                "$result.result | ConvertTo-Json -Depth 20 }"
            )

            completed = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-Command", ps_script],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={
                    **os.environ,
                    "CODEX_HOME": str(source_codex_home),
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "host_subprocess",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )

            result = json.loads(completed.stdout)
            self.assertEqual("completed", result["status"])
            self.assertTrue(result["live_native_execution"])
            codex_home_line = require_preview_line(result["stdout_preview"], "CODEX_HOME=")
            codex_home = codex_home_line.split("=", 1)[1]
            self.assertIn("CODEX_HOME_SEEDED=1", list(result["stdout_preview"]))
            self.assertFalse(Path(codex_home).exists())


if __name__ == "__main__":
    unittest.main()
