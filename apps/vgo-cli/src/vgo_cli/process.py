from __future__ import annotations

import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Sequence

from .errors import CliError


def choose_powershell() -> str | None:
    candidates = [
        shutil.which('pwsh'),
        shutil.which('pwsh.exe'),
        shutil.which('powershell'),
        shutil.which('powershell.exe'),
        r'C:\Program Files\PowerShell\7\pwsh.exe',
        r'C:\Program Files\PowerShell\7-preview\pwsh.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
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
    shell_path = choose_powershell()
    if not shell_path:
        raise CliError(f'PowerShell is required to run: {script_path}')
    leaf = Path(shell_path).name.lower()
    command = [shell_path, '-NoProfile']
    if leaf.startswith('powershell'):
        command += ['-ExecutionPolicy', 'Bypass']
    command += ['-File', str(script_path), *args]
    return run_subprocess(command)
