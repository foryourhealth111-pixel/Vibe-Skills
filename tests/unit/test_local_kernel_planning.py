from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel.finder import find_skill_candidates
from vgo_runtime.kernel.module_assignments import build_module_assignments
from vgo_runtime.kernel.planner import build_work_plan
from vgo_runtime.kernel.task_card import build_task_card


def _with_source_metadata(
    entry: dict[str, object],
    *,
    source_kind: str = "local",
    source_order: int = 0,
) -> dict[str, object]:
    root_dir = str(entry["root_dir"])
    skill_file = str(entry["skill_file"])
    base_path = "C:/agent/vibe"
    if source_kind == "local":
        source_root = "skills/local"
        source_priority = 0
    elif source_kind == "starter":
        source_root = "skills/starter"
        source_priority = 2
    else:
        raise AssertionError(f"unsupported source kind in test fixture: {source_kind}")
    return {
        **entry,
        "source_kind": source_kind,
        "source_root": source_root,
        "resolved_source_root": f"{base_path}/{source_root}",
        "source_priority": source_priority,
        "source_order": source_order,
        "resolved_root_dir": f"{base_path}/{root_dir}",
        "resolved_skill_file": f"{base_path}/{skill_file}",
        "path_contract": "vibe_relative",
        "path_base": base_path,
    }


def test_build_task_card_uses_prompt_and_context_contract() -> None:
    task_card = build_task_card(
        prompt="Review the routing redesign and produce an implementation plan.",
        context={
            "deliverables": ["review notes", "implementation plan"],
            "constraints": ["prefer local skills", "keep configuration small"],
            "known_context": ["installed into agent directory"],
            "completion_criteria": ["review risks are explicit", "plan is concrete"],
            "mode": "design",
        },
    )

    assert task_card.goal == "Review the routing redesign and produce an implementation plan."
    assert task_card.deliverables == ("review notes", "implementation plan")
    assert task_card.constraints == ("prefer local skills", "keep configuration small")
    assert task_card.known_context == ("installed into agent directory",)
    assert task_card.completion_criteria == ("review risks are explicit", "plan is concrete")
    assert task_card.mode == "design"
    assert task_card.id.startswith("task-")


def test_build_task_card_infers_mode_deliverables_and_completion_criteria_from_prompt() -> None:
    task_card = build_task_card(
        prompt="Review the runtime redesign and produce an implementation plan and add focused tests.",
    )

    assert task_card.mode == "review"
    assert task_card.deliverables == ("review notes", "implementation plan", "focused tests")
    assert task_card.completion_criteria == (
        "review notes exists",
        "implementation plan exists",
        "focused tests exists",
        "review findings are explicit",
        "plan or design is concrete",
        "tests cover the changed behavior",
    )


def test_build_task_card_infers_code_change_and_verification_evidence_deliverables() -> None:
    task_card = build_task_card(
        prompt="Design a runtime improvement. Implement the code change. Add focused tests. Provide verification evidence.",
    )

    assert task_card.mode == "design"
    assert task_card.deliverables == (
        "implementation plan",
        "code change",
        "focused tests",
        "verification evidence",
    )
    assert "verification evidence exists" in task_card.completion_criteria
    assert "verification evidence is direct" in task_card.completion_criteria


def test_build_task_card_infers_reporting_mode_and_report_completion_criteria() -> None:
    task_card = build_task_card(
        prompt="Summarize the benchmark results and produce a report.",
    )

    assert task_card.mode == "reporting"
    assert task_card.deliverables == ("report",)
    assert task_card.completion_criteria == (
        "report exists",
        "report or summary is concrete",
    )


def test_find_skill_candidates_returns_enabled_matches_sorted_by_relevance() -> None:
    task_card = build_task_card(prompt="Review the runtime change and check missing tests.")
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local", "skills/starter"],
        "skills": [
            _with_source_metadata({
                "id": "code-review",
                "name": "Code Review",
                "description": "Review implementation risk and test gaps.",
                "when_to_use": ["The user asks for a review."],
                "not_for": ["Building a feature from scratch."],
                "tags": ["review", "testing"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/local/code-review",
                "skill_file": "skills/local/code-review/SKILL.md",
            }),
            _with_source_metadata({
                "id": "write-plan",
                "name": "Write Plan",
                "description": "Turn a task into explicit work steps.",
                "when_to_use": ["The user needs a plan."],
                "not_for": ["Final review."],
                "tags": ["planning"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/starter/write-plan",
                "skill_file": "skills/starter/write-plan/SKILL.md",
            }, source_kind="starter"),
            _with_source_metadata({
                "id": "disabled-review",
                "name": "Disabled Review",
                "description": "Review code.",
                "when_to_use": ["The user asks for a review."],
                "not_for": [],
                "tags": ["review"],
                "enabled": False,
                "priority": 99,
                "root_dir": "skills/local/disabled-review",
                "skill_file": "skills/local/disabled-review/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload, limit=4)

    assert [candidate.skill_id for candidate in candidates] == ["code-review", "write-plan"]
    assert candidates[0].score > candidates[1].score
    assert "review" in candidates[0].matched_tokens
    assert "review" in candidates[0].reasons[0]


def test_find_skill_candidates_ignores_stopword_only_overlap() -> None:
    task_card = build_task_card(prompt="Design the runtime migration. Produce review notes.")
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "spreadsheet-cleanup",
                "name": "Spreadsheet Cleanup",
                "description": "Normalize spreadsheet columns and formatting.",
                "when_to_use": ["The user needs help cleaning spreadsheets."],
                "not_for": ["Runtime redesign work."],
                "tags": ["spreadsheet", "cleanup"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/local/spreadsheet-cleanup",
                "skill_file": "skills/local/spreadsheet-cleanup/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)

    assert candidates == ()


def test_build_work_plan_uses_deliverables_and_skill_candidates() -> None:
    task_card = build_task_card(
        prompt="Review the runtime change and produce a plan.",
        context={
            "deliverables": ["review notes", "implementation plan"],
            "completion_criteria": ["review is concrete", "plan is executable"],
        },
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "code-review",
                "name": "Code Review",
                "description": "Review implementation risk and test gaps.",
                "when_to_use": ["The user asks for a review."],
                "not_for": ["Building a feature from scratch."],
                "tags": ["review", "testing"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/local/code-review",
                "skill_file": "skills/local/code-review/SKILL.md",
            }),
            _with_source_metadata({
                "id": "write-plan",
                "name": "Write Plan",
                "description": "Turn a task into explicit work steps.",
                "when_to_use": ["The user needs a plan."],
                "not_for": ["Final review."],
                "tags": ["planning"],
                "enabled": True,
                "priority": 40,
                "root_dir": "skills/local/write-plan",
                "skill_file": "skills/local/write-plan/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert plan.task_id == task_card.id
    assert [unit.id for unit in plan.work_units] == ["wu-1", "wu-2"]
    assert plan.work_units[0].expected_artifacts == ("review notes",)
    assert plan.work_units[1].expected_artifacts == ("implementation plan",)
    assert plan.work_units[0].preferred_skill == "code-review"
    assert plan.work_units[0].binding_profile == "general_support_owner"
    assert plan.work_units[0].binding_reason == "Selected one skill as the current owner and kept nearby supporting skills as alternatives."
    assert plan.work_units[0].model_dump()["bound_skill"] == "code-review"
    assert plan.work_units[0].fallback_skills == ("write-plan",)
    assert plan.work_units[0].verification == ("review notes exists", "review is concrete")
    assert plan.work_units[1].preferred_skill == "write-plan"
    assert plan.work_units[1].binding_profile == "general_support_owner"
    assert plan.work_units[1].binding_reason == "Selected one skill as the current owner and kept nearby supporting skills as alternatives."
    assert plan.work_units[1].model_dump()["bound_skill"] == "write-plan"
    assert plan.work_units[1].fallback_skills == ("code-review",)
    assert plan.work_units[1].verification == ("implementation plan exists", "plan is executable")


def test_build_work_plan_uses_inferred_task_card_deliverables_when_context_is_empty() -> None:
    task_card = build_task_card(
        prompt="Fix the runtime bug and add focused tests and verify the result.",
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "debug-runtime",
                "name": "Debug Runtime",
                "description": "Diagnose runtime failures and fix bugs.",
                "when_to_use": ["The user asks to debug or fix a problem."],
                "not_for": ["Writing a long design document."],
                "tags": ["debug", "testing"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/local/debug-runtime",
                "skill_file": "skills/local/debug-runtime/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [unit.expected_artifacts for unit in plan.work_units] == [
        ("code change",),
        ("focused tests",),
        ("verification evidence",),
    ]
    assert plan.work_units[0].verification == (
        "code change exists",
        "tests cover the changed behavior",
        "changed behavior is fixed",
    )
    assert plan.work_units[1].verification == (
        "focused tests exists",
        "tests cover the changed behavior",
    )
    assert plan.work_units[2].verification == (
        "verification evidence exists",
        "verification evidence is direct",
    )
    assert [unit.preferred_skill for unit in plan.work_units] == [
        "debug-runtime",
        "debug-runtime",
        None,
    ]
    assert [unit.binding_profile for unit in plan.work_units] == [
        "general_support_owner",
        "general_support_owner",
        "partial_helpers_only",
    ]
    assert plan.work_units[2].fallback_skills == ("debug-runtime",)


def test_build_work_plan_can_leave_deliverable_unbound_when_no_skill_supports_it() -> None:
    task_card = build_task_card(
        prompt="Fix the runtime bug. Add focused tests. Provide verification evidence.",
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "code-review",
                "name": "Code Review",
                "description": "Review implementation risk and test gaps.",
                "when_to_use": ["The user asks for a review."],
                "not_for": ["Building a feature from scratch."],
                "tags": ["review", "testing"],
                "enabled": True,
                "priority": 50,
                "root_dir": "skills/local/code-review",
                "skill_file": "skills/local/code-review/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [unit.preferred_skill for unit in plan.work_units] == ["code-review", "code-review", None]
    assert plan.work_units[2].binding_profile == "partial_helpers_only"
    assert plan.work_units[2].model_dump()["bound_skill"] is None
    assert "partial helpers only" in (plan.work_units[2].binding_reason or "")
    assert plan.work_units[2].fallback_skills == ("code-review",)


def test_build_work_plan_respects_not_for_boundary_on_deliverable() -> None:
    task_card = build_task_card(
        prompt="Design the runtime migration. Produce review notes.",
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "runtime-outline-writer",
                "name": "Runtime Outline Writer",
                "description": "Draft short runtime redesign outlines and migration briefs.",
                "when_to_use": ["The user needs a runtime redesign outline or migration brief."],
                "not_for": ["Owning runtime migration implementation planning or full review notes."],
                "tags": ["runtime", "migration", "outline", "design"],
                "outputs": ["outline"],
                "enabled": True,
                "priority": 20,
                "root_dir": "skills/local/runtime-outline-writer",
                "skill_file": "skills/local/runtime-outline-writer/SKILL.md",
            }),
            _with_source_metadata({
                "id": "release-note-editor",
                "name": "Release Note Editor",
                "description": "Polish runtime change notes into short release text.",
                "when_to_use": ["The user needs release notes about runtime changes."],
                "not_for": ["Owning runtime migration implementation planning or full review notes."],
                "tags": ["runtime", "release", "notes"],
                "outputs": ["release notes"],
                "enabled": True,
                "priority": 20,
                "root_dir": "skills/local/release-note-editor",
                "skill_file": "skills/local/release-note-editor/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert [unit.preferred_skill for unit in plan.work_units] == [None, None]
    assert [unit.binding_profile for unit in plan.work_units] == ["partial_helpers_only", "partial_helpers_only"]
    assert all("partial helpers only" in (unit.binding_reason or "") for unit in plan.work_units)
    assert plan.work_units[0].fallback_skills == ("release-note-editor", "runtime-outline-writer")
    assert plan.work_units[1].fallback_skills == ("release-note-editor", "runtime-outline-writer")


def test_build_work_plan_prefers_declared_output_owner_over_higher_general_score() -> None:
    task_card = build_task_card(
        prompt="Prepare a runtime release brief.",
        context={
            "deliverables": ["release brief"],
            "completion_criteria": ["release brief exists"],
        },
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
                _with_source_metadata({
                    "id": "runtime-redesign-advisor",
                    "name": "Runtime Redesign Advisor",
                    "description": "Provide runtime redesign guidance, release brief framing, and migration advice.",
                    "when_to_use": ["The user needs runtime redesign advice or release framing."],
                    "not_for": [],
                    "tags": ["runtime", "release", "brief", "migration", "advice"],
                    "outputs": ["advice"],
                    "enabled": True,
                    "priority": 90,
                    "root_dir": "skills/local/runtime-redesign-advisor",
                    "skill_file": "skills/local/runtime-redesign-advisor/SKILL.md",
                }),
                _with_source_metadata({
                    "id": "release-brief-writer",
                    "name": "Brief Writer",
                    "description": "Turn runtime changes into a short summary.",
                    "when_to_use": ["The user needs a brief."],
                    "not_for": [],
                    "tags": ["writing"],
                    "outputs": ["release brief"],
                    "enabled": True,
                    "priority": 10,
                    "root_dir": "skills/local/release-brief-writer",
                    "skill_file": "skills/local/release-brief-writer/SKILL.md",
                }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert candidates[0].skill_id == "runtime-redesign-advisor"
    assert plan.work_units[0].preferred_skill == "release-brief-writer"
    assert plan.work_units[0].binding_profile == "declared_output_owner"
    assert plan.work_units[0].binding_reason == "Selected this skill because its declared outputs overlap the deliverable."
    assert plan.work_units[0].fallback_skills == ("runtime-redesign-advisor",)


def test_build_work_plan_carries_selected_skill_execution_guidance() -> None:
    task_card = build_task_card(
        prompt="Prepare a concise runtime release brief.",
        context={
            "deliverables": ["release brief", "supporting evidence"],
            "completion_criteria": ["release brief is concise", "supporting evidence exists"],
        },
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "release-brief-writer",
                "name": "Release Brief Writer",
                "description": "Turn runtime changes into a concise release brief.",
                "when_to_use": ["The user needs a runtime release brief."],
                "not_for": [],
                "inputs": ["agreed release scope"],
                "outputs": ["release brief"],
                "plan_hints": [
                    "Confirm the audience and agreed release scope.",
                    "Lead with the shipped outcome.",
                ],
                "verify_hints": ["Check every claim against the release evidence."],
                "tags": ["runtime", "release", "brief"],
                "enabled": True,
                "priority": 10,
                "root_dir": "skills/local/release-brief-writer",
                "skill_file": "skills/local/release-brief-writer/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)
    assignments = build_module_assignments(plan)

    assert candidates[0].inputs == ("agreed release scope",)
    assert candidates[0].outputs == ("release brief",)
    assert plan.work_units[0].preferred_skill == "release-brief-writer"
    assert plan.work_units[0].binding_profile == "declared_output_owner"
    assert plan.work_units[0].plan_hints == (
        "Confirm the audience and agreed release scope.",
        "Lead with the shipped outcome.",
    )
    assert plan.work_units[0].verification == (
        "release brief exists",
        "release brief is concise",
        "Check every claim against the release evidence.",
    )
    assert assignments.units[0].plan_hints == plan.work_units[0].plan_hints
    assert assignments.units[0].verify_hints == plan.work_units[0].verify_hints
    assert assignments.units[1].depends_on == ("wu-1",)


def test_build_work_plan_does_not_claim_declared_output_owner_without_output_overlap() -> None:
    task_card = build_task_card(
        prompt="Prepare a runtime release brief.",
        context={
            "deliverables": ["release brief"],
            "completion_criteria": ["release brief exists"],
        },
    )
    index_payload = {
        "version": 1,
        "generated_at": "2026-06-20T00:00:00Z",
        "roots": ["skills/local"],
        "skills": [
            _with_source_metadata({
                "id": "runtime-redesign-advisor",
                "name": "Runtime Redesign Advisor",
                "description": "Provide runtime redesign guidance, release brief framing, and migration advice.",
                "when_to_use": ["The user needs runtime redesign advice or release framing."],
                "not_for": [],
                "tags": ["runtime", "release", "brief", "migration", "advice"],
                "outputs": ["advice"],
                "enabled": True,
                "priority": 90,
                "root_dir": "skills/local/runtime-redesign-advisor",
                "skill_file": "skills/local/runtime-redesign-advisor/SKILL.md",
            }),
        ],
    }

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)

    assert plan.work_units[0].preferred_skill == "runtime-redesign-advisor"
    assert plan.work_units[0].binding_profile == "general_support_owner"
    assert plan.work_units[0].binding_reason == "Selected the only supporting skill."
