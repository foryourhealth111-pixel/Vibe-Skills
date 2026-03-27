#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


TransportFn = Callable[[dict[str, Any]], dict[str, Any]]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    candidates: list[Path] = []
    while True:
        if (current / "config" / "version-governance.json").exists():
            candidates.append(current)
        if current.parent == current:
            break
        current = current.parent
    if not candidates:
        raise RuntimeError(f"Unable to resolve VCO repo root from: {start_path}")
    git_candidates = [candidate for candidate in candidates if (candidate / ".git").exists()]
    return git_candidates[-1] if git_candidates else candidates[-1]


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


@dataclass
class ProbeContext:
    prefix_detected: bool = True
    grade: str = "M"
    task_type: str = "coding"
    route_mode: str = "legacy_fallback"


def provider_credential_env(provider_type: str) -> str:
    return "OPENAI_API_KEY"


def advice_model_candidates(provider_type: str) -> list[str]:
    return ["VCO_RUCNLPIR_MODEL"]


def resolve_advice_base_url(provider_type: str, provider_cfg: dict[str, Any], settings_values: dict[str, str]) -> str | None:
    configured = non_empty(provider_cfg.get("base_url"))
    if configured:
        return configured

    normalized = provider_type.strip().lower()
    if normalized in {"openai", "openai-compatible", "mock"}:
        return resolve_first_value(["OPENAI_BASE_URL", "OPENAI_API_BASE"], settings_values) or "https://api.openai.com/v1"
    return resolve_first_value(["OPENAI_BASE_URL", "OPENAI_API_BASE"], settings_values)


def classify_scope(policy: dict[str, Any], context: ProbeContext) -> dict[str, Any]:
    enabled = bool(policy.get("enabled", False))
    mode = str(policy.get("mode") or "off")
    if not enabled or mode == "off":
        return {"status": "disabled_by_policy", "reasons": ["policy_disabled" if not enabled else "mode_off"]}

    activation = policy.get("activation")
    explicit_vibe_only = bool(activation.get("explicit_vibe_only", True)) if isinstance(activation, dict) else True
    if explicit_vibe_only and not context.prefix_detected:
        return {"status": "prefix_required", "reasons": ["explicit_vibe_only"]}

    reasons: list[str] = []
    scope = policy.get("scope")
    if isinstance(scope, dict):
        grade_allow = scope.get("grade_allow")
        if isinstance(grade_allow, list) and grade_allow and context.grade not in grade_allow:
            reasons.append("grade_not_allowed")
        task_allow = scope.get("task_allow")
        if isinstance(task_allow, list) and task_allow and context.task_type not in task_allow:
            reasons.append("task_not_allowed")
        route_mode_allow = scope.get("route_mode_allow")
        if isinstance(route_mode_allow, list) and route_mode_allow and context.route_mode not in route_mode_allow:
            reasons.append("route_mode_not_allowed")
    if reasons:
        return {"status": "scope_not_applicable", "reasons": reasons}
    return {"status": "scope_applicable", "reasons": ["scope_match"]}


def request_attempt(
    transport: TransportFn,
    *,
    purpose: str,
    endpoint_kind: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_ms: int,
) -> dict[str, Any]:
    response = transport(
        {
            "purpose": purpose,
            "endpoint_kind": endpoint_kind,
            "url": url,
            "headers": headers,
            "json_body": payload,
            "timeout_ms": timeout_ms,
        }
    )
    return {
        "endpoint_kind": endpoint_kind,
        "url": url,
        "ok": bool(response.get("ok", False)),
        "status_code": response.get("status_code"),
        "error_kind": response.get("error_kind"),
        "error": response.get("error"),
        "latency_ms": int(response.get("latency_ms", 0)),
        "json": response.get("json"),
        "body_text": response.get("body_text"),
    }


def classify_advice_probe_result(attempts: list[dict[str, Any]]) -> tuple[str, str | None, list[dict[str, Any]]]:
    rejected_seen = False
    network_seen = False
    parse_seen = False
    parsed_endpoint: str | None = None

    compact_attempts: list[dict[str, Any]] = []
    for attempt in attempts:
        outcome = "unknown"
        parsed_ok = False
        if attempt["ok"]:
            payload = attempt.get("json")
            if isinstance(payload, dict):
                text = None
                if attempt["endpoint_kind"] == "responses":
                    text = extract_openai_response_output_text(payload)
                elif attempt["endpoint_kind"] == "chat_completions":
                    text = extract_chat_completion_text(payload)

                if text:
                    parsed = parse_json_text(text)
                    if parsed is not None:
                        parsed_ok = True
                    else:
                        parse_seen = True
                        outcome = "parse_error"
                elif payload:
                    parsed_ok = True
                else:
                    parse_seen = True
                    outcome = "parse_error"
            else:
                parse_seen = True
                outcome = "parse_error"

            if parsed_ok:
                parsed_endpoint = attempt["endpoint_kind"]
                outcome = "ok"
        else:
            if attempt.get("error_kind") == "http":
                rejected_seen = True
                outcome = "http_error"
            elif attempt.get("error_kind") == "network":
                network_seen = True
                outcome = "network_error"
            else:
                network_seen = True
                outcome = "transport_error"

        compact_attempts.append(
            {
                "endpoint_kind": attempt["endpoint_kind"],
                "status_code": attempt["status_code"],
                "error_kind": attempt["error_kind"],
                "latency_ms": attempt["latency_ms"],
                "outcome": outcome,
            }
        )

        if parsed_ok:
            return "ok", parsed_endpoint, compact_attempts

    if parse_seen:
        return "parse_error", parsed_endpoint, compact_attempts
    if rejected_seen:
        return "provider_rejected_request", parsed_endpoint, compact_attempts
    if network_seen:
        return "provider_unreachable", parsed_endpoint, compact_attempts
    return "provider_unreachable", parsed_endpoint, compact_attempts


def probe_advice_connectivity(
    *,
    policy: dict[str, Any],
    settings_values: dict[str, str],
    registry: dict[str, Any],
    transport: TransportFn,
) -> dict[str, Any]:
    provider = policy.get("provider")
    provider_cfg = provider if isinstance(provider, dict) else {}
    provider_type = str(provider_cfg.get("type") or "openai")
    provider_type_normalized = provider_type.lower()

    model = non_empty(provider_cfg.get("model")) or resolve_first_value(advice_model_candidates(provider_type), settings_values)
    if not model and provider_type_normalized != "mock":
        return {
            "status": "missing_model",
            "provider_type": provider_type,
            "model": None,
            "credential_env": provider_credential_env(provider_type),
            "credential_state": "unknown",
            "attempts": [],
        }

    credential_env = provider_credential_env(provider_type)
    api_key = resolve_env_value(credential_env, settings_values)
    if provider_type_normalized != "mock" and not api_key:
        offline_reason = None
        providers = registry.get("providers") if isinstance(registry, dict) else None
        if isinstance(providers, list):
            for provider_entry in providers:
                if not isinstance(provider_entry, dict):
                    continue
                provider_id = str(provider_entry.get("id") or "")
                if "openai" in provider_id and credential_env == "OPENAI_API_KEY":
                    contract = provider_entry.get("offline_contract")
                    if isinstance(contract, dict):
                        offline_reason = non_empty(contract.get("abstain_reason"))
                    break
        if not offline_reason:
            offline_reason = "missing_openai_api_key"
        return {
            "status": "missing_credentials",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "credential_state": "missing",
            "offline_degrade_active": True,
            "offline_reason": offline_reason,
            "attempts": [],
        }

    base_url = resolve_advice_base_url(provider_type, provider_cfg, settings_values)
    if provider_type_normalized != "mock" and not base_url:
        return {
            "status": "missing_base_url",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "credential_state": "configured",
            "attempts": [],
        }

    if provider_type_normalized == "mock":
        mock_relpath = non_empty(provider_cfg.get("mock_response_path"))
        if not mock_relpath:
            return {
                "status": "parse_error",
                "provider_type": provider_type,
                "model": model,
                "credential_env": credential_env,
                "credential_state": "not_required",
                "attempts": [],
            }
        return {
            "status": "ok",
            "provider_type": provider_type,
            "model": model,
            "base_url": None,
            "credential_env": credential_env,
            "credential_state": "not_required",
            "attempts": [{"endpoint_kind": "mock_fixture", "status_code": 200, "error_kind": None, "latency_ms": 0, "outcome": "ok"}],
            "endpoint_used": "mock_fixture",
        }

    if provider_type_normalized not in {"openai", "openai-compatible"}:
        return {
            "status": "provider_rejected_request",
            "provider_type": provider_type,
            "model": model,
            "base_url": base_url,
            "credential_env": credential_env,
            "credential_state": "configured",
            "attempts": [],
            "reason": "unsupported_provider_type",
        }

    timeout_ms = int(provider_cfg.get("timeout_ms", 12000) or 12000)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    base_v1 = openai_v1_base_url(str(base_url))

    responses_payload = {
        "model": model,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": 'Return JSON object {"ok": true} only.'}]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "router_probe",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                },
                "strict": True,
            }
        },
        "max_output_tokens": 32,
        "temperature": 0.0,
        "top_p": 1.0,
        "tools": [],
        "tool_choice": "none",
        "store": False,
    }
    chat_payload = {
        "model": model,
        "messages": [{"role": "user", "content": 'Return JSON object {"ok": true} only.'}],
        "response_format": {"type": "json_object"},
        "max_tokens": 32,
        "temperature": 0.0,
        "top_p": 1.0,
        "stream": False,
    }

    attempts = [
        request_attempt(
            transport,
            purpose="advice",
            endpoint_kind="responses",
            url=f"{base_v1}/responses",
            headers=headers,
            payload=responses_payload,
            timeout_ms=timeout_ms,
        ),
        request_attempt(
            transport,
            purpose="advice",
            endpoint_kind="chat_completions",
            url=f"{base_v1}/chat/completions",
            headers=headers,
            payload=chat_payload,
            timeout_ms=timeout_ms,
        ),
    ]
    status, endpoint_used, compact_attempts = classify_advice_probe_result(attempts)
    result = {
        "status": status,
        "provider_type": provider_type,
        "model": model,
        "base_url": base_url,
        "credential_env": credential_env,
        "credential_state": "configured",
        "attempts": compact_attempts,
    }
    if endpoint_used:
        result["endpoint_used"] = endpoint_used
    return result


def resolve_vector_base_url(provider_type: str, provider_cfg: dict[str, Any], settings_values: dict[str, str]) -> str | None:
    configured = non_empty(provider_cfg.get("base_url"))
    if configured:
        return configured
    normalized = provider_type.strip().lower()
    if normalized in {"openai", "openai-compatible"}:
        return resolve_first_value(["OPENAI_BASE_URL", "OPENAI_API_BASE"], settings_values) or "https://api.openai.com/v1"
    return None


def probe_vector_diff(
    *,
    policy: dict[str, Any],
    settings_values: dict[str, str],
    transport: TransportFn,
) -> dict[str, Any]:
    context = policy.get("context")
    if not isinstance(context, dict):
        return {"status": "vector_diff_not_configured", "availability_state": "not_configured", "attempts": []}
    vector_cfg = context.get("vector_diff")
    if not isinstance(vector_cfg, dict) or not bool(vector_cfg.get("enabled", False)):
        return {"status": "vector_diff_not_configured", "availability_state": "not_configured", "attempts": []}

    model = non_empty(vector_cfg.get("embedding_model"))
    provider = vector_cfg.get("embedding_provider")
    provider_cfg = provider if isinstance(provider, dict) else {}
    provider_type = str(provider_cfg.get("type") or "openai")
    if not model:
        return {
            "status": "vector_diff_not_configured",
            "availability_state": "not_configured",
            "provider_type": provider_type,
            "attempts": [],
        }

    credential_env = non_empty(provider_cfg.get("api_key_env")) or provider_credential_env(provider_type)
    api_key = resolve_env_value(credential_env, settings_values)
    if not api_key:
        return {
            "status": "vector_diff_missing_credentials",
            "availability_state": "unavailable",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "attempts": [],
        }

    base_url = resolve_vector_base_url(provider_type, provider_cfg, settings_values)
    if not base_url:
        return {
            "status": "vector_diff_not_configured",
            "availability_state": "not_configured",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "attempts": [],
        }

    timeout_ms = int(provider_cfg.get("timeout_ms", 6000) or 6000)
    provider_type_normalized = provider_type.lower()
    if provider_type_normalized in {"openai", "openai-compatible"}:
        endpoint = f"{openai_v1_base_url(base_url)}/embeddings"
    else:
        return {
            "status": "vector_diff_provider_rejected_request",
            "availability_state": "unavailable",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "attempts": [],
            "reason": "unknown_embedding_provider",
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": ["router vector diff probe"],
    }
    attempt = request_attempt(
        transport,
        purpose="vector_diff",
        endpoint_kind="embeddings",
        url=endpoint,
        headers=headers,
        payload=payload,
        timeout_ms=timeout_ms,
    )
    compact_attempt = {
        "endpoint_kind": attempt["endpoint_kind"],
        "status_code": attempt["status_code"],
        "error_kind": attempt["error_kind"],
        "latency_ms": attempt["latency_ms"],
        "outcome": "unknown",
    }
    if attempt["ok"]:
        payload_json = attempt.get("json")
        if isinstance(payload_json, dict) and extract_vectors(payload_json):
            compact_attempt["outcome"] = "ok"
            return {
                "status": "vector_diff_ok",
                "availability_state": "ok",
                "provider_type": provider_type,
                "model": model,
                "credential_env": credential_env,
                "attempts": [compact_attempt],
            }
        compact_attempt["outcome"] = "parse_error"
        return {
            "status": "vector_diff_parse_error",
            "availability_state": "unavailable",
            "provider_type": provider_type,
            "model": model,
            "credential_env": credential_env,
            "attempts": [compact_attempt],
        }

    if attempt.get("error_kind") == "http":
        compact_attempt["outcome"] = "http_error"
        status = "vector_diff_provider_rejected_request"
    elif attempt.get("error_kind") == "network":
        compact_attempt["outcome"] = "network_error"
        status = "vector_diff_provider_unreachable"
    else:
        compact_attempt["outcome"] = "transport_error"
        status = "vector_diff_provider_unreachable"

    return {
        "status": status,
        "availability_state": "unavailable",
        "provider_type": provider_type,
        "model": model,
        "credential_env": credential_env,
        "attempts": [compact_attempt],
    }


def next_step_for_advice(status: str, advice: dict[str, Any]) -> str | None:
    if status == "disabled_by_policy":
        return "Enable llm acceleration policy (`enabled=true`, `mode` not `off`) before checking advice connectivity."
    if status == "prefix_required":
        return "Run probe in /vibe scope (or pass `--prefix-detected`) to evaluate advice provider connectivity."
    if status == "scope_not_applicable":
        return "Use an allowed grade/task/route_mode for this policy to test advice connectivity."
    if status == "missing_credentials":
        env_name = advice.get("credential_env") or "OPENAI_API_KEY"
        return f"Configure `{env_name}` in local settings env or process environment."
    if status == "missing_model":
        return "Set `provider.model` in `config/llm-acceleration-policy.json` or configure `VCO_RUCNLPIR_MODEL` locally."
    if status == "missing_base_url":
        return "Set `provider.base_url` in policy or configure `OPENAI_BASE_URL` / `OPENAI_API_BASE` locally."
    if status == "provider_unreachable":
        return "Check base_url reachability, DNS, network egress, and provider timeout."
    if status == "provider_rejected_request":
        return "Verify API key validity, model id, and endpoint compatibility (`/responses` or `/chat/completions`)."
    if status == "parse_error":
        return "Inspect response body in JSON artifact and align provider output format expectations."
    return None


def next_step_for_vector(status: str, vector: dict[str, Any]) -> str | None:
    if status == "vector_diff_not_configured":
        return "If needed, enable `context.vector_diff` and set `embedding_model` plus provider config."
    if status == "vector_diff_missing_credentials":
        env_name = vector.get("credential_env") or "OPENAI_API_KEY"
        return f"Configure `{env_name}` for vector_diff embeddings probe."
    if status == "vector_diff_provider_unreachable":
        return "Check embeddings provider base_url/network reachability."
    if status == "vector_diff_provider_rejected_request":
        return "Verify embeddings model id, API key scope, and endpoint path."
    if status == "vector_diff_parse_error":
        return "Provider replied but embeddings payload shape was not parseable; inspect raw response."
    return None


def compute_gate_result(advice_status: str, vector_status: str) -> str:
    if advice_status == "ok" and vector_status in {"vector_diff_ok", "vector_diff_not_configured"}:
        return "PASS"
    if advice_status in {"disabled_by_policy", "prefix_required", "scope_not_applicable"}:
        return "WARN"
    if advice_status == "ok" and vector_status in {
        "vector_diff_missing_credentials",
        "vector_diff_provider_unreachable",
        "vector_diff_provider_rejected_request",
        "vector_diff_parse_error",
    }:
        return "WARN"
    return "FAIL"


def evaluate(
    repo_root: Path,
    target_root: Path,
    *,
    probe_context: ProbeContext | None = None,
    transport: TransportFn | None = None,
) -> dict[str, Any]:
    policy = load_json(repo_root / "config" / "llm-acceleration-policy.json")
    registry = load_json(repo_root / "config" / "router-provider-registry.json")
    settings_values = settings_env(target_root)
    context = probe_context or ProbeContext()
    transport_fn = transport or default_transport

    scope = classify_scope(policy if isinstance(policy, dict) else {}, context)
    scope_status = scope["status"]

    if scope_status == "disabled_by_policy":
        advice = {
            "status": "disabled_by_policy",
            "provider_type": str((policy.get("provider") or {}).get("type") if isinstance(policy, dict) else "openai"),
            "attempts": [],
        }
    elif scope_status == "prefix_required":
        advice = {
            "status": "prefix_required",
            "provider_type": str((policy.get("provider") or {}).get("type") if isinstance(policy, dict) else "openai"),
            "attempts": [],
        }
    elif scope_status == "scope_not_applicable":
        advice = {
            "status": "scope_not_applicable",
            "provider_type": str((policy.get("provider") or {}).get("type") if isinstance(policy, dict) else "openai"),
            "attempts": [],
        }
    else:
        advice = probe_advice_connectivity(
            policy=policy if isinstance(policy, dict) else {},
            settings_values=settings_values,
            registry=registry if isinstance(registry, dict) else {},
            transport=transport_fn,
        )

    vector_diff = probe_vector_diff(
        policy=policy if isinstance(policy, dict) else {},
        settings_values=settings_values,
        transport=transport_fn,
    )

    advice_step = next_step_for_advice(advice["status"], advice)
    vector_step = next_step_for_vector(vector_diff["status"], vector_diff)
    next_steps = [step for step in [advice_step, vector_step] if step]
    gate_result = compute_gate_result(advice["status"], vector_diff["status"])

    return {
        "gate": "vibe-router-ai-connectivity-gate",
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "target_root": str(target_root.resolve()),
        "advisory_only": True,
        "route_mutation": False,
        "scope": {
            "status": scope_status,
            "reasons": scope["reasons"],
            "prefix_detected": context.prefix_detected,
            "grade": context.grade,
            "task_type": context.task_type,
            "route_mode": context.route_mode,
        },
        "advice": advice,
        "vector_diff": vector_diff,
        "next_steps": next_steps,
        "summary": {
            "advice_status": advice["status"],
            "vector_diff_status": vector_diff["status"],
            "gate_result": gate_result,
            "warning_count": 0 if gate_result == "PASS" else 1,
        },
    }


def write_artifacts(repo_root: Path, artifact: dict[str, Any], output_directory: str | None) -> None:
    output_root = Path(output_directory) if output_directory else repo_root / "outputs" / "verify"
    write_text(output_root / "vibe-router-ai-connectivity-gate.json", json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# VCO Router AI Connectivity Gate",
        "",
        f"- Gate Result: **{artifact['summary']['gate_result']}**",
        f"- Advice Status: `{artifact['summary']['advice_status']}`",
        f"- Vector Diff Status: `{artifact['summary']['vector_diff_status']}`",
        f"- Scope Status: `{artifact['scope']['status']}`",
        f"- Advisory Only: `{artifact['advisory_only']}`",
        f"- Route Mutation: `{artifact['route_mutation']}`",
        "",
        "## Advice Probe",
        "",
        f"- Provider Type: `{artifact['advice'].get('provider_type')}`",
        f"- Model: `{artifact['advice'].get('model')}`",
        f"- Credential Env: `{artifact['advice'].get('credential_env')}`",
        "",
        "## Vector Diff Probe",
        "",
        f"- Status: `{artifact['vector_diff'].get('status')}`",
        f"- Provider Type: `{artifact['vector_diff'].get('provider_type')}`",
        f"- Model: `{artifact['vector_diff'].get('model')}`",
        "",
    ]
    if artifact["next_steps"]:
        lines += ["## Next Steps", ""]
        for step in artifact["next_steps"]:
            lines.append(f"- {step}")
        lines.append("")
    write_text(output_root / "vibe-router-ai-connectivity-gate.md", "\n".join(lines) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral Router AI advice connectivity probe.")
    parser.add_argument("--repo-root")
    parser.add_argument("--target-root", default=str(Path.home() / ".codex"))
    parser.add_argument("--grade", default="M")
    parser.add_argument("--task-type", default="coding")
    parser.add_argument("--route-mode", default="legacy_fallback")
    parser.add_argument("--prefix-detected", dest="prefix_detected", action="store_true")
    parser.add_argument("--no-prefix-detected", dest="prefix_detected", action="store_false")
    parser.set_defaults(prefix_detected=True)
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument("--output-directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        repo_root = Path(args.repo_root).resolve() if args.repo_root else resolve_repo_root(Path(__file__))
        artifact = evaluate(
            repo_root=repo_root,
            target_root=Path(args.target_root),
            probe_context=ProbeContext(
                prefix_detected=bool(args.prefix_detected),
                grade=str(args.grade),
                task_type=str(args.task_type),
                route_mode=str(args.route_mode),
            ),
        )
        if args.write_artifacts:
            write_artifacts(repo_root, artifact, args.output_directory)
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] advice_status={artifact['summary']['advice_status']}")
    print(f"[INFO] vector_diff_status={artifact['summary']['vector_diff_status']}")
    print(f"[INFO] gate_result={artifact['summary']['gate_result']}")
    for step in artifact["next_steps"]:
        print(f"[NEXT] {step}")
    return 0 if artifact["summary"]["gate_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
