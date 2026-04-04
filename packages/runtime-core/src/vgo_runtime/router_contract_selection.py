from __future__ import annotations

from typing import Any

from .router_contract_support import candidate_name_score, keyword_ratio, normalize_text


def get_pack_default_candidate(pack: dict[str, Any], task_type: str, filtered_candidates: list[str], all_candidates: list[str]) -> str | None:
    defaults = pack.get("defaults_by_task") or {}
    preferred = normalize_text(defaults.get(task_type))
    if preferred and preferred in filtered_candidates:
        return preferred
    if preferred and preferred in all_candidates:
        return preferred
    return filtered_candidates[0] if filtered_candidates else (all_candidates[0] if all_candidates else None)


def select_pack_candidate(
    prompt_lower: str,
    candidates: list[str],
    task_type: str,
    requested_canonical: str | None,
    skill_keyword_index: dict[str, Any],
    routing_rules: dict[str, Any],
    pack: dict[str, Any],
    candidate_selection_config: dict[str, Any],
) -> dict[str, Any]:
    if not candidates:
        return {
            "selected": None,
            "score": 0.0,
            "reason": "no_candidates",
            "ranking": [],
            "top1_top2_gap": 0.0,
            "filtered_out_by_task": [],
        }

    if requested_canonical and requested_canonical in candidates:
        return {
            "selected": requested_canonical,
            "score": 1.0,
            "reason": "requested_skill",
            "ranking": [
                {
                    "skill": requested_canonical,
                    "score": 1.0,
                    "keyword_score": 1.0,
                    "name_score": 1.0,
                    "positive_score": 1.0,
                    "negative_score": 0.0,
                    "canonical_for_task_hit": 1.0,
                }
            ],
            "top1_top2_gap": 1.0,
            "filtered_out_by_task": [],
        }

    selection_cfg = skill_keyword_index.get("selection") or {}
    selection_weights = selection_cfg.get("weights") or {}
    weight_keyword = float(selection_weights.get("keyword_match", 0.85))
    weight_name = float(selection_weights.get("name_match", 0.15))
    fallback_min = float(selection_cfg.get("fallback_to_first_when_score_below", 0.15))

    positive_bonus = float(candidate_selection_config.get("rule_positive_keyword_bonus", 0.2))
    negative_penalty = float(candidate_selection_config.get("rule_negative_keyword_penalty", 0.25))
    canonical_bonus = float(candidate_selection_config.get("canonical_for_task_bonus", 0.12))

    rules = (routing_rules.get("skills") or {}) if routing_rules else {}
    filtered_candidates: list[str] = []
    blocked_by_task: list[str] = []
    for candidate in candidates:
        rule = rules.get(candidate) or {}
        task_allow = [normalize_text(item) for item in (rule.get("task_allow") or [])]
        if not task_allow or task_type in task_allow:
            filtered_candidates.append(candidate)
        else:
            blocked_by_task.append(candidate)

    default_candidate = get_pack_default_candidate(pack, task_type, filtered_candidates, candidates)
    if not filtered_candidates:
        fallback = default_candidate or candidates[0]
        return {
            "selected": fallback,
            "score": 0.0,
            "reason": "fallback_task_default_after_task_filter" if default_candidate else "fallback_first_candidate_after_task_filter",
            "ranking": [],
            "top1_top2_gap": 0.0,
            "filtered_out_by_task": blocked_by_task,
        }

    scored: list[dict[str, Any]] = []
    keywords_by_skill = skill_keyword_index.get("skills") or {}
    for ordinal, candidate in enumerate(filtered_candidates):
        skill_entry = keywords_by_skill.get(candidate) or {}
        keyword_score = keyword_ratio(prompt_lower, skill_entry.get("keywords") or [])
        name_score = candidate_name_score(prompt_lower, candidate)

        rule = rules.get(candidate) or {}
        positive_score = keyword_ratio(prompt_lower, rule.get("positive_keywords") or [])
        negative_score = keyword_ratio(prompt_lower, rule.get("negative_keywords") or [])
        canonical_for_task = [normalize_text(item) for item in (rule.get("canonical_for_task") or [])]
        canonical_hit = 1.0 if task_type in canonical_for_task else 0.0

        score = (
            (weight_keyword * keyword_score)
            + (weight_name * name_score)
            + (positive_bonus * positive_score)
            - (negative_penalty * negative_score)
            + (canonical_bonus * canonical_hit)
        )
        score = round(max(0.0, min(1.0, score)), 4)
        scored.append(
            {
                "skill": candidate,
                "score": score,
                "keyword_score": round(keyword_score, 4),
                "name_score": round(name_score, 4),
                "positive_score": round(positive_score, 4),
                "negative_score": round(negative_score, 4),
                "canonical_for_task_hit": round(canonical_hit, 4),
                "ordinal": ordinal,
            }
        )

    ranked = sorted(scored, key=lambda row: (-row["score"], -row["keyword_score"], -row["positive_score"], row["ordinal"]))
    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    gap = round(max(0.0, float(top["score"]) - float(second["score"] if second else 0.0)), 4)

    if top["score"] < fallback_min:
        fallback = default_candidate or filtered_candidates[0]
        default_row = next((row for row in ranked if row["skill"] == fallback), top)
        return {
            "selected": fallback,
            "score": float(default_row["score"]),
            "reason": "fallback_task_default" if fallback == default_candidate else "fallback_first_candidate",
            "ranking": ranked[:6],
            "top1_top2_gap": gap,
            "filtered_out_by_task": blocked_by_task,
        }

    return {
        "selected": top["skill"],
        "score": float(top["score"]),
        "reason": "keyword_ranked",
        "ranking": ranked[:6],
        "top1_top2_gap": gap,
        "filtered_out_by_task": blocked_by_task,
    }
