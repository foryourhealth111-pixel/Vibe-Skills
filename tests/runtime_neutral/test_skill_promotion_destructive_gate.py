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
RUNTIME_ENTRY = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
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

    run_id = "pytest-promotion-" + uuid.uuid4().hex[:10]
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


def as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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


class SkillPromotionDestructiveGateTests(unittest.TestCase):
    def test_destructive_match_is_blocked_with_artifact_backed_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = run_runtime(DESTRUCTIVE_PROMPT, Path(tempdir))
            summary = payload["summary"]
            runtime_input = load_json(summary["artifacts"]["runtime_input_packet"])
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])

            dispatch = runtime_input["specialist_dispatch"]
            self.assertEqual([], list(dispatch["approved_dispatch"]))
            self.assertGreaterEqual(len(as_list(dispatch["blocked_skill_ids"])), 1)
            self.assertEqual([], as_list(dispatch["ghost_match_skill_ids"]))

            specialist_accounting = execution_manifest["specialist_accounting"]
            self.assertGreaterEqual(int(specialist_accounting["blocked_specialist_unit_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["approved_dispatch_count"]))

            blocked_units = list(specialist_accounting["blocked_specialist_units"])
            self.assertGreaterEqual(len(blocked_units), 1)
            first_blocked = load_json(blocked_units[0]["result_path"])
            self.assertEqual("blocked", first_blocked["status"])

    def test_non_destructive_match_can_execute_live_after_auto_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            fake_codex = create_fake_codex_command(temp_path)
            payload = run_runtime(
                ML_PROMPT,
                temp_path,
                extra_env={
                    "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                    "VGO_SPECIALIST_CONSULTATION_MODE": "",
                    "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
                    "VGO_CODEX_EXECUTABLE": str(fake_codex),
                },
            )
            summary = payload["summary"]
            execution_manifest = load_json(summary["artifacts"]["execution_manifest"])
            specialist_accounting = execution_manifest["specialist_accounting"]

            self.assertGreaterEqual(int(specialist_accounting["approved_dispatch_count"]), 1)
            self.assertEqual(0, int(specialist_accounting["executed_specialist_unit_count"]))
            self.assertGreaterEqual(int(specialist_accounting["direct_routed_specialist_unit_count"]), 1)
            self.assertEqual("direct_current_session_routed", specialist_accounting["effective_execution_status"])
