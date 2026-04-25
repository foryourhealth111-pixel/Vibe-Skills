from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT_PS1 = REPO_ROOT / "install.ps1"
RUNTIME_TASK = "Debug installed runtime remap behavior before proposing fixes. $vibe"
HOST_HOME_ENV = {
    "claude-code": "CLAUDE_HOME",
}
HOST_BRIDGE_ENV = {
    "claude-code": "VGO_CLAUDE_CODE_SPECIALIST_BRIDGE_COMMAND",
}


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


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
        bridge_path.chmod(0o755)
    return bridge_path


def install_claude_runtime(target_root: Path, env: dict[str, str]) -> Path:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    subprocess.run(
        [
            shell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALL_SCRIPT_PS1),
            "-HostId",
            "claude-code",
            "-Profile",
            "full",
            "-TargetRoot",
            str(target_root),
            "-RequireClosedReady",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        env=env,
    )
    return target_root / "skills" / "vibe"


def run_installed_runtime(installed_root: Path, *, artifact_root: Path, env: dict[str, str]) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-installed-remap-{uuid.uuid4().hex[:8]}"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "& { "
            f"$result = & {ps_quote(installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1')} "
            f"-Task {ps_quote(RUNTIME_TASK)} "
            "-Mode interactive_governed "
            f"-RunId {ps_quote(run_id)} "
            f"-ArtifactRoot {ps_quote(artifact_root)}; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(f"installed invoke-vibe-runtime returned null payload. stderr={completed.stderr.strip()}")
    return json.loads(stdout)


class InstalledRuntimePolicyRemapTests(unittest.TestCase):
    def test_claude_installed_runtime_remaps_repo_only_freshness_gate(self) -> None:
        sandbox_root = REPO_ROOT.parent / ".pytest-tmp-installed-runtime"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        tempdir = tempfile.TemporaryDirectory(dir=str(sandbox_root))
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        target_root = root / "claude-home"
        bridge_root = root / "bridges"
        target_root.mkdir(parents=True, exist_ok=True)
        bridge_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env[HOST_HOME_ENV["claude-code"]] = str(target_root)
        env[HOST_BRIDGE_ENV["claude-code"]] = str(create_fake_bridge(bridge_root, "claude-code"))

        installed_root = install_claude_runtime(target_root, env)
        payload = run_installed_runtime(
            installed_root,
            artifact_root=target_root / ".vibeskills" / "simulated-remap",
            env={
                **env,
                "VCO_HOST_ID": "claude-code",
                "VGO_NATIVE_SPECIALIST_EXECUTION_MODE": "",
                "VGO_SPECIALIST_CONSULTATION_MODE": "",
                "VGO_ENABLE_NATIVE_SPECIALIST_EXECUTION": "1",
                "VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION": "0",
            },
        )

        execution_manifest_path = Path(payload["summary"]["artifacts"]["execution_manifest"])
        execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
        unit_ids = {
            str(unit["unit_id"])
            for wave in execution_manifest.get("waves") or []
            for unit in wave.get("units") or []
        }

        self.assertIn("installed-runtime-freshness-gate", unit_ids)
        self.assertNotIn("runtime-neutral-freshness-gate-tests", unit_ids)


if __name__ == "__main__":
    unittest.main()
