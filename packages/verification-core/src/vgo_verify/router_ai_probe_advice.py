from __future__ import annotations

from typing import Any

from .router_ai_probe_support import (
    INTENT_ADVICE_API_KEY_ENV,
    INTENT_ADVICE_BASE_URL_ENV,
    INTENT_ADVICE_MODEL_ENV,
    ProbeContext,
    TransportFn,
    anthropic_messages_base_url,
    extract_anthropic_message_text,
    extract_chat_completion_text,
    extract_openai_response_output_text,
    non_empty,
    openai_v1_base_url,
    parse_json_text,
    resolve_env_value,
    resolve_first_value,
)


def provider_credential_env(provider_type: str, provider_cfg: dict[str, Any] | None = None) -> str:
    if isinstance(provider_cfg, dict):
        configured = non_empty(provider_cfg.get("api_key_env"))
        if configured:
            return configured
    return INTENT_ADVICE_API_KEY_ENV


def advice_model_candidates(provider_type: str, provider_cfg: dict[str, Any] | None = None) -> list[str]:
    if isinstance(provider_cfg, dict):
        configured = non_empty(provider_cfg.get("model_env"))
        if configured:
            return [configured]
    return [INTENT_ADVICE_MODEL_ENV]


def resolve_advice_base_url(provider_type: str, provider_cfg: dict[str, Any], settings_values: dict[str, str]) -> str | None:
    configured = non_empty(provider_cfg.get("base_url"))
    if configured:
        return configured

    env_candidates = provider_cfg.get("base_url_env_candidates") if isinstance(provider_cfg, dict) else None
    base_url_names = [str(item) for item in env_candidates] if isinstance(env_candidates, list) and env_candidates else [
        INTENT_ADVICE_BASE_URL_ENV
    ]
    normalized = provider_type.strip().lower()
    if normalized in {"openai", "openai-compatible", "mock"}:
        return resolve_first_value(base_url_names, settings_values) or "https://api.openai.com/v1"
    return resolve_first_value(base_url_names, settings_values)


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
                elif attempt["endpoint_kind"] in {"chat_completions", "chat_completions_plain"}:
                    text = extract_chat_completion_text(payload)
                elif attempt["endpoint_kind"] == "anthropic_messages":
                    text = extract_anthropic_message_text(payload)

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

    model = non_empty(provider_cfg.get("model")) or resolve_first_value(advice_model_candidates(provider_type, provider_cfg), settings_values)
    if not model and provider_type_normalized != "mock":
        return {
            "status": "missing_model",
            "provider_type": provider_type,
            "model": None,
            "credential_env": provider_credential_env(provider_type, provider_cfg),
            "credential_state": "unknown",
            "attempts": [],
        }

    credential_env = provider_credential_env(provider_type, provider_cfg)
    api_key = resolve_env_value(credential_env, settings_values)
    if provider_type_normalized != "mock" and not api_key:
        offline_reason = None
        providers = registry.get("providers") if isinstance(registry, dict) else None
        if isinstance(providers, list):
            for provider_entry in providers:
                if not isinstance(provider_entry, dict):
                    continue
                provider_id = str(provider_entry.get("id") or "")
                if "openai" in provider_id and credential_env == INTENT_ADVICE_API_KEY_ENV:
                    contract = provider_entry.get("offline_contract")
                    if isinstance(contract, dict):
                        offline_reason = non_empty(contract.get("abstain_reason"))
                    break
        if not offline_reason:
            offline_reason = "missing_intent_advice_api_key"
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

    timeout_ms = int(provider_cfg.get("timeout_ms", 12000) or 12000)

    if provider_type_normalized in {"anthropic", "anthropic-compatible"}:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": str(provider_cfg.get("anthropic_version") or "2023-06-01"),
            "Content-Type": "application/json",
        }
        base_v1 = anthropic_messages_base_url(str(base_url))
        anthropic_payload = {
            "model": model,
            "max_tokens": 32,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": 'Return JSON object {"ok": true} only.'}],
                }
            ],
            "system": "Reply with a JSON object only. Do not wrap it in markdown.",
        }
        attempts = [
            request_attempt(
                transport,
                purpose="advice",
                endpoint_kind="anthropic_messages",
                url=f"{base_v1}/messages",
                headers=headers,
                payload=anthropic_payload,
                timeout_ms=timeout_ms,
            )
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
    plain_chat_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Reply with a JSON object only. Do not wrap it in markdown.",
            },
            {"role": "user", "content": 'Return JSON object {"ok": true} only.'},
        ],
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
        request_attempt(
            transport,
            purpose="advice",
            endpoint_kind="chat_completions_plain",
            url=f"{base_v1}/chat/completions",
            headers=headers,
            payload=plain_chat_payload,
            timeout_ms=timeout_ms,
        ),
    ]
    status, endpoint_used, compact_attempts = classify_advice_probe_result(attempts)
    normalized_base_url = str(base_url).strip().lower()
    should_try_anthropic_fallback = (
        status != "ok"
        and normalized_base_url not in {"", "https://api.openai.com/v1", "https://api.openai.com"}
        and "openai.com" not in normalized_base_url
    )
    if should_try_anthropic_fallback:
        anthropic_attempt = request_attempt(
            transport,
            purpose="advice",
            endpoint_kind="anthropic_messages",
            url=f"{anthropic_messages_base_url(str(base_url))}/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": str(provider_cfg.get("anthropic_version") or "2023-06-01"),
                "Content-Type": "application/json",
            },
            payload={
                "model": model,
                "max_tokens": 32,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": 'Return JSON object {"ok": true} only.'}],
                    }
                ],
                "system": "Reply with a JSON object only. Do not wrap it in markdown.",
            },
            timeout_ms=timeout_ms,
        )
        attempts.append(anthropic_attempt)
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
