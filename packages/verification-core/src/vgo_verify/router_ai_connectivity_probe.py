#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .router_ai_probe_advice import (
    TransportFn,
    classify_scope,
    probe_advice_connectivity,
)
from .router_ai_probe_support import (
    INTENT_ADVICE_API_KEY_ENV,
    ProbeContext,
    VECTOR_DIFF_API_KEY_ENV,
    default_transport,
    load_json,
    resolve_repo_root,
    settings_env,
    utc_now,
    write_text,
)
from .router_ai_probe_vector import probe_vector_diff


def attempt_info_lines(label: str, attempts: list[dict[str, Any]] | None) -> list[str]:
    lines: list[str] = []
    for attempt in attempts or []:
        endpoint = str(attempt.get("endpoint_kind") or "unknown")
        status = attempt.get("status_code")
        outcome = str(attempt.get("outcome") or "unknown")
        error_kind = str(attempt.get("error_kind") or "none")
        latency_ms = attempt.get("latency_ms")
        lines.append(
            f"[INFO] {label}_attempt endpoint={endpoint} status={status} outcome={outcome} error_kind={error_kind} latency_ms={latency_ms}"
        )
    return lines


def next_step_for_advice(status: str, advice: dict[str, Any]) -> str | None:
    provider_type = str(advice.get("provider_type") or "").strip().lower()
    if status == "disabled_by_policy":
        return "Enable llm acceleration policy (`enabled=true`, `mode` not `off`) before checking advice connectivity."
    if status == "prefix_required":
        return "Run probe in /vibe scope (or pass `--prefix-detected`) to evaluate advice provider connectivity."
    if status == "scope_not_applicable":
        return "Use an allowed grade/task/route_mode for this policy to test advice connectivity."
    if status == "missing_credentials":
        env_name = advice.get("credential_env") or INTENT_ADVICE_API_KEY_ENV
        return f"Configure `{env_name}` in local settings env or process environment."
    if status == "missing_model":
        return "Set `provider.model` in `config/llm-acceleration-policy.json` or configure `VCO_INTENT_ADVICE_MODEL` locally."
    if status == "missing_base_url":
        return "Set `provider.base_url` in policy or configure `VCO_INTENT_ADVICE_BASE_URL` locally."
    if status == "provider_unreachable":
        return "Check base_url reachability, DNS, network egress, and provider timeout."
    if status == "provider_rejected_request":
        if provider_type in {"anthropic", "anthropic-compatible"}:
            return "Verify API key validity, model id, and Anthropic-compatible endpoint compatibility (`/v1/messages`)."
        return "Verify API key validity, model id, and endpoint compatibility (`/responses`, `/chat/completions`, or `/v1/messages` when using Anthropic-compatible gateways)."
    if status == "parse_error":
        return "Inspect response body in JSON artifact and align provider output format expectations."
    return None


def next_step_for_vector(status: str, vector: dict[str, Any]) -> str | None:
    if status == "vector_diff_not_configured":
        return "If needed, enable `context.vector_diff` and set `embedding_model` or `VCO_VECTOR_DIFF_MODEL` plus vector provider config."
    if status == "vector_diff_missing_credentials":
        env_name = vector.get("credential_env") or VECTOR_DIFF_API_KEY_ENV
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
        f"- Endpoint Used: `{artifact['advice'].get('endpoint_used')}`",
        "",
    ]
    advice_attempts = artifact["advice"].get("attempts") or []
    if advice_attempts:
        lines += ["### Advice Attempts", ""]
        for attempt in advice_attempts:
            lines.append(
                "- endpoint=`{endpoint}` status=`{status}` outcome=`{outcome}` error_kind=`{error_kind}` latency_ms=`{latency}`".format(
                    endpoint=attempt.get("endpoint_kind"),
                    status=attempt.get("status_code"),
                    outcome=attempt.get("outcome"),
                    error_kind=attempt.get("error_kind"),
                    latency=attempt.get("latency_ms"),
                )
            )
        lines.append("")
    lines += [
        "## Vector Diff Probe",
        "",
        f"- Status: `{artifact['vector_diff'].get('status')}`",
        f"- Provider Type: `{artifact['vector_diff'].get('provider_type')}`",
        f"- Model: `{artifact['vector_diff'].get('model')}`",
        "",
    ]
    vector_attempts = artifact["vector_diff"].get("attempts") or []
    if vector_attempts:
        lines += ["### Vector Diff Attempts", ""]
        for attempt in vector_attempts:
            lines.append(
                "- endpoint=`{endpoint}` status=`{status}` outcome=`{outcome}` error_kind=`{error_kind}` latency_ms=`{latency}`".format(
                    endpoint=attempt.get("endpoint_kind"),
                    status=attempt.get("status_code"),
                    outcome=attempt.get("outcome"),
                    error_kind=attempt.get("error_kind"),
                    latency=attempt.get("latency_ms"),
                )
            )
        lines.append("")
    if artifact["next_steps"]:
        lines += ["## Next Steps", ""]
        for step in artifact["next_steps"]:
            lines.append(f"- {step}")
        lines.append("")
    write_text(output_root / "vibe-router-ai-connectivity-gate.md", "\n".join(lines) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime-neutral Router AI advice connectivity probe.")
    parser.add_argument("--repo-root")
    parser.add_argument("--target-root", default=str(Path.home() / ".vibeskills" / "targets" / "codex"))
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
    for line in attempt_info_lines("advice", artifact["advice"].get("attempts")):
        print(line)
    for line in attempt_info_lines("vector_diff", artifact["vector_diff"].get("attempts")):
        print(line)
    for step in artifact["next_steps"]:
        print(f"[NEXT] {step}")
    return 0 if artifact["summary"]["gate_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
