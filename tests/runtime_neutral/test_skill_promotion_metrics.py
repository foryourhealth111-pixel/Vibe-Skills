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
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
PLAN_EXECUTE_SCRIPT = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
ML_PROMPT = (
    "Build a scikit-learn tabular classification baseline, "
    "run feature selection, and compare cross-validation metrics."
)
DESTRUCTIVE_PROMPT = (
    "Delete the old generated artifacts, remove the obsolete branch, "
    "and overwrite the install settings to reset the environment."
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


def run_runtime(task: str, artifact_root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = "pytest-metrics-" + uuid.uuid4().hex[:10]
    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "& { "
                f"$result = & '{RUNTIME_ENTRY}' "
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
        env={**os.environ, **(extra_env or {})},
    )
    return json.loads(completed.stdout)


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def run_powershell_json(script_body: str) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    completed = subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            script_body,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def extract_expression(pattern: str) -> str:
    content = PLAN_EXECUTE_SCRIPT.read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise AssertionError(f"Unable to extract expression with pattern: {pattern}")
    return match.group(1).strip()


class SkillPromotionMetricsTests(unittest.TestCase):
    def test_metrics_capture_match_surface_dispatch_and_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            payload = run_runtime(
                ML_PROMPT,
                temp_path,
                extra_env={
                    "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            funnel = execution_manifest["specialist_accounting"]["promotion_funnel"]
            self.assertGreaterEqual(int(funnel["matched"]), 1)
            self.assertGreaterEqual(int(funnel["surfaced"]), int(funnel["matched"]))
            self.assertGreaterEqual(int(funnel["dispatched"]), 1)
            self.assertEqual(0, int(funnel["executed"]))
            self.assertGreaterEqual(int(funnel["routed"]), 1)
            self.assertEqual(0, int(funnel["ghost_match"]))

    def test_metrics_record_destructive_block_instead_of_ghost_match(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(DESTRUCTIVE_PROMPT, Path(tempdir))
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            funnel = execution_manifest["specialist_accounting"]["promotion_funnel"]
            self.assertEqual(0, int(funnel["ghost_match"]))
            self.assertGreaterEqual(int(funnel["blocked_due_to_destructive"]), 1)
            self.assertEqual(0, int(funnel["executed"]))

    def test_specialist_dispatch_outcomes_do_not_duplicate_degraded_results(self) -> None:
        degraded_expr = extract_expression(r"^\$degradedSpecialistUnits = (.+)$")
        non_degraded_expr = extract_expression(r"^\$nonDegradedExecutedSpecialistUnits = (.+)$")
        outcomes_expr = extract_expression(r"^\s*specialist_dispatch_outcomes = (.+)$")
        payload = run_powershell_json(
            (
                "& { "
                "$executedSpecialistUnits = @("
                "[pscustomobject]@{ unit_id = 'exec-degraded'; skill_id = 'demo'; degraded = $true; result_path = 'exec-degraded.json' },"
                "[pscustomobject]@{ unit_id = 'exec-ok'; skill_id = 'demo'; degraded = $false; result_path = 'exec-ok.json' }"
                "); "
                "$blockedSpecialistUnits = @(); "
                "$preDispatchDegradedUnits = @("
                "[pscustomobject]@{ unit_id = 'pre-degraded'; skill_id = 'demo'; degraded = $true; result_path = 'pre-degraded.json' }"
                "); "
                f"$degradedSpecialistUnits = {degraded_expr}; "
                f"$nonDegradedExecutedSpecialistUnits = {non_degraded_expr}; "
                f"$specialist_dispatch_outcomes = {outcomes_expr}; "
                "[pscustomobject]@{ "
                "result_paths = @($specialist_dispatch_outcomes | ForEach-Object { [string]$_.result_path }); "
                "degraded_paths = @($degradedSpecialistUnits | ForEach-Object { [string]$_.result_path }) "
                "} | ConvertTo-Json -Depth 20 }"
            )
        )

        self.assertEqual(
            len(payload["result_paths"]),
            len(set(payload["result_paths"])),
            msg=f"duplicate outcome paths: {payload['result_paths']}",
        )
