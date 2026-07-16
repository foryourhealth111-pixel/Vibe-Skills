from __future__ import annotations

from pathlib import Path

from vgo_runtime.kernel.skill_index import build_skill_index
from vgo_runtime.router_contract_runtime import route_prompt


def _write_skill(root: Path, skill_id: str, frontmatter: str, body: str = "# Overview\n") -> Path:
    skill_dir = root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body}", encoding="utf-8")
    return skill_file


def test_route_prefers_local_skill_with_matching_capability_over_generic_words(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "local-stats-helper",
        """
name: Local Stats Helper
description: Local skill for variable relationship modeling.
capabilities:
  - statistics.relationship_modeling
  - statistics.correlation
  - statistics.regression
  - data.quality_check
not_for:
  - study plan pool
tags:
  - statistics
""",
    )
    _write_skill(
        skills_root,
        "local-study-pool",
        """
name: Local Study Pool
description: Local skill for research data plan scope and study pool construction.
capabilities:
  - research.study_plan_pool
tags:
  - research
""",
    )

    result = route_prompt(
        "small csv report compare sleep hours stress and focus with data quality, trend, relationship, correlation, regression, figure, reader report",
        "M",
        "research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    assert result["candidate_focus"]["skill"] == "local-stats-helper"
    assert "statistics.regression" in result["task_card"]["required_capabilities"]
    assert result["ranked"][0]["role"] == "primary_owner"
    assert "research.study_plan_pool" in result["task_card"]["rejected_capabilities"]


def test_skill_index_cache_reuses_unchanged_cards_and_refreshes_changed_skill(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)

    alpha = _write_skill(
        skills_root,
        "alpha-stats",
        """
name: Alpha Stats
description: Correlation and regression helper.
capabilities:
  - statistics.correlation
""",
    )
    beta = _write_skill(
        skills_root,
        "beta-report",
        """
name: Beta Report
description: Reader report helper.
capabilities:
  - writing.reader_report
""",
    )

    first = build_skill_index(agent_root, host_roots=(skills_root,))
    cards = {card["skill_id"]: Path(card["card_path"]) for card in first["skill_cache"]["cards"]}
    alpha_first_mtime = cards["alpha-stats"].stat().st_mtime_ns
    beta_first_mtime = cards["beta-report"].stat().st_mtime_ns

    second = build_skill_index(agent_root, host_roots=(skills_root,))
    second_cards = {card["skill_id"]: Path(card["card_path"]) for card in second["skill_cache"]["cards"]}
    assert second_cards["alpha-stats"].stat().st_mtime_ns == alpha_first_mtime
    assert second_cards["beta-report"].stat().st_mtime_ns == beta_first_mtime

    beta.write_text(beta.read_text(encoding="utf-8") + "\n# Changed\n", encoding="utf-8")
    third = build_skill_index(agent_root, host_roots=(skills_root,))
    third_cards = {card["skill_id"]: Path(card["card_path"]) for card in third["skill_cache"]["cards"]}

    assert third_cards["alpha-stats"].stat().st_mtime_ns == alpha_first_mtime
    assert third_cards["beta-report"].stat().st_mtime_ns > beta_first_mtime
    assert third["skill_cache"]["reused_count"] >= 1
    assert third["skill_cache"]["refreshed_count"] >= 1


def test_route_uses_weak_text_capability_evidence_for_existing_skills_without_capability_fields(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "statistical-analysis",
        """
name: statistical-analysis
description: Statistical test, assumption check, power analysis, and result reporting.
tags:
  - statistics
""",
        """
# Overview
Use for hypothesis tests, regression, correlation, effect sizes, data diagnostics, and reporting.
""",
    )
    _write_skill(
        skills_root,
        "paper-writer",
        """
name: paper-writer
description: Scientific manuscript writing workflow.
tags:
  - writing
""",
    )

    result = route_prompt(
        "small csv report compare sleep hours stress and focus with data quality, trend, relationship, correlation, regression, figure, reader report",
        "M",
        "research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    assert result["candidate_focus"]["skill"] == "statistical-analysis"
    assert "statistics.regression" in result["ranked"][0]["matched_capabilities"]
    assert result["ranked"][0]["capability_evidence_level"] == "weak_text"


def test_route_prefers_statistics_owner_over_visualization_helper_for_chinese_data_task(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "statistical-analysis",
        """
name: statistical-analysis
description: 用于统计分析、检验选择、假设检查和结果报告。
tags:
  - statistics
""",
        """
# Overview
Use for hypothesis tests, regression, correlation, effect sizes, data diagnostics, and reporting.
""",
    )
    _write_skill(
        skills_root,
        "scientific-visualization",
        """
name: scientific-visualization
description: Figure and visualization workflow for scientific reports.
tags:
  - visualization
""",
        """
# Overview
Use for correlation plots, regression figures, data quality charts, and visual reports.
""",
    )

    result = route_prompt(
        "比较睡眠时长和主观压力水平对第二天专注度的影响。小数据，检查数据质量和基本趋势，用相关、回归、图表，写普通读者报告。",
        "XL",
        "research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    assert result["candidate_focus"]["skill"] == "statistical-analysis"
    assert result["ranked"][0]["role"] == "primary_owner"
    assert "statistics.regression" in result["ranked"][0]["matched_capabilities"]


def test_xl_composite_research_route_selects_minimal_skill_set(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "exploratory-data-analysis",
        """
name: exploratory-data-analysis
description: Data quality checks and exploratory data analysis.
capabilities:
  - data.quality_check
  - data.eda
tags:
  - eda
""",
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        """
name: statistical-analysis
description: Statistical tests and relationship modeling.
capabilities:
  - statistics.relationship_modeling
  - statistics.regression
tags:
  - statistics
""",
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        """
name: scikit-learn
description: Predictive model training and model evaluation.
capabilities:
  - model.training
  - model.evaluation
tags:
  - machine-learning
""",
    )
    _write_skill(
        skills_root,
        "shap",
        """
name: shap
description: SHAP model explanation and feature importance.
capabilities:
  - model.explainability
tags:
  - shap
""",
    )
    _write_skill(
        skills_root,
        "matplotlib",
        """
name: matplotlib
description: Reader-facing charts and figures.
capabilities:
  - visualization.figure
tags:
  - plotting
""",
    )
    _write_skill(
        skills_root,
        "pptx-collab-integrated",
        """
name: pptx-collab-integrated
description: Openable PPT summary deck.
capabilities:
  - presentation.deck
tags:
  - pptx
""",
    )

    result = route_prompt(
        "XL clinical machine learning study with synthetic CSV, data quality checks, exploratory analysis, statistical relationship tests, scikit-learn prediction model, SHAP explanation, reader figures, Chinese report, PPT summary, and actual skill evidence files",
        "XL",
        "planning",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    selected_skills = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]

    assert result["candidate_focus"]["skill"] in selected_skills
    assert result["skill_routing"]["primary_candidate_skill"] == result["candidate_focus"]["skill"]
    assert set(selected_skills) >= {
        "exploratory-data-analysis",
        "statistical-analysis",
        "scikit-learn",
        "shap",
        "matplotlib",
        "pptx-collab-integrated",
    }


def test_xl_composite_route_uses_weak_text_specialists_for_explainability_and_ppt(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "scikit-learn",
        """
name: scikit-learn
description: Python machine learning model training and evaluation.
tags:
  - machine-learning
""",
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        """
name: statistical-analysis
description: Statistical tests, regression, and relationship modeling.
tags:
  - statistics
""",
    )
    _write_skill(
        skills_root,
        "shap",
        """
name: shap
description: SHAP model explanation and feature importance workflow.
tags:
  - shap
""",
    )
    _write_skill(
        skills_root,
        "pptx-collab-integrated",
        """
name: pptx-collab-integrated
description: Openable PPT summary deck workflow.
tags:
  - pptx
""",
    )
    _write_skill(
        skills_root,
        "first-principles-explorer",
        """
name: first-principles-explorer
description: Clarify assumptions and write reader-facing reports.
tags:
  - thinking
""",
    )

    result = route_prompt(
        "XL clinical machine learning study with statistical tests, scikit-learn prediction model, SHAP explanation, reader figures, Chinese report, PPT summary, and actual skill evidence files",
        "XL",
        "planning",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    selected_skills = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]

    assert "scikit-learn" in selected_skills
    assert "statistical-analysis" in selected_skills
    assert "shap" in selected_skills
    assert "pptx-collab-integrated" in selected_skills
    assert "first-principles-explorer" not in selected_skills


def test_xl_composite_route_prefers_openable_pptx_delivery_skill(tmp_path: Path) -> None:
    agent_root = tmp_path / ".agents"
    skills_root = agent_root / "skills"
    skills_root.mkdir(parents=True)
    (tmp_path / ".codex" / "skills").mkdir(parents=True)

    _write_skill(
        skills_root,
        "scikit-learn",
        """
name: scikit-learn
description: Python machine learning model training and evaluation.
capabilities:
  - data.quality_check
  - data.eda
  - statistics.regression
  - model.training
  - model.evaluation
  - model.explainability
  - visualization.figure
tags:
  - machine-learning
""",
    )
    _write_skill(
        skills_root,
        "shap",
        """
name: shap
description: SHAP model explanation and feature importance.
capabilities:
  - model.explainability
tags:
  - shap
""",
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        """
name: statistical-analysis
description: Statistical tests and relationship modeling.
capabilities:
  - statistics.relationship_modeling
  - statistics.regression
tags:
  - statistics
""",
    )
    _write_skill(
        skills_root,
        "exploratory-data-analysis",
        """
name: exploratory-data-analysis
description: Data quality checks and exploratory data analysis.
capabilities:
  - data.quality_check
  - data.eda
tags:
  - eda
""",
    )
    _write_skill(
        skills_root,
        "scientific-visualization",
        """
name: scientific-visualization
description: Reader-facing figures and scientific visualization.
capabilities:
  - visualization.figure
tags:
  - visualization
""",
    )
    _write_skill(
        skills_root,
        "ppt-image-first",
        """
name: ppt-image-first
description: Image-first PPT design workflow.
capabilities:
  - data.quality_check
  - model.explainability
  - visualization.figure
  - presentation.deck
tags:
  - ppt
""",
    )
    _write_skill(
        skills_root,
        "nature-paper2ppt",
        """
name: nature-paper2ppt
description: Convert an existing academic paper with model figures into a PPTX deck.
capabilities:
  - presentation.deck
  - visualization.figure
tags:
  - pptx
""",
    )
    _write_skill(
        skills_root,
        "pptx-collab-integrated",
        """
name: pptx-collab-integrated
description: Openable PPTX summary deck workflow.
capabilities:
  - presentation.deck
tags:
  - pptx
""",
    )

    result = route_prompt(
        "XL clinical machine learning study with data quality, EDA, statistics, scikit-learn model, SHAP explanation, reader figures, Chinese report, and openable PPTX summary",
        "XL",
        "planning",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=Path(__file__).resolve().parents[4],
    )

    selected_skills = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]

    assert "pptx-collab-integrated" in selected_skills
    assert "ppt-image-first" not in selected_skills
    assert "nature-paper2ppt" not in selected_skills
