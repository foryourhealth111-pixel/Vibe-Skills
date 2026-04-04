from __future__ import annotations

from typing import Any

from .router_ai_probe_advice import request_attempt
from .router_ai_probe_support import (
    TransportFn,
    VECTOR_DIFF_API_KEY_ENV,
    VECTOR_DIFF_BASE_URL_ENV,
    VECTOR_DIFF_MODEL_ENV,
    extract_vectors,
    non_empty,
    openai_v1_base_url,
    resolve_env_value,
    resolve_first_value,
)


def resolve_vector_base_url(provider_type: str, provider_cfg: dict[str, Any], settings_values: dict[str, str]) -> str | None:
    configured = non_empty(provider_cfg.get("base_url"))
    if configured:
        return configured
    env_candidates = provider_cfg.get("base_url_env_candidates") if isinstance(provider_cfg, dict) else None
    base_url_names = [str(item) for item in env_candidates] if isinstance(env_candidates, list) and env_candidates else [
        VECTOR_DIFF_BASE_URL_ENV
    ]
    normalized = provider_type.strip().lower()
    if normalized in {"openai", "openai-compatible"}:
        return resolve_first_value(base_url_names, settings_values) or "https://api.openai.com/v1"
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

    model = non_empty(vector_cfg.get("embedding_model")) or resolve_first_value(
        [non_empty(vector_cfg.get("embedding_model_env")) or VECTOR_DIFF_MODEL_ENV],
        settings_values,
    )
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

    credential_env = non_empty(provider_cfg.get("api_key_env")) or VECTOR_DIFF_API_KEY_ENV
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
