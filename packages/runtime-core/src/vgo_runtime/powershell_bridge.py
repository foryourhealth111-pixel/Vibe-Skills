from __future__ import annotations

import json
import locale
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


def _preferred_bridge_encodings() -> tuple[str, ...]:
    preferred = str(locale.getpreferredencoding(False) or "").strip()
    candidates = [
        "utf-8-sig",
        "utf-8",
        preferred,
        "utf-16",
        "utf-16-le",
        "utf-16-be",
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
        text = value.decode("utf-8", errors="replace")
    else:
        text = value
    flattened = " ".join(text.split())
    if not flattened:
        return None
    if len(flattened) > 160:
        return flattened[:157] + "..."
    return flattened


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
            raise RuntimeError(f"{bridge_label} returned invalid JSON stdout") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"{bridge_label} returned non-object payload")
        return payload

    if not stdout.strip():
        detail = f"; stderr={stderr_preview}" if stderr_preview else ""
        raise RuntimeError(f"{bridge_label} returned empty stdout{detail}")

    decode_failures: list[str] = []
    last_json_error: json.JSONDecodeError | None = None
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
            last_json_error = exc
            continue
        if not isinstance(payload, dict):
            raise RuntimeError(f"{bridge_label} returned non-object payload")
        return payload

    detail_parts: list[str] = []
    if decode_failures:
        detail_parts.append("decode failed for " + ", ".join(decode_failures))
    stdout_preview = _preview_stream(stdout)
    if stdout_preview:
        detail_parts.append(f"stdout={stdout_preview}")
    if stderr_preview:
        detail_parts.append(f"stderr={stderr_preview}")
    detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""
    if last_json_error is not None:
        raise RuntimeError(f"{bridge_label} returned invalid JSON stdout{detail}") from last_json_error
    raise RuntimeError(f"{bridge_label} returned undecodable JSON stdout{detail}")


def run_powershell_json_command(
    command: Sequence[str],
    *,
    cwd: Path,
    bridge_label: str,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        capture_output=True,
        check=True,
        env=dict(env) if env is not None else None,
    )
    return _decode_json_object_stdout(
        completed.stdout,
        bridge_label=bridge_label,
        stderr=completed.stderr,
    )
