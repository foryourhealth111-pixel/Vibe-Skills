from __future__ import annotations

from pathlib import Path

from .custom_admission import load_custom_admission
from .router_contract_presentation import build_confirm_ui, build_fallback_truth
from .router_contract_selection import get_pack_default_candidate, select_pack_candidate
from .router_contract_support import (
    RepoContext,
    candidate_name_score,
    keyword_ratio,
    load_json,
    load_router_config_bundle,
    normalize_keyword_list,
    normalize_text,
    read_skill_descriptor,
    resolve_home_directory,
    resolve_host_id,
    resolve_repo_root,
    resolve_requested_canonical,
    resolve_skill_md_path,
    resolve_target_root,
)


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return deduped


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pack_intent_score(prompt_lower: str, pack_id: str, candidates: list[str]) -> float:
    score = 0.0
    normalized_pack = normalize_text(pack_id).replace("_", " ")
    for token in normalized_pack.split():
        if len(token) >= 3 and keyword_ratio(prompt_lower, [token]) > 0:
            score += 0.35
    for candidate in candidates:
        if keyword_ratio(prompt_lower, [candidate]) > 0:
            score += 0.25
    return min(1.0, score)


def _workspace_signal_score(prompt_lower: str, requested_canonical: str | None, candidates: list[str]) -> float:
    normalized_requested = normalize_text(requested_canonical or "")
    normalized_candidates = [normalize_text(candidate) for candidate in candidates if normalize_text(candidate)]
    if normalized_requested and normalized_requested in normalized_candidates:
        return 1.0

    for candidate in candidates:
        if keyword_ratio(prompt_lower, [candidate]) > 0:
            return 0.6
    return 0.0


def _build_deep_discovery_advice(repo: RepoContext, prompt_lower: str, grade: str, task_type: str) -> dict[str, object] | None:
    policy_path = repo.config_root / "deep-discovery-policy.json"
    catalog_path = repo.config_root / "capability-catalog.json"
    if not policy_path.exists() or not catalog_path.exists():
        return None

    policy = load_json(policy_path)
    catalog = load_json(catalog_path)
    if not isinstance(policy, dict) or not isinstance(catalog, dict):
        return None
    if not bool(policy.get("enabled", False)):
        return None

    mode = str(policy.get("mode") or "off").strip() or "off"
    if mode == "off":
        return None

    scope = policy.get("scope") or {}
    grade_allow = [normalize_text(item) for item in scope.get("grade_allow") or []]
    task_allow = [normalize_text(item) for item in scope.get("task_allow") or []]
    scope_reasons: list[str] = []
    if grade_allow and grade not in grade_allow:
        scope_reasons.append("grade_not_allowed")
    if task_allow and task_type not in task_allow:
        scope_reasons.append("task_not_allowed")
    scope_applicable = not scope_reasons

    capabilities = catalog.get("capabilities") or []
    capability_hits: list[dict[str, object]] = []
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        capability_task_allow = [normalize_text(item) for item in capability.get("task_allow") or []]
        if capability_task_allow and task_type not in capability_task_allow:
            continue
        matched_keywords = [
            str(keyword).strip()
            for keyword in capability.get("keywords") or []
            if keyword_ratio(prompt_lower, [str(keyword)]) > 0
        ]
        if not matched_keywords:
            continue
        capability_hits.append(
            {
                "capability_id": str(capability.get("id") or ""),
                "display_name": str(capability.get("display_name") or ""),
                "score": round(keyword_ratio(prompt_lower, capability.get("keywords") or []), 4),
                "matched_keyword_count": len(matched_keywords),
                "matched_keywords": matched_keywords,
                "skills": [str(skill).strip() for skill in capability.get("skills") or [] if str(skill).strip()],
            }
        )

    capability_hits.sort(
        key=lambda item: (
            -int(item.get("matched_keyword_count", 0)),
            str(item.get("display_name") or ""),
        )
    )

    trigger_cfg = policy.get("trigger") or {}
    min_trigger_score = float(trigger_cfg.get("min_trigger_score", 0.2))
    min_capability_hits = int(trigger_cfg.get("min_capability_hits", 1))
    ambiguity_score = float(keyword_ratio(prompt_lower, trigger_cfg.get("ambiguity_keywords") or []))
    composite_score = float(keyword_ratio(prompt_lower, trigger_cfg.get("composite_keywords") or []))
    execution_score = float(keyword_ratio(prompt_lower, trigger_cfg.get("execution_keywords") or []))
    capability_hit_count = len(capability_hits)
    capability_score = min(1.0, capability_hit_count / 3.0)
    trigger_score = round(
        min(
            1.0,
            max(
                0.0,
                (0.25 * ambiguity_score)
                + (0.45 * composite_score)
                + (0.20 * execution_score)
                + (0.10 * capability_score),
            ),
        ),
        4,
    )
    trigger_reasons: list[str] = []
    if ambiguity_score > 0:
        trigger_reasons.append("ambiguity_signal")
    if composite_score > 0:
        trigger_reasons.append("composite_signal")
    if execution_score > 0:
        trigger_reasons.append("execution_signal")
    if capability_hit_count >= min_capability_hits:
        trigger_reasons.append("capability_hits")
    active_by_score = trigger_score >= min_trigger_score and capability_hit_count >= min_capability_hits
    active_by_composite = composite_score >= 0.2 and capability_hit_count >= 1
    trigger_active = active_by_score or active_by_composite
    if not trigger_active:
        trigger_reasons.append("below_activation_threshold")

    interview_cfg = policy.get("interview") or {}
    max_questions = max(1, int(interview_cfg.get("max_questions", 3)))
    question_templates = [str(item) for item in interview_cfg.get("question_templates") or [] if str(item).strip()]
    if not question_templates:
        question_templates = [
            "What final deliverable shape do you want for this task (script, report, document, page, or runnable workflow)?",
            "What are the top two capability areas you want me to prioritize: {capabilities}?",
            "Do you want me to confirm the plan first, or execute directly from the current description?",
        ]

    capability_names = [str(item.get("display_name") or "").strip() for item in capability_hits if str(item.get("display_name") or "").strip()]
    capability_name_text = " / ".join(capability_names) if capability_names else "Requirement clarification and planning / Implementation and execution"

    questions: list[str] = []
    for template in question_templates:
        if len(questions) >= max_questions:
            break
        question = template.replace("{capabilities}", capability_name_text).strip()
        if question and question not in questions:
            questions.append(question)

    for item in catalog.get("default_interview_questions") or []:
        if len(questions) >= max_questions:
            break
        if not isinstance(item, dict):
            continue
        question = str(item.get("prompt") or "").strip()
        if question and question not in questions:
            questions.append(question)

    recommended_capabilities = _dedupe_strings([str(item.get("capability_id") or "") for item in capability_hits])
    recommended_skills = _dedupe_strings(
        [skill for item in capability_hits for skill in item.get("skills", []) if isinstance(skill, str)]
    )
    interview_required = scope_applicable and bool(trigger_active or recommended_capabilities)

    enforcement = "none"
    reason = "outside_scope"
    confirm_required = False
    if scope_applicable:
        if mode == "shadow":
            enforcement = "advisory"
            reason = "shadow_discovery_signal" if trigger_active else "shadow_scope_only"
        elif mode in {"soft", "strict"}:
            if trigger_active:
                enforcement = "confirm_required"
                reason = "deep_discovery_interview_required"
                confirm_required = True
            else:
                enforcement = "advisory"
                reason = "scope_match_no_trigger"
        else:
            enforcement = "advisory"
            reason = "unknown_mode_advisory"

    intent_contract = policy.get("intent_contract") or {}
    return {
        "enabled": True,
        "mode": mode,
        "scope_applicable": scope_applicable,
        "scope_reasons": scope_reasons,
        "preserve_routing_assignment": bool(policy.get("preserve_routing_assignment", True)),
        "trigger_active": trigger_active,
        "trigger_score": trigger_score,
        "trigger_details": {
            "active": trigger_active,
            "trigger_score": trigger_score,
            "ambiguity_score": round(ambiguity_score, 4),
            "composite_score": round(composite_score, 4),
            "execution_score": round(execution_score, 4),
            "capability_score": round(capability_score, 4),
            "capability_hit_count": capability_hit_count,
            "min_trigger_score": min_trigger_score,
            "min_capability_hits": min_capability_hits,
            "reasons": _dedupe_strings(trigger_reasons),
        },
        "capability_hit_count": len(capability_hits),
        "capability_hits": capability_hits,
        "recommended_capabilities": recommended_capabilities,
        "recommended_skills": recommended_skills,
        "interview_required": interview_required,
        "interview_questions": questions[:max_questions],
        "max_questions": max_questions,
        "min_completeness_for_confirm_required": float(intent_contract.get("min_completeness_for_confirm_required", 0.45)),
        "enforcement": enforcement,
        "reason": reason,
        "confirm_required": confirm_required,
        "should_apply_hook": interview_required,
    }


def _deep_discovery_deliverable_hint(prompt_lower: str) -> str:
    code_hit = float(keyword_ratio(prompt_lower, ["script", "code", "api", "service", "pipeline", "脚本", "代码", "接口", "服务"]))
    report_hit = float(keyword_ratio(prompt_lower, ["report", "analysis", "summary", "文档", "报告", "总结", "分析"]))
    plan_hit = float(keyword_ratio(prompt_lower, ["plan", "design", "architecture", "roadmap", "方案", "规划", "设计", "架构"]))

    if code_hit > 0 and report_hit > 0:
        return "code_plus_report"
    if code_hit > 0 and plan_hit > 0:
        return "plan_plus_code"
    if report_hit > 0 and plan_hit > 0:
        return "plan_plus_report"
    if code_hit > 0:
        return "code"
    if report_hit > 0:
        return "report"
    if plan_hit > 0:
        return "plan"
    return "unknown"


def _deep_discovery_constraint_hints(prompt_lower: str) -> list[str]:
    constraints: list[str] = []
    if keyword_ratio(prompt_lower, ["must", "必须", "strict", "严格"]) > 0:
        constraints.append("strict_requirement")
    if keyword_ratio(prompt_lower, ["today", "asap", "deadline", "今天", "尽快", "截止"]) > 0:
        constraints.append("timeline_constraint")
    if keyword_ratio(prompt_lower, ["json", "csv", "xlsx", "markdown", "pdf", "格式"]) > 0:
        constraints.append("output_format_constraint")
    if keyword_ratio(prompt_lower, ["test", "verify", "validation", "gate", "测试", "验证", "门禁"]) > 0:
        constraints.append("verification_constraint")
    return _dedupe_strings(constraints)


def _deep_discovery_execution_mode_hint(prompt_lower: str) -> str:
    plan_hit = float(keyword_ratio(prompt_lower, ["plan", "design", "brainstorm", "方案", "规划", "设计", "访谈"]))
    exec_hit = float(keyword_ratio(prompt_lower, ["implement", "execute", "build", "落地", "实现", "执行"]))

    if plan_hit > 0 and exec_hit > 0:
        return "plan_then_execute"
    if plan_hit > 0:
        return "plan_only"
    if exec_hit > 0:
        return "execute_only"
    return "unspecified"


def _build_deep_discovery_intent_contract(
    prompt: str,
    prompt_lower: str,
    deep_discovery_advice: dict[str, object] | None,
    deep_discovery_policy: dict[str, object] | None,
) -> dict[str, object]:
    goal_text = prompt.strip()
    deliverable = _deep_discovery_deliverable_hint(prompt_lower)
    constraints = _deep_discovery_constraint_hints(prompt_lower)
    capabilities = _dedupe_strings(
        [str(item) for item in (deep_discovery_advice or {}).get("recommended_capabilities") or []]
    )
    intent_contract_policy = (deep_discovery_policy or {}).get("intent_contract") or {}
    required_fields = [
        str(item).strip()
        for item in intent_contract_policy.get("required_fields") or []
        if str(item).strip()
    ]
    if not required_fields:
        required_fields = ["goal", "deliverable", "constraints", "capabilities"]

    field_presence = {
        "goal": bool(goal_text and len(goal_text) >= 8),
        "deliverable": deliverable != "unknown",
        "constraints": bool(constraints),
        "capabilities": bool(capabilities),
    }
    missing_fields = [field for field in required_fields if not field_presence.get(field, False)]
    completeness = round((len(required_fields) - len(missing_fields)) / float(len(required_fields) or 1), 4)

    return {
        "goal": goal_text,
        "deliverable": deliverable,
        "constraints": constraints,
        "capabilities": capabilities,
        "execution_mode": _deep_discovery_execution_mode_hint(prompt_lower),
        "required_fields": required_fields,
        "missing_fields": missing_fields,
        "completeness": completeness,
        "field_presence": field_presence,
    }


def _relax_deep_discovery_confirm(
    deep_discovery_advice: dict[str, object] | None,
    intent_contract: dict[str, object] | None,
) -> bool:
    if not deep_discovery_advice or not deep_discovery_advice.get("confirm_required"):
        return False

    completeness = float((intent_contract or {}).get("completeness") or 0.0)
    min_required = float(deep_discovery_advice.get("min_completeness_for_confirm_required") or 1.0)
    capability_count = len(deep_discovery_advice.get("recommended_capabilities") or [])
    if capability_count > 1 or completeness < min_required:
        return False

    deep_discovery_advice["enforcement"] = "advisory"
    deep_discovery_advice["reason"] = "intent_contract_sufficient_single_capability"
    deep_discovery_advice["confirm_required"] = False
    deep_discovery_advice["interview_required"] = False
    deep_discovery_advice["should_apply_hook"] = False
    return True


def _get_preferred_host_selection(pack_row: dict[str, object] | None) -> dict[str, object] | None:
    if not pack_row:
        return None

    preferred: dict[str, dict[str, object]] = {}
    ordinal = 0

    def add_candidate(
        candidate_row: dict[str, object] | None,
        fallback_score: float,
        fallback_skill: str,
        is_selected_candidate: bool,
    ) -> None:
        nonlocal ordinal
        skill = str((candidate_row or {}).get("skill") or fallback_skill or "").strip()
        if not skill:
            return
        score = float((candidate_row or {}).get("score", fallback_score) or 0.0)
        candidate = {
            "skill": skill,
            "score": score,
            "reason": str(pack_row.get("candidate_selection_reason") or "host_selection_candidate")
            if is_selected_candidate
            else "host_selection_candidate",
            "is_selected": is_selected_candidate,
            "ordinal": ordinal,
        }
        ordinal += 1

        existing = preferred.get(skill)
        if existing is None:
            preferred[skill] = candidate
            return
        if score > float(existing["score"]):
            preferred[skill] = candidate
            return
        if score == float(existing["score"]) and is_selected_candidate and not bool(existing["is_selected"]):
            preferred[skill] = candidate
            return
        if (
            score == float(existing["score"])
            and is_selected_candidate == bool(existing["is_selected"])
            and int(candidate["ordinal"]) < int(existing["ordinal"])
        ):
            preferred[skill] = candidate

    selected_skill = str(pack_row.get("selected_candidate") or "").strip()
    add_candidate(None, float(pack_row.get("candidate_selection_score") or 0.0), selected_skill, True)
    for row in pack_row.get("candidate_ranking", []) or []:
        if isinstance(row, dict):
            add_candidate(row, 0.0, "", str(row.get("skill") or "").strip() == selected_skill)
    for row in pack_row.get("stage_assistant_candidates", []) or []:
        if isinstance(row, dict):
            add_candidate(row, 0.0, "", str(row.get("skill") or "").strip() == selected_skill)

    if not preferred:
        return None

    return sorted(
        preferred.values(),
        key=lambda item: (-float(item["score"]), -int(bool(item["is_selected"])), int(item["ordinal"])),
    )[0]


def route_prompt(
    prompt: str,
    grade: str,
    task_type: str,
    requested_skill: str | None = None,
    entry_intent_id: str | None = None,
    requested_grade_floor: str | None = None,
    target_root: str | None = None,
    host_id: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    grade = normalize_text(grade)
    task_type = normalize_text(task_type)
    repo_path = repo_root or resolve_repo_root(Path(__file__))
    repo = RepoContext(
        repo_root=repo_path,
        config_root=repo_path / "config",
        bundled_skills_root=repo_path / "bundled" / "skills",
    )

    prompt_lower = normalize_text(prompt)
    router_config = load_router_config_bundle(repo.config_root)
    pack_manifest = router_config["pack_manifest"]
    alias_map = router_config["alias_map"]
    thresholds_cfg = router_config["thresholds"]
    skill_keyword_index = router_config["skill_keyword_index"]
    fallback_policy = router_config["fallback_policy"]
    routing_rules = router_config["routing_rules"]

    requested_canonical = resolve_requested_canonical(
        requested_skill,
        alias_map,
        repo_root=repo.repo_root,
    )
    resolved_target_root = resolve_target_root(target_root, host_id)
    custom_admission = load_custom_admission(
        repo_root=repo.repo_root,
        target_root=resolved_target_root,
        requested_canonical=requested_canonical,
    )
    threshold_values = thresholds_cfg.get("thresholds") or {}
    candidate_selection_cfg = thresholds_cfg.get("candidate_selection") or {}
    min_top_gap = float(threshold_values.get("min_top1_top2_gap", 0.08))
    min_candidate_signal_confirm = float(threshold_values.get("min_candidate_signal_for_confirm_override", 0.2))
    min_candidate_signal_auto = float(threshold_values.get("min_candidate_signal_for_auto_route", 0.6))
    auto_route_threshold = float(threshold_values.get("auto_route", 0.7))
    confirm_required_threshold = float(threshold_values.get("confirm_required", 0.45))
    fallback_threshold = float(threshold_values.get("fallback_to_legacy_below", 0.45))
    enforce_confirm_on_legacy_fallback = bool(thresholds_cfg.get("safety", {}).get("enforce_confirm_on_legacy_fallback", False))

    pack_results: list[dict[str, object]] = []
    packs: list[dict[str, object]] = list(pack_manifest.get("packs") or []) + list(custom_admission.get("admitted_packs") or [])
    for pack in packs:
        grade_allow = [normalize_text(item) for item in (pack.get("grade_allow") or [])]
        task_allow = [normalize_text(item) for item in (pack.get("task_allow") or [])]
        if grade_allow and grade not in grade_allow:
            continue
        if task_allow and task_type not in task_allow:
            continue

        selection = select_pack_candidate(
            prompt_lower=prompt_lower,
            candidates=[
                str(item).strip()
                for item in (pack.get("skill_candidates") or [])
                if str(item).strip()
            ],
            task_type=task_type,
            requested_canonical=requested_canonical,
            skill_keyword_index=skill_keyword_index,
            routing_rules=routing_rules,
            pack=pack,
            candidate_selection_config=candidate_selection_cfg,
        )
        trigger_ratio = keyword_ratio(prompt_lower, pack.get("trigger_keywords") or [])
        intent_score = _pack_intent_score(prompt_lower, str(pack.get("id") or ""), list(pack.get("skill_candidates") or []))
        workspace_score = _workspace_signal_score(
            prompt_lower,
            requested_canonical,
            list(pack.get("skill_candidates") or []),
        )
        priority_signal = min(max(float(pack.get("priority", 0)) / 100.0, 0.0), 1.0)
        relevance_score = float(selection.get("relevance_score", selection["score"]))
        score = ((0.5 * trigger_ratio) + (0.4 * relevance_score) + (0.1 * priority_signal))
        fallback_selected = str(selection.get("reason") or "").startswith("fallback_")
        weak_fallback = (
            fallback_selected
            and not requested_canonical
            and trigger_ratio < 0.5
            and relevance_score < 0.15
            and intent_score < 0.2
            and workspace_score < 0.1
        )
        if fallback_selected and not requested_canonical:
            score *= 0.35 if weak_fallback else 0.65
        score = round(max(0.0, min(1.0, score)), 4)
        candidate_signal = round(
            max(0.0, min(1.0, (0.75 * float(selection["score"])) + (0.25 * float(selection["top1_top2_gap"])))),
            4,
        )
        custom_metadata = pack.get("custom_admission")
        route_authority_eligible = bool(selection.get("route_authority_eligible", selection.get("selected") is not None))
        if isinstance(custom_metadata, dict):
            route_authority_eligible = route_authority_eligible and bool(custom_metadata.get("route_authority_eligible", False))
        if weak_fallback:
            route_authority_eligible = False
        pack_results.append(
            {
                "pack_id": normalize_text(pack.get("id")),
                "score": score,
                "intent": round(intent_score, 4),
                "workspace": round(workspace_score, 4),
                "selected_candidate": selection["selected"],
                "candidate_selection_reason": selection["reason"],
                "candidate_selection_score": round(float(selection["score"]), 4),
                "candidate_relevance_score": round(relevance_score, 4),
                "candidate_ranking": selection["ranking"],
                "stage_assistant_candidates": selection.get("stage_assistant_candidates", []),
                "candidate_top1_top2_gap": round(float(selection["top1_top2_gap"]), 4),
                "candidate_signal": candidate_signal,
                "candidate_filtered_out_by_task": selection["filtered_out_by_task"],
                "route_authority_eligible": route_authority_eligible,
                "custom_admission": custom_metadata,
            }
        )

    ranked = sorted(pack_results, key=lambda row: (-row["score"], row["pack_id"]))
    authority_ranked = [row for row in ranked if bool(row.get("route_authority_eligible", True))]
    selection_pool = authority_ranked if authority_ranked else ranked
    top = selection_pool[0] if selection_pool else None
    confidence = float(top["score"]) if top else 0.0
    top_gap = float(top["candidate_top1_top2_gap"]) if top else 0.0
    candidate_signal = float(top["candidate_signal"]) if top else 0.0
    can_override = bool(
        top
        and top["candidate_selection_reason"] in {"keyword_ranked", "requested_skill"}
        and candidate_signal >= min_candidate_signal_confirm
    )
    can_auto_route = bool(
        top
        and top["candidate_selection_reason"] in {"keyword_ranked", "requested_skill"}
        and candidate_signal >= min_candidate_signal_auto
        and top_gap >= min_top_gap
    )

    if not top:
        route_mode = "legacy_fallback"
        route_reason = "no_eligible_pack"
    elif confidence < fallback_threshold:
        route_mode = "pack_overlay"
        if can_auto_route:
            route_reason = "candidate_signal_auto_route"
            confidence = max(confidence, auto_route_threshold)
        elif can_override:
            route_reason = "candidate_signal_host_selection"
        else:
            route_reason = "host_selection_required"
    elif top_gap < min_top_gap:
        route_mode = "pack_overlay"
        route_reason = "top_candidates_host_selection"
    elif confidence < auto_route_threshold:
        if can_auto_route:
            route_mode = "pack_overlay"
            route_reason = "candidate_signal_auto_route"
            confidence = max(confidence, auto_route_threshold)
        else:
            route_mode = "pack_overlay"
            route_reason = "host_selection_required"
    else:
        route_mode = "pack_overlay"
        route_reason = "auto_route"

    deep_discovery_policy_path = repo.config_root / "deep-discovery-policy.json"
    deep_discovery_policy = load_json(deep_discovery_policy_path) if deep_discovery_policy_path.exists() else {}
    deep_discovery_advice = _build_deep_discovery_advice(repo, prompt_lower, grade, task_type)
    intent_contract = _build_deep_discovery_intent_contract(prompt, prompt_lower, deep_discovery_advice, deep_discovery_policy)
    deep_discovery_route_filter_applied = False
    deep_discovery_confirm_relaxed = _relax_deep_discovery_confirm(deep_discovery_advice, intent_contract)
    if (
        route_mode == "pack_overlay"
        and deep_discovery_advice
        and bool(deep_discovery_advice.get("scope_applicable"))
        and bool(deep_discovery_advice.get("confirm_required"))
    ):
        route_mode = "confirm_required"
        route_reason = "deep_discovery_confirm_required"
        confidence = max(confidence, confirm_required_threshold)

    legacy_fallback_guard_applied = False
    legacy_fallback_original_reason = None
    if route_mode == "legacy_fallback" and enforce_confirm_on_legacy_fallback:
        legacy_fallback_original_reason = route_reason
        route_mode = "confirm_required"
        route_reason = "legacy_fallback_guard"
        confidence = max(confidence, confirm_required_threshold)
        legacy_fallback_guard_applied = True

    preferred_selection = _get_preferred_host_selection(top) if top and not bool(top.get("route_authority_eligible", True)) else None
    selected_skill = (
        str(preferred_selection["skill"])
        if preferred_selection
        else _optional_text(top.get("selected_candidate"))
        if top
        else None
    )
    selection_reason = (
        str(preferred_selection["reason"])
        if preferred_selection
        else str(top["candidate_selection_reason"])
        if top
        else None
    )
    selection_score = (
        round(float(preferred_selection["score"]), 4)
        if preferred_selection
        else top["candidate_selection_score"]
        if top
        else None
    )

    result = {
        "prompt": prompt,
        "grade": grade,
        "task_type": task_type,
        "route_mode": route_mode,
        "route_reason": route_reason,
        "confidence": round(confidence, 4),
        "top1_top2_gap": round(top_gap, 4),
        "candidate_signal": round(candidate_signal, 4),
        "legacy_fallback_guard_applied": legacy_fallback_guard_applied,
        "legacy_fallback_original_reason": legacy_fallback_original_reason,
        "alias": {
            "requested_input": requested_skill,
            "requested_canonical": requested_canonical,
            "entry_intent_id": entry_intent_id,
            "requested_grade_floor": requested_grade_floor,
        },
        "thresholds": {
            "auto_route": auto_route_threshold,
            "confirm_required": confirm_required_threshold,
            "fallback_to_legacy_below": fallback_threshold,
            "min_top1_top2_gap": min_top_gap,
            "min_candidate_signal_for_confirm_override": min_candidate_signal_confirm,
            "min_candidate_signal_for_auto_route": min_candidate_signal_auto,
            "enforce_confirm_on_legacy_fallback": enforce_confirm_on_legacy_fallback,
        },
        "selected": (
            {
                "pack_id": top["pack_id"],
                "skill": selected_skill,
                "selection_reason": selection_reason,
                "selection_score": selection_score,
                "top1_top2_gap": top["candidate_top1_top2_gap"],
                "candidate_signal": top["candidate_signal"],
                "filtered_out_by_task": top["candidate_filtered_out_by_task"],
            }
            if top
            else None
        ),
        "ranked": ranked[:3],
        "intent_contract": intent_contract,
        "deep_discovery_route_filter_applied": deep_discovery_route_filter_applied,
        "deep_discovery_route_mode_override": bool(
            route_mode == "confirm_required" and route_reason == "deep_discovery_confirm_required"
        ),
        "runtime_neutral_bridge": {
            "enabled": True,
            "engine": "python",
            "host": "runtime_neutral",
        },
        "custom_admission": {
            "status": custom_admission.get("status"),
            "target_root": custom_admission.get("target_root"),
            "manifest_paths": custom_admission.get("manifest_paths"),
            "manifests_present": custom_admission.get("manifests_present"),
            "invalid_entries": custom_admission.get("invalid_entries"),
            "dependency_failures": custom_admission.get("dependency_failures"),
            "admitted_candidates": custom_admission.get("admitted_candidates"),
        },
    }
    if deep_discovery_advice:
        result["deep_discovery_advice"] = deep_discovery_advice
        result["deep_discovery_confirm_relaxed"] = deep_discovery_confirm_relaxed
    result.update(build_fallback_truth(result, fallback_policy))

    confirm_ui = build_confirm_ui(repo, result, target_root, host_id)
    if confirm_ui:
        result["confirm_ui"] = confirm_ui
    return result
