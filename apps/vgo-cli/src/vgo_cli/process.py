from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Sequence
import warnings

from .errors import CliError


REPO_ROOT = Path(__file__).resolve().parents[4]
POWERSHELL_HOST_POLICY_PATH = REPO_ROOT / "config" / "powershell-host-policy.json"
POWERSHELL_HOST_POLICY_DEFAULTS: dict[str, Any] = {
    "preferred_powershell_host": "pwsh",
    "require_pwsh_on_non_windows": True,
    "allow_windows_powershell_fallback": True,
    "record_host_resolution_artifacts": True,
}
SUPPORTED_POWERSHELL_HOSTS = frozenset({"pwsh", "windows-powershell"})


def _powershell_host_policy() -> dict[str, Any]:
    policy = dict(POWERSHELL_HOST_POLICY_DEFAULTS)
    try:
        raw_payload = POWERSHELL_HOST_POLICY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        warnings.warn(
            f"PowerShell host policy file not found: {POWERSHELL_HOST_POLICY_PATH}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy
    except OSError as exc:
        warnings.warn(
            f"Failed to read PowerShell host policy {POWERSHELL_HOST_POLICY_PATH}: {exc}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        warnings.warn(
            f"Invalid JSON in PowerShell host policy {POWERSHELL_HOST_POLICY_PATH}: {exc}; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    if not isinstance(payload, dict):
        warnings.warn(
            f"PowerShell host policy {POWERSHELL_HOST_POLICY_PATH} must contain a JSON object; using defaults",
            RuntimeWarning,
            stacklevel=2,
        )
        return policy

    preferred_host = str(payload.get("preferred_powershell_host", "")).strip().lower()
    if preferred_host in SUPPORTED_POWERSHELL_HOSTS:
        policy["preferred_powershell_host"] = preferred_host
    elif preferred_host:
        warnings.warn(
            (
                f"Unsupported preferred_powershell_host in {POWERSHELL_HOST_POLICY_PATH}: "
                f"{preferred_host!r}; using default"
            ),
            RuntimeWarning,
            stacklevel=2,
        )
    for key in (
        "require_pwsh_on_non_windows",
        "allow_windows_powershell_fallback",
        "record_host_resolution_artifacts",
    ):
        if key in payload:
            if isinstance(payload[key], bool):
                policy[key] = payload[key]
            else:
                warnings.warn(
                    f"PowerShell host policy field {key} must be boolean; using default",
                    RuntimeWarning,
                    stacklevel=2,
                )
    return policy


def _is_windows_host() -> bool:
    return os.name == "nt"


def choose_powershell(*, return_diagnostics: bool = False) -> str | dict[str, Any] | None:
    policy = _powershell_host_policy()
    is_windows = _is_windows_host()
    prefer_pwsh = str(policy["preferred_powershell_host"]).strip().lower() == "pwsh"
    pwsh_candidates: list[tuple[str, str | None, str]] = [
        ("path-pwsh", shutil.which("pwsh"), "pwsh"),
        ("path-pwsh-exe", shutil.which("pwsh.exe"), "pwsh"),
    ]
    if is_windows:
        pwsh_candidates.extend(
            [
                ("default-pwsh", r"C:\Program Files\PowerShell\7\pwsh.exe", "pwsh"),
                ("preview-pwsh", r"C:\Program Files\PowerShell\7-preview\pwsh.exe", "pwsh"),
            ]
        )
    windows_powershell_candidates: list[tuple[str, str | None, str]] = []
    if is_windows:
        windows_powershell_candidates.extend(
            [
                ("path-powershell", shutil.which("powershell"), "windows-powershell"),
                ("path-powershell-exe", shutil.which("powershell.exe"), "windows-powershell"),
            ]
        )
    candidates: list[tuple[str, str | None, str]] = []
    if prefer_pwsh:
        candidates.extend(pwsh_candidates)
        if is_windows and policy["allow_windows_powershell_fallback"]:
            candidates.extend(windows_powershell_candidates)
    elif is_windows:
        candidates.extend(windows_powershell_candidates)

    checked: list[dict[str, Any]] = []
    for name, candidate, kind in candidates:
        resolved = str(Path(candidate)) if candidate else None
        exists = bool(resolved and Path(resolved).exists())
        is_file = bool(resolved and Path(resolved).is_file())
        checked.append(
            {
                "candidate_name": name,
                "candidate_kind": kind,
                "candidate_path": resolved,
                "exists": exists,
                "is_file": is_file,
            }
        )
        if exists and is_file:
            diagnostics = {
                "host_path": resolved,
                "host_kind": kind,
                "fallback_used": kind == "windows-powershell",
                "candidates_checked": checked,
                "policy": policy,
            }
            return diagnostics if return_diagnostics else resolved

    if not is_windows and policy["require_pwsh_on_non_windows"]:
        if return_diagnostics:
            return {
                "host_path": None,
                "host_kind": None,
                "fallback_used": False,
                "candidates_checked": checked,
                "policy": policy,
                "error": "pwsh is required on non-Windows hosts",
            }
        return None

    if return_diagnostics:
        return {
            "host_path": None,
            "host_kind": None,
            "fallback_used": False,
            "candidates_checked": checked,
            "policy": policy,
        }
    return None


def print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def run_subprocess(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), cwd=cwd, capture_output=True, text=True)


def invoke_python_core(
    main_fn: Callable[[Sequence[str] | None], int | None],
    argv: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    exit_code = 0
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            result = main_fn(list(argv))
        except SystemExit as exc:
            code = exc.code
            if code is None:
                exit_code = 0
            elif isinstance(code, int):
                exit_code = code
            else:
                stderr_buffer.write(str(code))
                exit_code = 1
        else:
            exit_code = int(result or 0)
    return subprocess.CompletedProcess(
        args=list(argv),
        returncode=exit_code,
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
    )


def run_powershell_file(script_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    resolution = choose_powershell(return_diagnostics=True)
    if not isinstance(resolution, dict) or not resolution.get("host_path"):
        checked = []
        if isinstance(resolution, dict):
            checked = [
                entry.get("candidate_path") or entry.get("candidate_name") or "<unknown>"
                for entry in resolution.get("candidates_checked", [])
            ]
        detail = f"; candidates checked: {', '.join(checked)}" if checked else ""
        raise CliError(f"PowerShell is required to run: {script_path}{detail}")
    shell_path = str(resolution["host_path"])
    leaf = Path(shell_path).name.lower()
    command = [shell_path, '-NoProfile']
    if leaf.startswith('powershell'):
        command += ['-ExecutionPolicy', 'Bypass']
    command += ['-File', str(script_path), *args]
    return run_subprocess(command)
