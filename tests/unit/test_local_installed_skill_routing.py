from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel.skill_index import build_skill_catalog, build_skill_index_from_catalog
from vgo_runtime.router_contract_runtime import route_prompt


def _write_skill(root: Path, skill_id: str, frontmatter: str, body: str = "") -> Path:
    skill_file = root / skill_id / "SKILL.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(frontmatter.strip() + "\n---\n" + body, encoding="utf-8")
    return skill_file


def _frontmatter(name: str, description: str, extra: str = "") -> str:
    return f"""---
name: {name}
description: {description}
{extra}"""


def test_local_skill_index_accepts_real_codex_frontmatter_and_extra_fields(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    agents_skills = agent_root / "skills"
    skill_path = _write_skill(
        agents_skills,
        "accelerate",
        _frontmatter(
            "Accelerate",
            "Use Hugging Face Accelerate for distributed training.",
            """version: 1.2.3
author: local user
tags:
  - training
  - gpu
dependencies:
  - torch
""",
        ),
        "# Usage\n\n## Launch\n\nUse accelerate launch.",
    )

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(agents_skills,))
    index = build_skill_index_from_catalog(catalog)

    assert catalog["schema_version"] == "local_skill_index_v2"
    assert index["schema_version"] == "local_skill_index_v2"
    assert index["skills"][0]["skill_id"] == "accelerate"
    assert index["skills"][0]["display_name"] == "Accelerate"
    assert index["skills"][0]["description"] == "Use Hugging Face Accelerate for distributed training."
    assert index["skills"][0]["skill_entrypoint"] == str(skill_path.resolve())
    assert index["skills"][0]["skill_root"] == str(skill_path.parent.resolve())
    assert index["skills"][0]["source_kind"] == "host_installed"
    assert index["skills"][0]["active"] is True
    assert index["skills"][0]["duplicate_state"] == "active"
    assert index["skills"][0]["content_sha256"]
    assert index["skills"][0]["tags"] == ["training", "gpu"]


def test_local_skill_index_uses_agents_then_codex_then_claude_duplicate_priority(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    agents_skills = home / ".agents" / "skills"
    codex_skills = home / ".codex" / "skills"
    claude_skills = home / ".claude" / "skills"
    agents_path = _write_skill(
        agents_skills,
        "statistical-analysis",
        _frontmatter("Stats Agents", "Agents copy should win."),
    )
    codex_path = _write_skill(
        codex_skills,
        "statistical-analysis",
        _frontmatter("Stats Codex", "Codex copy should be inactive."),
    )
    claude_path = _write_skill(
        claude_skills,
        "statistical-analysis",
        _frontmatter("Stats Claude", "Claude copy should be inactive."),
    )

    catalog = build_skill_catalog(
        agent_root=agent_root,
        host_roots=(agents_skills, codex_skills, claude_skills),
    )
    rows = [entry for entry in catalog["entries"] if entry["skill_id"] == "statistical-analysis"]

    assert [row["skill_entrypoint"] for row in rows] == [
        str(agents_path.resolve()),
        str(codex_path.resolve()),
        str(claude_path.resolve()),
    ]
    assert [row["active"] for row in rows] == [True, False, False]
    assert [row["duplicate_state"] for row in rows] == [
        "active",
        "shadowed_duplicate",
        "shadowed_duplicate",
    ]
    assert build_skill_index_from_catalog(catalog)["skills"][0]["display_name"] == "Stats Agents"
    assert catalog["discovery_diagnostics"]["duplicates"][0]["active_entrypoint"] == str(agents_path.resolve())


def test_local_skill_index_discovers_a_unique_skill_inside_the_codex_plugin_cache(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    plugin_cache = tmp_path / "home" / ".codex" / "plugins" / "cache"
    skill_path = _write_skill(
        plugin_cache / "openai-primary-runtime" / "documents" / "1" / "skills",
        "documents",
        _frontmatter("Documents", "Render and verify formal documents."),
    )

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(plugin_cache,))
    index = build_skill_index_from_catalog(catalog)

    assert [entry["skill_id"] for entry in index["skills"]] == ["documents"]
    assert index["skills"][0]["skill_entrypoint"] == str(skill_path.resolve())


def test_local_skill_index_does_not_choose_between_ambiguous_plugin_cache_skills(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    plugin_cache = tmp_path / "home" / ".codex" / "plugins" / "cache"
    first = _write_skill(
        plugin_cache / "provider-a" / "documents" / "1" / "skills",
        "documents",
        _frontmatter("Documents A", "Render formal documents."),
    )
    second = _write_skill(
        plugin_cache / "provider-b" / "documents" / "1" / "skills",
        "documents",
        _frontmatter("Documents B", "Render formal documents."),
    )

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(plugin_cache,))
    index = build_skill_index_from_catalog(catalog)

    assert index["skills"] == []
    ambiguous = [
        row
        for row in catalog["discovery_diagnostics"]["invalid_entries"]
        if row["reason"] == "ambiguous_plugin_skill_id"
    ]
    assert {row["path"] for row in ambiguous} == {str(first.resolve()), str(second.resolve())}


def test_local_skill_index_records_invalid_and_excludes_only_canonical_controller_entry(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(skills_root, "vibe", _frontmatter("vibe", "Controller entry."))
    _write_skill(skills_root, "vibe-upgrade", _frontmatter("vibe-upgrade", "Legacy name reused as a local helper."))
    _write_skill(skills_root, "missing-description", "---\nname: Missing Description")
    _write_skill(skills_root, "usable-local", _frontmatter("Usable Local", "A real local helper."))

    catalog = build_skill_catalog(agent_root=agent_root, host_roots=(skills_root,))
    index = build_skill_index_from_catalog(catalog)

    assert [row["skill_id"] for row in index["skills"]] == ["usable-local", "vibe-upgrade"]
    reasons = {
        item["skill_id"]: item["reason"]
        for item in catalog["discovery_diagnostics"]["invalid_entries"]
    }
    assert reasons["vibe"] == "controller_entry_excluded"
    assert "vibe-upgrade" not in reasons
    assert reasons["missing-description"] == "missing_required_frontmatter"


def test_local_router_selects_new_installed_skill_not_present_in_old_pack_files(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    skill_path = _write_skill(
        skills_root,
        "sleep-stress-focus",
        _frontmatter(
            "Sleep Stress Focus",
            "Analyze sleep logs, stress scores, focus ratings, and daily wellness tables.",
            "tags:\n  - sleep\n  - stress\n  - focus\n  - wellness\n",
        ),
        "# Analyze Sleep Tables\n\n## Stress and focus\n",
    )

    result = route_prompt(
        prompt="Analyze sleep logs and stress scores, then summarize focus patterns.",
        grade="L",
        task_type="research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_source"] == "local_skill_index"
    assert result["candidate_focus"]["skill"] == "sleep-stress-focus"
    assert result["candidate_focus"]["skill_entrypoint"] == str(skill_path.resolve())
    assert result["candidate_focus"]["pack_id"] == "local-skill-index"
    assert result["ranked"][0]["candidate_source"] == "local_skill_index"
    assert result["ranked"][0]["skill_entrypoint"] == str(skill_path.resolve())


def test_local_router_focuses_plausible_local_near_match_without_confirm_ui(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    skill_path = _write_skill(
        skills_root,
        "sleep-stress-focus",
        _frontmatter(
            "Sleep Stress Focus",
            "Analyze sleep logs, stress scores, focus ratings, and daily wellness tables.",
            "tags:\n  - wellness\n",
        ),
    )

    result = route_prompt(
        prompt="Review sleep and stress patterns from wearable exports before I decide next steps.",
        grade="L",
        task_type="research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["route_reason"] == "candidate_signal_confirm_override"
    assert "confirm_required" not in result
    assert result["candidate_focus"]["skill"] == "sleep-stress-focus"
    assert "confirm_options" not in result


def test_local_router_uses_declared_capability_bridge_for_semantic_near_match(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    skill_path = _write_skill(
        skills_root,
        "vercel-helper",
        _frontmatter(
            "Vercel Helper",
            "Deploy web apps.",
            "capabilities:\n  - deploy.vercel\n",
        ),
    )

    result = route_prompt(
        prompt="Need a preview deployment for this Next.js app before merge.",
        grade="L",
        task_type="coding",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["route_reason"] in {"auto_route", "candidate_signal_host_selection", "candidate_signal_confirm_override"}
    assert "confirm_required" not in result
    assert result["candidate_focus"]["skill"] == "vercel-helper"
    assert "confirm_options" not in result


def test_local_router_uses_body_intent_weak_capability_bridge_for_semantic_near_match(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    skill_path = _write_skill(
        skills_root,
        "managed-release-helper",
        _frontmatter(
            "Managed Release Helper",
            "Deploy web apps.",
        ),
        "# Usage\n\nUse for preview deployment workflows.\n",
    )

    result = route_prompt(
        prompt="Need a preview deployment for this Next.js app before merge.",
        grade="L",
        task_type="coding",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["route_reason"] in {"auto_route", "candidate_signal_host_selection", "candidate_signal_confirm_override"}
    assert "confirm_required" not in result
    assert result["candidate_focus"]["skill"] == "managed-release-helper"
    assert "confirm_options" not in result


def test_local_router_does_not_use_metadata_only_weak_capability_bridge_for_semantic_near_match(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "vercel-helper",
        _frontmatter(
            "Vercel Helper",
            "Deploy web apps.",
        ),
    )

    result = route_prompt(
        prompt="Need a preview deployment for this Next.js app before merge.",
        grade="L",
        task_type="coding",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"] is None
    assert result["route_reason"] == "no_local_candidate_above_threshold"
    assert result["top1_top2_gap"] == 0.0
    assert "confirm_required" not in result
    assert "confirm_options" not in result


def test_local_router_does_not_treat_metadata_only_training_mentions_as_route_active_capabilities(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Train predictive models.",
            "capabilities:\n  - model.training\n",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "Optimize For GPU",
            "Speed up machine learning training on GPU.",
        ),
    )

    result = route_prompt(
        prompt="训练模型",
        grade="L",
        task_type="planning",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "scikit-learn"
    assert ranked["scikit-learn"]["matched_capabilities"] == ["model.training"]
    assert "optimize-for-gpu" not in ranked


def test_local_router_uses_named_when_to_use_sections_for_sparse_training_prompts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local",
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Classical ML helper.",
        ),
        (
            "# Scikit-learn\n\n"
            "## When to Use This Skill\n\n"
            "Use the scikit-learn skill when:\n\n"
            "- Building classification or regression models\n"
            "- Training baseline machine learning systems\n"
        ),
    )

    result = route_prompt(
        prompt="训练模型",
        grade="L",
        task_type="planning",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "scikit-learn"
    assert "model.training" in ranked["scikit-learn"]["matched_capabilities"]
    assert ranked["scikit-learn"]["capability_evidence_level"] == "weak_text"


def test_local_router_uses_explicit_description_intent_for_debug_regression_prompts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnosing-bugs",
        _frontmatter(
            "diagnosing-bugs",
            "Diagnosis loop for hard bugs. Use when the user reports failing tests, stack traces, or slow pages.",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "Analyze statistical regression workflows.",
            "capabilities:\n  - statistics.regression\n",
        ),
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "diagnosing-bugs"
    assert "debug.systematic_workflow" in ranked["diagnosing-bugs"]["matched_capabilities"]
    assert ranked["diagnosing-bugs"]["candidate_selection_reason"] == "capability_ranked"


def test_local_router_does_not_infer_statistical_regression_from_generic_model_training_language(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Train predictive models.",
            "capabilities:\n  - model.training\n",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "Analyze regression analysis workflows.",
            "capabilities:\n  - statistics.regression\n",
        ),
    )

    result = route_prompt(
        prompt="训练模型",
        grade="L",
        task_type="planning",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "scikit-learn"
    assert "statistics.regression" not in result["task_card"]["required_capabilities"]
    assert "statistical-analysis" not in ranked


def test_local_router_does_not_infer_statistical_regression_from_software_performance_regression(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnosing-bugs",
        _frontmatter(
            "diagnosing-bugs",
            "Diagnosis loop for hard bugs.",
            "capabilities:\n  - debug.systematic_workflow\n",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "Analyze regression analysis workflows.",
            "capabilities:\n  - statistics.regression\n",
        ),
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "diagnosing-bugs"
    assert "statistics.regression" not in result["task_card"]["required_capabilities"]
    assert ranked["statistical-analysis"]["matched_capabilities"] == []


def test_local_router_keeps_statistical_regression_for_explicit_regression_analysis_requests(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "Analyze regression analysis workflows.",
            "capabilities:\n  - statistics.regression\n",
        ),
    )

    result = route_prompt(
        prompt="做线性回归分析并解释 effect size",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"]["skill"] == "statistical-analysis"
    assert "statistics.regression" in result["task_card"]["required_capabilities"]
    assert "statistics.regression" in result["ranked"][0]["matched_capabilities"]


def test_local_router_does_not_route_generic_help_prompt_from_task_type_alone(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "literature-review",
        _frontmatter(
            "literature-review",
            "Conduct research literature reviews.",
        ),
    )
    _write_skill(
        skills_root,
        "scientific-reporting",
        _frontmatter(
            "scientific-reporting",
            "Write research reports.",
        ),
    )

    result = route_prompt(
        prompt="help me with this",
        grade="M",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"] is None
    assert result["route_mode"] == "no_local_candidate"
    assert result["route_reason"] == "no_local_candidate_above_threshold"


def test_local_router_treats_machine_learning_result_figure_requests_as_visualization_not_training(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scientific-visualization",
        _frontmatter(
            "scientific-visualization",
            "Create publication figures, result plots, and scientific visualization outputs.",
            "capabilities:\n  - visualization.figure\n",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Train predictive models and compare classic ML baselines.",
            "capabilities:\n  - model.training\n",
        ),
    )

    result = route_prompt(
        prompt="对机器学习结果做数据可视化和结果图",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"]["skill"] == "scientific-visualization"
    assert "model.training" not in result["task_card"]["required_capabilities"]
    assert "visualization.figure" in result["task_card"]["required_capabilities"]


def test_local_router_treats_data_leakage_audit_requests_as_guard_not_training(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "ml-data-leakage-guard",
        _frontmatter(
            "ml-data-leakage-guard",
            "Check feature pipelines for data leakage, fit before split, and prediction time violations.",
            "capabilities:\n  - model.data_leakage_guard\n",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Train predictive models and compare classic ML baselines.",
            "capabilities:\n  - model.training\n",
        ),
    )

    result = route_prompt(
        prompt="请检查这个特征工程流程有没有数据泄漏，尤其是 fit before split 和 prediction time 问题",
        grade="L",
        task_type="review",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"]["skill"] == "ml-data-leakage-guard"
    assert "model.training" not in result["task_card"]["required_capabilities"]
    assert "model.data_leakage_guard" in result["task_card"]["required_capabilities"]


def test_local_router_keeps_latex_submission_owned_by_latex_pipeline_when_figure_skill_only_exports_pdf(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scientific-visualization",
        _frontmatter(
            "scientific-visualization",
            "Create publication figures with export PDF/EPS/TIFF for journal-ready scientific plots.",
        ),
        (
            "# Scientific Visualization\n\n"
            "## When to Use This Skill\n\n"
            "- Preparing figures for journal submission\n"
            "- Exporting publication plots as PDF/EPS/TIFF\n"
        ),
    )
    _write_skill(
        skills_root,
        "latex-submission-pipeline",
        _frontmatter(
            "latex-submission-pipeline",
            "Build a LaTeX manuscript submission pipeline.",
            "capabilities:\n  - document.latex_submission\n",
        ),
    )

    result = route_prompt(
        prompt="做数据可视化和结果图，最后用 LaTeX 写成论文 PDF",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "document.latex_submission" not in ranked["scientific-visualization"]["matched_capabilities"]
    assert "latex-submission-pipeline" in selected_ids


def test_local_router_prefers_scientific_reporting_for_report_authoring_prompts(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scientific-reporting",
        _frontmatter(
            "scientific-reporting",
            "Write research/technical reports with executive summary, methods, results, discussion, and PDF outputs.",
        ),
        (
            "# Scientific Reporting\n\n"
            "## 适用场景（关键词）\n\n"
            "- 中文：科研报告、技术报告、项目报告、实验报告\n"
            "- 英文：research report、technical report、Quarto、PDF report\n"
        ),
    )
    _write_skill(
        skills_root,
        "webthinker-deep-research",
        _frontmatter(
            "webthinker-deep-research",
            "Deep web research with a structured report and auditable trace.",
        ),
    )

    result = route_prompt(
        prompt="请把我们现有实验结果整理成 research report，带 executive summary、appendix、Quarto/PDF 导出",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked = {row["skill"]: row for row in result["ranked"]}
    assert result["candidate_focus"]["skill"] == "scientific-reporting"
    assert "writing.scientific_report" in ranked["scientific-reporting"]["matched_capabilities"]


def test_local_router_reports_actual_top1_top2_gap_for_selected_candidate(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "vercel-helper",
        _frontmatter(
            "Vercel Helper",
            "Deploy web apps.",
            "capabilities:\n  - deploy.vercel\n",
        ),
    )
    _write_skill(
        skills_root,
        "netlify-helper",
        _frontmatter(
            "Netlify Helper",
            "Deploy static sites.",
            "capabilities:\n  - deploy.netlify\n",
        ),
    )

    result = route_prompt(
        prompt="Need a preview deployment for this app before merge.",
        grade="L",
        task_type="coding",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    expected_gap = round(result["ranked"][0]["score"] - result["ranked"][1]["score"], 4)
    assert result["candidate_focus"]["skill"] == "vercel-helper"
    assert result["top1_top2_gap"] == expected_gap
    assert result["candidate_focus"]["top1_top2_gap"] == expected_gap


def test_local_router_does_not_auto_route_when_top_gap_is_below_threshold(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    common_frontmatter = "capabilities:\n  - quality.test_report\n"
    _write_skill(
        skills_root,
        "test-report-alpha",
        _frontmatter(
            "Test Report Alpha",
            "Summarize pytest coverage pass fail rollups.",
            common_frontmatter,
        ),
    )
    _write_skill(
        skills_root,
        "test-report-beta",
        _frontmatter(
            "Test Report Beta",
            "Summarize pytest coverage pass fail rollups.",
            common_frontmatter,
        ),
    )

    result = route_prompt(
        prompt="Package pass/fail rollups and coverage summaries for this pytest run.",
        grade="L",
        task_type="coding",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["top1_top2_gap"] == 0.0
    assert result["route_reason"] == "candidate_signal_host_selection"
    assert "confirm_required" not in result
    assert result["candidate_focus"]["skill"] == "test-report-alpha"


def test_local_router_allows_explicit_existing_skill_and_rejects_absent_old_skill(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    skill_path = _write_skill(
        skills_root,
        "fresh-local-skill",
        _frontmatter("Fresh Local Skill", "A local skill that never existed in old pack lists."),
    )

    selected = route_prompt(
        prompt="Use the local workflow.",
        grade="M",
        task_type="planning",
        requested_skill="fresh-local-skill",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )
    missing = route_prompt(
        prompt="Use manuscript-as-code.",
        grade="M",
        task_type="planning",
        requested_skill="manuscript-as-code",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert selected["candidate_focus"]["skill"] == "fresh-local-skill"
    assert selected["candidate_focus"]["skill_entrypoint"] == str(skill_path.resolve())
    assert missing["candidate_focus"] is None
    assert missing["route_reason"] == "requested_local_skill_not_found"
    assert "manuscript-as-code" in missing["rejected_specialist_reasons"]


def test_local_router_does_not_fallback_when_no_local_candidate_matches(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(skills_root, "spreadsheet-cleanup", _frontmatter("Spreadsheet Cleanup", "Clean spreadsheet columns."))

    result = route_prompt(
        prompt="Prepare a quantum compiler proof for superconducting qubit pulse schedules.",
        grade="XL",
        task_type="research",
        target_root=str(skills_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"] is None
    assert result["route_mode"] == "no_local_candidate"
    assert result["route_reason"] == "no_local_candidate_above_threshold"
    assert result["ranked"][0]["skill"] == "spreadsheet-cleanup"
    assert result["ranked"][0]["selected_candidate"] is None
    assert "confirm_required" not in result
    assert "confirm_options" not in result
    assert "confirm_ui" not in result


def test_local_router_augments_sparse_chinese_research_prompts_before_scoring(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "research",
        _frontmatter(
            "Research",
            "Investigate research questions, compare sources, and synthesize literature reviews.",
        ),
    )
    _write_skill(
        skills_root,
        "humanizer",
        _frontmatter(
            "Humanizer",
            "Edit writing to sound more natural, plain-language, and human-written.",
        ),
    )

    result = route_prompt(
        prompt="脓毒症 公共数据库 研究综述 浅显易懂 去AI味",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["route_mode"] == "local_skill_overlay"
    assert result["candidate_focus"] is not None
    assert any(
        row["skill"] == "research" and float(row["score"]) > 0.0
        for row in result["ranked"]
    )
    assert any(
        row["skill"] == "humanizer" and float(row["score"]) > 0.0
        for row in result["ranked"]
    )


def test_local_router_selects_architecture_bundle_from_generic_engineering_skill_descriptions(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "domain-modeling",
        _frontmatter(
            "domain-modeling",
            "Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model.",
        ),
    )
    _write_skill(
        skills_root,
        "codebase-design",
        _frontmatter(
            "codebase-design",
            "Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.",
        ),
    )
    _write_skill(
        skills_root,
        "prototype",
        _frontmatter(
            "prototype",
            "Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whether a state model or logic feels right, or explore what a UI should look like.",
        ),
    )
    _write_skill(
        skills_root,
        "to-prd",
        _frontmatter(
            "to-prd",
            "Turn the current conversation into a PRD and publish it to the project issue tracker.",
        ),
    )
    _write_skill(
        skills_root,
        "to-issues",
        _frontmatter(
            "to-issues",
            "Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices.",
        ),
    )
    _write_skill(
        skills_root,
        "implement",
        _frontmatter(
            "implement",
            "Implement a piece of work based on a PRD or set of issues.",
        ),
    )

    result = route_prompt(
        prompt="接手一个已经变得臃肿的 Python 服务：先抽象领域模型和边界，再重设计模块接口，做一个小型原型验证，再把方案整理成 PRD 和可拆分 issues。",
        grade="XL",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "domain-modeling" in selected_ids
    assert "codebase-design" in selected_ids
    assert "prototype" in selected_ids
    assert "to-prd" in selected_ids
    assert "to-issues" in selected_ids
    assert result["candidate_focus"]["skill"] != "implement"


def test_local_router_splits_artifact_delivery_and_model_training_for_game_plus_ml_prompt(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "implement",
        _frontmatter(
            "implement",
            "Implement a piece of work based on a PRD or set of issues.",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "用于 Python scikit-learn 机器学习，包括分类、回归、聚类、降维、预处理、pipeline、防数据泄漏、交叉验证、模型评估和超参调优。关键词：scikit-learn, model selection。",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "用于把 Python、NumPy、pandas、scikit-learn、图像、图、地理、向量检索或科学计算任务迁移到 GPU/CUDA 加速，涉及 CuPy、Numba、cuDF、cuML、cuGraph 等。关键词：GPU optimization, CUDA。",
        ),
        "# Intent\n\n- User is doing machine learning (training, inference, hyperparameter tuning, preprocessing)\n",
    )

    result = route_prompt(
        prompt="做一个贪吃蛇游戏，再训练一个机器学习模型，让它学会玩贪吃蛇，并给我一个可运行演示。",
        grade="L",
        task_type="planning",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    required_capabilities = result["task_card"]["required_capabilities"]
    assert "runtime.feature_delivery" in required_capabilities
    assert "model.training" in required_capabilities
    assert len(result["task_card"]["modules"]) >= 2

    assert result["route_reason"] == "composite_module_confirm_override"
    assert "confirm_required" not in result
    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "implement" in selected_ids
    assert "scikit-learn" in selected_ids
    assert result["candidate_focus"]["skill"] == "implement"


def test_local_router_uses_earliest_module_owner_as_primary_for_architecture_bundle(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "domain-modeling",
        _frontmatter(
            "domain-modeling",
            "Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language.",
        ),
    )
    _write_skill(
        skills_root,
        "codebase-design",
        _frontmatter(
            "codebase-design",
            "Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface.",
        ),
    )
    _write_skill(
        skills_root,
        "prototype",
        _frontmatter(
            "prototype",
            "Build a throwaway prototype to answer a design question.",
        ),
    )
    _write_skill(
        skills_root,
        "to-prd",
        _frontmatter(
            "to-prd",
            "Turn the current conversation into a PRD and publish it to the project issue tracker.",
        ),
    )
    _write_skill(
        skills_root,
        "to-issues",
        _frontmatter(
            "to-issues",
            "Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices.",
        ),
    )

    result = route_prompt(
        prompt="接手一个已经变得臃肿的 Python 服务：先抽象领域模型和边界，再重设计模块接口，做一个小型原型验证，再把方案整理成 PRD 和可拆分 issues。",
        grade="XL",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"]["skill"] == "domain-modeling"
    assert result["skill_routing"]["primary_candidate_skill"] == "domain-modeling"


def test_local_router_prefers_direct_prd_owner_over_review_support_owner_inside_prd_module(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "to-prd",
        _frontmatter(
            "to-prd",
            "Turn the current conversation into a PRD and publish it to the project issue tracker.",
        ),
    )
    _write_skill(
        skills_root,
        "code-review",
        _frontmatter(
            "code-review",
            "Review the changes since a fixed point and compare the result against the originating issue, PRD, or spec. Use when the user asks for review work.",
        ),
    )
    _write_skill(
        skills_root,
        "to-issues",
        _frontmatter(
            "to-issues",
            "Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices.",
        ),
    )

    result = route_prompt(
        prompt="把现在已经讨论清楚的方案整理成 PRD，再拆成可执行 issues。",
        grade="XL",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_candidates = {
        row["module_id"]: row["candidates"]
        for row in result["skill_routing"]["module_candidates"]
    }

    assert module_candidates["planning.prd"][0]["skill"] == "to-prd"
    assert module_candidates["planning.prd"][0]["evidence"][0]["role"] == "applicable"
    assert all(candidate["skill"] != "code-review" for candidate in module_candidates["planning.prd"][1:])


def test_local_router_allows_l_routes_to_surface_multiple_reader_facing_skills(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "deep-reading-analyst",
        _frontmatter(
            "deep-reading-analyst",
            "Comprehensive framework for deep analysis of articles, papers, and long-form content. Use when users want to deeply understand complex articles, analyze arguments, extract insights, compare sources, or create study notes.",
        ),
    )
    _write_skill(
        skills_root,
        "first-principles-explorer",
        _frontmatter(
            "first-principles-explorer",
            "用于从第一性原理重新理解问题，穿透表面答案、澄清真实问题、挑战隐藏假设、追溯根因或在行动前重定义模糊主题。",
        ),
    )
    _write_skill(
        skills_root,
        "qu-ai-wei",
        _frontmatter(
            "qu-ai-wei",
            "用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )

    result = route_prompt(
        prompt="精读一份很长的技术 RFC 和配套设计文档，提炼核心论证和隐藏假设，用第一性原理挑战方案，再输出一份给中文团队看的说人话决策备忘录。",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "deep-reading-analyst" in selected_ids
    assert "first-principles-explorer" in selected_ids
    assert "qu-ai-wei" in selected_ids
    assert "diagnose" not in selected_ids


def test_local_router_selects_manuscript_review_audit_and_chinese_humanization_bundle(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "sciwrite",
        _frontmatter(
            "manuscript-writing-review",
            "用于审阅、编辑和提升科学或工程论文写作质量，改善清晰度、逻辑、段落、术语和学术表达；用户要求 manuscript review、论文润色时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "scientific-critical-thinking",
        _frontmatter(
            "scientific-critical-thinking",
            "用于评估科学主张、证据质量、实验设计、偏倚、混杂因素和方法学严谨性；做科研建模审计、实验设计检查或证据分级时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "用于统计分析指导、检验选择、假设检查、功效分析和结果报告；需要为数据选择合适统计方法或写学术统计结论时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "qu-ai-wei",
        _frontmatter(
            "qu-ai-wei",
            "用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "用于 Python scikit-learn 机器学习，包括分类、回归、聚类、降维、预处理、pipeline、防数据泄漏、交叉验证、模型评估和超参调优。",
        ),
    )

    result = route_prompt(
        prompt="审阅一篇已有的医学机器学习论文草稿：检查实验设计和统计方法是否站得住脚，指出证据薄弱处，重写摘要和讨论，让中文表达更像真人。",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "sciwrite" in selected_ids
    assert "scientific-critical-thinking" in selected_ids
    assert "qu-ai-wei" in selected_ids
    assert "scikit-learn" not in selected_ids


def test_local_router_composes_multimodule_route_from_module_candidates_not_skill_id_anchors(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "source-digger",
        _frontmatter(
            "source-digger",
            "Search primary literature and PubMed evidence.",
            "capabilities:\n  - research.literature_search\n",
        ),
    )
    _write_skill(
        skills_root,
        "helpful-briefer",
        _frontmatter(
            "helpful-briefer",
            "Turn technical material into plain-language summaries for ordinary readers.",
            "capabilities:\n  - writing.reader_report\n",
        ),
    )
    _write_skill(
        skills_root,
        "slide-craft",
        _frontmatter(
            "slide-craft",
            "Prepare presentation slides and deck outputs.",
            "capabilities:\n  - presentation.deck\n",
        ),
    )

    result = route_prompt(
        prompt="先检索 PubMed 和 primary literature，再写一份给普通读者看的通俗 brief，最后整理成 slides。",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    module_candidates = {
        row["module_id"]: [candidate["skill"] for candidate in row["candidates"]]
        for row in result["skill_routing"]["module_candidates"]
    }

    assert "source-digger" in selected_ids
    assert "helpful-briefer" in selected_ids
    assert "slide-craft" in selected_ids
    assert module_candidates["research.literature_search"][0] == "source-digger"
    assert module_candidates["writing.reader_report"][0] == "helpful-briefer"
    assert module_candidates["presentation.deck"][0] == "slide-craft"
    assert result["skill_routing"]["uncovered_modules"] == []


def test_local_router_reports_uncovered_modules_when_the_local_corpus_has_a_real_gap(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "source-digger",
        _frontmatter(
            "source-digger",
            "Search primary literature and PubMed evidence.",
            "capabilities:\n  - research.literature_search\n",
        ),
    )
    _write_skill(
        skills_root,
        "helpful-briefer",
        _frontmatter(
            "helpful-briefer",
            "Turn technical material into plain-language summaries for ordinary readers.",
            "capabilities:\n  - writing.reader_report\n",
        ),
    )

    result = route_prompt(
        prompt="先检索 PubMed 和 primary literature，再写一份给普通读者看的通俗 brief，最后整理成 slides。",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    uncovered_ids = [row["module_id"] for row in result["skill_routing"]["uncovered_modules"]]

    assert "source-digger" in selected_ids
    assert "helpful-briefer" in selected_ids
    assert "presentation.deck" in uncovered_ids


def test_local_router_extracts_frontend_preview_and_test_report_modules_from_composite_delivery_prompt(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "frontend-builder",
        _frontmatter(
            "frontend-builder",
            "Build React and Next.js frontends, dashboard pages, and app UI flows.",
        ),
    )

    result = route_prompt(
        prompt="做一个可用的数据看板前端，接着部署 preview，再根据 pytest 和 coverage 输出生成测试报告",
        grade="XL",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_ids = [row["module_id"] for row in result["task_card"]["modules"]]

    assert module_ids == ["frontend.build", "deploy.preview", "quality.test_report"]
    assert result["task_card"]["required_capabilities"] == [
        "frontend.build",
        "deploy.preview",
        "quality.test_report",
    ]


def test_local_router_routes_frontend_preview_and_report_bundle_from_direct_module_owners(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "frontend-builder",
        _frontmatter(
            "frontend-builder",
            "Build React and Next.js frontends, dashboard pages, and app UI flows.",
        ),
    )
    _write_skill(
        skills_root,
        "preview-ship",
        _frontmatter(
            "preview-ship",
            "Use for preview deployment workflows on Vercel or Netlify before merge.",
        ),
    )
    _write_skill(
        skills_root,
        "test-report-brief",
        _frontmatter(
            "test-report-brief",
            "Summarize pytest runs, coverage summaries, and pass/fail rollups into a test report.",
        ),
    )

    result = route_prompt(
        prompt="做一个可用的数据看板前端，接着部署 preview，再根据 pytest 和 coverage 输出生成测试报告",
        grade="XL",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    module_candidates = {
        row["module_id"]: [candidate["skill"] for candidate in row["candidates"]]
        for row in result["skill_routing"]["module_candidates"]
    }

    assert result["candidate_focus"]["skill"] == "frontend-builder"
    assert result["skill_routing"]["primary_candidate_skill"] == "frontend-builder"
    assert selected_ids == ["frontend-builder", "preview-ship", "test-report-brief"]
    assert module_candidates["frontend.build"][0] == "frontend-builder"
    assert module_candidates["deploy.preview"][0] == "preview-ship"
    assert module_candidates["quality.test_report"][0] == "test-report-brief"
    assert result["skill_routing"]["uncovered_modules"] == []


def test_local_router_does_not_auto_select_explicit_only_frontend_style_skill_for_generic_frontend_work(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "design-taste-frontend",
        _frontmatter(
            "design-taste-frontend",
            "Specialized niche workflow. Use only when the user explicitly asks for it.",
        ),
        "# Usage\n\nBuild high-agency React and Next.js frontends.\n",
    )

    result = route_prompt(
        prompt="做一个可用的数据看板前端",
        grade="L",
        task_type="coding",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"] is None
    assert result["route_reason"] == "no_local_candidate_above_threshold"
    assert result["skill_routing"]["uncovered_modules"] == []
    assert result["skill_routing"]["module_candidates"][0]["candidates"][0]["skill"] == "design-taste-frontend"


def test_local_router_does_not_promote_below_threshold_explicit_only_module_candidate_into_selected_stack(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "Use when debugging hard bugs, failing tests, stack traces, and slow pages.",
            "capabilities:\n  - debug.systematic_workflow\n  - performance.regression_debugging\n",
        ),
    )
    _write_skill(
        skills_root,
        "design-taste-frontend",
        _frontmatter(
            "design-taste-frontend",
            "Specialized niche workflow. Use only when the user explicitly asks for it.",
        ),
        "# Usage\n\nBuild high-agency React and Next.js frontends.\n",
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert result["candidate_focus"]["skill"] == "diagnose"
    assert selected_ids == ["diagnose"]
    assert "frontend.build" not in result["task_card"]["required_capabilities"]
    assert [row["module_id"] for row in result["skill_routing"]["uncovered_modules"]] == []


def test_local_router_does_not_let_humanization_support_claim_reader_report_module(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "helpful-briefer",
        _frontmatter(
            "helpful-briefer",
            "Turn technical material into plain-language summaries for ordinary readers.",
            "capabilities:\n  - writing.reader_report\n",
        ),
    )
    _write_skill(
        skills_root,
        "qu-ai-wei",
        _frontmatter(
            "qu-ai-wei",
            "用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。",
        ),
    )

    result = route_prompt(
        prompt="把这份技术材料改成给普通读者看的通俗 brief。",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_candidates = {
        row["module_id"]: row["candidates"]
        for row in result["skill_routing"]["module_candidates"]
    }
    reader_candidates = module_candidates["writing.reader_report"]

    assert reader_candidates[0]["skill"] == "helpful-briefer"
    assert all(candidate["skill"] != "qu-ai-wei" for candidate in reader_candidates)


def test_local_router_module_candidates_surface_applicable_evidence_snippets(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "source-digger",
        _frontmatter(
            "source-digger",
            "Search the literature for high-trust sources.",
        ),
        (
            "# Source Digger\n\n"
            "Use this skill for PubMed and primary literature search.\n"
        ),
    )
    _write_skill(
        skills_root,
        "helpful-briefer",
        _frontmatter(
            "helpful-briefer",
            "Turn technical material into plain-language summaries for ordinary readers.",
            "capabilities:\n  - writing.reader_report\n",
        ),
    )

    result = route_prompt(
        prompt="先检索 PubMed 和 primary literature，再写一份给普通读者看的通俗 brief。",
        grade="L",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_candidates = {
        row["module_id"]: row["candidates"]
        for row in result["skill_routing"]["module_candidates"]
    }
    evidence = module_candidates["research.literature_search"][0]["evidence"]

    assert evidence
    assert evidence[0]["role"] == "applicable"
    assert "PubMed and primary literature search" in evidence[0]["text"]
    assert evidence[0]["line_start"] >= 1
    assert evidence[0]["line_end"] >= evidence[0]["line_start"]


def test_local_router_prefers_applicable_route_evidence_over_example_only_deck_hits(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "deck-archive",
        _frontmatter(
            "deck-archive",
            "Archive of old presentation decks.",
            "capabilities:\n  - presentation.deck\n",
        ),
        (
            "# Deck Archive\n\n"
            "## Examples\n\n"
            "- Example: rebuild an old slides deck after the fact.\n"
        ),
    )
    _write_skill(
        skills_root,
        "workshop-helper",
        _frontmatter(
            "workshop-helper",
            "General workshop support.",
            "capabilities:\n  - presentation.deck\n",
        ),
        (
            "# Workshop Helper\n\n"
            "Use this skill for presentation slides and deck outputs.\n"
        ),
    )

    result = route_prompt(
        prompt="Prepare presentation slides and a short deck for the workshop update.",
        grade="L",
        task_type="planning",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_candidates = {
        row["module_id"]: row["candidates"]
        for row in result["skill_routing"]["module_candidates"]
    }

    assert result["candidate_focus"]["skill"] == "workshop-helper"
    assert module_candidates["presentation.deck"][0]["skill"] == "workshop-helper"
    assert module_candidates["presentation.deck"][0]["evidence"][0]["role"] == "applicable"
    assert module_candidates["presentation.deck"][1]["skill"] == "deck-archive"
    assert module_candidates["presentation.deck"][1]["evidence"][0]["role"] == "example"


def test_local_router_prefers_cv_analysis_and_figures_over_map_token_noise(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "senior-computer-vision",
        _frontmatter(
            "senior-computer-vision",
            "用于计算机视觉工程和建模，包括目标检测、图像分割、CNN/ViT、YOLO、Faster R-CNN、DETR、Mask R-CNN、SAM、训练策略、mAP 指标和部署优化。",
        ),
    )
    _write_skill(
        skills_root,
        "scientific-visualization",
        _frontmatter(
            "scientific-visualization",
            "Meta-skill for publication-ready figures. Use when creating journal submission figures requiring multi-panel layouts, significance annotations, error bars, colorblind-safe palettes, and journal formatting.",
        ),
    )
    _write_skill(
        skills_root,
        "scientific-critical-thinking",
        _frontmatter(
            "scientific-critical-thinking",
            "用于评估科学主张、证据质量、实验设计、偏倚、混杂因素和方法学严谨性；做科研建模审计、实验设计检查或证据分级时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "context-keeper",
        _frontmatter(
            "context-keeper",
            "用于长任务、上下文压缩、继续/恢复、跨会话跟进和关键决策留痕；当用户说继续、resume、担心遗忘或需要持久项目记忆时使用。",
        ),
    )

    result = route_prompt(
        prompt="分析一个目标检测项目为什么小目标 mAP 很差：需要从误检漏检模式、数据标注、训练策略和评估口径找原因，最后整理成图和技术结论。",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert result["candidate_focus"]["skill"] == "senior-computer-vision"
    assert "scientific-visualization" in selected_ids
    assert "context-keeper" not in selected_ids


def test_local_router_selects_debug_training_and_gpu_migration_for_cpu_bound_pipeline_prompt(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "用于 Python scikit-learn 机器学习，包括分类、回归、聚类、降维、预处理、pipeline、防数据泄漏、交叉验证、模型评估和超参调优。",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "用于把 Python、NumPy、pandas、scikit-learn、图像、图、地理、向量检索或科学计算任务迁移到 GPU/CUDA 加速，涉及 CuPy、Numba、cuDF、cuML、cuGraph 等。",
        ),
    )
    _write_skill(
        skills_root,
        "hyperparameter-composite-search",
        _frontmatter(
            "hyperparameter-composite-search",
            "用于设计或审计复杂超参数搜索，重点防止搜索空间自相矛盾、训练参数前后不吻合、缓存把磁盘撑爆，以及 CPU 高占用但 GPU 吃不满的伪并行。",
        ),
    )

    result = route_prompt(
        prompt="排查一个本地 pandas + scikit-learn 分析流水线为什么又慢又吃 CPU：先区分是算法问题还是工程实现问题，再判断哪些步骤值得迁移到 GPU，并给出验证计划。",
        grade="XL",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    assert "diagnose" in selected_ids
    assert "scikit-learn" in selected_ids
    assert "optimize-for-gpu" in selected_ids


def test_local_router_uses_earliest_module_owner_as_primary_for_cpu_gpu_triage(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "用于 Python scikit-learn 机器学习，包括分类、回归、聚类、降维、预处理、pipeline、防数据泄漏、交叉验证、模型评估和超参调优。",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "用于把 Python、NumPy、pandas、scikit-learn、图像、图、地理、向量检索或科学计算任务迁移到 GPU/CUDA 加速，涉及 CuPy、Numba、cuDF、cuML、cuGraph 等。",
        ),
    )

    result = route_prompt(
        prompt="排查一个本地 pandas + scikit-learn 分析流水线为什么又慢又吃 CPU：先区分是算法问题还是工程实现问题，再判断哪些步骤值得迁移到 GPU，并给出验证计划。",
        grade="XL",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    assert result["candidate_focus"]["skill"] == "diagnose"
    assert result["skill_routing"]["primary_candidate_skill"] == "diagnose"


def test_local_router_prefers_direct_training_owner_over_gpu_support_owner_inside_training_module(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Use when training scikit-learn baselines and validating classic ML pipelines.",
            "capabilities:\n  - model.training\n",
        ),
        (
            "# Scikit Learn\n\n"
            "Use this skill for training baseline models, cross-validation, and model evaluation.\n"
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "Use when migrating existing Python and scikit-learn workloads onto GPU/CUDA acceleration.",
            "capabilities:\n  - model.training\n  - performance.gpu_migration\n",
        ),
        (
            "# Optimize for GPU\n\n"
            "Use this skill for GPU migration, CUDA acceleration, and throughput tuning after a workload already exists.\n"
        ),
    )
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "Use when debugging slow pipelines and isolating root causes.",
            "capabilities:\n  - debug.systematic_workflow\n",
        ),
    )

    result = route_prompt(
        prompt="排查一个本地 pandas + scikit-learn 分析流水线为什么又慢又吃 CPU：先区分是算法问题还是工程实现问题，再判断哪些步骤值得迁移到 GPU，并给出验证计划。",
        grade="XL",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    module_candidates = {
        row["module_id"]: row["candidates"]
        for row in result["skill_routing"]["module_candidates"]
    }

    assert module_candidates["model.training"][0]["skill"] == "scikit-learn"
    assert module_candidates["performance.gpu_migration"][0]["skill"] == "optimize-for-gpu"


def test_local_router_hides_zero_signal_tail_when_meaningful_candidates_exist(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "scikit-learn",
        _frontmatter(
            "scikit-learn",
            "Use when training machine learning baselines with scikit-learn.",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "Use when migrating Python and scikit-learn workloads onto GPU/CUDA acceleration.",
        ),
    )
    _write_skill(
        skills_root,
        "accelerate",
        _frontmatter(
            "accelerate",
            "Distributed training helper.",
        ),
    )
    _write_skill(
        skills_root,
        "algernom-building-analysis-pools",
        _frontmatter(
            "algernom-building-analysis-pools",
            "Use when the user explicitly asks for the Algernom analysis-pool workflow.",
        ),
    )

    result = route_prompt(
        prompt="训练模型",
        grade="L",
        task_type="planning",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked_ids = [row["skill"] for row in result["ranked"]]
    assert "scikit-learn" in ranked_ids
    assert "optimize-for-gpu" in ranked_ids
    assert "accelerate" not in ranked_ids
    assert "algernom-building-analysis-pools" not in ranked_ids


def test_local_router_prefers_primary_source_research_stack_for_public_db_review_bundle(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "research",
        _frontmatter(
            "research",
            "Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.",
        ),
    )
    _write_skill(
        skills_root,
        "paper-writer",
        _frontmatter(
            "paper-writer",
            "Medical/scientific paper writing workflow skill. Manages the full pipeline from literature search to submission-ready manuscript.",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "用于统计分析指导、检验选择、假设检查、功效分析和结果报告；需要为数据选择合适统计方法或写学术统计结论时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "qu-ai-wei",
        _frontmatter(
            "qu-ai-wei",
            "用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "pptx-collab-integrated",
        _frontmatter(
            "pptx-collab-integrated",
            "Specialized niche workflow for dense PPT collaboration and deck editing.",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "用于把 Python、NumPy、pandas、scikit-learn、图像、图、地理、向量检索或科学计算任务迁移到 GPU/CUDA 加速。",
        ),
    )
    _write_skill(
        skills_root,
        "algernom-building-problem-pools",
        _frontmatter(
            "algernom-building-problem-pools",
            "Use when a kept journal pool already exists and the next step is to decide which dry-lab opening questions that journal set repeatedly rewards in the target field.",
        ),
    )

    result = route_prompt(
        prompt="做脓毒症公共数据库研究：检索 full-text 文献，提取样本量和 effect size，做统计比较，再写通俗综述并整理成汇报",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    ranked_ids = [row["skill"] for row in result["ranked"]]
    uncovered_ids = [row["module_id"] for row in result["skill_routing"]["uncovered_modules"]]
    assert "research" in selected_ids
    assert "statistical-analysis" in selected_ids
    assert "pptx-collab-integrated" in selected_ids
    assert "qu-ai-wei" not in selected_ids
    assert "qu-ai-wei" not in ranked_ids
    assert "writing.reader_report" in uncovered_ids
    assert "optimize-for-gpu" not in ranked_ids
    assert "algernom-building-problem-pools" not in ranked_ids


def test_local_router_shows_only_close_debug_alternatives_in_perf_regression_shortlist(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )
    _write_skill(
        skills_root,
        "diagnosing-bugs",
        _frontmatter(
            "diagnosing-bugs",
            "Diagnosis loop for hard bugs and performance regressions. Use when the user says diagnose/debug, or reports something broken/throwing/failing/slow.",
        ),
    )
    _write_skill(
        skills_root,
        "tdd",
        _frontmatter(
            "tdd",
            "Test-driven development. Use when the user wants to build features or fix bugs test-first.",
        ),
    )
    _write_skill(
        skills_root,
        "deepspeed",
        _frontmatter(
            "deepspeed",
            "Specialized niche workflow. Use only when the user explicitly asks for it.",
        ),
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked_ids = [row["skill"] for row in result["ranked"]]
    assert ranked_ids[:2] == ["diagnose", "diagnosing-bugs"]
    assert "tdd" not in ranked_ids
    assert "deepspeed" not in ranked_ids


def test_local_router_ignores_explicit_only_debug_docs_in_perf_shortlist(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )
    _write_skill(
        skills_root,
        "deepspeed",
        _frontmatter(
            "deepspeed",
            "Specialized niche workflow. Use only when the user explicitly asks for it.",
        ),
        """# Deepspeed Skill

## When to Use This Skill

This skill should be triggered when:
- Working with deepspeed
- Asking about deepspeed features or APIs
- Implementing deepspeed solutions
- Debugging deepspeed code
""",
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked_ids = [row["skill"] for row in result["ranked"]]
    assert ranked_ids[0] == "diagnose"
    assert "deepspeed" not in ranked_ids


def test_local_router_does_not_promote_body_text_collisions_into_public_db_review_shortlist(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "research",
        _frontmatter(
            "research",
            "Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "用于统计分析指导、检验选择、假设检查、功效分析和结果报告；需要为数据选择合适统计方法或写学术统计结论时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "qu-ai-wei",
        _frontmatter(
            "qu-ai-wei",
            "用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。",
        ),
    )
    _write_skill(
        skills_root,
        "pptx-collab-integrated",
        _frontmatter(
            "pptx-collab-integrated",
            "Specialized niche workflow for dense PPT collaboration and deck editing.",
        ),
    )
    _write_skill(
        skills_root,
        "optimize-for-gpu",
        _frontmatter(
            "optimize-for-gpu",
            "用于把 Python、NumPy、pandas、scikit-learn、图像、图、地理、向量检索或科学计算任务迁移到 GPU/CUDA 加速，涉及 CuPy、Numba、cuDF、cuML、cuGraph 等。",
        ),
        """# GPU Optimization for Python with NVIDIA

## When This Skill Applies

- User is doing graph analytics (centrality, community detection, shortest paths, PageRank, etc.)
- User is working with whole-slide images (WSI), digital pathology, microscopy, or remote sensing imagery
- User needs mesh operations (ray casting, closest-point queries, signed distance fields) or geometry processing on GPU
""",
    )
    _write_skill(
        skills_root,
        "algernom-building-problem-pools",
        _frontmatter(
            "algernom-building-problem-pools",
            "Use when a kept journal pool already exists and the next step is to decide which dry-lab opening questions that journal set repeatedly rewards in the target field.",
        ),
        """# Algernom: Building Problem Pools

## Activation Gate

Formal problem-pool construction is allowed only when one of these is true:

- the user explicitly names this skill

## When to Use

Use this skill when:

- the upstream journal pool has already been screened and kept

Do not use this skill for:

- generic literature review with no downstream publication strategy
""",
    )

    result = route_prompt(
        prompt="做脓毒症公共数据库研究：检索 full-text 文献，提取样本量和 effect size，做统计比较，再写通俗综述并整理成汇报",
        grade="XL",
        task_type="research",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    selected_ids = [row["skill"] for row in result["skill_routing"]["focused_candidates"]]
    ranked_ids = [row["skill"] for row in result["ranked"]]
    uncovered_ids = [row["module_id"] for row in result["skill_routing"]["uncovered_modules"]]
    assert "research" in selected_ids
    assert "statistical-analysis" in selected_ids
    assert "pptx-collab-integrated" in selected_ids
    assert "qu-ai-wei" not in selected_ids
    assert "qu-ai-wei" not in ranked_ids
    assert "writing.reader_report" in uncovered_ids
    assert "optimize-for-gpu" not in ranked_ids
    assert "algernom-building-problem-pools" not in ranked_ids


def test_local_router_hides_low_signal_root_cause_lexical_tail_in_perf_shortlist(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agent_root = home / ".agents"
    skills_root = agent_root / "skills"
    _write_skill(
        skills_root,
        "diagnose",
        _frontmatter(
            "diagnose",
            "用于困难 bug、性能回退和复杂异常的纪律化诊断；当用户说 diagnose/debug、报告 broken、throwing、failing 或性能变差时，按复现、最小化、假设、插桩、修复、回归测试推进。",
        ),
    )
    _write_skill(
        skills_root,
        "diagnosing-bugs",
        _frontmatter(
            "diagnosing-bugs",
            "Diagnosis loop for hard bugs and performance regressions. Use when the user says diagnose/debug, or reports something broken/throwing/failing/slow.",
        ),
    )
    _write_skill(
        skills_root,
        "first-principles-explorer",
        _frontmatter(
            "first-principles-explorer",
            "用于从第一性原理重新理解问题，穿透表面答案、澄清真实问题、挑战隐藏假设、追溯根因或在行动前重定义模糊主题。关键词：first principles, root cause, assumption。",
        ),
    )
    _write_skill(
        skills_root,
        "statistical-analysis",
        _frontmatter(
            "statistical-analysis",
            "用于统计分析指导、检验选择、假设检查、功效分析和结果报告；需要为数据选择合适统计方法或写学术统计结论时使用。关键词：statistical test, power analysis。",
        ),
        """# Statistical Analysis

# Core frequentist stack
""",
    )

    result = route_prompt(
        prompt="React 前端性能回归，点击筛选后页面卡顿并伴随 failing test 和 stack trace，请系统排查 root cause",
        grade="L",
        task_type="debug",
        target_root=str(agent_root),
        host_id="codex",
        repo_root=REPO_ROOT,
    )

    ranked_ids = [row["skill"] for row in result["ranked"]]
    assert ranked_ids == ["diagnose", "diagnosing-bugs"]
