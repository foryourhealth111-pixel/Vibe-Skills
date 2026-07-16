from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime import router_contract_runtime
from vgo_runtime.kernel import skill_index
from vgo_runtime.kernel.capability_bridge import CAPABILITY_BRIDGE
from vgo_runtime.kernel.skill_index import build_skill_index, write_skill_index
from vgo_runtime.kernel.skill_manifest import parse_skill_manifest


def _write_skill(skill_dir: Path, frontmatter: str, body: str = "# Skill\n") -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(frontmatter + "\n" + body, encoding="utf-8")
    return skill_file


def test_parse_skill_manifest_reads_required_contract_fields(tmp_path: Path) -> None:
    skill_file = _write_skill(
        tmp_path / "skill-a",
        """---
id: code-review
name: Code Review
description: Review implementation risk.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
priority: 50
---""",
    )

    manifest = parse_skill_manifest(skill_file)

    assert manifest.id == "code-review"
    assert manifest.name == "Code Review"
    assert manifest.description == "Review implementation risk."
    assert manifest.when_to_use == ("The user asks for a review.",)
    assert manifest.not_for == ("Building a feature from scratch.",)
    assert manifest.inputs == ("changed files",)
    assert manifest.outputs == ("findings",)
    assert manifest.enabled is True
    assert manifest.priority == 50


def test_build_skill_index_collects_vibe_local_skills(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    skill_path = _write_skill(
        vibe_root / "skills" / "local" / "code-review",
        """---
name: Code Review
description: Review implementation risk.
tags:
  - review
  - testing
---""",
    )

    payload = build_skill_index(agent_root)
    index_path = write_skill_index(agent_root, payload)

    assert payload["schema_version"] == "local_skill_index_v2"
    assert payload["roots"] == ["skills/local"]
    assert payload["catalog_source_kinds"] == ["vibe_local"]
    assert payload["active_source_kinds"] == ["vibe_local"]
    assert [entry["skill_id"] for entry in payload["skills"]] == ["code-review"]
    assert payload["skills"][0]["display_name"] == "Code Review"
    assert payload["skills"][0]["source_kind"] == "vibe_local"
    assert payload["skills"][0]["skill_entrypoint"] == str(skill_path.resolve())
    assert payload["skills"][0]["tags"] == ["review", "testing"]
    assert index_path == vibe_root / "generated" / "skills-index.json"
    assert index_path.exists()


def test_build_skill_index_host_roots_precede_vibe_local_duplicates(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    host_root = tmp_path / "host-skills"
    vibe_root = agent_root / "vibe"
    host_skill = _write_skill(
        host_root / "duplicate-skill",
        """---
name: Host Duplicate Skill
description: The host-installed copy should stay active.
---""",
    )
    _write_skill(
        vibe_root / "skills" / "local" / "duplicate-skill",
        """---
name: Vibe Local Duplicate Skill
description: The Vibe local copy should stay inactive.
---""",
    )

    payload = build_skill_index(agent_root, host_roots=(host_root,))

    assert payload["roots"] == [str(host_root.resolve()), "skills/local"]
    assert [entry["skill_id"] for entry in payload["skills"]] == ["duplicate-skill"]
    assert payload["skills"][0]["display_name"] == "Host Duplicate Skill"
    assert payload["skills"][0]["source_kind"] == "host_installed"
    assert payload["skills"][0]["skill_entrypoint"] == str(host_skill.resolve())
    duplicate = payload["discovery_diagnostics"]["duplicates"][0]
    assert duplicate["skill_id"] == "duplicate-skill"
    assert duplicate["active_entrypoint"] == str(host_skill.resolve())


def test_build_skill_index_records_invalid_local_entries_without_activating_them(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "missing-description",
        """---
name: Missing Description
---""",
    )
    (vibe_root / "skills" / "local" / "missing-file").mkdir(parents=True)
    _write_skill(
        vibe_root / "skills" / "local" / "usable",
        """---
name: Usable
description: A real local skill.
---""",
    )

    payload = build_skill_index(agent_root)

    assert [entry["skill_id"] for entry in payload["skills"]] == ["usable"]
    reasons = {
        item["skill_id"]: item["reason"]
        for item in payload["discovery_diagnostics"]["invalid_entries"]
    }
    assert reasons["missing-description"] == "missing_required_frontmatter"
    assert reasons["missing-file"] == "missing_skill_md"


def test_build_skill_index_does_not_infer_capabilities_from_incidental_body_text(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "grant-writer",
        """---
name: Grant Writer
description: Draft research grant proposals and narrative sections.
---""",
        "# Grant Writer\n\nReviewers may ask whether supporting tables mention missing values, duplicate records, or outlier notes.\n",
    )

    payload = build_skill_index(agent_root)

    assert payload["skills"][0]["skill_id"] == "grant-writer"
    assert payload["skills"][0]["capabilities"] == []
    assert payload["skills"][0]["capability_evidence"] == []


def test_build_skill_index_keeps_metadata_only_weak_capabilities_out_of_route_active_capabilities(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "optimize-for-gpu",
        """---
name: Optimize For GPU
description: Speed up machine learning training on GPU.
---""",
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "optimize-for-gpu"
    assert "model.training" not in entry["capabilities"]
    assert any(
        row["capability"] == "model.training"
        and row["evidence_level"] == "weak_text"
        and row["source"] == "metadata_text"
        for row in entry["capability_evidence"]
    )


def test_build_skill_index_uses_named_when_to_use_sections_as_body_intent(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "scikit-learn",
        """---
name: scikit-learn
description: Classical ML helper.
---""",
        (
            "# Scikit-learn\n\n"
            "## When to Use This Skill\n\n"
            "Use the scikit-learn skill when:\n\n"
            "- Building classification or regression models\n"
            "- Training baseline machine learning systems\n"
        ),
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "scikit-learn"
    assert "model.training" in entry["capabilities"]
    assert any(
        row["capability"] == "model.training"
        and row["evidence_level"] == "weak_text"
        and row["source"] == "body_text"
        for row in entry["capability_evidence"]
    )


def test_build_skill_index_uses_explicit_description_intent_as_route_active_capability(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "diagnosing-bugs",
        """---
name: diagnosing-bugs
description: Diagnosis loop for hard bugs. Use when the user reports failing tests, stack traces, or slow pages.
---""",
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "diagnosing-bugs"
    assert "debug.systematic_workflow" in entry["capabilities"]
    assert any(
        row["capability"] == "debug.systematic_workflow"
        and row["evidence_level"] == "weak_text"
        and row["source"] == "frontmatter_intent"
        for row in entry["capability_evidence"]
    )


def test_build_skill_index_treats_action_led_description_as_route_active_capability(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "prototype",
        """---
name: prototype
description: Build a throwaway prototype to answer a design question.
---""",
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "prototype"
    assert "prototype.throwaway_validation" in entry["capabilities"]
    assert any(
        row["capability"] == "prototype.throwaway_validation"
        and row["evidence_level"] == "weak_text"
        and row["source"] == "frontmatter_intent"
        for row in entry["capability_evidence"]
    )
    assert any(
        chunk["role"] == "applicable"
        and "Build a throwaway prototype" in chunk["text"]
        for chunk in entry["route_evidence_chunks"]
    )


def test_build_skill_index_does_not_promote_dependency_mentions_into_planning_owner_capabilities(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "implement",
        """---
name: implement
description: Implement a piece of work based on a PRD or set of issues.
---""",
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "implement"
    assert "runtime.feature_delivery" in entry["capabilities"]
    assert any(
        row["capability"] == "runtime.feature_delivery"
        and row["evidence_level"] == "weak_text"
        and row["source"] == "frontmatter_intent"
        for row in entry["capability_evidence"]
    )
    assert "planning.prd" not in entry["capabilities"]
    assert "planning.issue_breakdown" not in entry["capabilities"]


def test_build_skill_index_keeps_humanization_descriptions_out_of_reader_report_owner_capabilities(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "qu-ai-wei",
        """---
name: qu-ai-wei
description: 用于去除简体中文文本中的 AI 写作痕迹，让内容更像真人表达且不虚构事实；用户说去 AI 味、改得说人话、humanize 中文时使用。
---""",
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert entry["skill_id"] == "qu-ai-wei"
    assert "writing.chinese_humanization" in entry["capabilities"]
    assert "writing.reader_report" not in entry["capabilities"]


def test_build_skill_index_emits_route_evidence_chunks_with_roles_and_source_spans(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "reader-brief-helper",
        """---
name: Reader Brief Helper
description: Help readers understand technical work.
---""",
        (
            "# Reader Brief Helper\n\n"
            "Use this skill for plain-language summaries of technical documents.\n\n"
            "## Routing Boundary\n\n"
            "This is not final slide production or poster layout.\n\n"
            "## Examples\n\n"
            "- Example: turn a spec into a short summary for leadership.\n\n"
            "```python\n"
            "use for plotting and chart export\n"
            "```\n"
        ),
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]
    chunks = entry["route_evidence_chunks"]

    assert any(
        chunk["role"] == "applicable"
        and "plain-language summaries" in chunk["text"]
        for chunk in chunks
    )
    assert any(
        chunk["role"] == "not_applicable"
        and "final slide production" in chunk["text"]
        for chunk in chunks
    )
    assert any(
        chunk["role"] == "example"
        and "short summary for leadership" in chunk["text"]
        for chunk in chunks
    )
    assert all("plotting and chart export" not in chunk["text"] for chunk in chunks)
    assert all(
        isinstance(chunk["line_start"], int)
        and isinstance(chunk["line_end"], int)
        and chunk["line_end"] >= chunk["line_start"] >= 1
        for chunk in chunks
    )


def test_build_skill_index_ignores_non_leading_use_lines_in_related_skill_examples(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "imaging-data-helper",
        """---
name: Imaging Data Helper
description: Query cancer imaging datasets by metadata.
---""",
        (
            "# Imaging Data Helper\n\n"
            "Use this skill for cancer imaging cohort lookup and DICOMWeb retrieval.\n\n"
            "- **seaborn** - statistical visualization with pandas integration. use for quick exploration of metadata distributions and relationships between variables.\n"
            "- **plotly** - interactive visualization. use when you need hover info, zoom, and pan.\n"
        ),
    )

    payload = build_skill_index(agent_root)

    assert payload["skills"][0]["skill_id"] == "imaging-data-helper"
    assert payload["skills"][0]["capabilities"] == []
    assert payload["skills"][0]["capability_evidence"] == []


def test_build_skill_index_extracts_not_for_phrases_from_routing_boundary(tmp_path: Path) -> None:
    agent_root = tmp_path / "home" / ".agents"
    vibe_root = agent_root / "vibe"
    _write_skill(
        vibe_root / "skills" / "local" / "imaging-data-helper",
        """---
name: Imaging Data Helper
description: Query cancer imaging datasets by metadata.
---""",
        (
            "# Imaging Data Helper\n\n"
            "## Routing Boundary\n\n"
            "Use this skill for Imaging Data Commons and DICOMWeb retrieval. "
            "This is not generic Data Commons, population indicators, statistical variables, DCIDs, or public dataset search.\n"
        ),
    )

    payload = build_skill_index(agent_root)
    entry = payload["skills"][0]

    assert "generic Data Commons" in entry["not_for"]
    assert "population indicators" in entry["not_for"]
    assert "statistical variables" in entry["not_for"]
    assert "DCIDs" in entry["not_for"]
    assert "public dataset search" in entry["not_for"]


def test_local_skill_index_and_router_share_the_same_capability_bridge() -> None:
    assert router_contract_runtime.CAPABILITY_HINTS == tuple(
        (capability, tuple(spec["prompt_hints"]))
        for capability, spec in CAPABILITY_BRIDGE
    )
    assert skill_index.CAPABILITY_INFERENCE_HINTS == tuple(
        (capability, tuple(spec["skill_inference_hints"]))
        for capability, spec in CAPABILITY_BRIDGE
    )
