from __future__ import annotations

from typing import Any

from .router_contract_support import RepoContext, read_skill_descriptor


# UI string constants for confirm UI rendering
CONFIRM_UI_BATCH_PROMPT = "请尽量一次性回答下面问题；能合并回答的内容可以放在同一条消息里："  # noqa: RUF001
CONFIRM_UI_ROUTE_PREFIX = "路由需要确认：当前命中候选包"  # noqa: RUF001
CONFIRM_UI_ROUTE_OVERLAY_PREFIX = "路由已生成候选技能：当前主选包"  # noqa: RUF001
CONFIRM_UI_COMBINED_INSTRUCTION = "你可以在同一条回复里同时回答上面的问题，并输入序号或 `$<skill>` 来指定技能。若不指定，宿主可采用当前主选。"  # noqa: RUF001
CONFIRM_UI_SIMPLE_INSTRUCTION = "回复序号或 `$<skill>` 来明确选择。若不指定，宿主可采用当前主选。"

# Deep discovery first question template (from deep-discovery-policy.json)
DEEP_DISCOVERY_FIRST_QUESTION = "你希望这次任务最终交付什么形式"


def _collect_clarification_questions(route_result: dict[str, Any], max_items: int = 6) -> list[str]:
    cap = min(max_items, 6)
    questions: list[str] = []
    sources = [
        (route_result.get("deep_discovery_advice") or {}).get("interview_questions", []),
        (route_result.get("llm_acceleration_advice") or {}).get("confirm_questions", []),
        (route_result.get("prompt_asset_boost_advice") or {}).get("confirm_questions", []),
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
    elif selected["skill"] not in {str(item.get("skill") or "").strip() for item in ranking}:
        selected_row = None
        for row in route_result.get("ranked", []):
            if row["pack_id"] != selected["pack_id"]:
                continue
            for candidate in row.get("stage_assistant_candidates", []):
                if str(candidate.get("skill") or "").strip() == selected["skill"]:
                    selected_row = candidate
                    break
            if selected_row:
                break
        ranking = [selected_row or {"skill": selected["skill"], "score": selected["selection_score"]}, *ranking]

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
            rendered.append(f"触发原因：`{hazard['reason']}`。")  # noqa: RUF001
        if hazard.get("recovery_action"):
            rendered.append(str(hazard["recovery_action"]))
        rendered.append("")
    if clarification_questions:
        rendered.append(CONFIRM_UI_BATCH_PROMPT)
        for index, question in enumerate(clarification_questions, start=1):
            rendered.append(f"Q{index}. {question}")
        rendered.append("")
    route_prefix = CONFIRM_UI_ROUTE_PREFIX if route_result.get("route_mode") == "confirm_required" else CONFIRM_UI_ROUTE_OVERLAY_PREFIX
    rendered.append(f"{route_prefix} `{selected['pack_id']}`。")
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

    return {
        "enabled": True,
        "pack_id": selected["pack_id"],
        "selected_skill": selected["skill"],
        "options": options,
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
