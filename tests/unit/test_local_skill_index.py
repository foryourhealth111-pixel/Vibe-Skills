from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime import router_contract_runtime
from vgo_runtime.kernel import skill_index
from vgo_runtime.kernel.capability_bridge import CAPABILITY_BRIDGE
from vgo_runtime.kernel.finder import find_skill_candidates
from vgo_runtime.kernel.task_card import build_task_card
from vgo_runtime.kernel.skill_index import build_skill_index, write_skill_index
from vgo_runtime.kernel.skill_manifest import parse_installed_skill_manifest, parse_skill_manifest


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


@pytest.mark.parametrize("damaged_content", [b"", b'{"schema_version":', b"\xff\xfe"])
def test_skill_index_rebuilds_corrupt_derived_cards(tmp_path: Path, damaged_content: bytes) -> None:
    agent_root = tmp_path / "agent-root"
    _write_skill(
        agent_root / "vibe/skills/local/write-report",
        "---\nname: Write Report\ndescription: Produce a report from results.\n---",
    )
    first = build_skill_index(agent_root)
    card_path = Path(first["skill_cache"]["cards"][0]["card_path"])
    card_path.write_bytes(damaged_content)

    refreshed = build_skill_index(agent_root)

    assert [entry["skill_id"] for entry in refreshed["skills"]] == ["write-report"]
    assert json.loads(card_path.read_text(encoding="utf-8"))["skill_id"] == "write-report"
    assert refreshed["skill_cache"]["refreshed_count"] == 1
    assert refreshed["skill_cache"]["cards"][0]["refresh_reason"] == "invalid_cache"
    previous_mtime = card_path.stat().st_mtime_ns
    reused = build_skill_index(agent_root)
    assert reused["skill_cache"]["reused_count"] == 1
    assert card_path.stat().st_mtime_ns == previous_mtime


def test_skill_card_interrupted_refresh_preserves_previous_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_root = tmp_path / "agent-root"
    skill_file = _write_skill(
        agent_root / "vibe/skills/local/write-report",
        "---\nname: Write Report\ndescription: Produce a report from results.\n---",
    )
    first = build_skill_index(agent_root)
    card_path = Path(first["skill_cache"]["cards"][0]["card_path"])
    previous_content = card_path.read_bytes()
    previous_mtime = card_path.stat().st_mtime_ns
    skill_file.write_text(skill_file.read_text(encoding="utf-8") + "\nUpdated guidance.\n", encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        assert Path(destination) == card_path
        assert card_path.read_bytes() == previous_content
        raise OSError("simulated replacement failure")

    with monkeypatch.context() as patch:
        patch.setattr(skill_index.os, "replace", fail_replace)
        with pytest.raises(OSError, match="simulated replacement failure"):
            build_skill_index(agent_root)

    assert card_path.read_bytes() == previous_content
    assert card_path.stat().st_mtime_ns == previous_mtime
    assert set(card_path.parent.iterdir()) == {card_path}
    refreshed = build_skill_index(agent_root)
    assert refreshed["skill_cache"]["refreshed_count"] == 1
    assert card_path.read_bytes() != previous_content
    assert card_path.stat().st_mtime_ns > previous_mtime
    assert json.loads(card_path.read_text(encoding="utf-8"))["content_sha256"] == refreshed["skills"][0]["content_sha256"]


@pytest.mark.parametrize("skill_ids", [("report+writer", "report writer"), ("report_writer", "report+writer")])
def test_distinct_installed_skill_ids_have_distinct_stable_cache_cards(
    tmp_path: Path, skill_ids: tuple[str, str],
) -> None:
    agent_root = tmp_path / "agent"
    host_root = tmp_path / "host-skills"
    for skill_id in skill_ids:
        _write_skill(
            host_root / skill_id,
            f"---\nname: {skill_id}\ndescription: Write a report.\n---",
        )
    first = skill_index.build_skill_catalog(agent_root=agent_root, host_roots=(host_root,))
    entries = [row for row in first["entries"] if row["active"] and row["source_kind"] == "host_installed"]
    assert {row["skill_id"] for row in entries} == set(skill_ids)
    paths = {row["skill_id"]: row["capability_card_path"] for row in entries}
    assert len(set(paths.values())) == len(skill_ids)
    for skill_id, path in paths.items():
        card = json.loads(Path(path).read_text(encoding="utf-8"))
        assert card["skill_id"] == skill_id
    second = skill_index.build_skill_catalog(agent_root=agent_root, host_roots=(host_root,))
    assert {
        row["skill_id"]: row["capability_card_path"]
        for row in second["entries"] if row["active"] and row["source_kind"] == "host_installed"
    } == paths
    assert second["skill_cache"]["refreshed_count"] == 0


@pytest.mark.parametrize(
    "prompt",
    [
        "请整理实验资料，撰写实验报告并核对数据一致性。",
        "整理实验资料，生成中文实验报告。",
        "Produce an experimental report and verify data consistency.",
    ],
)
def test_installed_catalog_recalls_chinese_skill_for_matching_task(tmp_path: Path, prompt: str) -> None:
    agent_root = tmp_path / "agent"
    skills_root = agent_root / "vibe/skills/local"
    _write_skill(
        skills_root / "cn-report",
        "---\nname: 中文报告整理\ndescription: 整理实验资料，撰写实验报告并核对数据一致性。\n---",
    )
    _write_skill(
        skills_root / "poster-design",
        "---\nname: 海报设计\ndescription: 制作营销海报，选择配色和字体。\n---",
    )
    index = build_skill_index(agent_root)
    task = build_task_card(prompt=prompt)

    candidates = find_skill_candidates(task, index)

    assert [candidate.skill_id for candidate in candidates] == ["cn-report"]


@pytest.mark.parametrize("format_variant", ["block", "comment", "flow", "quoted_flow"])
def test_installed_manifest_preserves_comment_and_flow_list_metadata(tmp_path: Path, format_variant: str) -> None:
    header = 'name: yaml-report\ndescription: "Preserve the user\'s C# report, summary."\n'
    expected_outputs = ("report", "summary")
    if format_variant == "comment":
        header = "# Maintained by the team\n" + header
        outputs = "outputs:\n  # Required deliveries\n  - report # primary output\n  - summary\n"
    elif format_variant == "flow":
        outputs = "outputs: [report, summary] # Required deliveries\n"
    elif format_variant == "quoted_flow":
        outputs = 'outputs: ["report, detail", \'C# outline\'] # Required deliveries\n'
        expected_outputs = ("report, detail", "C# outline")
    else:
        outputs = "outputs:\n  - report\n  - summary\n"
    skill_file = _write_skill(tmp_path / "yaml-report", f"---\n{header}{outputs}---")

    manifest = parse_installed_skill_manifest(skill_file)

    assert manifest.name == "yaml-report"
    assert manifest.description == "Preserve the user's C# report, summary."
    assert manifest.outputs == expected_outputs


@pytest.mark.parametrize("manifest_kind", ["contract", "installed"])
@pytest.mark.parametrize("list_style", ["block", "flow"])
def test_skill_manifest_decodes_supported_quoted_scalar_escapes(
    tmp_path: Path, manifest_kind: str, list_style: str,
) -> None:
    items = [r"'User''s guide, # notes'", r'"C:\\notes \"guide\", # appendix"']
    outputs = (
        "outputs: [" + ", ".join(items) + "] # deliveries\n"
        if list_style == "flow"
        else "outputs:\n" + "".join(f"  - {item} # delivery\n" for item in items)
    )
    skill_file = _write_skill(
        tmp_path / "quoted-report",
        "---\nid: quoted-report\nname: 'User''s guide'\n"
        r'description: "Review \"guide\" in C:\\notes # archive."'
        "\nwhen_to_use: []\nnot_for: []\ninputs: []\n"
        f"{outputs}---",
    )
    parser = parse_skill_manifest if manifest_kind == "contract" else parse_installed_skill_manifest

    manifest = parser(skill_file)

    assert manifest.name == "User's guide"
    assert manifest.description == r'Review "guide" in C:\notes # archive.'
    assert manifest.outputs == ("User's guide, # notes", r'C:\notes "guide", # appendix')


@pytest.mark.parametrize(
    "outputs",
    ["[report, summary", "['unterminated, report]", "[report,, summary]", "[[report]]", "[report: summary]", '["report" trailing]'],
)
def test_installed_manifest_rejects_malformed_or_structured_flow_items(tmp_path: Path, outputs: str) -> None:
    skill_file = _write_skill(
        tmp_path / "yaml-report",
        f"---\nname: yaml-report\ndescription: Write a report.\noutputs: {outputs}\n---",
    )

    with pytest.raises(ValueError):
        parse_installed_skill_manifest(skill_file)


@pytest.mark.parametrize("marker", [">", ">-", "|", "|-"])
def test_installed_manifest_keeps_hash_content_in_multiline_scalar(tmp_path: Path, marker: str) -> None:
    skill_file = _write_skill(
        tmp_path / "yaml-report",
        "---\n# Team metadata\nname: yaml-report\n"
        f"description: {marker} # Description follows\n"
        "  Preserve the user's C# report.\n  # Keep this scalar content.\n"
        "outputs: [] # No declared output names\n---",
    )

    manifest = parse_installed_skill_manifest(skill_file)

    assert manifest.description == "Preserve the user's C# report. # Keep this scalar content."
    assert manifest.outputs == ()


@pytest.mark.parametrize("enabled", ['"false"', "1", "[true]"])
def test_installed_catalog_rejects_non_boolean_enabled_metadata(tmp_path: Path, enabled: str) -> None:
    agent_root = tmp_path / "agent"
    _write_skill(
        agent_root / "vibe/skills/local/report",
        f"---\nname: report\ndescription: Write a report.\nenabled: {enabled}\n---",
    )

    catalog = skill_index.build_skill_catalog(agent_root=agent_root)

    assert catalog["entries"] == []
    assert len(catalog["discovery_diagnostics"]["invalid_entries"]) == 1
    assert "enabled must be a boolean" in catalog["discovery_diagnostics"]["invalid_entries"][0]["message"]
