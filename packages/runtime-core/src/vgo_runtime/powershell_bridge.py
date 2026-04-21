from __future__ import annotations

import json
import locale
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


LOGGER = logging.getLogger(__name__)
SENSITIVE_COMMAND_FLAGS = frozenset(
    {
        "-task",
        "-prompt",
        "--task",
        "--prompt",
    }
)


def _preferred_bridge_encodings() -> tuple[str, ...]:
    preferred = str(locale.getpreferredencoding(False) or "").strip()
    candidates = [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        preferred,
    ]
    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        ordered.append(normalized)
    return tuple(ordered)


def _preview_stream(value: bytes | str | None) -> str | None:
    if value in (None, b"", ""):
        return None
    if isinstance(value, bytes):
        if value.startswith(b"\xff\xfe"):
            text = value.decode("utf-16", errors="replace")
        elif value.startswith(b"\xfe\xff"):
            text = value.decode("utf-16-be", errors="replace")
        else:
            preview_encodings = ["utf-8-sig", str(locale.getpreferredencoding(False) or "").strip()]
            text: str | None = None
            for encoding in preview_encodings:
                normalized = encoding.strip()
                if not normalized:
                    continue
                try:
                    candidate = value.decode(normalized)
                except (LookupError, UnicodeDecodeError):
                    continue
                if "\ufffd" in candidate or "\x00" in candidate:
                    continue
                text = candidate
                break
            if text is None:
                for encoding in preview_encodings:
                    normalized = encoding.strip()
                    if not normalized:
                        continue
                    try:
                        candidate = value.decode(normalized, errors="replace")
                    except LookupError:
                        continue
                    if "\ufffd" in candidate or "\x00" in candidate:
                        continue
                    text = candidate
                    break
            if text is None:
                text = value.decode("latin-1", errors="replace")
        text = text.replace("\x00", "")
    else:
        text = value
    flattened = " ".join(text.split())
    if not flattened:
        return None
    if len(flattened) > 160:
        return flattened[:157] + "..."
    return flattened


def _resolve_bridge_timeout(timeout: float | None) -> float | None:
    if timeout is not None:
        return timeout
    raw = str(os.environ.get("VGO_POWERSHELL_BRIDGE_TIMEOUT_SECONDS") or "").strip()
    if not raw:
        return 300.0
    try:
        resolved = float(raw)
    except ValueError:
        LOGGER.warning(
            "Invalid VGO_POWERSHELL_BRIDGE_TIMEOUT_SECONDS=%r; using default timeout 300.0s",
            raw,
        )
        return 300.0
    if resolved <= 0:
        return None
    return resolved


def _command_preview(command: Sequence[str]) -> str:
    parts = [str(part) for part in command]
    if not parts:
        return ""

    executable = Path(parts[0]).name or parts[0]
    script_name: str | None = None
    for index, part in enumerate(parts[1:], start=1):
        lowered = part.lower()
        if lowered in {"-file", "--file"} and index + 1 < len(parts):
            script_name = Path(parts[index + 1]).name or parts[index + 1]
            break
        if lowered.endswith((".ps1", ".py", ".sh", ".cmd", ".bat")):
            script_name = Path(part).name or part
            break

    arg_count = max(len(parts) - 1, 0)
    if script_name:
        return f"{executable} ... {script_name} ({arg_count} args)"
    if len(parts) > 2:
        return f"{executable} ({arg_count} args)"

    redacted: list[str] = []
    redact_next = False
    for part in parts:
        lowered = part.lower()
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        redacted.append(part)
        if lowered in SENSITIVE_COMMAND_FLAGS:
            redact_next = True
    return " ".join(redacted)


def _stream_preview_parts(*, stdout: bytes | str | None, stderr: bytes | str | None) -> list[str]:
    parts: list[str] = []
    stdout_preview = _preview_stream(stdout)
    stderr_preview = _preview_stream(stderr)
    if stdout_preview:
        parts.append(f"stdout={stdout_preview}")
    if stderr_preview:
        parts.append(f"stderr={stderr_preview}")
    return parts


def _classify_bridge_failure(bridge_label: str) -> str:
    normalized = bridge_label.strip().lower()
    if "delegated lane" in normalized:
        return "delegated lane payload handoff"
    if "canonical entry" in normalized:
        return "canonical bridge startup"
    return "powershell bridge invocation"


def _bridge_context_parts(
    *,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[bytes] | None = None,
    stdout: bytes | str | None = None,
    stderr: bytes | str | None = None,
    extra_parts: Sequence[str] | None = None,
) -> list[str]:
    context_parts = [f"cwd={cwd}", f"command={_command_preview(command)}"]
    if completed is not None:
        context_parts.insert(0, f"exit={completed.returncode}")
        stdout = completed.stdout
        stderr = completed.stderr
    context_parts.extend(extra_parts or [])
    context_parts.extend(_stream_preview_parts(stdout=stdout, stderr=stderr))
    return context_parts


def _raise_bridge_failure(
    *,
    bridge_label: str,
    message: str,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[bytes] | None = None,
    stdout: bytes | str | None = None,
    stderr: bytes | str | None = None,
    extra_parts: Sequence[str] | None = None,
) -> None:
    failure_kind = _classify_bridge_failure(bridge_label)
    details = "; ".join(
        _bridge_context_parts(
            command=command,
            cwd=cwd,
            completed=completed,
            stdout=stdout,
            stderr=stderr,
            extra_parts=extra_parts,
        )
    )
    raise RuntimeError(f"{bridge_label} failed during {failure_kind}: {message} ({details})")


def _build_stream_detail(
    *,
    stdout: bytes | str | None,
    stderr: bytes | str | None,
    decoded_as: str | None = None,
    extra_parts: Sequence[str] | None = None,
) -> str:
    detail_parts: list[str] = list(extra_parts or [])
    stdout_preview = _preview_stream(stdout)
    stderr_preview = _preview_stream(stderr)
    if stdout_preview:
        detail_parts.append(f"stdout={stdout_preview}")
    if decoded_as:
        detail_parts.append(f"decoded-as-{decoded_as}")
    if stderr_preview:
        detail_parts.append(f"stderr={stderr_preview}")
    if not detail_parts:
        return ""
    return f" ({'; '.join(detail_parts)})"


def _decode_json_object_stdout(
    stdout: bytes | str | None,
    *,
    bridge_label: str,
    stderr: bytes | str | None = None,
) -> dict[str, Any]:
    stderr_preview = _preview_stream(stderr)
    if stdout is None:
        detail = f"; stderr={stderr_preview}" if stderr_preview else ""
        raise RuntimeError(f"{bridge_label} returned no stdout{detail}")

    if isinstance(stdout, str):
        payload_text = stdout.strip()
        if not payload_text:
            detail = f"; stderr={stderr_preview}" if stderr_preview else ""
            raise RuntimeError(f"{bridge_label} returned empty stdout{detail}")
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            detail = _build_stream_detail(stdout=stdout, stderr=stderr)
            raise RuntimeError(f"{bridge_label} returned invalid JSON stdout{detail}") from exc
        if not isinstance(payload, dict):
            detail = _build_stream_detail(stdout=stdout, stderr=stderr)
            raise RuntimeError(f"{bridge_label} returned non-object payload{detail}")
        return payload

    if not stdout.strip():
        detail = f"; stderr={stderr_preview}" if stderr_preview else ""
        raise RuntimeError(f"{bridge_label} returned empty stdout{detail}")

    decode_failures: list[str] = []
    last_json_error: tuple[str, json.JSONDecodeError] | None = None
    last_non_object: tuple[str, Any] | None = None
    for encoding in _preferred_bridge_encodings():
        try:
            payload_text = stdout.decode(encoding)
        except UnicodeDecodeError:
            decode_failures.append(encoding)
            continue
        if not payload_text.strip():
            continue
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            last_json_error = (encoding, exc)
            continue
        if not isinstance(payload, dict):
            last_non_object = (encoding, payload)
            continue
        return payload

    extra_parts = ["decode failed for " + ", ".join(decode_failures)] if decode_failures else []
    if last_json_error is not None:
        detail = _build_stream_detail(
            stdout=stdout,
            stderr=stderr,
            decoded_as=last_json_error[0],
            extra_parts=extra_parts,
        )
        raise RuntimeError(f"{bridge_label} returned invalid JSON stdout{detail}") from last_json_error[1]
    if last_non_object is not None:
        detail = _build_stream_detail(
            stdout=stdout,
            stderr=stderr,
            decoded_as=last_non_object[0],
            extra_parts=extra_parts,
        )
        raise RuntimeError(f"{bridge_label} returned non-object payload{detail}")
    detail = _build_stream_detail(stdout=stdout, stderr=stderr, extra_parts=extra_parts)
    raise RuntimeError(f"{bridge_label} returned undecodable JSON stdout{detail}")


def run_powershell_json_command(
    command: Sequence[str],
    *,
    cwd: Path,
    bridge_label: str,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    resolved_timeout = _resolve_bridge_timeout(timeout)
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            check=False,
            env=dict(env) if env is not None else None,
            timeout=resolved_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        _raise_bridge_failure(
            bridge_label=bridge_label,
            message=f"timed out after {resolved_timeout}s",
            command=command,
            cwd=cwd,
            stdout=exc.stdout,
            stderr=exc.stderr,
            extra_parts=[f"timeout={resolved_timeout}s"],
        )
    if completed.returncode != 0:
        _raise_bridge_failure(
            bridge_label=bridge_label,
            message="subprocess exited non-zero before JSON payload was returned",
            command=command,
            cwd=cwd,
            completed=completed,
        )
    try:
        return _decode_json_object_stdout(
            completed.stdout,
            bridge_label=bridge_label,
            stderr=completed.stderr,
        )
    except RuntimeError as exc:
        _raise_bridge_failure(
            bridge_label=bridge_label,
            message=str(exc),
            command=command,
            cwd=cwd,
            completed=completed,
        )
