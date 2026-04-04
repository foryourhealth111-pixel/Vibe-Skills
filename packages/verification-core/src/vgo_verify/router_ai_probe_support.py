from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ._io import load_json, utc_now, write_text
from ._repo import resolve_repo_root


TransportFn = Callable[[dict[str, Any]], dict[str, Any]]

INTENT_ADVICE_API_KEY_ENV = "VCO_INTENT_ADVICE_API_KEY"
INTENT_ADVICE_BASE_URL_ENV = "VCO_INTENT_ADVICE_BASE_URL"
INTENT_ADVICE_MODEL_ENV = "VCO_INTENT_ADVICE_MODEL"
VECTOR_DIFF_API_KEY_ENV = "VCO_VECTOR_DIFF_API_KEY"
VECTOR_DIFF_BASE_URL_ENV = "VCO_VECTOR_DIFF_BASE_URL"
VECTOR_DIFF_MODEL_ENV = "VCO_VECTOR_DIFF_MODEL"


@dataclass
class ProbeContext:
    prefix_detected: bool = True
    grade: str = "M"
    task_type: str = "coding"
    route_mode: str = "legacy_fallback"


def placeholder_value(value: str | None) -> bool:
    if value is None:
        return False
    trimmed = value.strip()
    return bool(trimmed) and trimmed.startswith("<") and trimmed.endswith(">")


def non_empty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def settings_env(target_root: Path) -> dict[str, str]:
    path = target_root / "settings.json"
    if not path.exists():
        return {}
    try:
        content = load_json(path)
    except Exception:
        return {}
    if not isinstance(content, dict):
        return {}
    env = content.get("env")
    if not isinstance(env, dict):
        return {}
    resolved: dict[str, str] = {}
    for key, value in env.items():
        name = non_empty(key)
        raw = non_empty(value)
        if not name or not raw:
            continue
        resolved[name] = raw
    return resolved


def resolve_env_value(name: str, settings_values: dict[str, str]) -> str | None:
    env_value = non_empty(os.environ.get(name))
    if env_value and not placeholder_value(env_value):
        return env_value
    setting_value = non_empty(settings_values.get(name))
    if setting_value and not placeholder_value(setting_value):
        return setting_value
    return None


def resolve_first_value(names: list[str], settings_values: dict[str, str]) -> str | None:
    for name in names:
        value = resolve_env_value(name, settings_values)
        if value:
            return value
    return None


def openai_v1_base_url(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        return trimmed
    return f"{trimmed}/v1"


def parse_json_text(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def extract_openai_response_output_text(payload: dict[str, Any]) -> str | None:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output = payload.get("output")
    if not isinstance(output, list):
        return None

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "output_text":
                continue
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    if not parts:
        return None
    return "\n".join(parts).strip()


def extract_chat_completion_text(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def extract_vectors(payload: dict[str, Any]) -> list[list[Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    rows: list[list[Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        embedding = item.get("embedding")
        if isinstance(embedding, list) and embedding:
            rows.append(embedding)
            continue
        if isinstance(embedding, dict):
            nested = embedding.get("embedding")
            if isinstance(nested, list) and nested:
                rows.append(nested)
                continue
            nested = embedding.get("vector")
            if isinstance(nested, list) and nested:
                rows.append(nested)
                continue
    return rows


def default_transport(request_spec: dict[str, Any]) -> dict[str, Any]:
    url = str(request_spec["url"])
    timeout_ms = int(request_spec.get("timeout_ms", 12000))
    headers = dict(request_spec.get("headers") or {})
    payload = request_spec.get("json_body")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
    timeout_seconds = max(1.0, timeout_ms / 1000.0)
    started = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = int(response.getcode() or 200)
            return {
                "ok": True,
                "status_code": status,
                "error_kind": None,
                "error": None,
                "body_text": raw,
                "json": parse_json_text(raw),
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return {
            "ok": False,
            "status_code": int(exc.code),
            "error_kind": "http",
            "error": str(exc),
            "body_text": raw,
            "json": parse_json_text(raw),
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
        return {
            "ok": False,
            "status_code": None,
            "error_kind": "network",
            "error": str(exc),
            "body_text": None,
            "json": None,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "error_kind": "other",
            "error": str(exc),
            "body_text": None,
            "json": None,
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
