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
CAPABILITY_PROMPT_HINTS_BY_CAPABILITY = {
    capability: tuple(spec["prompt_hints"])
    for capability, spec in CAPABILITY_BRIDGE
}
ROUTER_QUERY_ALIAS_HINTS = (
    (("综述", "文献综述", "系统综述"), ("literature review", "review")),
    (("数据库", "公共数据库", "公开数据库"), ("public database", "database", "literature search")),
    (("浅显易懂", "通俗易懂", "通俗"), ("plain language", "reader report")),
    (("去ai味", "去 ai 味", "像人写", "更自然"), ("human written", "natural writing", "editing")),
)
MODULE_CAPABILITY_ALIASES = {
    "deploy.netlify": "deploy.preview",
    "deploy.vercel": "deploy.preview",
    "research.pubmed_search": "research.literature_search",
}
MODULE_PRIORITY_ORDER = {
    "primary": 0,
    "supporting": 1,
    "secondary": 2,
}
ALIASED_CAPABILITY_STRENGTH = 0.25


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
            "candidate_focus": CONFIRM_ROUTE_MIN_SCORE,
            "min_top1_top2_gap": 0.0,
            "min_candidate_signal_for_near_match": CONFIRM_ROUTE_MIN_SCORE,
            "min_candidate_signal_for_focus": AUTO_ROUTE_MIN_SCORE,
        }
    payload = load_json(path)
    thresholds = payload.get("thresholds") if isinstance(payload, dict) else {}
    if not isinstance(thresholds, dict):
        thresholds = {}
    return {
        "candidate_focus": float(thresholds.get("candidate_focus", CONFIRM_ROUTE_MIN_SCORE)),
        "min_top1_top2_gap": float(thresholds.get("min_top1_top2_gap", 0.0)),
        "min_candidate_signal_for_near_match": float(
            thresholds.get("min_candidate_signal_for_near_match", CONFIRM_ROUTE_MIN_SCORE)
        ),
        "min_candidate_signal_for_focus": float(
            thresholds.get("min_candidate_signal_for_focus", AUTO_ROUTE_MIN_SCORE)
        ),
    }


def _augment_prompt_for_local_routing(prompt: str, task_type: str) -> str:
    prompt_text = str(prompt or "").strip()
    prompt_lower = normalize_text(prompt_text)
    parts: list[str] = [prompt_text] if prompt_text else []

    for aliases, hint_values in ROUTER_QUERY_ALIAS_HINTS:
        if any(alias in prompt_lower for alias in aliases):
            parts.extend(hint_values)

    augmented: list[str] = []
    seen: set[str] = set()
    for value in parts:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        augmented.append(text)
        seen.add(text)
    return " ".join(augmented)


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


def _expand_capability_names(capabilities: list[str] | set[str] | tuple[str, ...]) -> set[str]:
    expanded: set[str] = set()
    for raw_capability in capabilities:
        capability = str(raw_capability).strip()
        if not capability:
            continue
        expanded.add(capability)
        alias = MODULE_CAPABILITY_ALIASES.get(capability)
        if alias:
            expanded.add(alias)
    return expanded


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
        for expanded_capability in _expand_capability_names([capability_text]):
            hints.extend(CAPABILITY_SEARCH_HINTS_BY_CAPABILITY.get(expanded_capability, ()))
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
        alias = MODULE_CAPABILITY_ALIASES.get(capability)
        if alias:
            strengths[alias] = max(strengths.get(alias, 0.0), min(strength, ALIASED_CAPABILITY_STRENGTH))
    for capability in entry.get("capabilities") or []:
        text = str(capability).strip()
        if not text:
            continue
        strengths.setdefault(text, 0.55)
        alias = MODULE_CAPABILITY_ALIASES.get(text)
        if alias:
            strengths.setdefault(alias, ALIASED_CAPABILITY_STRENGTH)
    return strengths


def _capability_evidence_level(entry: dict[str, Any], matched_capabilities: list[str]) -> str | None:
    matched = set(matched_capabilities)
    levels: list[str] = []
    for row in entry.get("capability_evidence") or []:
        if not isinstance(row, dict):
            continue
        capability = str(row.get("capability") or "").strip()
        if not capability:
            continue
        level = str(row.get("evidence_level") or "").strip()
        if capability in matched:
            if level:
                levels.append(level)
            continue
        alias = MODULE_CAPABILITY_ALIASES.get(capability)
        if alias and alias in matched:
            levels.append("weak_text")
    if "declared" in levels:
        return "declared"
    if "weak_text" in levels:
        return "weak_text"
    return levels[0] if levels else None


def _domain_anchor_score(entry: dict[str, Any], task_card: dict[str, Any]) -> float:
    primary = set(task_card.get("primary_capabilities") or [])
    skill_id = str(entry.get("skill_id") or entry.get("id") or "").casefold()
    raw_entry_capabilities = {
        str(capability).strip()
        for capability in entry.get("capabilities") or []
        if str(capability).strip()
    }
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
    if "research.literature_search" in primary and skill_id == "research":
        return 0.45
    if "research.literature_review" in primary and skill_id == "research":
        return 0.35
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
    if "architecture.domain_model" in primary and any(
        anchor in identity_text for anchor in ("domain model", "ubiquitous language", "bounded context", "领域模型", "统一语言")
    ):
        return 0.5
    if "architecture.interface_design" in primary and any(
        anchor in identity_text for anchor in ("module interface", "interface design", "service boundary", "deep module", "seam", "模块接口", "边界设计")
    ):
        return 0.45
    if "frontend.build" in primary and "frontend.build" in raw_entry_capabilities and any(
        anchor in identity_text for anchor in ("frontend", "front-end", "react", "next.js", "前端", "看板前端", "网页界面")
    ):
        return 0.45
    if "observability.sentry" in primary and any(
        anchor in identity_text for anchor in ("sentry", "production error", "线上报错", "线上告警")
    ):
        return 0.55
    if "visualization.figure" in primary and skill_id == "scientific-visualization":
        return 0.35
    if "visualization.figure" in primary and any(
        anchor in identity_text for anchor in ("visualization", "figure", "plot", "matplotlib", "chart", "科研绘图", "结果图")
    ):
        return 0.18
    if "visualization.infographic" in primary and skill_id == "infographics":
        return 0.32
    if "visualization.schematic" in primary and skill_id == "scientific-schematics":
        return 0.32
    if "docs.deep_reading" in primary and any(
        anchor in identity_text for anchor in ("deep reading", "deep analysis", "long-form content", "technical rfc", "精读")
    ):
        return 0.42
    if "debug.systematic_workflow" in primary and any(
        anchor in identity_text for anchor in ("diagnose", "debug", "bug", "调试", "性能回退", "性能变差")
    ):
        return 0.45
    if "reasoning.first_principles" in primary and any(
        anchor in identity_text for anchor in ("first principles", "第一性原理", "隐藏假设")
    ):
        return 0.48
    if "prototype.throwaway_validation" in primary and any(
        anchor in identity_text for anchor in ("throwaway prototype", "prototype", "spike", "原型验证")
    ):
        return 0.42
    if "deploy.preview" in primary and "deploy.preview" in raw_entry_capabilities and any(
        anchor in identity_text for anchor in ("preview deployment", "preview link", "vercel", "netlify", "预览部署")
    ):
        return 0.42
    if "planning.prd" in primary and "planning.prd" in raw_entry_capabilities and any(
        anchor in identity_text for anchor in ("prd", "product requirements", "requirements doc", "需求文档")
    ):
        return 0.42
    if "planning.issue_breakdown" in primary and "planning.issue_breakdown" in raw_entry_capabilities and any(
        anchor in identity_text for anchor in ("to-issues", "issue breakdown", "task breakdown", "issue tracker", "拆分 issues", "任务拆分")
    ):
        return 0.42
    if "performance.gpu_migration" in primary and any(
        anchor in identity_text for anchor in ("gpu", "cuda", "gpu acceleration", "迁移到 gpu", "cuda 加速")
    ):
        return 0.5
    if "performance.regression_debugging" in primary and any(
        anchor in identity_text for anchor in ("diagnose", "debug", "performance regression", "性能回退", "性能变差")
    ):
        return 0.45
    if "science.methodology_audit" in primary and any(
        anchor in identity_text for anchor in ("methodology", "experimental design", "evidence quality", "bias", "confounding", "方法学", "偏倚", "混杂")
    ):
        return 0.4
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
    if "statistics.test_selection_or_result_check" in primary and any(
        anchor in identity_text for anchor in ("statistical analysis", "检验选择", "假设检查", "power analysis", "统计方法")
    ):
        return 0.18
    if "research.literature_search" in primary and any(
        anchor in identity_text for anchor in ("literature search", "primary sources", "high-trust primary sources", "文献检索")
    ):
        return 0.22
    if "research.literature_review" in primary and any(
        anchor in identity_text for anchor in ("literature review", "systematic review", "综述", "evidence table")
    ):
        return 0.22
    if "vision.error_analysis" in primary and any(
        anchor in identity_text for anchor in ("computer vision", "object detection", "目标检测", "m ap", "map 指标", "mAP")
    ):
        return 0.52
    if "vision.training_strategy" in primary and any(
        anchor in identity_text for anchor in ("training strategy", "object detection", "yolo", "detr", "训练策略")
    ):
        return 0.42
    if "writing.chinese_humanization" in primary and any(
        anchor in identity_text for anchor in ("去 ai 味", "humanize 中文", "说人话", "真人表达", "human-written", "natural writing")
    ):
        return 0.42
    if "writing.manuscript_review" in primary and any(
        anchor in identity_text for anchor in ("manuscript review", "scientific writing", "论文润色", "审阅论文")
    ):
        return 0.42
    if "writing.reader_report" in primary and any(
        anchor in identity_text for anchor in ("plain language", "ordinary reader", "通俗", "说人话")
    ):
        return 0.2
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


def _hint_prompt_positions(prompt_lower: str, hints: tuple[str, ...] | list[str]) -> list[int]:
    positions: list[int] = []
    for hint in hints:
        normalized_hint = normalize_text(hint)
        if not normalized_hint or not keyword_hit(prompt_lower, normalized_hint):
            continue
        position = prompt_lower.find(normalized_hint)
        if position >= 0:
            positions.append(position)
    return positions


def _hint_prompt_position(prompt_lower: str, hints: tuple[str, ...] | list[str]) -> int | None:
    positions = _hint_prompt_positions(prompt_lower, hints)
    if not positions:
        return None
    return min(positions)


def _capability_prompt_position(prompt_lower: str, capability: str) -> int | None:
    return _hint_prompt_position(prompt_lower, CAPABILITY_PROMPT_HINTS_BY_CAPABILITY.get(capability, ()))


def _build_task_card(prompt_lower: str, task_type: str) -> dict[str, Any]:
    required: list[str] = []
    capability_prompt_positions: dict[str, int | None] = {}
    for capability, hints in CAPABILITY_HINTS:
        if any(keyword_hit(prompt_lower, hint) for hint in hints):
            required.append(capability)

    has_performance_regression_context = any(
        hint in prompt_lower
        for hint in ("performance regression", "latency regression", "slow page", "性能回归", "性能退化", "卡顿")
    )
    if keyword_hit(prompt_lower, "regression") and not has_performance_regression_context:
        required.append("statistics.regression")
    if "回归" in prompt_lower and not has_performance_regression_context:
        required.append("statistics.regression")

    review_or_existing_artifact_context = any(
        keyword_hit(prompt_lower, hint)
        for hint in (
            "manuscript review",
            "paper draft",
            "existing paper",
            "revise abstract",
            "revise discussion",
            "论文草稿",
            "审阅论文",
            "重写摘要",
            "重写讨论",
            "已有的",
        )
    )
    training_action_context = any(
        keyword_hit(prompt_lower, hint)
        for hint in (
            "train model",
            "model training",
            "training strategy",
            "training baseline",
            "build model",
            "prototype baseline",
            "训练模型",
            "模型训练",
            "训练策略",
            "重新训练",
            "训练 baseline",
        )
    )
    if review_or_existing_artifact_context and not training_action_context:
        required = [capability for capability in required if not capability.startswith("model.")]

    contextual_model_output_or_audit = any(
        capability in required
        for capability in (
            "model.data_leakage_guard",
            "visualization.figure",
        )
    )
    if contextual_model_output_or_audit and not training_action_context:
        required = [capability for capability in required if capability != "model.training"]

    artifact_delivery_action_hints = (
        "build",
        "create",
        "develop",
        "implement",
        "make",
        "ship",
        "构建",
        "开发",
        "实现",
        "做一个",
        "做个",
        "搭一个",
        "写一个",
    )
    artifact_delivery_target_hints = (
        "game",
        "app",
        "tool",
        "service",
        "script",
        "cli",
        "bot",
        "website",
        "web app",
        "demo",
        "interactive demo",
        "runnable demo",
        "游戏",
        "应用",
        "工具",
        "服务",
        "脚本",
        "命令行",
        "网站",
        "网页",
        "界面",
        "程序",
        "软件",
        "演示",
        "可运行演示",
    )
    artifact_delivery_action_positions = _hint_prompt_positions(prompt_lower, artifact_delivery_action_hints)
    artifact_delivery_target_positions = _hint_prompt_positions(prompt_lower, artifact_delivery_target_hints)
    artifact_delivery_action_context = bool(artifact_delivery_action_positions)
    artifact_delivery_target_context = bool(artifact_delivery_target_positions)
    artifact_delivery_position_pairs = [
        (action_position, target_position)
        for action_position in artifact_delivery_action_positions
        for target_position in artifact_delivery_target_positions
        if target_position >= action_position and (target_position - action_position) <= 24
    ]
    specific_delivery_capabilities = {
        "document.latex_submission",
        "frontend.build",
        "presentation.deck",
        "presentation.poster",
        "presentation.pptx_poster",
        "presentation.slidev",
    }
    if (
        artifact_delivery_action_context
        and artifact_delivery_target_context
        and artifact_delivery_position_pairs
        and not review_or_existing_artifact_context
        and not any(capability in required for capability in specific_delivery_capabilities)
    ):
        required.append("runtime.feature_delivery")
        closest_action_position, closest_target_position = min(
            artifact_delivery_position_pairs,
            key=lambda pair: (abs(pair[0] - pair[1]), min(pair)),
        )
        capability_prompt_positions["runtime.feature_delivery"] = min(
            closest_action_position,
            closest_target_position,
        )

    frontend_build_action_context = any(
        keyword_hit(prompt_lower, hint)
        for hint in (
            "build frontend",
            "build a frontend",
            "build ui",
            "build dashboard",
            "create dashboard",
            "implement frontend",
            "frontend app",
            "做一个",
            "搭一个",
            "实现前端",
            "开发前端",
            "看板前端",
        )
    )
    frontend_debug_context = any(
        capability in required
        for capability in (
            "debug.systematic_workflow",
            "performance.regression_debugging",
        )
    )
    if frontend_debug_context and not frontend_build_action_context:
        required = [capability for capability in required if capability != "frontend.build"]

    statistical_work = any(
        capability.startswith(("statistics.", "data."))
        for capability in required
    )
    rejected: list[str] = []
    if statistical_work and not any(hint in prompt_lower for hint in ("study pool", "analysis pool", "data pool", "cohort pool")):
        rejected.append("research.study_plan_pool")

    primary_capabilities = _dedupe_strings(
        [
            capability
            for capability in required
            if capability.startswith(
                (
                    "architecture.",
                    "chem.",
                    "clinical.",
                    "data.",
                    "debug.",
                    "deploy.",
                    "devops.",
                    "docs.",
                    "document.",
                    "frontend.",
                    "model.",
                    "observability.",
                    "performance.",
                    "planning.",
                    "presentation.",
                    "prototype.",
                    "quality.",
                    "reasoning.",
                    "runtime.",
                    "science.",
                    "statistics.",
                    "vision.",
                    "visualization.",
                    "writing.",
                )
            )
            or capability.startswith("research.")
        ]
    )
    supporting_capabilities = _dedupe_strings(
        [
            capability
            for capability in required
            if not capability.startswith(("data.", "statistics.", "model."))
        ]
    )
    return {
        "task_type": normalize_text(task_type) or "planning",
        "required_capabilities": _dedupe_strings(required),
        "primary_capabilities": primary_capabilities,
        "supporting_capabilities": supporting_capabilities,
        "modules": _build_task_modules(
            prompt_lower=prompt_lower,
            required_capabilities=_dedupe_strings(required),
            primary_capabilities=primary_capabilities,
            supporting_capabilities=supporting_capabilities,
            capability_prompt_positions=capability_prompt_positions,
        ),
        "rejected_capabilities": _dedupe_strings(rejected),
    }


def _build_task_modules(
    *,
    prompt_lower: str,
    required_capabilities: list[str],
    primary_capabilities: list[str],
    supporting_capabilities: list[str],
    capability_prompt_positions: dict[str, int | None] | None = None,
) -> list[dict[str, Any]]:
    primary = set(primary_capabilities)
    supporting = set(supporting_capabilities)
    modules: list[dict[str, Any]] = []
    module_by_id: dict[str, dict[str, Any]] = {}
    explicit_prompt_positions = capability_prompt_positions or {}
    for capability in required_capabilities:
        module_id = MODULE_CAPABILITY_ALIASES.get(capability, capability)
        module = module_by_id.get(module_id)
        capability_position = explicit_prompt_positions.get(capability, _capability_prompt_position(prompt_lower, capability))
        if module is None:
            module = {
                "module_id": module_id,
                "label": module_id,
                "required_capabilities": [capability],
                "priority": "primary" if capability in primary else "supporting" if capability in supporting else "secondary",
                "prompt_position": capability_position,
            }
            module_by_id[module_id] = module
            modules.append(module)
            continue
        if capability not in module["required_capabilities"]:
            module["required_capabilities"].append(capability)
        if capability_position is not None and (
            module.get("prompt_position") is None or int(module["prompt_position"]) > capability_position
        ):
            module["prompt_position"] = capability_position
        if module["priority"] != "primary" and capability in primary:
            module["priority"] = "primary"
        elif module["priority"] == "secondary" and capability in supporting:
            module["priority"] = "supporting"
    return modules


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
    entry_capabilities = _expand_capability_names(entry.get("capabilities") or [])
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
    lexical_score = (0.75 * token_score) + (0.25 * tag_score)
    if not required_capabilities:
        local_lexical_score = lexical_score
    elif not entry_capabilities:
        local_lexical_score = 0.35 * lexical_score
    else:
        local_lexical_score = 0.0
    base_score = max(name_score, capability_weighted_score, local_lexical_score)
    if rejected_capability_matches:
        base_score = min(base_score, 0.1)
    matched_not_for = _matched_not_for_boundaries(entry, prompt_lower, query_tokens)
    if matched_not_for:
        base_score = min(base_score, 0.05)
    if bool(entry.get("explicit_only")):
        base_score = min(base_score, 0.1)
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
        "skill_entrypoint": entry.get("skill_entrypoint"),
        "skill_root": entry.get("skill_root"),
        "description": entry.get("description"),
        "explicit_only": bool(entry.get("explicit_only")),
        "capabilities": list(entry.get("capabilities") or []),
        "capability_card_path": entry.get("capability_card_path"),
        "route_evidence_chunks": list(entry.get("route_evidence_chunks") or []),
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


def _preferred_primary_row(
    scored_rows: list[dict[str, Any]],
    task_card: dict[str, Any],
) -> dict[str, Any] | None:
    if not scored_rows:
        return None
    if len(task_card.get("modules") or []) <= 1:
        return scored_rows[0]

    eligible_rows = [row for row in scored_rows if not row.get("rejected_capabilities") and row.get("matched_capabilities")]
    if not eligible_rows:
        return scored_rows[0]

    def _primary_key(row: dict[str, Any]) -> tuple[float, ...]:
        return (
            float(len(row.get("matched_primary_capabilities") or [])),
            float(len(row.get("matched_capabilities") or [])),
            float(row.get("capability_score") or 0.0),
            -float(_evidence_level_priority(row)),
            float(row.get("score") or 0.0),
        )

    return max(eligible_rows, key=_primary_key)


def _visible_ranked_rows(ranked_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positive_rows = [row for row in ranked_rows if float(row.get("score") or 0.0) > 0.0]
    if positive_rows:
        if len(positive_rows) <= 2:
            return positive_rows[:2]
        visible_rows = [
            row
            for index, row in enumerate(positive_rows)
            if index == 0
            or row.get("role") in {"primary_owner", "supporting_owner"}
            or row.get("matched_capabilities")
            or _has_confirmable_near_match(row)
        ]
        if visible_rows:
            return visible_rows[:6]
        return positive_rows[:1]
    return ranked_rows[:1]


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
    if len(specific_tokens) < 2:
        return False
    return float(row.get("score") or 0.0) >= CONFIRM_ROUTE_MIN_SCORE


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
        "skill_entrypoint": row.get("skill_entrypoint"),
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

    if "architecture.domain_model" in required_capabilities and "architecture.domain_model" in matched_capabilities and (
        "domain" in skill or "ubiquitous" in skill
    ):
        surfaces.add("architecture.domain_model")
    if "architecture.interface_design" in required_capabilities and "architecture.interface_design" in matched_capabilities and (
        "interface" in skill or "design" in skill or "seam" in skill
    ):
        surfaces.add("architecture.interface_design")
    if "data.eda" in required_capabilities and "data.eda" in matched_capabilities and ("exploratory" in skill or skill == "eda"):
        surfaces.add("data.eda")
    if "docs.deep_reading" in required_capabilities and "docs.deep_reading" in matched_capabilities and (
        "deep-reading" in skill or "deep reading" in skill or "reading" in skill
    ):
        surfaces.add("docs.deep_reading")
    if (
        "debug.systematic_workflow" in required_capabilities
        and "debug.systematic_workflow" in matched_capabilities
        and ("diagnos" in skill or "debug" in skill or "bug" in skill)
    ):
        surfaces.add("debug.systematic_workflow")
    if (
        "performance.regression_debugging" in required_capabilities
        and "performance.regression_debugging" in matched_capabilities
        and ("diagnos" in skill or "debug" in skill or "bug" in skill)
    ):
        surfaces.add("performance.regression_debugging")
    if matched_capabilities & {"statistics.relationship_modeling", "statistics.correlation", "statistics.regression"} and "statistical" in skill:
        surfaces.add("statistics")
    if (
        "statistics.test_selection_or_result_check" in required_capabilities
        and "statistics.test_selection_or_result_check" in matched_capabilities
        and "statistical" in skill
    ):
        surfaces.add("statistics.test_selection_or_result_check")
    if "model.training" in required_capabilities and "model.training" in matched_capabilities and ("scikit" in skill or "machine-learning" in skill):
        surfaces.add("model.training")
    if "model.explainability" in required_capabilities and "model.explainability" in matched_capabilities and ("shap" in skill or "explain" in skill):
        surfaces.add("model.explainability")
    if (
        "performance.gpu_migration" in required_capabilities
        and "performance.gpu_migration" in matched_capabilities
        and ("gpu" in skill or "cuda" in skill)
    ):
        surfaces.add("performance.gpu_migration")
    if (
        "planning.issue_breakdown" in required_capabilities
        and "planning.issue_breakdown" in matched_capabilities
        and ("issue" in skill or "task" in skill)
    ):
        surfaces.add("planning.issue_breakdown")
    if "planning.prd" in required_capabilities and "planning.prd" in matched_capabilities and "prd" in skill:
        surfaces.add("planning.prd")
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
    if (
        "prototype.throwaway_validation" in required_capabilities
        and "prototype.throwaway_validation" in matched_capabilities
        and "prototype" in skill
    ):
        surfaces.add("prototype.throwaway_validation")
    if (
        "reasoning.first_principles" in required_capabilities
        and "reasoning.first_principles" in matched_capabilities
        and ("first-principles" in skill or "principles" in skill)
    ):
        surfaces.add("reasoning.first_principles")
    if (
        "science.methodology_audit" in required_capabilities
        and "science.methodology_audit" in matched_capabilities
        and ("critical" in skill or "audit" in skill or "review" in skill)
    ):
        surfaces.add("science.methodology_audit")
    if (
        "vision.error_analysis" in required_capabilities
        and "vision.error_analysis" in matched_capabilities
        and ("vision" in skill or "detection" in skill)
    ):
        surfaces.add("vision.error_analysis")
    if (
        "vision.training_strategy" in required_capabilities
        and "vision.training_strategy" in matched_capabilities
        and ("vision" in skill or "detection" in skill)
    ):
        surfaces.add("vision.training_strategy")
    if (
        "writing.reader_report" in required_capabilities
        and "writing.reader_report" in matched_capabilities
        and ("reader" in skill or "plain" in skill or "qu-ai-wei" in skill or "human" in skill)
    ):
        surfaces.add("writing.reader_report")
    if (
        "writing.chinese_humanization" in required_capabilities
        and "writing.chinese_humanization" in matched_capabilities
        and ("qu-ai-wei" in skill or "human" in skill or "ai" in skill)
    ):
        surfaces.add("writing.chinese_humanization")
    if (
        "writing.manuscript_review" in required_capabilities
        and "writing.manuscript_review" in matched_capabilities
        and ("manuscript" in skill or "sciwrite" in skill or "review" in skill)
    ):
        surfaces.add("writing.manuscript_review")

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


def _row_matches_module(row: dict[str, Any], module: dict[str, Any]) -> bool:
    required_capabilities = set(module.get("required_capabilities") or [])
    matched_capabilities = set(row.get("matched_capabilities") or [])
    return bool(required_capabilities & matched_capabilities)


def _evidence_level_priority(row: dict[str, Any]) -> int:
    level = str(row.get("capability_evidence_level") or "").strip()
    if level == "declared":
        return 0
    if level == "weak_text":
        return 1
    return 2


MODULE_EVIDENCE_ROLE_PRIORITY = {
    "applicable": 0,
    "deliverable": 1,
    "prerequisite": 2,
    "example": 3,
    "background": 4,
}


def _module_hint_texts(module: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    for capability in module.get("required_capabilities") or []:
        capability_text = str(capability).strip()
        if not capability_text:
            continue
        hints.extend(CAPABILITY_SEARCH_HINTS_BY_CAPABILITY.get(capability_text, ()))
        hints.append(capability_text.split(".", 1)[-1].replace("_", " "))
        hints.append(capability_text.replace(".", " ").replace("_", " "))
    return _dedupe_strings(hints)


def _public_route_evidence_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": str(chunk.get("text") or ""),
        "role": str(chunk.get("role") or ""),
        "source": str(chunk.get("source") or ""),
        "line_start": int(chunk.get("line_start") or 0),
        "line_end": int(chunk.get("line_end") or 0),
    }


def _module_candidate_evidence(module: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    hint_texts = _module_hint_texts(module)
    matched_chunks: list[tuple[int, int, int, dict[str, Any]]] = []
    fallback_chunks: list[tuple[int, int, dict[str, Any]]] = []
    for raw_chunk in row.get("route_evidence_chunks") or []:
        if not isinstance(raw_chunk, dict):
            continue
        public_chunk = _public_route_evidence_chunk(raw_chunk)
        role = public_chunk["role"]
        if role == "not_applicable" or not public_chunk["text"]:
            continue
        role_priority = MODULE_EVIDENCE_ROLE_PRIORITY.get(role, 5)
        text_lower = normalize_text(public_chunk["text"])
        hint_hits = sum(1 for hint in hint_texts if keyword_hit(text_lower, hint))
        if hint_hits > 0:
            matched_chunks.append((role_priority, -hint_hits, public_chunk["line_start"], public_chunk))
            continue
        if role == "applicable":
            fallback_chunks.append((role_priority, public_chunk["line_start"], public_chunk))
    if matched_chunks:
        matched_chunks.sort(key=lambda item: (item[0], item[1], item[2], item[3]["text"]))
        return [item[3] for item in matched_chunks[:2]]
    if fallback_chunks:
        fallback_chunks.sort(key=lambda item: (item[0], item[1], item[2]["text"]))
        return [item[2] for item in fallback_chunks[:1]]
    return []


def _module_candidate_evidence_priority(module: dict[str, Any], row: dict[str, Any]) -> int:
    evidence = _module_candidate_evidence(module, row)
    if not evidence:
        return 5
    return MODULE_EVIDENCE_ROLE_PRIORITY.get(str(evidence[0].get("role") or ""), 5)


def _module_capability_profile(module: dict[str, Any], row: dict[str, Any]) -> tuple[int, int]:
    required_capabilities = {
        str(capability).strip()
        for capability in module.get("required_capabilities") or []
        if str(capability).strip()
    }
    matched_capabilities = {
        str(capability).strip()
        for capability in row.get("matched_capabilities") or []
        if str(capability).strip()
    }
    required_hits = len(required_capabilities & matched_capabilities)
    extra_hits = len(matched_capabilities - required_capabilities)
    return required_hits, extra_hits


def _module_candidate_sort_key(module: dict[str, Any], row: dict[str, Any], prompt_lower: str) -> tuple[Any, ...]:
    module_id = str(module.get("module_id") or "")
    skill_text = " ".join(
        [
            str(row.get("skill") or ""),
            str(row.get("description") or ""),
        ]
    ).casefold()
    evidence_priority = _module_candidate_evidence_priority(module, row)
    required_hits, extra_hits = _module_capability_profile(module, row)
    if module_id == "presentation.deck":
        return (
            evidence_priority,
            -required_hits,
            extra_hits,
            *_presentation_delivery_priority(row, prompt_lower),
        )
    delivery_penalty = 1 if any(anchor in skill_text for anchor in ("ppt", "pptx", "slide", "deck", "paper2ppt", "image-first")) else 0
    return (
        evidence_priority,
        delivery_penalty,
        _evidence_level_priority(row),
        -required_hits,
        extra_hits,
        -float(row.get("score") or 0.0),
        str(row.get("skill") or ""),
    )


def _public_module_candidate(module: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": str(row.get("skill") or ""),
        "score": float(row.get("score") or 0.0),
        "matched_capabilities": list(row.get("matched_capabilities") or []),
        "capability_evidence_level": row.get("capability_evidence_level"),
        "evidence": _module_candidate_evidence(module, row),
    }


def _build_module_candidates(
    scored_rows: list[dict[str, Any]],
    task_card: dict[str, Any],
    prompt_lower: str,
) -> list[dict[str, Any]]:
    module_candidates: list[dict[str, Any]] = []
    for module in task_card.get("modules") or []:
        rows = [
            row
            for row in scored_rows
            if not row.get("rejected_capabilities") and _row_matches_module(row, module)
        ]
        rows.sort(key=lambda row: _module_candidate_sort_key(module, row, prompt_lower))
        module_candidates.append(
            {
                "module_id": str(module.get("module_id") or ""),
                "label": str(module.get("label") or ""),
                "priority": str(module.get("priority") or ""),
                "prompt_position": module.get("prompt_position"),
                "required_capabilities": list(module.get("required_capabilities") or []),
                "candidate_rows": rows,
                "candidates": [_public_module_candidate(module, row) for row in rows[:3]],
            }
        )
    return module_candidates


def _module_priority_sort_key(module: dict[str, Any]) -> tuple[Any, ...]:
    prompt_position = module.get("prompt_position")
    top_candidate_score = float((module.get("candidate_rows") or [{}])[0].get("score") or 0.0)
    weak_module_owner = top_candidate_score < AUTO_ROUTE_MIN_SCORE
    return (
        int(MODULE_PRIORITY_ORDER.get(str(module.get("priority") or ""), 3)),
        weak_module_owner,
        prompt_position is None,
        int(prompt_position if prompt_position is not None else 10**9),
        -top_candidate_score,
        str(module.get("module_id") or ""),
    )


def _selected_module_ids(selected_rows: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for row in selected_rows:
        covered.update(str(capability) for capability in row.get("matched_capabilities") or [] if str(capability).strip())
    return covered


def _public_uncovered_modules(
    module_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    uncovered: list[dict[str, Any]] = []
    for module in module_candidates:
        required_capabilities = [str(capability) for capability in module.get("required_capabilities") or [] if str(capability).strip()]
        if module.get("candidates"):
            continue
        uncovered.append(
            {
                "module_id": str(module.get("module_id") or ""),
                "label": str(module.get("label") or ""),
                "priority": str(module.get("priority") or ""),
                "required_capabilities": required_capabilities,
            }
        )
    return uncovered


def _selected_row_sort_key(
    row: dict[str, Any],
    module_order: dict[str, int],
    module_capabilities: dict[str, set[str]],
    module_prompt_positions: dict[str, int],
    row_index: int,
) -> tuple[Any, ...]:
    matched_capabilities = {
        str(capability).strip()
        for capability in row.get("matched_capabilities") or []
        if str(capability).strip()
    }
    covered_module_indexes = sorted(
        order
        for module_id, order in module_order.items()
        if module_capabilities[module_id] & matched_capabilities
    )
    covered_prompt_positions = sorted(
        module_prompt_positions[module_id]
        for module_id in module_order
        if module_capabilities[module_id] & matched_capabilities
    )
    first_module_index = covered_module_indexes[0] if covered_module_indexes else len(module_order) + row_index
    first_prompt_position = covered_prompt_positions[0] if covered_prompt_positions else 10**9
    prompt_bucket = first_prompt_position // 8 if first_prompt_position < 10**9 else 10**9
    return (
        prompt_bucket,
        -len(covered_module_indexes),
        -len(row.get("matched_primary_capabilities") or []),
        -float(row.get("score") or 0.0),
        first_prompt_position,
        first_module_index,
        row_index,
    )


def _reorder_selected_rows_by_module_priority(
    selected_rows: list[dict[str, Any]],
    module_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(selected_rows) <= 1 or not module_candidates:
        return selected_rows

    ordered_modules = sorted(module_candidates, key=_module_priority_sort_key)
    module_order = {
        str(module.get("module_id") or ""): index
        for index, module in enumerate(ordered_modules)
    }
    module_capabilities = {
        str(module.get("module_id") or ""): {
            str(capability).strip()
            for capability in module.get("required_capabilities") or []
            if str(capability).strip()
        }
        for module in ordered_modules
    }
    module_prompt_positions = {
        str(module.get("module_id") or ""): int(module.get("prompt_position") if module.get("prompt_position") is not None else 10**9)
        for module in ordered_modules
    }
    composite_gap = max(float(row.get("candidate_top1_top2_gap") or 0.0) for row in selected_rows)
    reordered = sorted(
        enumerate(selected_rows),
        key=lambda item: _selected_row_sort_key(item[1], module_order, module_capabilities, module_prompt_positions, item[0]),
    )

    normalized_rows: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(reordered):
        normalized = dict(row)
        normalized["role"] = "primary_owner" if index == 0 else "supporting_owner"
        if index == 0:
            normalized["candidate_top1_top2_gap"] = composite_gap
        normalized_rows.append(normalized)
    return normalized_rows


def _first_viable_module_seed_row(
    module: dict[str, Any],
    *,
    min_score: float,
) -> dict[str, Any] | None:
    for row in module.get("candidate_rows") or []:
        if bool(row.get("explicit_only")) or row.get("rejected_capabilities"):
            continue
        if float(row.get("score") or 0.0) < min_score:
            continue
        return row
    return None


def _preferred_module_seed_row(
    module_candidates: list[dict[str, Any]],
    *,
    grade: str,
    thresholds: dict[str, float],
) -> tuple[dict[str, Any] | None, float]:
    if len(module_candidates) <= 1:
        return None, 0.0

    normalized_grade = normalize_text(grade).upper()
    min_seed_score = 0.1 if normalized_grade == "XL" else float(
        thresholds.get("min_candidate_signal_for_near_match", CONFIRM_ROUTE_MIN_SCORE)
    )
    max_modules = 5 if normalized_grade == "XL" else 3

    viable_modules: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for module in sorted(module_candidates, key=_module_priority_sort_key):
        row = _first_viable_module_seed_row(module, min_score=min_seed_score)
        if row is None:
            continue
        viable_modules.append((module, row))

    if len(viable_modules) <= 1:
        return None, 0.0

    composite_signal = round(
        sum(float(row.get("score") or 0.0) for _, row in viable_modules[:max_modules]),
        4,
    )
    if composite_signal < float(thresholds.get("candidate_focus", CONFIRM_ROUTE_MIN_SCORE)):
        return None, composite_signal

    return dict(viable_modules[0][1]), composite_signal


def _selected_rows_for_route(
    scored_rows: list[dict[str, Any]],
    selected_row: dict[str, Any] | None,
    *,
    grade: str,
    task_card: dict[str, Any],
    module_candidates: list[dict[str, Any]],
    prompt_lower: str,
    thresholds: dict[str, float],
    requested_canonical: str | None,
    selection_reason: str,
) -> list[dict[str, Any]]:
    if selected_row is None:
        return []

    primary = _mark_selected_row(selected_row, role="primary_owner", reason=selection_reason)
    selected_rows = [primary]
    if requested_canonical:
        return selected_rows

    if len(module_candidates) <= 1:
        return selected_rows

    normalized_grade = normalize_text(grade).upper()
    max_selected = 6 if normalized_grade == "XL" else 3

    selected_skill_ids = {str(primary.get("skill") or "")}
    covered_modules = _selected_module_ids(selected_rows)

    module_queue = sorted(module_candidates, key=_module_priority_sort_key)
    min_module_score = 0.1 if normalized_grade == "XL" else float(
        thresholds.get("min_candidate_signal_for_near_match", CONFIRM_ROUTE_MIN_SCORE)
    )

    for module in module_queue:
        if len(selected_rows) >= max_selected:
            break
        required_capabilities = set(str(capability) for capability in module.get("required_capabilities") or [] if str(capability).strip())
        module_already_covered = bool(required_capabilities & covered_modules)
        if normalized_grade != "XL" and module_already_covered:
            continue
        candidate_rows = list(module.get("candidate_rows") or [])
        if normalized_grade == "XL":
            candidate_rows = candidate_rows[:2]
        for row in candidate_rows:
            if bool(row.get("explicit_only")):
                continue
            if float(row.get("score") or 0.0) < min_module_score:
                continue
            skill = str(row.get("skill") or "").strip()
            if not skill or skill in selected_skill_ids:
                continue
            selected_rows.append(
                _mark_selected_row(
                    row,
                    role="supporting_owner",
                    reason="module_coverage_xl" if normalized_grade == "XL" else "module_coverage_l",
                )
            )
            selected_skill_ids.add(skill)
            covered_modules.update(str(capability) for capability in row.get("matched_capabilities") or [] if str(capability).strip())
            break

    for row in scored_rows:
        if len(selected_rows) >= max_selected:
            break
        skill = str(row.get("skill") or "").strip()
        if not skill or skill in selected_skill_ids or row.get("rejected_capabilities"):
            continue
        explicitly_named = _skill_is_named(row, prompt_lower)
        if not explicitly_named:
            continue
        selected_rows.append(
            _mark_selected_row(
                row,
                role="supporting_owner",
                reason="explicit_xl_skill" if normalized_grade == "XL" else "explicit_l_skill",
            )
        )
        selected_skill_ids.add(skill)

    return _reorder_selected_rows_by_module_priority(selected_rows, module_candidates)


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
    routing_prompt = _augment_prompt_for_local_routing(prompt, task_type)
    prompt_lower = normalize_text(routing_prompt)
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
        score = _score_entry(routing_prompt, prompt_lower, entry, task_card)
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
    preferred_primary_row = _preferred_primary_row(scored_rows, task_card)
    module_candidates = _build_module_candidates(scored_rows, task_card, prompt_lower)

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
        preferred_primary_row is not None
        and float(preferred_primary_row["score"]) >= float(thresholds["min_candidate_signal_for_focus"])
        and float(top1_top2_gap) >= float(thresholds["min_top1_top2_gap"])
    ):
        selected_row = dict(preferred_primary_row)
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "capability_ranked" if selected_row["matched_capabilities"] else "keyword_ranked"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "auto_route"
        selection_reason = selected_row["candidate_selection_reason"]
    elif preferred_primary_row is not None and float(preferred_primary_row["score"]) >= float(thresholds["candidate_focus"]):
        selected_row = dict(preferred_primary_row)
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "capability_ranked" if selected_row["matched_capabilities"] else "keyword_ranked"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "candidate_signal_host_selection"
        selection_reason = selected_row["candidate_selection_reason"]
    elif (
        preferred_primary_row is not None
        and float(preferred_primary_row["score"]) >= float(thresholds["min_candidate_signal_for_near_match"])
        and _has_confirmable_near_match(preferred_primary_row)
        and not preferred_primary_row["rejected_capabilities"]
    ):
        selected_row = dict(preferred_primary_row)
        selected_row["selected_candidate"] = selected_row["skill"]
        selected_row["candidate_selection_reason"] = "near_match_confirm_required"
        selected_row["authority_eligible"] = True
        selected_row["authority_rejection_reasons"] = []
        selected_row["role"] = "primary_owner"
        selected_row["candidate_top1_top2_gap"] = top1_top2_gap
        route_reason = "candidate_signal_confirm_override"
        selection_reason = "near_match_confirm_required"

    if selected_row is None:
        module_seed_row, composite_signal = _preferred_module_seed_row(
            module_candidates,
            grade=grade,
            thresholds=thresholds,
        )
        if module_seed_row is not None:
            selected_row = module_seed_row
            selected_row["selected_candidate"] = selected_row["skill"]
            selected_row["candidate_selection_reason"] = "composite_module_seed"
            selected_row["authority_eligible"] = True
            selected_row["authority_rejection_reasons"] = []
            selected_row["role"] = "primary_owner"
            selected_row["candidate_top1_top2_gap"] = top1_top2_gap
            selected_row["composite_module_signal"] = composite_signal
            route_reason = "composite_module_confirm_override"
            selection_reason = "composite_module_seed"

    selected_rows = _selected_rows_for_route(
        scored_rows,
        selected_row,
        grade=grade,
        task_card=task_card,
        module_candidates=module_candidates,
        prompt_lower=prompt_lower,
        thresholds=thresholds,
        requested_canonical=None if requested_controller else requested_canonical,
        selection_reason=selection_reason,
    )
    selected_skill_ids = {str(row.get("skill") or "") for row in selected_rows}
    ranked_rows = selected_rows + [
        row for row in scored_rows if str(row.get("skill") or "") not in selected_skill_ids
    ]
    visible_rows = _visible_ranked_rows(ranked_rows)

    primary_row = selected_rows[0] if selected_rows else None
    selected = (
        _selected_payload(
            primary_row,
            reason=str(primary_row.get("candidate_selection_reason") or selection_reason),
        )
        if primary_row is not None
        else None
    )
    confidence = float(primary_row["score"]) if primary_row is not None else (float(ranked_rows[0]["score"]) if ranked_rows else 0.0)
    public_top1_top2_gap = float(primary_row["candidate_top1_top2_gap"]) if primary_row is not None else 0.0
    route_mode = "local_skill_overlay" if selected is not None else "no_local_candidate"
    result: dict[str, Any] = {
        "prompt": prompt,
        "grade": normalize_text(grade).upper() or "M",
        "task_type": normalize_text(task_type) or "planning",
        "router_contract_mode": "candidate_discovery_only",
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
            "pack_id": LOCAL_PACK_ID if visible_rows else None,
            "skill": str(visible_rows[0]["skill"]) if visible_rows else None,
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
        "candidates": visible_rows,
        "candidate_focus": selected,
        "ranked": visible_rows,
        "skill_routing": {
            "schema_version": "composite_skill_routing_v1",
            "primary_candidate_skill": str(primary_row.get("skill") or "") if primary_row is not None else None,
            "focused_candidates": selected_rows,
            "module_candidates": [
                {
                    "module_id": str(module.get("module_id") or ""),
                    "label": str(module.get("label") or ""),
                    "priority": str(module.get("priority") or ""),
                    "required_capabilities": list(module.get("required_capabilities") or []),
                    "candidates": list(module.get("candidates") or []),
                }
                for module in module_candidates
            ],
            "uncovered_modules": _public_uncovered_modules(module_candidates),
        },
        "quality_debt_advice": _build_quality_debt_advice(
            repo_root=repo_path,
            prompt_lower=prompt_lower,
            grade=grade,
            task_type=task_type,
            route_mode=route_mode,
            selected=selected,
        ),
    }
    result.update(build_fallback_truth(result, None))
    return result
