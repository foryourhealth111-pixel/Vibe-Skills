from __future__ import annotations

from typing import Any

from .router_contract_support import RepoContext, read_skill_descriptor


def build_confirm_ui(repo: RepoContext, route_result: dict[str, Any], target_root: str | None, host_id: str | None = None) -> dict[str, Any] | None:
    if route_result["route_mode"] != "confirm_required" or not route_result.get("selected"):
        return None

    selected = route_result["selected"]
    ranking = []
    for row in route_result.get("ranked", []):
        if row["pack_id"] == selected["pack_id"]:
            ranking = row.get("candidate_ranking", [])
            break
    if not ranking:
        ranking = [{"skill": selected["skill"], "score": selected["selection_score"]}]

    options = []
    for index, row in enumerate(ranking[:5], start=1):
        descriptor = read_skill_descriptor(repo, row["skill"], target_root, host_id)
        options.append(
            {
                "option_id": index,
                "skill": row["skill"],
                "pack_id": selected["pack_id"],
                "score": row.get("score"),
                "description": descriptor["description"],
                "skill_md_path": descriptor["skill_md_path"],
            }
        )

    rendered: list[str] = []
    if route_result.get("hazard_alert_required") and route_result.get("hazard_alert"):
        hazard = route_result["hazard_alert"]
        rendered.append(str(hazard.get("title") or "FALLBACK HAZARD ALERT"))
        rendered.append(str(hazard.get("message") or "This result came from a fallback or degraded path and is not equivalent to standard success."))
        if hazard.get("reason"):
            rendered.append(f"Trigger reason: `{hazard['reason']}`.")
        if hazard.get("recovery_action"):
            rendered.append(str(hazard["recovery_action"]))
        rendered.append("")
    rendered.append(f"Route confirmation required for pack `{selected['pack_id']}`.")
    for option in options:
        score = option["score"]
        score_text = f" (score={round(float(score), 4)})" if score is not None else ""
        if option["description"]:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text} - {option['description']}")
        else:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text}")
    rendered.append("Reply with the option number or `$<skill>` to choose explicitly.")

    return {
        "enabled": True,
        "pack_id": selected["pack_id"],
        "selected_skill": selected["skill"],
        "options": options,
        "rendered_text": "\n".join(rendered),
        "hazard_alert_required": bool(route_result.get("hazard_alert_required")),
        "truth_level": route_result.get("truth_level"),
        "degradation_state": route_result.get("degradation_state"),
        "hazard_alert": route_result.get("hazard_alert"),
    }


def build_fallback_truth(route_result: dict[str, Any], fallback_policy: dict[str, Any] | None) -> dict[str, Any]:
    policy = fallback_policy or {}
    truth_contract = policy.get("truth_contract", {}) if isinstance(policy, dict) else {}
    fallback_active = bool(
        route_result.get("route_mode") == "legacy_fallback"
        or route_result.get("route_reason") == "legacy_fallback_guard"
        or route_result.get("legacy_fallback_guard_applied")
    )
    degradation_state = (
        truth_contract.get("fallback_guarded_state", "fallback_guarded")
        if route_result.get("legacy_fallback_guard_applied")
        else truth_contract.get("fallback_degradation_state", "fallback_active")
        if fallback_active
        else "standard"
    )
    truth_level = (
        truth_contract.get("fallback_truth_level", "non_authoritative")
        if fallback_active
        else truth_contract.get("standard_truth_level", "authoritative")
    )
    hazard_alert_required = bool(policy.get("require_hazard_alert", True) and fallback_active)
    hazard_alert = None
    if hazard_alert_required:
        hazard_alert = {
            "title": policy.get("hazard_alert_title", "FALLBACK HAZARD ALERT"),
            "severity": policy.get("hazard_alert_severity", "critical"),
            "reason": route_result.get("legacy_fallback_original_reason") or route_result.get("route_reason"),
            "message": policy.get(
                "hazard_summary",
                "This result came from a fallback or degraded path and is not equivalent to standard success.",
            ),
            "recovery_action": policy.get(
                "hazard_recovery_action",
                "Repair the primary path or restore missing dependencies before claiming authoritative success.",
            ),
            "manual_review_required": bool(truth_contract.get("manual_review_required", True)),
        }
    return {
        "fallback_active": fallback_active,
        "hazard_alert_required": hazard_alert_required,
        "truth_level": truth_level,
        "degradation_state": degradation_state,
        "non_authoritative": truth_level != "authoritative",
        "hazard_alert": hazard_alert,
    }
