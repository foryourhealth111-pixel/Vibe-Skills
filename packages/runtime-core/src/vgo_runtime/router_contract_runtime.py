from __future__ import annotations

from pathlib import Path

from .custom_admission import load_custom_admission
from .router_contract_presentation import build_confirm_ui, build_fallback_truth
from .router_contract_selection import get_pack_default_candidate, select_pack_candidate
from .router_contract_support import (
    RepoContext,
    candidate_name_score,
    keyword_ratio,
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


def route_prompt(
    prompt: str,
    grade: str,
    task_type: str,
    requested_skill: str | None = None,
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

    requested_canonical = resolve_requested_canonical(requested_skill, alias_map)
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
            candidates=[normalize_text(item) for item in (pack.get("skill_candidates") or [])],
            task_type=task_type,
            requested_canonical=requested_canonical,
            skill_keyword_index=skill_keyword_index,
            routing_rules=routing_rules,
            pack=pack,
            candidate_selection_config=candidate_selection_cfg,
        )
        trigger_ratio = keyword_ratio(prompt_lower, pack.get("trigger_keywords") or [])
        priority_signal = min(max(float(pack.get("priority", 0)) / 100.0, 0.0), 1.0)
        score = ((0.5 * trigger_ratio) + (0.4 * float(selection["score"])) + (0.1 * priority_signal))
        score = round(max(0.0, min(1.0, score)), 4)
        candidate_signal = round(
            max(0.0, min(1.0, (0.75 * float(selection["score"])) + (0.25 * float(selection["top1_top2_gap"])))),
            4,
        )
        custom_metadata = pack.get("custom_admission")
        route_authority_eligible = True
        if isinstance(custom_metadata, dict):
            route_authority_eligible = bool(custom_metadata.get("route_authority_eligible", False))
        pack_results.append(
            {
                "pack_id": normalize_text(pack.get("id")),
                "score": score,
                "selected_candidate": selection["selected"],
                "candidate_selection_reason": selection["reason"],
                "candidate_selection_score": round(float(selection["score"]), 4),
                "candidate_ranking": selection["ranking"],
                "candidate_top1_top2_gap": round(float(selection["top1_top2_gap"]), 4),
                "candidate_signal": candidate_signal,
                "candidate_filtered_out_by_task": selection["filtered_out_by_task"],
                "route_authority_eligible": route_authority_eligible,
                "custom_admission": custom_metadata,
            }
        )

    ranked = sorted(pack_results, key=lambda row: (-row["score"], row["pack_id"]))
    authority_ranked = [row for row in ranked if bool(row.get("route_authority_eligible", True))]
    top = authority_ranked[0] if authority_ranked else None
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
        if can_auto_route:
            route_mode = "pack_overlay"
            route_reason = "candidate_signal_auto_route"
            confidence = max(confidence, auto_route_threshold)
        elif can_override:
            route_mode = "confirm_required"
            route_reason = "candidate_signal_override"
            confidence = max(confidence, confirm_required_threshold)
        else:
            route_mode = "legacy_fallback"
            route_reason = "confidence_below_fallback"
    elif top_gap < min_top_gap:
        route_mode = "confirm_required"
        route_reason = "top_candidates_too_close"
    elif confidence < auto_route_threshold:
        if can_auto_route:
            route_mode = "pack_overlay"
            route_reason = "candidate_signal_auto_route"
            confidence = max(confidence, auto_route_threshold)
        else:
            route_mode = "confirm_required"
            route_reason = "confidence_requires_confirmation"
    else:
        route_mode = "pack_overlay"
        route_reason = "auto_route"

    legacy_fallback_guard_applied = False
    legacy_fallback_original_reason = None
    if route_mode == "legacy_fallback" and enforce_confirm_on_legacy_fallback:
        legacy_fallback_original_reason = route_reason
        route_mode = "confirm_required"
        route_reason = "legacy_fallback_guard"
        confidence = max(confidence, confirm_required_threshold)
        legacy_fallback_guard_applied = True

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
                "skill": top["selected_candidate"],
                "selection_reason": top["candidate_selection_reason"],
                "selection_score": top["candidate_selection_score"],
                "top1_top2_gap": top["candidate_top1_top2_gap"],
                "candidate_signal": top["candidate_signal"],
                "filtered_out_by_task": top["candidate_filtered_out_by_task"],
            }
            if top
            else None
        ),
        "ranked": ranked[:3],
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
    result.update(build_fallback_truth(result, fallback_policy))

    confirm_ui = build_confirm_ui(repo, result, target_root, host_id)
    if confirm_ui:
        result["confirm_ui"] = confirm_ui
    return result
