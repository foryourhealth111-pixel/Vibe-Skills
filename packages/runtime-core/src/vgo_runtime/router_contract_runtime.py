from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .kernel.capability_bridge import CAPABILITY_BRIDGE, ROUTER_CAPABILITY_HINTS
from .kernel.host_skill_roots import resolve_host_skill_roots
from .kernel.skill_index import build_skill_catalog, build_skill_index_from_catalog
from .kernel.text_tokens import SKILL_MATCH_STOPWORDS, tokens_from_text, tokens_from_values
from .runtime_support import (
    RepoContext,
    keyword_hit,
    load_json,
    normalize_text,
    resolve_host_id,
    resolve_target_root,
)


LOCAL_PACK_ID = "local-skill-index"
LOCAL_CANDIDATE_SOURCE = "local_skill_index"
CONTROLLER_REQUESTED_SKILLS = {"vibe"}
AUTO_ROUTE_MIN_SCORE = 0.35
CONFIRM_ROUTE_MIN_SCORE = 0.18
CONFIRM_UI_ROUTE_PREFIX = "Bounded work suggested local skill options"
CONFIRM_UI_SIMPLE_INSTRUCTION = "Reply with an option number or `$<skill>` to make the selection explicit."
GENERIC_CONFIRM_TOKENS = frozenset(
    {
        "clarify",
        "choose",
        "constraint",
        "constraints",
        "create",
        "define",
        "deliverable",
        "deliverables",
        "feature",
        "implement",
        "path",
        "quality",
        "repo",
        "scope",
        "verification",
        "work",
    }
)
CAPABILITY_HINTS = ROUTER_CAPABILITY_HINTS
CAPABILITY_SEARCH_HINTS_BY_CAPABILITY = {
    capability: tuple(spec["skill_inference_hints"])
    for capability, spec in CAPABILITY_BRIDGE
}


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


def _normalize_requested_skill(requested_skill: str | None) -> str | None:
    requested = normalize_text(str(requested_skill or "").lstrip("$"))
    if requested in CONTROLLER_REQUESTED_SKILLS:
        return "vibe"
    return requested or None


def _load_local_thresholds(repo_root: Path) -> dict[str, float]:
    path = repo_root / "config" / "router-thresholds.json"
    if not path.exists():
        return {
            "auto_route": AUTO_ROUTE_MIN_SCORE,
            "confirm_required": CONFIRM_ROUTE_MIN_SCORE,
        }
    payload = load_json(path)
    thresholds = payload.get("thresholds") if isinstance(payload, dict) else {}
    if not isinstance(thresholds, dict):
        thresholds = {}
    return {
        "auto_route": float(thresholds.get("auto_route", AUTO_ROUTE_MIN_SCORE)),
        "confirm_required": float(thresholds.get("confirm_required", CONFIRM_ROUTE_MIN_SCORE)),
        "min_top1_top2_gap": float(thresholds.get("min_top1_top2_gap", 0.0)),
        "min_candidate_signal_for_confirm_override": float(
            thresholds.get("min_candidate_signal_for_confirm_override", CONFIRM_ROUTE_MIN_SCORE)
        ),
        "min_candidate_signal_for_auto_route": float(
            thresholds.get("min_candidate_signal_for_auto_route", AUTO_ROUTE_MIN_SCORE)
        ),
    }


def _resolve_local_host_roots(*, repo_root: Path, host_id: str | None, target_root: Path) -> tuple[Path, ...]:
    normalized_host_id = resolve_host_id(host_id)
    return tuple(
        root.path
        for root in resolve_host_skill_roots(
            repo_root=repo_root,
            host_id=normalized_host_id,
            agent_root=target_root,
            workspace_root=None,
        )
    )


def _entry_search_tokens(entry: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    tokens.update(tokens_from_text(str(entry.get("skill_id") or entry.get("id") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_text(str(entry.get("display_name") or entry.get("name") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_text(str(entry.get("description") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_values(entry.get("capabilities"), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_values(entry.get("tags"), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_values(entry.get("when_to_use"), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    tokens.update(tokens_from_values(_capability_bridge_search_hints(entry), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    return tokens


def _capability_bridge_search_hints(entry: dict[str, Any]) -> list[str]:
    weak_text_capabilities: set[str] = set()
    body_intent_weak_text_capabilities: set[str] = set()
    for row in entry.get("capability_evidence") or []:
        if not isinstance(row, dict):
            continue
        capability = str(row.get("capability") or "").strip()
        if not capability or str(row.get("evidence_level") or "").strip() != "weak_text":
            continue
        weak_text_capabilities.add(capability)
        if str(row.get("source") or "").strip() == "body_text":
            body_intent_weak_text_capabilities.add(capability)
    hints: list[str] = []
    for capability in entry.get("capabilities") or []:
        capability_text = str(capability).strip()
        if not capability_text:
            continue
        if capability_text in weak_text_capabilities and capability_text not in body_intent_weak_text_capabilities:
            continue
        hints.extend(CAPABILITY_SEARCH_HINTS_BY_CAPABILITY.get(capability_text, ()))
    return hints


def _capability_strengths(entry: dict[str, Any]) -> dict[str, float]:
    strengths: dict[str, float] = {}
    for row in entry.get("capability_evidence") or []:
        if not isinstance(row, dict):
            continue
        capability = str(row.get("capability") or "").strip()
        if not capability:
            continue
        strength = float(row.get("strength") or 0.0)
        strengths[capability] = max(strengths.get(capability, 0.0), strength)
    for capability in entry.get("capabilities") or []:
        text = str(capability).strip()
        if text:
            strengths.setdefault(text, 0.55)
    return strengths


def _capability_evidence_level(entry: dict[str, Any], matched_capabilities: list[str]) -> str | None:
    matched = set(matched_capabilities)
    levels: list[str] = []
    for row in entry.get("capability_evidence") or []:
        if not isinstance(row, dict) or str(row.get("capability") or "").strip() not in matched:
            continue
        level = str(row.get("evidence_level") or "").strip()
        if level:
            levels.append(level)
    if "declared" in levels:
        return "declared"
    if "weak_text" in levels:
        return "weak_text"
    return levels[0] if levels else None


def _domain_anchor_score(entry: dict[str, Any], task_card: dict[str, Any]) -> float:
    primary = set(task_card.get("primary_capabilities") or [])
    skill_id = str(entry.get("skill_id") or entry.get("id") or "").casefold()
    identity_text = " ".join(
        [
            skill_id,
            str(entry.get("display_name") or entry.get("name") or ""),
            str(entry.get("description") or ""),
            " ".join(str(tag) for tag in entry.get("tags") or []),
        ]
    ).casefold()
    if "model.data_leakage_guard" in primary and skill_id == "ml-data-leakage-guard":
        return 0.32
    if "model.preprocessing_pipeline" in primary and skill_id == "preprocessing-data-with-automated-pipelines":
        return 0.32
    if "quality.test_report" in primary and skill_id == "generating-test-reports":
        return 0.32
    if "research.literature_review" in primary and skill_id == "literature-review":
        return 0.32
    if "research.pubmed_search" in primary and skill_id == "pubmed-database":
        return 0.55
    if "research.zotero_management" in primary and skill_id == "pyzotero":
        return 0.55
    if "research.citation_management" in primary and skill_id == "citation-management":
        return 0.32
    if "research.critical_appraisal" in primary and skill_id == "scientific-critical-thinking":
        return 0.32
    if "research.scholar_evaluation" in primary and skill_id == "scholar-evaluation":
        return 0.32
    if "research.evidence_retrieval" in primary and skill_id == "flashrag-evidence":
        return 0.32
    if "research.deep_research" in primary and skill_id == "webthinker-deep-research":
        return 0.32
    if "visualization.figure" in primary and skill_id == "scientific-visualization":
        return 0.35
    if "visualization.infographic" in primary and skill_id == "infographics":
        return 0.32
    if "visualization.schematic" in primary and skill_id == "scientific-schematics":
        return 0.32
    if "presentation.deck" in primary and skill_id == "scientific-slides":
        return 0.18
    if "presentation.slidev" in primary and skill_id == "slides-as-code":
        return 0.32
    if "presentation.pptx_poster" in primary and skill_id == "pptx-posters":
        return 0.5
    if "presentation.poster" in primary and skill_id == "latex-posters":
        return 0.32
    if "chem.activity_database" in primary and skill_id == "chembl-database":
        return 0.32
    if "clinical.case_report" in primary and skill_id == "clinical-reports":
        return 0.32
    if any(capability.startswith("statistics.") for capability in primary) and any(
        anchor in identity_text for anchor in ("statistical-analysis", "statistical analysis", "statistics", "统计分析")
    ):
        return 0.08
    if "statistics.regression" in primary and skill_id == "scikit-learn":
        return 0.18
    if "writing.scientific_report" in primary and any(
        anchor in identity_text for anchor in ("scientific-reporting", "scientific reporting", "scientific report")
    ):
        return 0.08
    if "research.causal_analysis" in primary and skill_id == "performing-causal-analysis":
        return 0.08
    if "research.experimental_design" in primary and skill_id == "designing-experiments":
        return 0.08
    if "research.ideation" in primary and skill_id == "scientific-brainstorming":
        return 0.08
    if "research.literature_search" in primary and skill_id == "pubmed-database":
        return 0.08
    if "research.hypothesis_generation" in primary and skill_id == "hypothesis-generation":
        return 0.08
    if "document.latex_submission" in primary and skill_id == "latex-submission-pipeline":
        return 0.18
    if "document.venue_template" in primary and skill_id == "venue-templates":
        return 0.32
    return 0.0


def _build_task_card(prompt_lower: str, task_type: str) -> dict[str, Any]:
    required: list[str] = []
    for capability, hints in CAPABILITY_HINTS:
        if any(keyword_hit(prompt_lower, hint) for hint in hints):
            required.append(capability)

    statistical_work = any(
        capability.startswith(("statistics.", "data."))
        for capability in required
    )
    rejected: list[str] = []
    if statistical_work and not any(hint in prompt_lower for hint in ("study pool", "analysis pool", "data pool", "cohort pool")):
        rejected.append("research.study_plan_pool")

    return {
        "task_type": normalize_text(task_type) or "planning",
        "required_capabilities": _dedupe_strings(required),
        "primary_capabilities": _dedupe_strings(
            [
                capability
                for capability in required
                if capability.startswith(("data.", "statistics.", "model.", "visualization.", "presentation.", "chem.", "clinical.", "writing.scientific", "debug.", "devops.", "observability.", "deploy.", "runtime.", "document.", "quality."))
                or capability.startswith("research.")
            ]
        ),
        "supporting_capabilities": _dedupe_strings(
            [
                capability
                for capability in required
                if not capability.startswith(("data.", "statistics.", "model."))
            ]
        ),
        "rejected_capabilities": _dedupe_strings(rejected),
    }


def _matched_not_for_boundaries(entry: dict[str, Any], prompt_lower: str, query_tokens: set[str]) -> list[str]:
    matches: list[str] = []
    for raw_boundary in entry.get("not_for") or []:
        boundary = str(raw_boundary).strip()
        if not boundary:
            continue
        boundary_lower = normalize_text(boundary)
        if keyword_hit(prompt_lower, boundary_lower):
            matches.append(boundary)
            continue
        boundary_tokens = tokens_from_text(boundary, stem=True, stopwords=SKILL_MATCH_STOPWORDS)
        if not boundary_tokens:
            continue
        overlap = {token for token in boundary_tokens & query_tokens if keyword_hit(prompt_lower, token)}
        required = 2 if len(boundary_tokens) >= 2 else 1
        if len(overlap) >= required and len(overlap) / float(min(4, len(boundary_tokens))) >= 0.75:
            matches.append(boundary)
    return _dedupe_strings(matches)


def _identity_aliases(*values: str) -> list[str]:
    aliases: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        aliases.extend(
            [
                text,
                text.replace("-", " "),
                text.replace("_", " "),
                text.replace("-", "_"),
                text.replace("_", "-"),
                text.replace("-", "").replace("_", ""),
            ]
        )
    return _dedupe_strings(aliases)


def _score_entry(prompt: str, prompt_lower: str, entry: dict[str, Any], task_card: dict[str, Any]) -> dict[str, Any]:
    query_tokens = tokens_from_text(prompt, stem=True, stopwords=SKILL_MATCH_STOPWORDS)
    search_tokens = _entry_search_tokens(entry)
    matched_tokens = sorted(token for token in (query_tokens & search_tokens) if keyword_hit(prompt_lower, token))
    token_score = min(1.0, len(matched_tokens) / float(min(4, max(1, len(query_tokens)))))
    skill_id = str(entry.get("skill_id") or entry.get("id") or "").strip()
    name = str(entry.get("display_name") or entry.get("name") or "").strip()
    identity_text = " ".join(
        [
            skill_id,
            name,
            str(entry.get("description") or ""),
            " ".join(str(tag) for tag in entry.get("tags") or []),
        ]
    ).casefold()
    name_score = 1.0 if any(keyword_hit(prompt_lower, value) for value in _identity_aliases(skill_id, name)) else 0.0
    if skill_id == "pdf" and any(
        hint in prompt_lower
        for hint in ("research report", "executive summary", "quarto", "科研报告", "科研技术报告", "实验结果", "matplotlib", "tiff", "科研绘图", "多子图", "slidev", "组会汇报")
    ):
        name_score = 0.0
    tag_score = min(1.0, len(set(tokens_from_values(entry.get("tags"), stem=True, stopwords=SKILL_MATCH_STOPWORDS)) & query_tokens) / 2.0)
    required_capabilities = set(task_card.get("required_capabilities") or [])
    primary_capabilities = set(task_card.get("primary_capabilities") or [])
    supporting_capabilities = set(task_card.get("supporting_capabilities") or [])
    rejected_capabilities = set(task_card.get("rejected_capabilities") or [])
    if skill_id == "pdf" and "document.latex_submission" in required_capabilities:
        name_score = 0.0
    entry_capabilities = set(entry.get("capabilities") or [])
    matched_capabilities = sorted(required_capabilities & entry_capabilities)
    matched_primary_capabilities = sorted(primary_capabilities & entry_capabilities)
    matched_supporting_capabilities = sorted(supporting_capabilities & entry_capabilities)
    rejected_capability_matches = sorted(rejected_capabilities & entry_capabilities)
    if (
        "visualization.figure" in matched_primary_capabilities
        and not any(anchor in identity_text for anchor in ("visualization", "figure", "plot", "matplotlib", "chart", "infographic"))
    ):
        matched_capabilities = [capability for capability in matched_capabilities if capability != "visualization.figure"]
        matched_primary_capabilities = [capability for capability in matched_primary_capabilities if capability != "visualization.figure"]
        matched_supporting_capabilities = [capability for capability in matched_supporting_capabilities if capability != "visualization.figure"]
    weak_capabilities = {
        str(row.get("capability") or "").strip()
        for row in entry.get("capability_evidence") or []
        if isinstance(row, dict) and str(row.get("evidence_level") or "").strip() == "weak_text"
    }
    if any(anchor in identity_text for anchor in ("visualization", "figure", "plot", "matplotlib", "chart", "infographic")):
        weak_analysis_capabilities = {
            capability
            for capability in weak_capabilities
            if capability.startswith("data.") or capability.startswith("statistics.")
        }
        if weak_analysis_capabilities:
            matched_capabilities = [capability for capability in matched_capabilities if capability not in weak_analysis_capabilities]
            matched_primary_capabilities = [capability for capability in matched_primary_capabilities if capability not in weak_analysis_capabilities]
            matched_supporting_capabilities = [capability for capability in matched_supporting_capabilities if capability not in weak_analysis_capabilities]
    capability_strengths = _capability_strengths(entry)
    capability_score = 0.0
    if required_capabilities:
        primary_strength = sum(capability_strengths.get(capability, 0.0) for capability in matched_primary_capabilities)
        supporting_strength = 0.35 * sum(capability_strengths.get(capability, 0.0) for capability in matched_supporting_capabilities)
        denominator = min(3, len(primary_capabilities) or len(required_capabilities))
        capability_score = min(1.0, (primary_strength + supporting_strength) / float(denominator))
    if (
        len(primary_capabilities) == 1
        and "quality.test_report" in primary_capabilities
        and "quality.test_report" in matched_primary_capabilities
        and not any(anchor in identity_text for anchor in ("test-report", "test report", "generating-test-reports", "pytest", "coverage"))
    ):
        capability_score = 0.0
    domain_anchor_score = _domain_anchor_score(entry, task_card)
    capability_weighted_score = (0.7 * capability_score) + (0.2 * token_score) + (0.1 * tag_score) + domain_anchor_score
    local_lexical_score = (0.75 * token_score) + (0.25 * tag_score) if not required_capabilities or not entry_capabilities else 0.0
    base_score = max(name_score, capability_weighted_score, local_lexical_score)
    if rejected_capability_matches:
        base_score = min(base_score, 0.1)
    matched_not_for = _matched_not_for_boundaries(entry, prompt_lower, query_tokens)
    if matched_not_for:
        base_score = min(base_score, 0.05)
    score = round(base_score, 4)
    return {
        "score": score,
        "matched_tokens": matched_tokens,
        "matched_capabilities": matched_capabilities,
        "matched_primary_capabilities": matched_primary_capabilities,
        "matched_supporting_capabilities": matched_supporting_capabilities,
        "rejected_capabilities": rejected_capability_matches,
        "capability_evidence_level": _capability_evidence_level(entry, matched_capabilities),
        "capability_score": round(capability_score, 4),
        "domain_anchor_score": round(domain_anchor_score, 4),
        "keyword_score": round(token_score, 4),
        "name_score": round(name_score, 4),
        "tag_score": round(tag_score, 4),
        "matched_not_for": matched_not_for,
    }


def _candidate_row(entry: dict[str, Any], score: dict[str, Any], *, selected: bool) -> dict[str, Any]:
    skill_id = str(entry.get("skill_id") or entry.get("id") or "").strip()
    return {
        "pack_id": LOCAL_PACK_ID,
        "candidate_source": LOCAL_CANDIDATE_SOURCE,
        "source_root": entry.get("source_root"),
        "source_kind": entry.get("source_kind"),
        "source_priority": entry.get("source_priority"),
        "source_order": entry.get("source_order"),
        "skill": skill_id,
        "selected_candidate": skill_id if selected else None,
        "score": score["score"],
        "selection_score": score["score"],
        "candidate_selection_score": score["score"],
        "candidate_selection_reason": "capability_ranked" if selected and score["matched_capabilities"] else "keyword_ranked" if selected else "rejected_by_task_card" if score["rejected_capabilities"] else "below_local_threshold",
        "candidate_signal": score["score"],
        "candidate_ranking": [
            {
                "skill": skill_id,
                "score": score["score"],
                "matched_tokens": score["matched_tokens"],
                "matched_capabilities": score["matched_capabilities"],
            }
        ],
        "candidate_top1_top2_gap": score["score"],
        "candidate_filtered_out_by_task": score["rejected_capabilities"],
        "native_skill_entrypoint": entry.get("native_skill_entrypoint"),
        "skill_root": entry.get("skill_root"),
        "description": entry.get("description"),
        "capabilities": list(entry.get("capabilities") or []),
        "capability_card_path": entry.get("capability_card_path"),
        "matched_tokens": score["matched_tokens"],
        "matched_capabilities": score["matched_capabilities"],
        "matched_primary_capabilities": score["matched_primary_capabilities"],
        "matched_supporting_capabilities": score["matched_supporting_capabilities"],
        "rejected_capabilities": score["rejected_capabilities"],
        "capability_evidence_level": score["capability_evidence_level"],
        "capability_score": score["capability_score"],
        "domain_anchor_score": score["domain_anchor_score"],
        "role": "primary_owner" if selected else "candidate",
        "authority_tier": "local_installed",
        "authority_eligible": bool(selected) and not score["rejected_capabilities"],
        "authority_rejection_reasons": [] if selected else ["rejected_by_task_card"] if score["rejected_capabilities"] else ["candidate_signal_below_local_threshold"],
    }


def _top1_top2_gap(scored_rows: list[dict[str, Any]]) -> float:
    if not scored_rows:
        return 0.0
    top = float(scored_rows[0]["score"])
    second = float(scored_rows[1]["score"]) if len(scored_rows) > 1 else 0.0
    return round(max(0.0, top - second), 4)


def _has_confirmable_near_match(row: dict[str, Any]) -> bool:
    if row.get("matched_capabilities") and row.get("capability_evidence_level") != "weak_text":
        return True
    if row.get("matched_capabilities") and float(row.get("domain_anchor_score") or 0.0) > 0.0:
        return True
    specific_tokens = {
        str(token).casefold()
        for token in row.get("matched_tokens") or []
        if str(token).casefold() not in GENERIC_CONFIRM_TOKENS
    }
    return len(specific_tokens) >= 2


def _selected_payload(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "pack_id": LOCAL_PACK_ID,
        "candidate_source": LOCAL_CANDIDATE_SOURCE,
        "skill": row["skill"],
        "selection_reason": reason,
        "selection_score": row["score"],
        "top1_top2_gap": row["candidate_top1_top2_gap"],
        "candidate_signal": row["candidate_signal"],
        "filtered_out_by_task": row.get("candidate_filtered_out_by_task") or [],
        "native_skill_entrypoint": row.get("native_skill_entrypoint"),
        "skill_root": row.get("skill_root"),
        "capability_card_path": row.get("capability_card_path"),
        "matched_capabilities": row.get("matched_capabilities") or [],
        "source_root": row.get("source_root"),
        "source_kind": row.get("source_kind"),
        "authority": {
            "tier": "local_installed",
            "eligible": True,
        },
    }


def _mark_selected_row(row: dict[str, Any], *, role: str, reason: str) -> dict[str, Any]:
    selected = dict(row)
    selected["selected_candidate"] = selected["skill"]
    selected["candidate_selection_reason"] = reason
    selected["authority_eligible"] = True
    selected["authority_rejection_reasons"] = []
    selected["role"] = role
    return selected


def _skill_is_named(row: dict[str, Any], prompt_lower: str) -> bool:
    skill = str(row.get("skill") or "").strip()
    if not skill:
        return False
    return any(keyword_hit(prompt_lower, alias) for alias in _identity_aliases(skill))


def _specialist_surfaces(row: dict[str, Any], required_capabilities: set[str], prompt_lower: str) -> set[str]:
    skill = str(row.get("skill") or "").casefold()
    matched_capabilities = set(row.get("matched_capabilities") or [])
    surfaces: set[str] = set()

    if "data.eda" in required_capabilities and "data.eda" in matched_capabilities and ("exploratory" in skill or skill == "eda"):
        surfaces.add("data.eda")
    if matched_capabilities & {"statistics.relationship_modeling", "statistics.correlation", "statistics.regression"} and "statistical" in skill:
        surfaces.add("statistics")
    if "model.training" in required_capabilities and "model.training" in matched_capabilities and ("scikit" in skill or "machine-learning" in skill):
        surfaces.add("model.training")
    if "model.explainability" in required_capabilities and "model.explainability" in matched_capabilities and ("shap" in skill or "explain" in skill):
        surfaces.add("model.explainability")
    if "visualization.figure" in required_capabilities and "visualization.figure" in matched_capabilities and (
        "matplotlib" in skill or "visualization" in skill or "figure" in skill
    ):
        surfaces.add("visualization.figure")
    if "presentation.deck" in required_capabilities and "presentation.deck" in matched_capabilities and (
        "ppt" in skill or "pptx" in skill or "slide" in skill or "presentation" in skill
    ) and ("image-first" not in skill or _skill_is_named(row, prompt_lower)):
        surfaces.add("presentation.deck")
    if "document.latex_submission" in required_capabilities and "document.latex_submission" in matched_capabilities and "latex" in skill:
        surfaces.add("document.latex_submission")

    return surfaces


def _presentation_delivery_priority(row: dict[str, Any], prompt_lower: str) -> tuple[int, float, str]:
    skill = str(row.get("skill") or "").casefold()
    if _skill_is_named(row, prompt_lower):
        priority = 0
    elif "pptx" in skill:
        priority = 1
    elif "presentation" in skill or "slide" in skill or "deck" in skill:
        priority = 2
    elif "image-first" in skill or "paper2ppt" in skill or "gptimage" in skill or "pdf-to" in skill:
        priority = 4
    else:
        priority = 3
    return (priority, -float(row.get("score") or 0.0), skill)


def _preferred_presentation_skill(
    scored_rows: list[dict[str, Any]],
    required_capabilities: set[str],
    prompt_lower: str,
) -> str | None:
    if "presentation.deck" not in required_capabilities:
        return None
    rows = [
        row
        for row in scored_rows
        if not row.get("rejected_capabilities")
        and "presentation.deck" in _specialist_surfaces(row, required_capabilities, prompt_lower)
    ]
    if not rows:
        return None
    return str(min(rows, key=lambda row: _presentation_delivery_priority(row, prompt_lower)).get("skill") or "")


def _selected_rows_for_route(
    scored_rows: list[dict[str, Any]],
    selected_row: dict[str, Any] | None,
    *,
    grade: str,
    task_card: dict[str, Any],
    prompt_lower: str,
    thresholds: dict[str, float],
    requested_canonical: str | None,
    selection_reason: str,
) -> list[dict[str, Any]]:
    if selected_row is None:
        return []

    primary = _mark_selected_row(selected_row, role="primary_owner", reason=selection_reason)
    selected_rows = [primary]
    if requested_canonical or normalize_text(grade).upper() != "XL":
        return selected_rows

    required_capabilities = set(task_card.get("required_capabilities") or [])
    if len(required_capabilities) <= 1:
        return selected_rows

    selected_surfaces = _specialist_surfaces(primary, required_capabilities, prompt_lower)
    selected_skill_ids = {str(primary.get("skill") or "")}
    preferred_presentation_skill = _preferred_presentation_skill(scored_rows, required_capabilities, prompt_lower)

    for row in scored_rows:
        if len(selected_rows) >= 6:
            break
        skill = str(row.get("skill") or "").strip()
        if not skill or skill in selected_skill_ids:
            continue
        if row.get("rejected_capabilities"):
            continue

        surfaces = _specialist_surfaces(row, required_capabilities, prompt_lower)
        if (
            "presentation.deck" in surfaces
            and "presentation.deck" not in selected_surfaces
            and preferred_presentation_skill
            and skill != preferred_presentation_skill
        ):
            continue
        adds_surface = bool(surfaces - selected_surfaces)
        explicitly_named = _skill_is_named(row, prompt_lower)
        if skill == "pdf" and "document.latex_submission" in required_capabilities:
            explicitly_named = False
        if not adds_surface and not explicitly_named:
            continue

        reason = "composite_xl_specialist_surface" if adds_surface else "explicit_xl_skill"
        selected_rows.append(_mark_selected_row(row, role="supporting_owner", reason=reason))
        selected_skill_ids.add(skill)
        selected_surfaces.update(surfaces)

    return selected_rows


def _empty_custom_admission(target_root: Path | None) -> dict[str, Any]:
    return {
        "status": "disabled_default_local_index_only",
        "target_root": str(target_root) if target_root is not None else None,
        "manifest_paths": {},
        "manifests_present": {},
        "invalid_entries": [],
        "dependency_failures": [],
        "admitted_candidates": [],
    }


def _public_admitted_candidates(rows: object) -> list[dict[str, object]]:
    return [dict(row) for row in rows or [] if isinstance(row, dict)]


def _public_pack_row(row: dict[str, object]) -> dict[str, object]:
    return dict(row)


def _public_custom_metadata(value: object) -> object:
    return dict(value) if isinstance(value, dict) else value


def _public_nested_pack_metadata(value: object) -> object:
    return dict(value) if isinstance(value, dict) else value


def _build_deep_discovery_advice(repo: RepoContext, prompt_lower: str, grade: str, task_type: str) -> dict[str, object] | None:
    return None


def _list_strings(value: object, default: list[str] | None = None) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return list(default or [])


def _quality_debt_external_payload(
    *,
    enabled: bool,
    command: str | None,
    invoke_mode: str,
    status: str,
    tool_available: bool = False,
    should_invoke: bool = False,
    manual_command_hint: str | None = None,
) -> dict[str, object]:
    return {
        "enabled": enabled,
        "command": command,
        "invoke_mode": invoke_mode,
        "status": status,
        "tool_available": tool_available,
        "should_invoke": should_invoke,
        "invoked": False,
        "manual_command_hint": manual_command_hint,
        "output_excerpt": None,
        "error": None,
    }


def _quality_debt_off_advice(reason: str) -> dict[str, object]:
    return {
        "enabled": False,
        "mode": "off",
        "task_applicable": False,
        "grade_applicable": False,
        "pack_applicable": False,
        "skill_applicable": False,
        "scope_applicable": False,
        "enforcement": "none",
        "reason": reason,
        "preserve_routing_assignment": True,
        "risk_signal_score": 0.0,
        "debt_likelihood": "none",
        "risk_keyword_hits": [],
        "suppress_keyword_hits": [],
        "focus_facets_matched": [],
        "focus_facet_hits": {},
        "confirm_recommended": False,
        "confirm_required": False,
        "should_apply_hook": False,
        "recommended_followup": None,
        "external_analyzer": _quality_debt_external_payload(
            enabled=False,
            command=None,
            invoke_mode="disabled",
            status="disabled",
        ),
    }


def _keyword_ratio(prompt_lower: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    matched = sum(1 for keyword in keywords if keyword_hit(prompt_lower, keyword))
    if matched <= 0:
        return 0.0
    return min(1.0, matched / float(min(len(keywords), 4)))


def _build_quality_debt_advice(
    *,
    repo_root: Path,
    prompt_lower: str,
    grade: str,
    task_type: str,
    route_mode: str,
    selected: dict[str, Any] | None,
) -> dict[str, object]:
    policy_path = repo_root / "config" / "quality-debt-overlay.json"
    if not policy_path.exists():
        return _quality_debt_off_advice("policy_missing")

    policy = load_json(policy_path)
    if not isinstance(policy, dict):
        return _quality_debt_off_advice("policy_missing")

    enabled = bool(policy.get("enabled", True))
    mode = str(policy.get("mode") or "off")
    if not enabled or mode == "off":
        return _quality_debt_off_advice("policy_off")

    selected_pack = str((selected or {}).get("pack_id") or LOCAL_PACK_ID)
    selected_skill = str((selected or {}).get("skill") or "")
    monitor = policy.get("monitor") if isinstance(policy.get("monitor"), dict) else {}
    pack_allow = _list_strings(monitor.get("pack_allow"), ["code-quality"])
    skill_allow = _list_strings(monitor.get("skill_allow"), [])
    task_allow = _list_strings(policy.get("task_allow"), ["coding", "review"])
    grade_allow = _list_strings(policy.get("grade_allow"), ["L", "XL"])

    normalized_task = normalize_text(task_type) or "planning"
    normalized_grade = normalize_text(grade).upper() or "M"
    task_applicable = normalized_task in task_allow
    grade_applicable = normalized_grade in grade_allow
    pack_applicable = True if route_mode == "local_skill_overlay" else (not pack_allow or selected_pack in pack_allow)
    skill_applicable = True if route_mode == "local_skill_overlay" else (not skill_allow or selected_skill in skill_allow)
    scope_applicable = task_applicable and grade_applicable and pack_applicable and skill_applicable

    thresholds = policy.get("thresholds") if isinstance(policy.get("thresholds"), dict) else {}
    confirm_risk_min = float(thresholds.get("confirm_risk_score_min", 0.65))
    high_risk_min = float(thresholds.get("high_risk_score_min", 0.8))
    suppress_weight = float(thresholds.get("suppress_penalty_weight", 0.35))
    min_risk_hits = int(thresholds.get("min_risk_hits_for_overlay", 1))
    risk_keywords = _list_strings(policy.get("risk_keywords"), [])
    suppress_keywords = _list_strings(policy.get("suppress_keywords"), [])
    risk_hits = [keyword for keyword in risk_keywords if keyword_hit(prompt_lower, keyword)]
    suppress_hits = [keyword for keyword in suppress_keywords if keyword_hit(prompt_lower, keyword)]
    risk_score = max(0.0, min(1.0, _keyword_ratio(prompt_lower, risk_keywords) - (suppress_weight * _keyword_ratio(prompt_lower, suppress_keywords))))
    if len(risk_hits) < min_risk_hits:
        risk_score = 0.0

    debt_likelihood = "none"
    if risk_score >= high_risk_min:
        debt_likelihood = "high"
    elif risk_score >= confirm_risk_min:
        debt_likelihood = "medium"
    elif risk_score > 0.0:
        debt_likelihood = "low"

    focus_hits: dict[str, list[str]] = {}
    focus_facets = policy.get("focus_facets") if isinstance(policy.get("focus_facets"), dict) else {}
    for facet, keywords in focus_facets.items():
        hits = [keyword for keyword in _list_strings(keywords) if keyword_hit(prompt_lower, keyword)]
        focus_hits[str(facet)] = hits
    matched_facets = [facet for facet, hits in focus_hits.items() if hits]

    confirm_recommended = scope_applicable and risk_score >= confirm_risk_min
    enforcement = "none"
    reason = "outside_scope"
    if scope_applicable:
        if mode == "strict" and confirm_recommended:
            enforcement = "confirm_required"
            reason = "strict_confirm_high_risk"
        elif mode == "shadow":
            enforcement = "advisory"
            reason = "shadow_advisory"
        elif mode == "soft":
            enforcement = "advisory"
            reason = "soft_high_risk_advisory" if confirm_recommended else "soft_advisory"
        else:
            enforcement = "advisory"
            reason = "strict_advisory_low_risk" if mode == "strict" else "unknown_mode_advisory"
    confirm_required = enforcement == "confirm_required"

    external = policy.get("external_analyzer") if isinstance(policy.get("external_analyzer"), dict) else {}
    external_enabled = bool(external.get("enabled", False))
    external_command = str(external.get("command") or "") or None
    external_invoke_mode = str(external.get("invoke_mode") or ("manual_only" if external_enabled else "disabled"))
    external_run_modes = _list_strings(external.get("run_in_modes"), ["soft", "strict"])
    external_risk_min = float(external.get("risk_score_min", confirm_risk_min))
    manual_command_hint = str(external.get("manual_command_hint") or "") or (
        f"{external_command} analyze --path <repo>" if external_command else None
    )
    external_status = "disabled"
    tool_available = False
    should_invoke = False
    if scope_applicable and external_enabled:
        if mode not in external_run_modes:
            external_status = "skipped_mode"
        elif risk_score < external_risk_min:
            external_status = "risk_below_threshold"
        elif not external_command:
            external_status = "command_missing"
        else:
            should_invoke = True
            tool_available = shutil.which(external_command) is not None
            external_status = "not_executed_manual_mode" if tool_available else "tool_unavailable"

    return {
        "enabled": True,
        "mode": mode,
        "task_applicable": task_applicable,
        "grade_applicable": grade_applicable,
        "pack_applicable": pack_applicable,
        "skill_applicable": skill_applicable,
        "scope_applicable": scope_applicable,
        "enforcement": enforcement,
        "reason": reason,
        "preserve_routing_assignment": bool(policy.get("preserve_routing_assignment", True)),
        "risk_signal_score": round(risk_score, 4),
        "debt_likelihood": debt_likelihood,
        "risk_keyword_hits": risk_hits,
        "suppress_keyword_hits": suppress_hits,
        "focus_facets_matched": matched_facets,
        "focus_facet_hits": focus_hits,
        "confirm_recommended": confirm_recommended,
        "confirm_required": confirm_required,
        "should_apply_hook": scope_applicable and (risk_score > 0.0 or confirm_required),
        "recommended_followup": "Run focused quality review and debt cleanup checklist before merge."
        if scope_applicable and debt_likelihood in {"medium", "high"}
        else None,
        "external_analyzer": _quality_debt_external_payload(
            enabled=external_enabled,
            command=external_command,
            invoke_mode=external_invoke_mode,
            status=external_status,
            tool_available=tool_available,
            should_invoke=should_invoke,
            manual_command_hint=manual_command_hint,
        ),
    }


def choose_authoritative_route(
    ranked: list[dict[str, Any]],
    task_type: str,
    requested_canonical: str | None,
    authority_policy: dict[str, Any],
) -> dict[str, Any]:
    top = ranked[0] if ranked else None
    if top is None:
        return {
            "selected_pack_id": None,
            "selected_skill": None,
            "selected_row": None,
            "fallback_applied": False,
            "fallback_target_pack_id": None,
            "fallback_target_skill": None,
            "pre_fallback_top_pack_id": None,
            "pre_fallback_top_skill": None,
            "rejected_specialist_reasons": [],
        }
    selected_skill = str(top.get("selected_candidate") or top.get("skill") or "").strip() or None
    return {
        "selected_pack_id": str(top.get("pack_id") or LOCAL_PACK_ID),
        "selected_skill": selected_skill,
        "selected_row": top if selected_skill else None,
        "fallback_applied": False,
        "fallback_target_pack_id": None,
        "fallback_target_skill": None,
        "pre_fallback_top_pack_id": str(top.get("pack_id") or LOCAL_PACK_ID),
        "pre_fallback_top_skill": str(top.get("skill") or ""),
        "rejected_specialist_reasons": list(top.get("authority_rejection_reasons") or []),
    }


def _build_route_decision_contract(
    *,
    selected_pack: str,
    selected_skill: str,
    options: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "decision_kind": "route_selection",
        "selected_pack": selected_pack,
        "selected_skill": selected_skill,
        "options": options,
        "preferred_payload": {
            "decision_kind": "route_selection",
            "selected_pack": selected_pack,
            "selected_skill": selected_skill,
        },
    }


def build_confirm_ui(
    repo: RepoContext,
    route_result: dict[str, Any],
    target_root: str | None,
    host_id: str | None = None,
) -> dict[str, object] | None:
    selected = route_result.get("selected")
    if not isinstance(selected, dict):
        return None
    selected_skill = str(selected.get("skill") or "").strip()
    if not selected_skill:
        return None

    options: list[dict[str, object]] = []
    for index, row in enumerate(route_result.get("ranked", [])[:6], start=1):
        if not isinstance(row, dict):
            continue
        skill = str(row.get("skill") or row.get("selected_candidate") or "").strip()
        if not skill:
            continue
        options.append(
            {
                "option_id": str(index),
                "pack_id": LOCAL_PACK_ID,
                "skill": skill,
                "score": row.get("score"),
                "description": row.get("description"),
                "native_skill_entrypoint": row.get("native_skill_entrypoint"),
            }
        )
    if not options:
        return None

    rendered = [f"{CONFIRM_UI_ROUTE_PREFIX} `{LOCAL_PACK_ID}`."]
    for option in options:
        score = option["score"]
        score_text = f" (score={round(float(score), 4)})" if score is not None else ""
        description = str(option.get("description") or "").strip()
        if description:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text} - {description}")
        else:
            rendered.append(f"{option['option_id']}. `{option['skill']}`{score_text}")
    rendered.append(CONFIRM_UI_SIMPLE_INSTRUCTION)

    return {
        "enabled": True,
        "pack_id": LOCAL_PACK_ID,
        "selected_skill": selected_skill,
        "options": options,
        "route_decision_contract": _build_route_decision_contract(
            selected_pack=LOCAL_PACK_ID,
            selected_skill=selected_skill,
            options=options,
        ),
        "clarification_questions": [],
        "rendered_text": "\n".join(rendered),
        "hazard_alert_required": False,
        "truth_level": route_result.get("truth_level"),
        "degradation_state": route_result.get("degradation_state"),
        "hazard_alert": None,
    }


def build_fallback_truth(route_result: dict[str, Any], fallback_policy: dict[str, Any] | None) -> dict[str, Any]:
    fallback_active = str(route_result.get("route_mode") or "") == "no_local_candidate"
    return {
        "fallback_active": False,
        "hazard_alert_required": False,
        "truth_level": "authoritative" if not fallback_active else "local_index_no_match",
        "degradation_state": "standard" if not fallback_active else "no_local_candidate",
        "non_authoritative": False,
        "hazard_alert": None,
    }


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
    repo_path = repo_root or Path(__file__).resolve().parents[4]
    normalized_host_id = resolve_host_id(host_id)
    resolved_target_root = resolve_target_root(target_root, normalized_host_id)
    thresholds = _load_local_thresholds(repo_path)
    host_roots = _resolve_local_host_roots(
        repo_root=repo_path,
        host_id=normalized_host_id,
        target_root=resolved_target_root,
    )
    catalog = build_skill_catalog(agent_root=resolved_target_root, host_roots=host_roots)
    index = build_skill_index_from_catalog(catalog)
    prompt_lower = normalize_text(prompt)
    requested_canonical = _normalize_requested_skill(requested_skill)
    requested_controller = requested_canonical == "vibe"

    active_entries = [entry for entry in index.get("skills", []) if isinstance(entry, dict)]
    by_skill_id = {
        normalize_text(entry.get("skill_id") or entry.get("id")): entry
        for entry in active_entries
        if normalize_text(entry.get("skill_id") or entry.get("id"))
    }
    task_card = _build_task_card(prompt_lower, task_type)

    scored_rows: list[dict[str, Any]] = []
    for entry in active_entries:
        score = _score_entry(prompt, prompt_lower, entry, task_card)
        scored_rows.append(_candidate_row(entry, score, selected=False))
    scored_rows.sort(
        key=lambda row: (
            -float(row["score"]),
            int(row.get("source_priority") or 0),
            int(row.get("source_order") or 0),
            str(row["skill"]),
        )
    )
    top1_top2_gap = _top1_top2_gap(scored_rows)
    if scored_rows:
        scored_rows[0]["candidate_top1_top2_gap"] = top1_top2_gap

    selected_row: dict[str, Any] | None = None
    route_reason = "no_local_candidate_above_threshold"
    selection_reason = "no_local_candidate"
    rejected_reasons: list[str] = []

    if requested_canonical and not requested_controller:
        requested_entry = by_skill_id.get(requested_canonical)
        if requested_entry is not None:
            selected_row = _candidate_row(
                requested_entry,
                {
                    "score": 1.0,
                    "matched_tokens": [requested_canonical],
                    "matched_capabilities": [],
                    "matched_primary_capabilities": [],
                    "matched_supporting_capabilities": [],
                    "rejected_capabilities": [],
                    "capability_evidence_level": None,
                    "capability_score": 0.0,
                    "domain_anchor_score": 0.0,
                    "keyword_score": 1.0,
                    "name_score": 1.0,
                    "tag_score": 0.0,
                },
                selected=True,
            )
            route_reason = "explicit_local_skill"
            selection_reason = "requested_skill"
            selected_row["candidate_top1_top2_gap"] = 1.0
        else:
            route_reason = "requested_local_skill_not_found"
            selection_reason = "requested_skill_missing"
            rejected_reasons.append(requested_canonical)
    elif (
        scored_rows
        and float(scored_rows[0]["score"]) >= float(thresholds["min_candidate_signal_for_auto_route"])
        and float(top1_top2_gap) >= float(thresholds["min_top1_top2_gap"])
    ):
        selected_row = dict(scored_rows[0])
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "capability_ranked" if selected_row["matched_capabilities"] else "keyword_ranked"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "auto_route"
        selection_reason = selected_row["candidate_selection_reason"]
    elif scored_rows and float(scored_rows[0]["score"]) >= float(thresholds["confirm_required"]):
        selected_row = dict(scored_rows[0])
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "capability_ranked" if selected_row["matched_capabilities"] else "keyword_ranked"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "candidate_signal_host_selection"
        selection_reason = selected_row["candidate_selection_reason"]
    elif (
        scored_rows
        and float(scored_rows[0]["score"]) >= float(thresholds["min_candidate_signal_for_confirm_override"])
        and _has_confirmable_near_match(scored_rows[0])
        and not scored_rows[0]["rejected_capabilities"]
    ):
        selected_row = dict(scored_rows[0])
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "near_match_confirm_required"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "candidate_signal_confirm_override"
        selection_reason = "near_match_confirm_required"

    selected_rows = _selected_rows_for_route(
        scored_rows,
        selected_row,
        grade=grade,
        task_card=task_card,
        prompt_lower=prompt_lower,
        thresholds=thresholds,
        requested_canonical=None if requested_controller else requested_canonical,
        selection_reason=selection_reason,
    )
    selected_skill_ids = {str(row.get("skill") or "") for row in selected_rows}
    ranked_rows = selected_rows + [
        row for row in scored_rows if str(row.get("skill") or "") not in selected_skill_ids
    ]

    primary_row = selected_rows[0] if selected_rows else None
    selected = _selected_payload(primary_row, reason=selection_reason) if primary_row is not None else None
    confidence = float(primary_row["score"]) if primary_row is not None else (float(ranked_rows[0]["score"]) if ranked_rows else 0.0)
    public_top1_top2_gap = float(primary_row["candidate_top1_top2_gap"]) if primary_row is not None else 0.0
    route_mode = "local_skill_overlay" if selected is not None else "no_local_candidate"
    result: dict[str, Any] = {
        "prompt": prompt,
        "grade": normalize_text(grade).upper() or "M",
        "task_type": normalize_text(task_type) or "planning",
        "router_contract_mode": "candidate_discovery_only",
        "work_binding_truth_source": "kernel",
        "candidate_source": LOCAL_CANDIDATE_SOURCE,
        "route_mode": route_mode,
        "route_reason": route_reason,
        "task_card": task_card,
        "confidence": round(confidence, 4),
        "top1_top2_gap": round(public_top1_top2_gap, 4),
        "candidate_signal": round(confidence, 4),
        "fallback_applied": False,
        "fallback_target": {
            "pack_id": None,
            "skill": None,
        },
        "pre_fallback_top": {
            "pack_id": LOCAL_PACK_ID if ranked_rows else None,
            "skill": str(ranked_rows[0]["skill"]) if ranked_rows else None,
        },
        "rejected_specialist_reasons": rejected_reasons,
        "thresholds": thresholds,
        "alias": {
            "requested_input": requested_skill,
            "requested_canonical": requested_canonical,
            "entry_intent_id": entry_intent_id,
            "requested_grade_floor": requested_grade_floor,
        },
        "local_skill_index": {
            "schema_version": index["schema_version"],
            "host_id": normalized_host_id,
            "target_root": str(resolved_target_root),
            "host_roots": [str(path.resolve()) for path in host_roots],
            "skill_count": len(active_entries),
            "discovery_diagnostics": index["discovery_diagnostics"],
            "skill_cache": index["skill_cache"],
        },
        "custom_admission": _empty_custom_admission(resolved_target_root),
        "candidates": ranked_rows[:6],
        "primary_candidate": selected,
        "selected": selected,
        "ranked": ranked_rows[:6],
        "skill_routing": {
            "schema_version": "composite_skill_routing_v1",
            "primary_skill": str(primary_row.get("skill") or "") if primary_row is not None else None,
            "selected": selected_rows,
        },
        "quality_debt_advice": _build_quality_debt_advice(
            repo_root=repo_path,
            prompt_lower=prompt_lower,
            grade=grade,
            task_type=task_type,
            route_mode=route_mode,
            selected=selected,
        ),
        "confirm_required": False,
        "confirm_options": [],
    }
    result.update(build_fallback_truth(result, None))
    confirm_ui = build_confirm_ui(
        RepoContext(repo_root=repo_path, config_root=repo_path / "config", bundled_skills_root=repo_path / "bundled" / "skills"),
        result,
        str(resolved_target_root),
        normalized_host_id,
    )
    if confirm_ui and selected is not None and route_reason in {"candidate_signal_host_selection", "candidate_signal_confirm_override"}:
        result["confirm_required"] = True
        result["confirm_options"] = confirm_ui["options"]
        result["confirm_ui"] = confirm_ui
    return result
