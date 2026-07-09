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
    assert index["skills"][0]["native_skill_entrypoint"] == str(skill_path.resolve())
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

    assert [row["native_skill_entrypoint"] for row in rows] == [
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
    assert result["selected"]["skill"] == "sleep-stress-focus"
    assert result["selected"]["native_skill_entrypoint"] == str(skill_path.resolve())
    assert result["selected"]["pack_id"] == "local-skill-index"
    assert result["ranked"][0]["candidate_source"] == "local_skill_index"
    assert result["ranked"][0]["native_skill_entrypoint"] == str(skill_path.resolve())


def test_local_router_offers_confirm_for_plausible_local_near_match(tmp_path: Path) -> None:
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
    assert result["confirm_required"] is True
    assert result["selected"]["skill"] == "sleep-stress-focus"
    assert result["confirm_options"][0]["skill"] == "sleep-stress-focus"
    assert result["confirm_options"][0]["native_skill_entrypoint"] == str(skill_path.resolve())


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

    assert result["route_reason"] in {"candidate_signal_host_selection", "candidate_signal_confirm_override"}
    assert result["confirm_required"] is True
    assert result["selected"]["skill"] == "vercel-helper"
    assert result["confirm_options"][0]["skill"] == "vercel-helper"
    assert result["confirm_options"][0]["native_skill_entrypoint"] == str(skill_path.resolve())


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

    assert result["route_reason"] in {"candidate_signal_host_selection", "candidate_signal_confirm_override"}
    assert result["confirm_required"] is True
    assert result["selected"]["skill"] == "managed-release-helper"
    assert result["confirm_options"][0]["skill"] == "managed-release-helper"
    assert result["confirm_options"][0]["native_skill_entrypoint"] == str(skill_path.resolve())


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

    assert result["selected"] is None
    assert result["route_reason"] == "no_local_candidate_above_threshold"
    assert result["top1_top2_gap"] == 0.0
    assert result["confirm_required"] is False
    assert result["confirm_options"] == []


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
    assert result["selected"]["skill"] == "vercel-helper"
    assert result["top1_top2_gap"] == expected_gap
    assert result["selected"]["top1_top2_gap"] == expected_gap


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
    assert result["confirm_required"] is True
    assert result["selected"]["skill"] == "test-report-alpha"


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

    assert selected["selected"]["skill"] == "fresh-local-skill"
    assert selected["selected"]["native_skill_entrypoint"] == str(skill_path.resolve())
    assert missing["selected"] is None
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

    assert result["selected"] is None
    assert result["route_mode"] == "no_local_candidate"
    assert result["route_reason"] == "no_local_candidate_above_threshold"
    assert result["ranked"][0]["skill"] == "spreadsheet-cleanup"
    assert result["ranked"][0]["selected_candidate"] is None
    assert result["confirm_required"] is False
    assert result["confirm_options"] == []
    assert "confirm_ui" not in result
