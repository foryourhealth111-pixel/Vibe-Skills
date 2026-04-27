#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ML_KEYWORDS = {
    "machine learning",
    "ml",
    "sklearn",
    "scikit",
    "classification",
    "regression",
    "clustering",
    "feature engineering",
    "feature importance",
    "model training",
    "model evaluation",
    "cross validation",
    "deep learning",
    "transformers",
    "fine tune",
    "fine-tune",
    "time series",
    "forecast",
    "anomaly",
    "data leakage",
    "机器学习",
    "分类",
    "回归",
    "聚类",
    "特征工程",
    "特征重要性",
    "模型训练",
    "模型评估",
    "预测模型",
    "数据泄漏",
}

SPECIALIST_DEFER_SKILLS = {
    "shap",
    "umap-learn",
    "statsmodels",
    "tensorboard",
    "weights-and-biases",
    "transformers",
    "torch-geometric",
    "stable-baselines3",
    "timesfm-forecasting",
    "scikit-survival",
    "deepchem",
    "torchdrug",
}

OWNER_SKILLS = {
    "scikit-learn",
    "ml-pipeline-workflow",
    "exploratory-data-analysis",
    "ml-data-leakage-guard",
    "LQF_Machine_Learning_Expert_Guide",
    "statistical-analysis",
    "statsmodels",
    "aeon",
}

DEFAULT_REPLACEMENTS = {
    "anomaly-detector": "scikit-learn",
    "confusion-matrix-generator": "scikit-learn",
    "correlation-analyzer": "exploratory-data-analysis",
    "data-normalization-tool": "preprocessing-data-with-automated-pipelines",
    "data-quality-checker": "exploratory-data-analysis",
    "engineering-features-for-machine-learning": "preprocessing-data-with-automated-pipelines",
    "evaluating-machine-learning-models": "scikit-learn",
    "feature-importance-analyzer": "shap",
    "regression-analysis-helper": "scikit-learn",
    "running-clustering-algorithms": "scikit-learn",
    "training-machine-learning-models": "scikit-learn",
}

CSV_FIELDS = [
    "skill_id",
    "category",
    "current_pack",
    "current_role",
    "lines",
    "has_scripts",
    "has_references",
    "quality_score",
    "duplication_score",
    "recommended_action",
    "replacement_skill",
    "deletion_reason",
    "config_cleanup_required",
    "risk_level",
]

PROBLEM_MAP_CSV_FIELDS = [
    "skill_id",
    "problem_ids",
    "primary_problem_id",
    "current_role",
    "target_role",
    "target_owner",
    "overlap_with",
    "unique_assets",
    "routing_change",
    "delete_allowed_after_migration",
    "risk_level",
    "rationale",
]

DATA_ML_TARGET_SKILLS = {
    "aeon",
    "evaluating-machine-learning-models",
    "exploratory-data-analysis",
    "ml-data-leakage-guard",
    "ml-pipeline-workflow",
    "preprocessing-data-with-automated-pipelines",
    "scikit-learn",
    "shap",
}

DATA_ML_PROBLEM_DECISIONS: dict[str, dict[str, Any]] = {
    "aeon": {
        "problem_ids": ["ml_time_series"],
        "primary_problem_id": "ml_time_series",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "statsmodels; timesfm-forecasting",
        "routing_change": "keep in data-ml as narrow time-series ML route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "时间序列 ML 是独立问题类型，普通 scikit-learn 不够精确。",
    },
    "creating-data-visualizations": {
        "problem_ids": ["ml_data_understanding"],
        "primary_problem_id": "ml_data_understanding",
        "target_role": "move-out",
        "target_owner": "science-figures-visualization",
        "overlap_with": "exploratory-data-analysis; data-exploration-visualization",
        "routing_change": "remove from data-ml; keep as visualization skill outside this pack",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "普通图表有价值，但不是 data-ml 核心主路由职责。",
    },
    "data-exploration-visualization": {
        "problem_ids": ["ml_data_understanding"],
        "primary_problem_id": "ml_data_understanding",
        "target_role": "merge-delete-after-migration",
        "target_owner": "exploratory-data-analysis",
        "overlap_with": "exploratory-data-analysis; creating-data-visualizations",
        "routing_change": "remove from data-ml; migrate reusable EDA assets before deleting",
        "delete_allowed_after_migration": True,
        "risk_level": "medium",
        "rationale": "EDA 主流程和普通可视化已由更清晰的 owner 覆盖。",
    },
    "engineering-features-for-machine-learning": {
        "problem_ids": ["ml_preprocessing_features"],
        "primary_problem_id": "ml_preprocessing_features",
        "target_role": "merge-delete-after-migration",
        "target_owner": "preprocessing-data-with-automated-pipelines",
        "overlap_with": "preprocessing-data-with-automated-pipelines; scikit-learn",
        "routing_change": "remove from data-ml; migrate reusable feature-engineering assets first",
        "delete_allowed_after_migration": True,
        "risk_level": "medium",
        "rationale": "特征工程和预处理是同一阶段问题，应集中到一个阶段助手。",
    },
    "evaluating-machine-learning-models": {
        "problem_ids": ["ml_model_evaluation"],
        "primary_problem_id": "ml_model_evaluation",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scikit-learn; training-machine-learning-models",
        "routing_change": "keep in data-ml as review/evaluation route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "模型评估、阈值、校准和比较是独立高价值问题。",
    },
    "exploratory-data-analysis": {
        "problem_ids": ["ml_data_understanding"],
        "primary_problem_id": "ml_data_understanding",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "data-exploration-visualization; creating-data-visualizations",
        "routing_change": "keep in data-ml as data-understanding route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "数据质量、结构、分布和初步理解是 ML 流程的核心入口。",
    },
    "LQF_Machine_Learning_Expert_Guide": {
        "problem_ids": ["ml_critical_review"],
        "primary_problem_id": "ml_critical_review",
        "target_role": "move-out",
        "target_owner": "explicit-review",
        "overlap_with": "ml-pipeline-workflow; evaluating-machine-learning-models",
        "routing_change": "remove from data-ml; keep only for explicit critical-review use",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "批判式评审有价值，但触发面过宽，不应压住普通 ML 主路由。",
    },
    "ml-data-leakage-guard": {
        "problem_ids": ["ml_leakage_audit"],
        "primary_problem_id": "ml_leakage_audit",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "evaluating-machine-learning-models; preprocessing-data-with-automated-pipelines",
        "routing_change": "keep in data-ml as leakage-audit route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "数据泄漏是独立高风险问题，应保留专门检查入口。",
    },
    "ml-pipeline-workflow": {
        "problem_ids": ["ml_workflow_orchestration"],
        "primary_problem_id": "ml_workflow_orchestration",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "training-machine-learning-models; scikit-learn",
        "routing_change": "keep in data-ml as planning/default workflow owner",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "端到端流程规划和 MLOps 生命周期需要独立 owner。",
    },
    "preprocessing-data-with-automated-pipelines": {
        "problem_ids": ["ml_preprocessing_features"],
        "primary_problem_id": "ml_preprocessing_features",
        "target_role": "stage-assistant",
        "target_owner": "",
        "overlap_with": "engineering-features-for-machine-learning; scikit-learn",
        "routing_change": "keep in data-ml as the only stage assistant",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "清洗、编码、缩放、转换和验证应集中到一个阶段助手。",
    },
    "running-clustering-algorithms": {
        "problem_ids": ["ml_tabular_modeling"],
        "primary_problem_id": "ml_tabular_modeling",
        "target_role": "merge-delete-after-migration",
        "target_owner": "scikit-learn",
        "overlap_with": "scikit-learn; aeon",
        "routing_change": "remove from data-ml; migrate reusable clustering assets first",
        "delete_allowed_after_migration": True,
        "risk_level": "medium",
        "rationale": "普通聚类是传统 ML 子问题，应由 scikit-learn 主导。",
    },
    "scikit-learn": {
        "problem_ids": ["ml_tabular_modeling", "ml_model_evaluation"],
        "primary_problem_id": "ml_tabular_modeling",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "training-machine-learning-models; running-clustering-algorithms",
        "routing_change": "keep in data-ml as coding/research default",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "传统表格分类、回归、聚类、调参和 baseline 的主入口。",
    },
    "shap": {
        "problem_ids": ["ml_explainability"],
        "primary_problem_id": "ml_explainability",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "evaluating-machine-learning-models",
        "routing_change": "keep in data-ml as narrow explainability route authority",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "模型解释和特征归因是独立问题，且 SHAP 工具边界清楚。",
    },
    "statistical-analysis": {
        "problem_ids": ["statistics_research"],
        "primary_problem_id": "statistics_research",
        "target_role": "move-out",
        "target_owner": "research-design",
        "overlap_with": "statsmodels; scikit-learn",
        "routing_change": "remove from data-ml; keep for statistics/research tasks",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "统计检验和研究统计有价值，但不应做普通 ML pack 候选。",
    },
    "statsmodels": {
        "problem_ids": ["statistics_modeling", "ml_time_series"],
        "primary_problem_id": "statistics_modeling",
        "target_role": "move-out",
        "target_owner": "research-design",
        "overlap_with": "statistical-analysis; aeon",
        "routing_change": "remove from data-ml; keep for explicit statistical modeling/ARIMA",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "统计建模和计量边界清楚，但更适合统计/科研设计语境。",
    },
    "training-machine-learning-models": {
        "problem_ids": ["ml_tabular_modeling", "ml_workflow_orchestration"],
        "primary_problem_id": "ml_tabular_modeling",
        "target_role": "merge-delete-after-migration",
        "target_owner": "scikit-learn",
        "overlap_with": "scikit-learn; ml-pipeline-workflow",
        "routing_change": "remove from data-ml; migrate useful training assets first",
        "delete_allowed_after_migration": True,
        "risk_level": "medium",
        "rationale": "训练本身不是独立 pack 问题，应由传统 ML 或流程 owner 接管。",
    },
    "umap-learn": {
        "problem_ids": ["ml_dimensionality_reduction"],
        "primary_problem_id": "ml_dimensionality_reduction",
        "target_role": "move-out",
        "target_owner": "explicit-tool",
        "overlap_with": "scikit-learn; exploratory-data-analysis",
        "routing_change": "remove from data-ml; keep for explicit UMAP/manifold requests",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "UMAP 是窄工具，只有明确降维/流形学习请求时应触发。",
    },
}


@dataclass(frozen=True)
class AuditRow:
    skill_id: str
    category: str
    current_pack: str
    current_role: str
    lines: int
    has_scripts: bool
    has_references: bool
    quality_score: int
    duplication_score: int
    recommended_action: str
    replacement_skill: str
    deletion_reason: str
    config_cleanup_required: str
    risk_level: str


@dataclass(frozen=True)
class AuditArtifact:
    generated_at: str
    repo_root: str
    rows: list[AuditRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "summary": {
                "ml_skill_count": len(self.rows),
                "delete_candidate_count": sum(1 for row in self.rows if row.recommended_action == "delete"),
                "merge_candidate_count": sum(1 for row in self.rows if row.recommended_action == "merge-into"),
                "specialist_deferred_count": sum(
                    1 for row in self.rows if row.recommended_action == "defer-specialist-review"
                ),
            },
            "rows": [asdict(row) for row in self.rows],
        }


@dataclass(frozen=True)
class ProblemMapRow:
    skill_id: str
    problem_ids: str
    primary_problem_id: str
    current_role: str
    target_role: str
    target_owner: str
    overlap_with: str
    unique_assets: str
    routing_change: str
    delete_allowed_after_migration: bool
    risk_level: str
    rationale: str


@dataclass(frozen=True)
class ProblemMapArtifact:
    generated_at: str
    repo_root: str
    rows: list[ProblemMapRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "summary": {
                "data_ml_skill_count": len(self.rows),
                "target_keep_count": sum(1 for row in self.rows if row.target_role == "keep"),
                "target_stage_assistant_count": sum(1 for row in self.rows if row.target_role == "stage-assistant"),
                "target_move_out_count": sum(1 for row in self.rows if row.target_role == "move-out"),
                "target_merge_delete_count": sum(
                    1 for row in self.rows if row.target_role == "merge-delete-after-migration"
                ),
            },
            "target_data_ml_skill_candidates": sorted(DATA_ML_TARGET_SKILLS),
            "rows": [asdict(row) for row in self.rows],
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join([str(key) + " " + _flatten_text(item) for key, item in value.items()])
    if isinstance(value, list | tuple | set):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _contains_keyword(text: str, keyword: str) -> bool:
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    if keyword_lower == "ml":
        return re.search(r"(?<![a-z0-9])ml(?![a-z0-9])", text_lower) is not None
    return keyword_lower in text_lower


def _skill_id_has_ml_signal(skill_id: str) -> bool:
    normalized = skill_id.lower().replace("_", "-")
    explicit_fragments = (
        "machine-learning",
        "ml-",
        "-ml",
        "scikit-learn",
        "sklearn",
        "feature-importance",
        "data-leakage",
        "data-scientist",
        "ml-engineer",
        "transformer",
        "datasets",
    )
    if any(fragment in normalized for fragment in explicit_fragments):
        return True
    return any(
        re.search(pattern, normalized) is not None
        for pattern in (
            r"(^|-)regression($|-)",
            r"(^|-)clustering($|-)",
            r"(^|-)anomaly($|-)",
        )
    )


def _pack_has_ml_signal(pack_ids: set[str]) -> bool:
    return any(pack_id.startswith("ml-") or pack_id.endswith("-ml") for pack_id in pack_ids)


def _is_ml_related(skill_id: str, pack_ids: set[str], route_metadata_text: str) -> bool:
    del route_metadata_text
    if "data-ml" in pack_ids:
        return True
    if skill_id in SPECIALIST_DEFER_SKILLS:
        return True
    if _pack_has_ml_signal(pack_ids):
        return True
    return _skill_id_has_ml_signal(skill_id)


def _has_files(directory: Path) -> bool:
    return directory.is_dir() and any(item.is_file() for item in directory.rglob("*"))


def _build_pack_index(pack_manifest: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    index: dict[str, dict[str, set[str]]] = {}
    for pack in _as_list(pack_manifest.get("packs")):
        if not isinstance(pack, dict):
            continue
        pack_id = str(pack.get("id", "")).strip()
        if not pack_id:
            continue
        defaults = {str(item).strip() for item in _flatten_text(pack.get("defaults_by_task")).split() if item}
        for value in _as_list(pack.get("skill_candidates")):
            skill_id = str(value).strip()
            if skill_id:
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
        for value in _as_list(pack.get("route_authority_candidates")):
            skill_id = str(value).strip()
            if skill_id:
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
                record["route_authority"].add(pack_id)
        for value in _as_list(pack.get("stage_assistant_candidates")):
            skill_id = str(value).strip()
            if skill_id:
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
                record["stage_assistant"].add(pack_id)
        defaults_by_task = pack.get("defaults_by_task")
        if isinstance(defaults_by_task, dict):
            for value in defaults_by_task.values():
                skill_id = str(value).strip()
                if skill_id:
                    record = index.setdefault(
                        skill_id,
                        {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                    )
                    record["packs"].add(pack_id)
                    record["defaults"].add(pack_id)
        elif defaults:
            for skill_id in defaults:
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
                record["defaults"].add(pack_id)
    return index


def _current_role(record: dict[str, set[str]]) -> str:
    if record["route_authority"]:
        return "route_authority"
    if record["stage_assistant"]:
        return "stage_assistant"
    if record["defaults"]:
        return "default"
    return "candidate"


def _quality_score(
    skill_id: str,
    *,
    line_count: int,
    text_length: int,
    has_scripts: bool,
    has_references: bool,
) -> int:
    score = 1
    if line_count >= 20 or text_length >= 3500:
        score += 1
    if has_scripts:
        score += 1
    if has_references:
        score += 1
    if skill_id in OWNER_SKILLS:
        score += 1
    return min(score, 5)


def _duplication_score(
    skill_id: str,
    *,
    current_role: str,
    text: str,
    has_scripts: bool,
    has_references: bool,
) -> int:
    if skill_id in OWNER_SKILLS or skill_id in SPECIALIST_DEFER_SKILLS:
        return 1
    if skill_id in DEFAULT_REPLACEMENTS and not has_scripts and not has_references:
        return 5
    if current_role == "stage_assistant" and len(text) < 3500 and skill_id in DEFAULT_REPLACEMENTS:
        return 4
    if any(_contains_keyword(text, keyword) for keyword in ML_KEYWORDS):
        return 3
    return 1


def _risk_level(skill_id: str, recommended_action: str, replacement_skill: str) -> str:
    if recommended_action == "delete":
        return "low"
    if recommended_action == "defer-specialist-review":
        return "medium"
    if recommended_action == "merge-into" and not replacement_skill:
        return "high"
    if recommended_action == "merge-into":
        return "medium"
    return "low"


def _deletion_reason(
    recommended_action: str,
    *,
    skill_id: str,
    replacement_skill: str,
    quality_score: int,
    duplication_score: int,
) -> str:
    if recommended_action == "delete":
        return (
            f"通用模板型 ML skill；质量分 {quality_score}，重复分 {duplication_score}；"
            f"可由 {replacement_skill} 接管。"
        )
    if recommended_action == "merge-into":
        target = replacement_skill or "待定 owner"
        return f"存在重复或边界不清，先归入 {target} 复核，不直接删除。"
    if recommended_action == "defer-specialist-review":
        return "专业工具或框架绑定 skill，第一轮只暂缓专项评估，不删除。"
    if skill_id in OWNER_SKILLS:
        return "主专家或 owner skill，第一轮保留。"
    return "未满足第一轮删除条件。"


def _category(skill_id: str, recommended_action: str, current_role: str) -> str:
    if recommended_action == "delete":
        return "删除候选"
    if skill_id in SPECIALIST_DEFER_SKILLS:
        return "工具型"
    if skill_id in OWNER_SKILLS or current_role == "route_authority":
        return "主专家"
    if current_role == "stage_assistant":
        return "阶段助手"
    return "参考型"


def _config_cleanup_required(skill_id: str, pack_index: dict[str, dict[str, set[str]]], keyword_index: dict[str, Any], routing_rules: dict[str, Any]) -> str:
    cleanup: list[str] = []
    if skill_id in pack_index:
        cleanup.append("config/pack-manifest.json")
    if skill_id in (keyword_index.get("skills") or {}):
        cleanup.append("config/skill-keyword-index.json")
    if skill_id in (routing_rules.get("skills") or {}):
        cleanup.append("config/skill-routing-rules.json")
    cleanup.append("config/skills-lock.json")
    return "; ".join(dict.fromkeys(cleanup))


def _all_candidate_skill_ids(repo_root: Path, pack_index: dict[str, dict[str, set[str]]], keyword_index: dict[str, Any], routing_rules: dict[str, Any]) -> set[str]:
    skill_ids = set(pack_index)
    skill_ids.update((keyword_index.get("skills") or {}).keys())
    skill_ids.update((routing_rules.get("skills") or {}).keys())
    skills_root = repo_root / "bundled" / "skills"
    if skills_root.is_dir():
        skill_ids.update(path.name for path in skills_root.iterdir() if path.is_dir())
    return {str(skill_id).strip() for skill_id in skill_ids if str(skill_id).strip()}


def _route_metadata_text(skill_id: str, keyword_index: dict[str, Any], routing_rules: dict[str, Any]) -> str:
    keyword_payload = (keyword_index.get("skills") or {}).get(skill_id, {})
    route_payload = (routing_rules.get("skills") or {}).get(skill_id, {})
    return " ".join([skill_id, _flatten_text(keyword_payload), _flatten_text(route_payload)])


def _make_row(
    repo_root: Path,
    skill_id: str,
    pack_index: dict[str, dict[str, set[str]]],
    keyword_index: dict[str, Any],
    routing_rules: dict[str, Any],
) -> AuditRow | None:
    record = pack_index.get(skill_id, {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()})
    skill_dir = repo_root / "bundled" / "skills" / skill_id
    skill_md = skill_dir / "SKILL.md"
    skill_text = skill_md.read_text(encoding="utf-8-sig") if skill_md.exists() else ""
    route_metadata_text = _route_metadata_text(skill_id, keyword_index, routing_rules)
    if not _is_ml_related(skill_id, record["packs"], route_metadata_text):
        return None
    metadata_text = " ".join([route_metadata_text, skill_text])

    line_count = len(skill_text.splitlines())
    has_scripts = _has_files(skill_dir / "scripts")
    has_references = _has_files(skill_dir / "references")
    current_role = _current_role(record)
    quality_score = _quality_score(
        skill_id,
        line_count=line_count,
        text_length=len(skill_text),
        has_scripts=has_scripts,
        has_references=has_references,
    )
    duplication_score = _duplication_score(
        skill_id,
        current_role=current_role,
        text=metadata_text,
        has_scripts=has_scripts,
        has_references=has_references,
    )
    replacement_skill = DEFAULT_REPLACEMENTS.get(skill_id, "")
    recommended_action = "keep"
    if skill_id in SPECIALIST_DEFER_SKILLS:
        recommended_action = "defer-specialist-review"
    elif skill_id in OWNER_SKILLS and quality_score >= 4:
        recommended_action = "keep"
    elif (
        quality_score <= 2
        and duplication_score >= 4
        and not has_scripts
        and not has_references
        and replacement_skill
    ):
        recommended_action = "delete"
    elif duplication_score >= 3 or quality_score <= 2:
        recommended_action = "merge-into"

    risk_level = _risk_level(skill_id, recommended_action, replacement_skill)
    if recommended_action == "delete" and risk_level == "high":
        recommended_action = "merge-into"
        risk_level = _risk_level(skill_id, recommended_action, replacement_skill)

    return AuditRow(
        skill_id=skill_id,
        category=_category(skill_id, recommended_action, current_role),
        current_pack=", ".join(sorted(record["packs"])),
        current_role=current_role,
        lines=line_count,
        has_scripts=has_scripts,
        has_references=has_references,
        quality_score=quality_score,
        duplication_score=duplication_score,
        recommended_action=recommended_action,
        replacement_skill=replacement_skill,
        deletion_reason=_deletion_reason(
            recommended_action,
            skill_id=skill_id,
            replacement_skill=replacement_skill,
            quality_score=quality_score,
            duplication_score=duplication_score,
        ),
        config_cleanup_required=_config_cleanup_required(skill_id, pack_index, keyword_index, routing_rules),
        risk_level=risk_level,
    )


def audit_repository(repo_root: Path) -> AuditArtifact:
    repo_root = repo_root.resolve()
    pack_manifest = _read_json(repo_root / "config" / "pack-manifest.json")
    keyword_index = _read_json(repo_root / "config" / "skill-keyword-index.json")
    routing_rules = _read_json(repo_root / "config" / "skill-routing-rules.json")
    pack_index = _build_pack_index(pack_manifest)
    rows = []
    for skill_id in sorted(_all_candidate_skill_ids(repo_root, pack_index, keyword_index, routing_rules)):
        row = _make_row(repo_root, skill_id, pack_index, keyword_index, routing_rules)
        if row is not None:
            rows.append(row)
    return AuditArtifact(
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo_root),
        rows=rows,
    )


def _data_ml_pack(pack_manifest: dict[str, Any]) -> dict[str, Any]:
    for pack in _as_list(pack_manifest.get("packs")):
        if isinstance(pack, dict) and str(pack.get("id", "")).strip() == "data-ml":
            return pack
    return {}


def _file_count(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for item in directory.rglob("*") if item.is_file())


def _asset_summary(skill_dir: Path) -> str:
    parts = [
        f"scripts={_file_count(skill_dir / 'scripts')}",
        f"references={_file_count(skill_dir / 'references')}",
        f"assets={_file_count(skill_dir / 'assets')}",
    ]
    return "; ".join(parts)


def _problem_decision_for(skill_id: str) -> dict[str, Any]:
    return DATA_ML_PROBLEM_DECISIONS.get(
        skill_id,
        {
            "problem_ids": ["manual_review"],
            "primary_problem_id": "manual_review",
            "target_role": "manual-review",
            "target_owner": "",
            "overlap_with": "",
            "routing_change": "manual review required before changing data-ml membership",
            "delete_allowed_after_migration": False,
            "risk_level": "high",
            "rationale": "未在 problem-first 决策表中登记，不能自动收敛。",
        },
    )


def audit_data_ml_problem_map(repo_root: Path) -> ProblemMapArtifact:
    repo_root = repo_root.resolve()
    pack_manifest = _read_json(repo_root / "config" / "pack-manifest.json")
    pack_index = _build_pack_index(pack_manifest)
    data_ml = _data_ml_pack(pack_manifest)
    rows: list[ProblemMapRow] = []
    for skill_id_raw in _as_list(data_ml.get("skill_candidates")):
        skill_id = str(skill_id_raw).strip()
        if not skill_id:
            continue
        record = pack_index.get(skill_id, {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()})
        decision = _problem_decision_for(skill_id)
        skill_dir = repo_root / "bundled" / "skills" / skill_id
        rows.append(
            ProblemMapRow(
                skill_id=skill_id,
                problem_ids="; ".join(_as_list(decision.get("problem_ids"))),
                primary_problem_id=str(decision.get("primary_problem_id", "")),
                current_role=_current_role(record),
                target_role=str(decision.get("target_role", "manual-review")),
                target_owner=str(decision.get("target_owner", "")),
                overlap_with=str(decision.get("overlap_with", "")),
                unique_assets=_asset_summary(skill_dir),
                routing_change=str(decision.get("routing_change", "")),
                delete_allowed_after_migration=bool(decision.get("delete_allowed_after_migration", False)),
                risk_level=str(decision.get("risk_level", "high")),
                rationale=str(decision.get("rationale", "")),
            )
        )
    return ProblemMapArtifact(
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(repo_root),
        rows=rows,
    )


def _markdown_table(rows: list[Any], fields: list[str]) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        data = asdict(row)
        values = [str(data[field]).replace("\n", " ").replace("|", "\\|") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def _write_markdown(path: Path, artifact: AuditArtifact) -> None:
    delete_rows = [row for row in artifact.rows if row.recommended_action == "delete"]
    merge_rows = [row for row in artifact.rows if row.recommended_action == "merge-into"]
    deferred_rows = [row for row in artifact.rows if row.recommended_action == "defer-specialist-review"]
    lines: list[str] = [
        "# ML Skills Pruning Audit",
        "",
        f"- Generated At: `{artifact.generated_at}`",
        f"- ML Skill Count: {len(artifact.rows)}",
        f"- Delete Candidates: {len(delete_rows)}",
        f"- Merge Candidates: {len(merge_rows)}",
        f"- Specialist Deferred: {len(deferred_rows)}",
        "",
        "## 删除候选",
        "",
    ]
    if delete_rows:
        lines.extend(
            _markdown_table(
                delete_rows,
                [
                    "skill_id",
                    "current_pack",
                    "current_role",
                    "quality_score",
                    "duplication_score",
                    "replacement_skill",
                    "risk_level",
                    "deletion_reason",
                ],
            )
        )
    else:
        lines.append("- none")
    lines.extend(["", "## 合并但暂不删除", ""])
    if merge_rows:
        lines.extend(_markdown_table(merge_rows, ["skill_id", "current_pack", "quality_score", "duplication_score", "replacement_skill", "deletion_reason"]))
    else:
        lines.append("- none")
    lines.extend(["", "## 专业工具型暂缓", ""])
    if deferred_rows:
        lines.extend(_markdown_table(deferred_rows, ["skill_id", "current_pack", "current_role", "risk_level", "deletion_reason"]))
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_problem_markdown(path: Path, artifact: ProblemMapArtifact) -> None:
    keep_rows = [row for row in artifact.rows if row.target_role == "keep"]
    stage_rows = [row for row in artifact.rows if row.target_role == "stage-assistant"]
    move_rows = [row for row in artifact.rows if row.target_role == "move-out"]
    merge_rows = [row for row in artifact.rows if row.target_role == "merge-delete-after-migration"]
    lines: list[str] = [
        "# Data-ML Problem-First Consolidation",
        "",
        f"- Generated At: `{artifact.generated_at}`",
        f"- Current Data-ML Skills: {len(artifact.rows)}",
        f"- Target Keep: {len(keep_rows)}",
        f"- Target Stage Assistants: {len(stage_rows)}",
        f"- Move Out: {len(move_rows)}",
        f"- Merge/Delete After Migration: {len(merge_rows)}",
        "",
        "## 目标保留",
        "",
    ]
    if keep_rows:
        lines.extend(_markdown_table(keep_rows, ["skill_id", "primary_problem_id", "current_role", "rationale"]))
    else:
        lines.append("- none")
    lines.extend(["", "## 阶段助手", ""])
    if stage_rows:
        lines.extend(_markdown_table(stage_rows, ["skill_id", "primary_problem_id", "current_role", "rationale"]))
    else:
        lines.append("- none")
    lines.extend(["", "## 移出 data-ml 但保留目录", ""])
    if move_rows:
        lines.extend(
            _markdown_table(
                move_rows,
                ["skill_id", "primary_problem_id", "target_owner", "unique_assets", "rationale"],
            )
        )
    else:
        lines.append("- none")
    lines.extend(["", "## 合并迁移后可删除", ""])
    if merge_rows:
        lines.extend(
            _markdown_table(
                merge_rows,
                ["skill_id", "primary_problem_id", "target_owner", "unique_assets", "rationale"],
            )
        )
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_data_ml_problem_artifacts(
    repo_root: Path,
    artifact: ProblemMapArtifact,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    repo_root = repo_root.resolve()
    output_dir = output_dir or repo_root / "outputs" / "skills-audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "data-ml-problem-map.json"
    csv_path = output_dir / "data-ml-problem-map.csv"
    markdown_path = output_dir / "data-ml-problem-consolidation.md"

    json_path.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROBLEM_MAP_CSV_FIELDS)
        writer.writeheader()
        for row in artifact.rows:
            writer.writerow(asdict(row))
    _write_problem_markdown(markdown_path, artifact)
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def write_artifacts(repo_root: Path, artifact: AuditArtifact, output_dir: Path | None = None) -> dict[str, Path]:
    repo_root = repo_root.resolve()
    output_dir = output_dir or repo_root / "outputs" / "skills-audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "ml-skills-pruning-audit.json"
    csv_path = output_dir / "ml-skills-pruning-candidates.csv"
    markdown_path = output_dir / "ml-skills-pruning-candidates.md"

    json_path.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in artifact.rows:
            writer.writerow(asdict(row))
    _write_markdown(markdown_path, artifact)
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit ML-related bundled skills before pruning.")
    parser.add_argument("--repo-root", help="Optional repository root. Defaults to the current working directory.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/CSV/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    artifact = audit_repository(repo_root)
    if args.write_artifacts:
        output_dir = Path(args.output_directory).resolve() if args.output_directory else None
        write_artifacts(repo_root, artifact, output_dir)
        problem_artifact = audit_data_ml_problem_map(repo_root)
        write_data_ml_problem_artifacts(repo_root, problem_artifact, output_dir)
    print(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
