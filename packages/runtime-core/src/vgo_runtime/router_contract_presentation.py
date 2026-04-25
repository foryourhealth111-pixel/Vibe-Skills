from __future__ import annotations

from typing import Any

from .router_contract_support import RepoContext, read_skill_descriptor


# UI string constants for confirm UI rendering
CONFIRM_UI_BATCH_PROMPT = "Please answer the following questions in one reply when possible:"  # noqa: RUF001
CONFIRM_UI_ROUTE_PREFIX = "Routing confirmation required: current candidate pack"  # noqa: RUF001
CONFIRM_UI_ROUTE_OVERLAY_PREFIX = "Routing suggested candidate skills: current primary pack"  # noqa: RUF001
CONFIRM_UI_COMBINED_INSTRUCTION = "You can answer the questions above and select a skill in the same reply by entering an option number or `$<skill>`. If you do not specify one, the host may use the current primary choice."  # noqa: RUF001
CONFIRM_UI_SIMPLE_INSTRUCTION = "Reply with an option number or `$<skill>` to make the selection explicit. If you do not specify one, the host may use the current primary choice."

# Deep discovery first question template (from deep-discovery-policy.json)
DEEP_DISCOVERY_FIRST_QUESTION = "What final deliverable shape do you want"


def _build_route_decision_contract(
    *,
    selected_pack: str,
    selected_skill: str,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "protocol_version": "v1",
        "decision_kind": "route_selection",
        "decision_context": "routing_confirmation",
        "selected_pack": selected_pack,
        "primary_skill": selected_skill,
        "allowed_decision_actions": ["accept_primary", "select_skill"],
        "allowed_skill_ids": [
            str(option.get("skill") or "").strip()
            for option in options
            if str(option.get("skill") or "").strip()
        ],
        "options": [
            {
                "option_id": option.get("option_id"),
                "skill": option.get("skill"),
                "pack_id": option.get("pack_id"),
                "is_primary": bool(option.get("is_primary")),
            }
            for option in options
        ],
        "preferred_payload": {
            "decision_kind": "route_selection",
            "decision_action": "accept_primary",
            "selected_pack": selected_pack,
            "selected_skill": selected_skill,
        },
        "selection_payload_template": {
            "decision_kind": "route_selection",
            "decision_action": "select_skill",
            "selected_pack": selected_pack,
            "selected_skill": "<allowed-skill>",
        },
    }


def _collect_clarification_questions(route_result: dict[str, Any], max_items: int = 6) -> list[str]:
    deep_discovery_advice = route_result.get("deep_discovery_advice") or {}
    llm_acceleration_advice = route_result.get("llm_acceleration_advice") or {}
    prompt_asset_boost_advice = route_result.get("prompt_asset_boost_advice") or {}
    clarification_required = bool(
        deep_discovery_advice.get("confirm_required")
        or llm_acceleration_advice.get("confirm_required")
        or prompt_asset_boost_advice.get("confirm_required")
    )
    if not clarification_required:
        return []

    cap = min(max_items, 6)
    questions: list[str] = []
    sources = [
        deep_discovery_advice.get("interview_questions", []),
        llm_acceleration_advice.get("confirm_questions", []),
        prompt_asset_boost_advice.get("confirm_questions", []),
    ]

    for source in sources:
        for item in source or []:
            question = str(item).strip()
            if not question or question in questions:
                continue
            questions.append(question)
            if len(questions) >= cap:
                return questions[:cap]

    return questions[:cap]


def _order_confirm_ranking(
    *,
    route_result: dict[str, Any],
    selected_pack: str,
    selected_skill: str,
    ranking: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not selected_skill:
        return [row for row in ranking if isinstance(row, dict)]

    selected_row: dict[str, Any] | None = None
    normalized_ranking: list[dict[str, Any]] = []
    seen_skills: set[str] = set()

    for row in ranking:
        if not isinstance(row, dict):
            continue
        skill = str(row.get("skill") or "").strip()
        if not skill or skill in seen_skills:
            continue
        if skill == selected_skill and selected_row is None:
            selected_row = row
        normalized_ranking.append(row)
        seen_skills.add(skill)

    if selected_row is None:
        for pack_row in route_result.get("ranked", []):
            if str(pack_row.get("pack_id") or "").strip() != selected_pack:
                continue
            for candidate in pack_row.get("stage_assistant_candidates", []) or []:
                if str(candidate.get("skill") or "").strip() == selected_skill:
                    selected_row = candidate
                    break
            if selected_row is not None:
                break

    if selected_row is None:
        selected_row = {"skill": selected_skill, "score": route_result["selected"].get("selection_score")}

    ordered = [selected_row]
    ordered.extend(
        row for row in normalized_ranking if str(row.get("skill") or "").strip() != selected_skill
    )
    return ordered


def build_confirm_ui(repo: RepoContext, route_result: dict[str, Any], target_root: str | None, host_id: str | None = None) -> dict[str, Any] | None:
    if route_result.get("route_mode") not in {"confirm_required", "pack_overlay"} or not route_result.get("selected"):
        return None

    selected = route_result["selected"]
    clarification_questions = _collect_clarification_questions(route_result)
    ranking = []
    for row in route_result.get("ranked", []):
        if row["pack_id"] == selected["pack_id"]:
            ranking = row.get("candidate_ranking", [])
            break
    if not ranking:
        ranking = [{"skill": selected["skill"], "score": selected["selection_score"]}]
    ranking = _order_confirm_ranking(
        route_result=route_result,
        selected_pack=str(selected["pack_id"]),
        selected_skill=str(selected["skill"] or ""),
        ranking=list(ranking),
    )

    options = []
    for index, row in enumerate(ranking[:5], start=1):
        descriptor = read_skill_descriptor(repo, row["skill"], target_root, host_id)
        options.append(
            {
                "option_id": index,
                "skill": row["skill"],
                "pack_id": selected["pack_id"],
                "is_primary": str(row["skill"] or "").strip() == str(selected["skill"] or "").strip(),
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
            rendered.append(f"Trigger reason: `{hazard['reason']}`.")  # noqa: RUF001
        if hazard.get("recovery_action"):
            rendered.append(str(hazard["recovery_action"]))
        rendered.append("")
    if clarification_questions:
        rendered.append(CONFIRM_UI_BATCH_PROMPT)
        for index, question in enumerate(clarification_questions, start=1):
            rendered.append(f"Q{index}. {question}")
        rendered.append("")
    route_prefix = CONFIRM_UI_ROUTE_PREFIX if route_result.get("route_mode") == "confirm_required" else CONFIRM_UI_ROUTE_OVERLAY_PREFIX
    rendered.append(f"{route_prefix} `{selected['pack_id']}`.")
    for option in options:
        score = option["score"]
        score_text = f" (score={round(float(score), 4)})" if score is not None else ""
        if option["description"]:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text} - {option['description']}")
        else:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text}")
    if clarification_questions:
        rendered.append(CONFIRM_UI_COMBINED_INSTRUCTION)
    else:
        rendered.append(CONFIRM_UI_SIMPLE_INSTRUCTION)
    rendered.append("The host may translate your natural-language reply into a structured route decision. Fixed keywords are not required.")

    return {
        "enabled": True,
        "pack_id": selected["pack_id"],
        "selected_skill": selected["skill"],
        "options": options,
        "route_decision_contract": _build_route_decision_contract(
            selected_pack=str(selected["pack_id"]),
            selected_skill=str(selected["skill"]),
            options=options,
        ),
        "clarification_questions": clarification_questions,
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
