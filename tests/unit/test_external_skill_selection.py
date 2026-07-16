from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel.finder import find_skill_candidates
from vgo_runtime.kernel.planner import build_work_plan
from vgo_runtime.kernel.task_card import build_task_card
from vgo_runtime.kernel.module_assignments import build_module_assignments


def _skill(
    *,
    skill_id: str,
    name: str,
    description: str,
    when_to_use: list[str],
    outputs: list[str],
    priority: int,
    source_kind: str,
    source_root: str,
    resolved_source_root: str,
    source_priority: int,
    source_order: int,
    root_dir: str,
    resolved_root_dir: str,
    skill_file: str,
    resolved_skill_file: str,
    path_contract: str,
    path_base: str,
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "when_to_use": when_to_use,
        "outputs": outputs,
        "not_for": [],
        "tags": tags or [],
        "enabled": True,
        "priority": priority,
        "source_kind": source_kind,
        "source_root": source_root,
        "resolved_source_root": resolved_source_root,
        "source_priority": source_priority,
        "source_order": source_order,
        "root_dir": root_dir,
        "resolved_root_dir": resolved_root_dir,
        "skill_file": skill_file,
        "resolved_skill_file": resolved_skill_file,
        "path_contract": path_contract,
        "path_base": path_base,
    }


def test_external_skill_beats_starter_when_both_match() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="starter-review-helper",
                name="Starter Review Helper",
                description="Generic review help for many tasks.",
                when_to_use=["The task needs a review report or review notes."],
                outputs=["review report"],
                priority=95,
                source_kind="starter",
                source_root="skills/starter",
                resolved_source_root="C:/agent/vibe/skills/starter",
                source_priority=2,
                source_order=2,
                root_dir="skills/starter/starter-review-helper",
                resolved_root_dir="C:/agent/vibe/skills/starter/starter-review-helper",
                skill_file="skills/starter/starter-review-helper/SKILL.md",
                resolved_skill_file="C:/agent/vibe/skills/starter/starter-review-helper/SKILL.md",
                path_contract="vibe_relative",
                path_base="C:/agent/vibe",
                tags=["review", "report", "generic", "chart", "annotations"],
            ),
            _skill(
                skill_id="diagram-review",
                name="Diagram Review",
                description="Review chart annotations and visual labels.",
                when_to_use=["The task is about diagrams, charts, or annotations."],
                outputs=["review report"],
                priority=10,
                source_kind="host_external",
                source_root="C:/external-skills",
                resolved_source_root="C:/external-skills",
                source_priority=1,
                source_order=1,
                root_dir="diagram-review",
                resolved_root_dir="C:/external-skills/diagram-review",
                skill_file="diagram-review/SKILL.md",
                resolved_skill_file="C:/external-skills/diagram-review/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-skills",
                tags=["diagram", "review", "chart", "annotations"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)
    binding = build_module_assignments(plan).model_dump()

    assert [candidate.skill_id for candidate in candidates] == [
        "diagram-review",
        "starter-review-helper",
    ]
    assert plan.work_units[0].preferred_skill == "diagram-review"
    assert binding["units"][0]["bound_skill"] == "diagram-review"
    assert binding["units"][0]["provenance"] == {
        "source_kind": "host_external",
        "source_root": "C:/external-skills",
        "resolved_skill_file": "C:/external-skills/diagram-review/SKILL.md",
        "source_priority": 1,
        "source_order": 1,
        "path_contract": "source_root_relative",
        "path_base": "C:/external-skills",
    }


def test_local_skill_still_beats_external_when_both_match() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="diagram-review",
                name="Diagram Review",
                description="Review chart annotations and visual labels.",
                when_to_use=["The task is about diagrams, charts, or annotations."],
                outputs=["review report"],
                priority=90,
                source_kind="host_external",
                source_root="C:/external-skills",
                resolved_source_root="C:/external-skills",
                source_priority=1,
                source_order=1,
                root_dir="diagram-review",
                resolved_root_dir="C:/external-skills/diagram-review",
                skill_file="diagram-review/SKILL.md",
                resolved_skill_file="C:/external-skills/diagram-review/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-skills",
                tags=["diagram", "review", "chart", "annotations"],
            ),
            _skill(
                skill_id="local-review-override",
                name="Local Review Override",
                description="Workspace-owned override for review work.",
                when_to_use=["A local override should own the review."],
                outputs=["review report"],
                priority=10,
                source_kind="local",
                source_root="skills/local",
                resolved_source_root="C:/agent/vibe/skills/local",
                source_priority=0,
                source_order=0,
                root_dir="skills/local/local-review-override",
                resolved_root_dir="C:/agent/vibe/skills/local/local-review-override",
                skill_file="skills/local/local-review-override/SKILL.md",
                resolved_skill_file="C:/agent/vibe/skills/local/local-review-override/SKILL.md",
                path_contract="vibe_relative",
                path_base="C:/agent/vibe",
                tags=["review", "report"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [candidate.skill_id for candidate in candidates] == [
        "local-review-override",
        "diagram-review",
    ]
    assert plan.work_units[0].preferred_skill == "local-review-override"


def test_local_skill_still_beats_external_output_owner() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="external-review-owner",
                name="External Review Owner",
                description="Review chart annotations and own detailed review reports.",
                when_to_use=["The task is about diagrams, charts, annotations, and review reports."],
                outputs=["review report"],
                priority=99,
                source_kind="host_external",
                source_root="C:/external-skills",
                resolved_source_root="C:/external-skills",
                source_priority=1,
                source_order=1,
                root_dir="external-review-owner",
                resolved_root_dir="C:/external-skills/external-review-owner",
                skill_file="external-review-owner/SKILL.md",
                resolved_skill_file="C:/external-skills/external-review-owner/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-skills",
                tags=["diagram", "review", "chart", "annotations", "report", "owner"],
            ),
            _skill(
                skill_id="local-review-override",
                name="Local Review Override",
                description="Workspace-owned override for review work.",
                when_to_use=["A local override should own the review."],
                outputs=["notes"],
                priority=1,
                source_kind="local",
                source_root="skills/local",
                resolved_source_root="C:/agent/vibe/skills/local",
                source_priority=0,
                source_order=0,
                root_dir="skills/local/local-review-override",
                resolved_root_dir="C:/agent/vibe/skills/local/local-review-override",
                skill_file="skills/local/local-review-override/SKILL.md",
                resolved_skill_file="C:/agent/vibe/skills/local/local-review-override/SKILL.md",
                path_contract="vibe_relative",
                path_base="C:/agent/vibe",
                tags=["review", "report"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [candidate.skill_id for candidate in candidates] == [
        "local-review-override",
        "external-review-owner",
    ]
    assert plan.work_units[0].preferred_skill == "local-review-override"


def test_module_assignments_carries_selected_skill_provenance() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="diagram-review",
                name="Diagram Review",
                description="Review chart annotations and visual labels.",
                when_to_use=["The task is about diagrams, charts, or annotations."],
                outputs=["review report"],
                priority=10,
                source_kind="host_external",
                source_root="C:/external-skills",
                resolved_source_root="C:/external-skills",
                source_priority=1,
                source_order=3,
                root_dir="diagram-review",
                resolved_root_dir="C:/external-skills/diagram-review",
                skill_file="diagram-review/SKILL.md",
                resolved_skill_file="C:/external-skills/diagram-review/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-skills",
                tags=["diagram", "review", "chart", "annotations"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)
    binding = build_module_assignments(plan).model_dump()

    assert plan.work_units[0].selected_skill_provenance is not None
    assert plan.work_units[0].selected_skill_provenance.model_dump() == {
        "source_kind": "host_external",
        "source_root": "C:/external-skills",
        "resolved_skill_file": "C:/external-skills/diagram-review/SKILL.md",
        "source_priority": 1,
        "source_order": 3,
        "path_contract": "source_root_relative",
        "path_base": "C:/external-skills",
    }
    assert binding["units"][0]["bound_skill"] == "diagram-review"
    assert binding["units"][0]["provenance"] == {
        "source_kind": "host_external",
        "source_root": "C:/external-skills",
        "resolved_skill_file": "C:/external-skills/diagram-review/SKILL.md",
        "source_priority": 1,
        "source_order": 3,
        "path_contract": "source_root_relative",
        "path_base": "C:/external-skills",
    }


def test_more_relevant_skill_wins_within_same_source_priority() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="diagram-review-second",
                name="Diagram Review Second",
                description="Review chart annotations, review reports, and chart labels in detail.",
                when_to_use=["The task is about chart review, annotations, and detailed review reports."],
                outputs=["review report"],
                priority=99,
                source_kind="host_external",
                source_root="C:/external-b",
                resolved_source_root="C:/external-b",
                source_priority=1,
                source_order=2,
                root_dir="diagram-review-second",
                resolved_root_dir="C:/external-b/diagram-review-second",
                skill_file="diagram-review-second/SKILL.md",
                resolved_skill_file="C:/external-b/diagram-review-second/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-b",
                tags=["diagram", "review", "chart", "annotations", "report", "detailed"],
            ),
            _skill(
                skill_id="diagram-review-first",
                name="Diagram Review First",
                description="Review chart annotations.",
                when_to_use=["The task is about chart review."],
                outputs=["review report"],
                priority=1,
                source_kind="host_external",
                source_root="C:/external-a",
                resolved_source_root="C:/external-a",
                source_priority=1,
                source_order=1,
                root_dir="diagram-review-first",
                resolved_root_dir="C:/external-a/diagram-review-first",
                skill_file="diagram-review-first/SKILL.md",
                resolved_skill_file="C:/external-a/diagram-review-first/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-a",
                tags=["diagram", "review", "chart", "annotations"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [candidate.skill_id for candidate in candidates] == [
        "diagram-review-second",
        "diagram-review-first",
    ]
    assert plan.work_units[0].preferred_skill == "diagram-review-second"


def test_source_order_breaks_true_ties_within_same_source_priority() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="diagram-review-second",
                name="Diagram Review Second",
                description="Review chart annotations.",
                when_to_use=["The task is about chart review."],
                outputs=["review report"],
                priority=10,
                source_kind="host_external",
                source_root="C:/external-b",
                resolved_source_root="C:/external-b",
                source_priority=1,
                source_order=2,
                root_dir="diagram-review-second",
                resolved_root_dir="C:/external-b/diagram-review-second",
                skill_file="diagram-review-second/SKILL.md",
                resolved_skill_file="C:/external-b/diagram-review-second/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-b",
                tags=["diagram", "review", "chart", "annotations"],
            ),
            _skill(
                skill_id="diagram-review-first",
                name="Diagram Review First",
                description="Review chart annotations.",
                when_to_use=["The task is about chart review."],
                outputs=["review report"],
                priority=10,
                source_kind="host_external",
                source_root="C:/external-a",
                resolved_source_root="C:/external-a",
                source_priority=1,
                source_order=1,
                root_dir="diagram-review-first",
                resolved_root_dir="C:/external-a/diagram-review-first",
                skill_file="diagram-review-first/SKILL.md",
                resolved_skill_file="C:/external-a/diagram-review-first/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-a",
                tags=["diagram", "review", "chart", "annotations"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [candidate.skill_id for candidate in candidates] == [
        "diagram-review-first",
        "diagram-review-second",
    ]
    assert plan.work_units[0].preferred_skill == "diagram-review-first"


def test_find_skill_candidates_requires_explicit_source_metadata() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            {
                "id": "diagram-review",
                "name": "Diagram Review",
                "description": "Review chart annotations and visual labels.",
                "when_to_use": ["The task is about diagrams, charts, or annotations."],
                "outputs": ["review report"],
                "not_for": [],
                "tags": ["diagram", "review", "chart", "annotations"],
                "enabled": True,
                "priority": 10,
            }
        ]
    }

    try:
        find_skill_candidates(task_card, index_payload)
    except ValueError as exc:
        assert "source_kind" in str(exc)
    else:
        raise AssertionError("expected missing source metadata to fail fast")


def test_find_skill_candidates_rejects_unmatched_enabled_entry_with_missing_source_metadata() -> None:
    task_card = build_task_card(
        prompt="Review the chart annotations and produce a review report.",
        context={"deliverables": ["review report"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="diagram-review",
                name="Diagram Review",
                description="Review chart annotations and visual labels.",
                when_to_use=["The task is about diagrams, charts, or annotations."],
                outputs=["review report"],
                priority=10,
                source_kind="host_external",
                source_root="C:/external-skills",
                resolved_source_root="C:/external-skills",
                source_priority=1,
                source_order=1,
                root_dir="diagram-review",
                resolved_root_dir="C:/external-skills/diagram-review",
                skill_file="diagram-review/SKILL.md",
                resolved_skill_file="C:/external-skills/diagram-review/SKILL.md",
                path_contract="source_root_relative",
                path_base="C:/external-skills",
                tags=["diagram", "review", "chart", "annotations"],
            ),
            {
                "id": "spreadsheet-cleanup",
                "name": "Spreadsheet Cleanup",
                "description": "Normalize spreadsheet columns and formatting.",
                "when_to_use": ["The user needs help cleaning spreadsheets."],
                "outputs": ["clean spreadsheet"],
                "not_for": [],
                "tags": ["spreadsheet", "cleanup"],
                "enabled": True,
                "priority": 5,
            },
        ]
    }

    try:
        find_skill_candidates(task_card, index_payload)
    except ValueError as exc:
        assert "source_kind" in str(exc)
    else:
        raise AssertionError("expected unmatched enabled bad entry to fail fast")


def test_find_skill_candidates_applies_same_token_variants_as_planner() -> None:
    task_card = build_task_card(
        prompt="Prepare runtime release briefs.",
        context={"deliverables": ["release briefs"]},
    )
    index_payload = {
        "skills": [
            _skill(
                skill_id="brief-writer",
                name="Brief Writer",
                description="Turn runtime changes into a short brief.",
                when_to_use=["The user needs a brief."],
                outputs=["release brief"],
                priority=10,
                source_kind="local",
                source_root="skills/local",
                resolved_source_root="C:/agent/vibe/skills/local",
                source_priority=0,
                source_order=0,
                root_dir="skills/local/brief-writer",
                resolved_root_dir="C:/agent/vibe/skills/local/brief-writer",
                skill_file="skills/local/brief-writer/SKILL.md",
                resolved_skill_file="C:/agent/vibe/skills/local/brief-writer/SKILL.md",
                path_contract="vibe_relative",
                path_base="C:/agent/vibe",
                tags=["release", "brief"],
            ),
        ]
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [candidate.skill_id for candidate in candidates] == ["brief-writer"]
    assert plan.work_units[0].preferred_skill == "brief-writer"
