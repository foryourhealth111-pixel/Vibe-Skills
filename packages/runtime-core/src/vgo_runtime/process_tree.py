from __future__ import annotations

import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Mapping, Sequence


_CLEANUP_TIMEOUT_SECONDS = 5.0
# The target starts only after the parent has assigned this waiting process to its job.
_WINDOWS_START_GATE = (
    "import subprocess, sys\n"
    "if sys.stdin.buffer.read(1) != b'1':\n"
    "    raise SystemExit(1)\n"
    "raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))\n"
)


class _JobBasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _JobIoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _JobExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimits),
        ("IoInfo", _JobIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JobAccounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in (
        "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime",
    )] + [(name, ctypes.c_uint32) for name in (
        "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses",
    )]


class _WindowsJob:
    def __init__(self) -> None:
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, ctypes.c_wchar_p], ctypes.c_void_p),
            "SetInformationJobObject": ([ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32], ctypes.c_int),
            "AssignProcessToJobObject": ([ctypes.c_void_p, ctypes.c_void_p], ctypes.c_int),
            "TerminateJobObject": ([ctypes.c_void_p, ctypes.c_uint32], ctypes.c_int),
            "QueryInformationJobObject": ([ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p], ctypes.c_int),
            "OpenProcess": ([ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32], ctypes.c_void_p),
            "CloseHandle": ([ctypes.c_void_p], ctypes.c_int),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes = arguments
            function.restype = result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _JobExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, pid: int) -> None:
        process = self.api.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def terminate_and_wait(self) -> None:
        if not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        deadline = time.monotonic() + _CLEANUP_TIMEOUT_SECONDS
        while True:
            accounting = _JobAccounting()
            if not self.api.QueryInformationJobObject(
                self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if accounting.ActiveProcesses == 0:
                return
            if time.monotonic() >= deadline:
                raise OSError("runtime bridge job did not terminate within the cleanup deadline")
            time.sleep(0.01)

    def close(self) -> None:
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _stop_process_tree(process: subprocess.Popen[bytes], job: _WindowsJob | None) -> None:
    try:
        if job is not None:
            job.terminate_and_wait()
        else:
            deadline = time.monotonic() + _CLEANUP_TIMEOUT_SECONDS
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
            while True:
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= deadline:
                    raise OSError("runtime bridge process group did not exit within the cleanup deadline")
                time.sleep(0.01)
    finally:
        if process.poll() is None:
            process.kill()


def run_process_tree(
    command: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None, timeout: float | None,
) -> subprocess.CompletedProcess[bytes]:
    """Capture one native bridge command and bound the lifetime of its process tree."""
    job = _WindowsJob() if os.name == "nt" else None
    launch_command = (
        [sys.executable, "-I", "-S", "-c", _WINDOWS_START_GATE, *command]
        if job is not None else list(command)
    )
    options = (
        {"creationflags": subprocess.CREATE_NO_WINDOW, "stdin": subprocess.PIPE}
        if job is not None else {"start_new_session": True, "stdin": subprocess.DEVNULL}
    )
    try:
        with subprocess.Popen(
            launch_command, cwd=cwd, env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options,
        ) as process:
            try:
                if job is not None:
                    job.assign(process.pid)
                stdout, stderr = process.communicate(
                    input=b"1" if job is not None else None, timeout=timeout,
                )
            except BaseException as error:
                _stop_process_tree(process, job)
                stdout, stderr = process.communicate(timeout=_CLEANUP_TIMEOUT_SECONDS)
                if isinstance(error, subprocess.TimeoutExpired):
                    raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr) from error
                raise
            _stop_process_tree(process, job)
            return subprocess.CompletedProcess(list(command), process.returncode, stdout, stderr)
    finally:
        if job is not None:
            job.close()
