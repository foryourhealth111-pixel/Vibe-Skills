from __future__ import annotations

from enum import IntEnum


class CliExitCode(IntEnum):
    FAILURE = 1
    USAGE = 2
    INVALID_STATE = 3
    MISSING_RESOURCE = 4
    PERMISSION_DENIED = 5
    UNAVAILABLE = 6
    IO_ERROR = 7


class CliError(RuntimeError):
    exit_code = CliExitCode.FAILURE


class CliStateError(CliError):
    exit_code = CliExitCode.INVALID_STATE


class CliMissingResourceError(CliError):
    exit_code = CliExitCode.MISSING_RESOURCE


class CliPermissionError(CliError):
    exit_code = CliExitCode.PERMISSION_DENIED


class CliUnavailableError(CliError):
    exit_code = CliExitCode.UNAVAILABLE


class CliIoError(CliError):
    exit_code = CliExitCode.IO_ERROR
