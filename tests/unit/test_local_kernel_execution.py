from __future__ import annotations

import json
from pathlib import Path
import sys
import uuid

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

from vgo_runtime.kernel.executor import execute_work_unit
from vgo_runtime.kernel.finder import find_skill_candidates
from vgo_runtime.kernel.loop import inspect_local_run, inspect_main, run_local_kernel
from vgo_runtime.kernel.planner import build_work_plan
from vgo_runtime.kernel.run_state import load_run_state, write_run_state
from vgo_runtime.kernel.task_card import build_task_card
from vgo_runtime.kernel.verifier import verify_run


def run_local_kernel_with_agent_choice(**kwargs: object) -> dict[str, object]:
    discovery = run_local_kernel(
        **{
            **kwargs,
            "run_id": f"{kwargs.get('run_id', 'run-default')}-agent-discovery-{uuid.uuid4().hex[:8]}",
            "execute": False,
        }
    )
    modules: list[dict[str, object]] = []
    selected_by_skill: dict[str, dict[str, object]] = {}
    uncovered_modules: list[dict[str, object]] = []
    for unit in discovery["plan"]["work_units"]:
        candidate_skill_ids = list(unit["fallback_skills"])
        modules.append(
            {
                "module_id": unit["id"],
                "goal": unit["goal"],
                "candidate_skill_ids": candidate_skill_ids,
                "execution_mode": "skill_assigned" if candidate_skill_ids else "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": f"{unit['id']}-result",
                        "description": f"{unit['goal']} satisfies the requested outcome.",
                        "verification_mode": "automated",
                    }
                ],
            }
        )
        if not candidate_skill_ids:
            uncovered_modules.append(
                {"module_id": unit["id"], "reason": "No local candidate owns this test module."}
            )
            continue
        skill_id = candidate_skill_ids[0]
        selected = selected_by_skill.setdefault(
            skill_id,
            {
                "skill_id": skill_id,
                "module_ids": [],
                "responsibility": unit["goal"],
                "reason": "The test Agent selected the first matching local owner.",
            },
        )
        selected["module_ids"].append(unit["id"])

    organization = {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": modules,
        "selected_skills": list(selected_by_skill.values()),
        "uncovered_modules": uncovered_modules,
        "workflow_level_contract": {
            "L": "Use one serial governed lane.",
            "XL": "Use bounded waves when needed.",
        },
    }
    return run_local_kernel(**kwargs, agent_skill_organization=organization)


def _with_source_metadata(
    entry: dict[str, object],
    *,
    source_kind: str = "vibe_local",
    source_order: int = 0,
) -> dict[str, object]:
    root_dir = str(entry["root_dir"])
    skill_file = str(entry["skill_file"])
    base_path = "C:/agent/vibe"
    if source_kind == "vibe_local":
        source_root = "skills/local"
        source_priority = source_order
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


def _index_payload() -> dict[str, object]:
    return {
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
            })
        ],
    }


def test_execute_work_unit_records_scaffold_that_needs_execution() -> None:
    task_card = build_task_card(prompt="Review the runtime change.")
    plan = build_work_plan(task_card, find_skill_candidates(task_card, _index_payload()))

    result = execute_work_unit(Path("D:/agent-root"), task_card, plan.work_units[0])

    assert result.work_unit_id == "wu-1"
    assert result.status == "needs_execution"
    assert result.lifecycle_state == "scaffolded"
    assert result.used_skill is None
    assert result.artifact_kind == "scaffold"
    assert result.proof_ready is False
    assert result.artifacts == ("review notes",)
    assert result.artifact_paths == ()
    assert result.proof_artifact_paths == ()
    assert result.checked_targets == ("review notes exists", "review findings are explicit")
    assert result.proof[0] == "wu-1: scaffolded for bound skill code-review"
    assert "requires real execution evidence" in result.notes[0]


def test_run_local_kernel_without_agent_organization_does_not_bind_planner_choice(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    skill_dir = agent_root / "vibe" / "skills" / "local" / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nid: code-review\nname: Code Review\ndescription: Review implementation risk and test gaps.\nenabled: true\n---\n",
        encoding="utf-8",
    )

    result = run_local_kernel(
        agent_root=agent_root,
        prompt="Review the runtime redesign and produce review notes.",
        run_id="agent-organization-required",
        execute=False,
    )

    assert result["state"] == "awaiting_agent_skill_organization"
    assert result["agent_skill_organization"] is None
    assert result["module_assignments"]["source"] is None
    assert result["module_assignments"]["units"] == []
    assert result["plan"]["work_units"][0]["preferred_skill"] is None
    assert "code-review" in result["plan"]["work_units"][0]["fallback_skills"]


def test_verify_run_requests_rework_when_a_work_unit_fails() -> None:
    task_card = build_task_card(
        prompt="Review the runtime change.",
        context={"completion_criteria": ["review exists"]},
    )
    plan = build_work_plan(task_card, find_skill_candidates(task_card, _index_payload()))
    failed_result = type("Result", (), {
        "work_unit_id": "wu-1",
        "status": "failed",
        "artifacts": (),
        "notes": ("execution failed",),
        "failure_reason": "broken step",
    })()

    verification = verify_run(task_card, plan, (failed_result,))

    assert verification.result == "revise_execution"
    assert verification.failed_criteria == ("review exists",)


def test_verify_run_reports_needs_execution_for_scaffold_only_result() -> None:
    task_card = build_task_card(
        prompt="Review the runtime change.",
        context={"completion_criteria": ["review exists"]},
    )
    plan = build_work_plan(task_card, find_skill_candidates(task_card, _index_payload()))
    result = execute_work_unit(Path("D:/agent-root"), task_card, plan.work_units[0])

    verification = verify_run(task_card, plan, (result,))

    assert verification.result == "needs_execution"
    assert verification.failed_criteria == ("review exists",)
    assert any("requires real execution evidence" in note for note in verification.notes)


def test_run_state_round_trip_persists_json(tmp_path: Path) -> None:
    state_path = tmp_path / "run-state.json"
    run_state = write_run_state(
        state_path,
        run_id="run-001",
        task_id="task-001",
        state="plan",
        continuation_mode="revised",
        accepted_revision_count=1,
        active_work_unit="wu-1",
        completed_work_units=("wu-0",),
        failed_work_units=(),
        reused_work_units=("wu-0",),
        superseded_work_units=("wu-old",),
    )

    loaded = load_run_state(state_path)

    assert run_state.run_id == "run-001"
    assert loaded.continuation_mode == "revised"
    assert loaded.accepted_revision_count == 1
    assert loaded.active_work_unit == "wu-1"
    assert loaded.completed_work_units == ("wu-0",)
    assert loaded.reused_work_units == ("wu-0",)
    assert loaded.superseded_work_units == ("wu-old",)
    assert loaded.state == "plan"


def test_run_local_kernel_writes_run_artifacts(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    (vibe_root / "skills" / "local" / "code-review").mkdir(parents=True, exist_ok=True)
    (vibe_root / "skills" / "local" / "code-review" / "SKILL.md").write_text(
        """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        encoding="utf-8",
    )

    result = run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Review the runtime redesign and produce review notes.",
        context={
            "deliverables": ["review notes"],
            "completion_criteria": ["review notes exist"],
            "mode": "design",
        },
        run_id="run-123",
    )

    run_root = vibe_root / "runs" / "run-123"
    assert result["run_id"] == "run-123"
    assert list(result)[:4] == ["run_id", "work_dossier", "artifacts", "work_summary"]
    assert result["verification"]["result"] == "needs_execution"
    assert not result["verification"]["evidence"]
    assert result["artifacts"]["work_dossier"].endswith("work-dossier.json")
    assert result["artifacts"]["work_dossier_markdown"].endswith("work-dossier.md")
    assert result["artifacts"]["task_card"].endswith("task-card.json")
    assert result["artifacts"]["work_plan"].endswith("plan.json")
    assert result["artifacts"]["module_assignments"].endswith("module-assignments.json")
    assert result["artifacts"]["work_results"].endswith("work-results.json")
    assert result["artifacts"]["verification"].endswith("verification.json")
    assert result["work_summary"]["proof_ready"] is False
    assert result["work_summary"]["work_unit_count"] == 1
    assert result["work_summary"]["primary_artifact"] == "work_dossier"
    assert result["work_summary"]["primary_artifact_path"].endswith("work-dossier.json")
    assert result["work_dossier"]["task_card"]["id"] == result["task_card"]["id"]
    assert result["work_dossier"]["work_plan"]["task_id"] == result["task_card"]["id"]
    assert result["work_dossier"]["module_assignments"]["task_id"] == result["task_card"]["id"]
    assert result["work_dossier"]["verification"]["result"] == "needs_execution"
    assert result["work_dossier"]["closure"]["task"] == result["task_card"]["goal"]
    assert result["work_dossier"]["closure"]["skills"]["bound_skill_ids"] == ["code-review"]
    assert set(result["work_dossier"]["closure"]["skills"]) == {"bound_skill_ids"}
    assert result["work_dossier"]["closure"]["outputs"]["artifacts"] == ["review notes"]
    assert result["work_dossier"]["reading_order"] == [
        "task_card",
        "work_plan",
        "module_assignments",
        "work_results",
        "verification",
        "proof",
    ]
    assert result["work_dossier"]["artifact_paths"]["task_card"].endswith("task-card.json")
    assert result["work_dossier"]["artifact_paths"]["work_plan"].endswith("plan.json")
    assert result["work_dossier"]["artifact_paths"]["module_assignments"].endswith("module-assignments.json")
    assert result["work_dossier"]["artifact_paths"]["work_results"].endswith("work-results.json")
    assert result["work_dossier"]["artifact_paths"]["verification"].endswith("verification.json")
    assert result["work_dossier"]["artifact_paths"]["proof"].endswith("work-dossier.json")
    assert result["work_dossier"]["artifact_paths"]["proof_markdown"].endswith("work-dossier.md")
    assert result["work_dossier"]["closure"]["proof"]["result"] == "needs_execution"
    assert result["work_dossier"]["closure"]["proof"]["evidence_count"] == len(result["verification"]["evidence"])
    assert result["work_plan"]["task_id"] == result["task_card"]["id"]
    assert result["module_assignments"]["task_id"] == result["task_card"]["id"]
    assert result["work_results"]["work_results"][0]["status"] == "needs_execution"
    assert result["work_results"]["work_results"][0]["used_skill"] is None
    assert result["work_results"]["work_results"][0]["artifact_kind"] == "scaffold"
    assert result["work_results"]["work_results"][0]["proof_ready"] is False
    assert result["work_dossier_path"].endswith("work-dossier.json")
    assert result["work_dossier_markdown_path"].endswith("work-dossier.md")
    assert result["work_plan_path"].endswith("plan.json")
    assert (run_root / "work-dossier.json").exists()
    assert (run_root / "work-dossier.md").exists()
    assert (run_root / "task-card.json").exists()
    assert (run_root / "plan.json").exists()
    assert (run_root / "module-assignments.json").exists()
    assert (run_root / "work-results.json").exists()
    assert (run_root / "work-units" / "wu-1" / "artifacts").exists()
    assert (run_root / "work-units" / "wu-1" / "execution-receipt.json").exists()
    assert (run_root / "run-state.json").exists()
    assert (run_root / "verification.json").exists()
    artifact_text = (run_root / "work-units" / "wu-1" / "artifacts" / "01-review-notes.md").read_text(encoding="utf-8")
    dossier_text = (run_root / "work-dossier.md").read_text(encoding="utf-8")
    assert "## Findings" in artifact_text
    assert "## Evidence To Check" in artifact_text
    assert "- review notes exists" in artifact_text
    assert "## Conclusion" in dossier_text
    assert "## Reading Path" in dossier_text
    assert "## Task Card" in dossier_text
    assert "## Work Plan" in dossier_text
    assert "## Work Binding" in dossier_text
    assert "## Work Results" in dossier_text
    assert "## Verification" in dossier_text
    assert "## Proof" in dossier_text
    assert "- task card: " in dossier_text
    assert "- work plan: " in dossier_text
    assert "- module assignments: " in dossier_text
    assert "- work results: " in dossier_text
    assert "- verification: " in dossier_text
    assert dossier_text.index("## Task Card") < dossier_text.index("## Task Evolution")
    assert dossier_text.index("## Verification") < dossier_text.index("## Proof")
    delivery_path = Path(result["work_results"]["work_results"][0]["artifact_paths"][0])
    assert delivery_path.is_file()
    assert "work-products" in str(delivery_path)


def test_run_local_kernel_infers_deliverables_without_explicit_context(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    (vibe_root / "skills" / "local" / "code-review").mkdir(parents=True, exist_ok=True)
    (vibe_root / "skills" / "local" / "code-review" / "SKILL.md").write_text(
        """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        encoding="utf-8",
    )

    result = run_local_kernel(
        agent_root=agent_root,
        prompt="Review the runtime redesign and produce review notes and add focused tests.",
        run_id="run-inferred",
    )

    assert result["run_id"] == "run-inferred"
    assert result["task_card"]["deliverables"] == ("review notes", "focused tests")
    assert result["task_card"]["completion_criteria"] == (
        "review notes exists",
        "focused tests exists",
        "review findings are explicit",
        "tests cover the changed behavior",
    )
    run_root = vibe_root / "runs" / "run-inferred"
    assert (run_root / "plan.json").exists()


def test_inspect_local_run_reads_run_artifacts_and_summary(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    (vibe_root / "skills" / "local" / "code-review").mkdir(parents=True, exist_ok=True)
    (vibe_root / "skills" / "local" / "code-review" / "SKILL.md").write_text(
        """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        encoding="utf-8",
    )

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Review the runtime redesign and produce review notes.",
        context={
            "deliverables": ["review notes"],
            "completion_criteria": ["review notes exist"],
            "mode": "design",
        },
        run_id="run-123",
    )

    inspected = inspect_local_run(agent_root=agent_root, run_id="run-123")

    assert inspected["run_id"] == "run-123"
    assert list(inspected)[:4] == ["run_id", "work_dossier", "summary", "artifacts"]
    assert inspected["summary"]["verification_result"] == "needs_execution"
    assert inspected["summary"]["proof_ready"] is False
    assert inspected["summary"]["work_unit_count"] == 1
    assert inspected["summary"]["primary_artifact"] == "work_dossier"
    assert inspected["summary"]["primary_artifact_path"].endswith("work-dossier.json")
    assert inspected["artifacts"]["work_dossier"].endswith("work-dossier.json")
    assert inspected["artifacts"]["work_dossier_markdown"].endswith("work-dossier.md")
    assert inspected["work_dossier"]["task_card"]["id"] == inspected["task_card"]["id"]
    assert inspected["work_dossier"]["work_plan"]["task_id"] == inspected["task_card"]["id"]
    assert inspected["work_dossier"]["verification"]["result"] == "needs_execution"
    assert inspected["work_dossier"]["reading_order"] == [
        "task_card",
        "work_plan",
        "module_assignments",
        "work_results",
        "verification",
        "proof",
    ]
    assert inspected["work_dossier"]["artifact_paths"]["proof_markdown"].endswith("work-dossier.md")
    assert inspected["work_dossier"]["closure"]["skills"]["bound_skill_ids"] == ["code-review"]
    assert inspected["work_dossier"]["closure"]["proof"]["evidence_count"] == len(inspected["verification"]["evidence"])
    assert inspected["task_card"]["goal"] == "Review the runtime redesign and produce review notes."
    assert inspected["artifacts"]["work_plan"].endswith("plan.json")
    assert inspected["work_plan"]["work_units"]
    assert inspected["artifacts"]["plan"] == inspected["artifacts"]["work_plan"]
    assert inspected["module_assignments"]["units"][0]["bound_skill"] == "code-review"
    assert inspected["module_assignments"]["units"][0]["binding_profile"] == "agent_selected"
    assert inspected["module_assignments"]["units"][0]["binding_reason"] == "The test Agent selected the first matching local owner."
    assert inspected["work_results"]["work_results"][0]["status"] == "needs_execution"
    assert inspected["work_results"]["work_results"][0]["used_skill"] is None
    assert inspected["work_results"]["work_results"][0]["artifact_kind"] == "scaffold"
    assert inspected["work_results"]["work_results"][0]["proof_ready"] is False
    assert inspected["work_results"]["work_results"][0]["artifact_paths"]
    assert inspected["work_results"]["work_results"][0]["proof_artifact_paths"]
    assert inspected["work_results"]["work_results"][0]["execution_receipt_path"].endswith("execution-receipt.json")
    assert not inspected["verification"]["evidence"]
    assert inspected["artifacts"]["verification"].endswith("verification.json")
    assert inspected["artifacts"]["module_assignments"].endswith("module-assignments.json")
    assert inspected["artifacts"]["work_results"].endswith("work-results.json")


def test_run_local_kernel_writes_host_aware_skills_catalog_artifact(tmp_path: Path) -> None:
    agent_root = tmp_path / "skills"
    workspace_root = tmp_path / "workspace"
    vibe_root = agent_root / "vibe"
    local_skill_dir = vibe_root / "skills" / "local" / "code-review"
    local_skill_dir.mkdir(parents=True, exist_ok=True)
    (local_skill_dir / "SKILL.md").write_text(
        """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        encoding="utf-8",
    )
    host_skill_dir = (agent_root / "write-report")
    host_skill_dir.mkdir(parents=True, exist_ok=True)
    (host_skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
enabled: true
---""",
        encoding="utf-8",
    )

    result = run_local_kernel(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="host-aware-run",
        host_id="codex",
        workspace_root=workspace_root,
    )

    catalog_path = Path(result["artifacts"]["skills_catalog"])
    assert catalog_path.name == "skills-catalog.json"
    assert catalog_path.is_file()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["host_roots"] == [
        str(agent_root.resolve()),
    ]
    assert catalog["catalog_source_kinds"] == ["host_installed", "vibe_local"]
    assert any(
        entry["id"] == "write-report" and entry["source_kind"] == "host_installed" and entry["active"] is True
        for entry in catalog["entries"]
    )
    assert result["work_dossier"]["artifact_paths"]["skills_catalog"].endswith("skills-catalog.json")


def test_verify_run_rejects_incomplete_proof() -> None:
    task_card = build_task_card(prompt="Review the runtime change.")
    plan = build_work_plan(task_card, find_skill_candidates(task_card, _index_payload()))
    incomplete_result = type("Result", (), {
        "work_unit_id": "wu-1",
        "status": "completed",
        "used_skill": "code-review",
        "artifacts": ("review notes",),
        "artifact_paths": (),
        "proof_artifact_paths": (),
        "checked_targets": ("review notes exists", "review findings are explicit"),
        "notes": ("execution completed",),
        "proof": ("wu-1: used skill code-review",),
        "execution_receipt_path": None,
        "failure_reason": None,
    })()

    verification = verify_run(task_card, plan, (incomplete_result,))

    assert verification.result == "revise_execution"
    assert any("missing artifact reference review notes" in note for note in verification.notes)


def test_run_local_kernel_writes_skill_aware_artifact_content(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    local_skills = {
        "code-review": """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
tags:
  - review
  - testing
enabled: true
---""",
        "write-plan": """---
id: write-plan
name: Write Plan
description: Turn a task into explicit work steps.
when_to_use:
  - The user needs a plan.
not_for:
  - Final review.
inputs:
  - task goal
outputs:
  - work plan
tags:
  - planning
enabled: true
---""",
    }
    for skill_id, content in local_skills.items():
        skill_dir = vibe_root / "skills" / "local" / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Review the runtime redesign and produce an implementation plan and add focused tests.",
        run_id="skill-aware-run",
    )

    run_root = vibe_root / "runs" / "skill-aware-run"
    review_text = (run_root / "work-units" / "wu-1" / "artifacts" / "01-review-notes.md").read_text(encoding="utf-8")
    plan_text = (run_root / "work-units" / "wu-2" / "artifacts" / "01-implementation-plan.md").read_text(encoding="utf-8")
    test_text = (run_root / "work-units" / "wu-3" / "artifacts" / "01-focused-tests.md").read_text(encoding="utf-8")

    assert "## Findings" in review_text
    assert "## Recommendation" in review_text
    assert "## Work Steps" in plan_text
    assert "## Exit Criteria" in plan_text
    assert "## Test Targets" in test_text
    assert "## Assertions" in test_text


def test_run_local_kernel_writes_report_artifact_content(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    skill_dir = vibe_root / "skills" / "local" / "write-report"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
tags:
  - report
  - summary
enabled: true
---""",
        encoding="utf-8",
    )

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="report-run",
    )

    run_root = vibe_root / "runs" / "report-run"
    report_text = (run_root / "work-units" / "wu-1" / "artifacts" / "01-report.md").read_text(encoding="utf-8")

    assert "## Summary" in report_text
    assert "## Key Points" in report_text
    assert "## Notes" in report_text


def test_run_local_kernel_resumes_existing_run_and_keeps_original_goal(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    (vibe_root / "skills" / "local" / "code-review").mkdir(parents=True, exist_ok=True)
    (vibe_root / "skills" / "local" / "code-review" / "SKILL.md").write_text(
        """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        encoding="utf-8",
    )

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Review the runtime redesign. Produce review notes.",
        run_id="resume-run",
    )
    resumed = run_local_kernel(
        agent_root=agent_root,
        prompt="Continue by adding focused tests and provide verification evidence.",
        run_id="resume-run",
        agent_skill_organization={
            "schema_version": "agent_skill_organization_v1",
            "derived_by": "agent",
            "workflow_level": "L",
            "modules": [
                {"module_id": "wu-1", "goal": "Produce review notes", "candidate_skill_ids": ["code-review"], "execution_mode": "skill_assigned", "acceptance_criteria": [{"criterion_id": "wu-1-result", "description": "The review notes exist.", "verification_mode": "automated"}]},
                {"module_id": "wu-2", "goal": "Produce focused tests", "candidate_skill_ids": ["code-review"], "execution_mode": "skill_assigned", "acceptance_criteria": [{"criterion_id": "wu-2-result", "description": "The focused tests exist.", "verification_mode": "automated"}]},
                {"module_id": "wu-3", "goal": "Produce verification evidence", "candidate_skill_ids": ["code-review"], "execution_mode": "skill_assigned", "acceptance_criteria": [{"criterion_id": "wu-3-result", "description": "The verification evidence exists.", "verification_mode": "automated"}]},
            ],
            "selected_skills": [
                {
                    "skill_id": "code-review",
                    "module_ids": ["wu-1", "wu-2", "wu-3"],
                    "responsibility": "Review the change and produce its test evidence.",
                    "reason": "The Agent selected the local review owner.",
                }
            ],
            "uncovered_modules": [],
            "workflow_level_contract": {
                "L": "Use one serial governed lane.",
                "XL": "Use bounded waves when needed.",
            },
        },
    )

    assert resumed["task_card"]["goal"] == "Review the runtime redesign. Produce review notes."
    assert resumed["task_card"]["initial_goal"] == "Review the runtime redesign. Produce review notes."
    assert len(resumed["task_card"]["accepted_revisions"]) == 1
    assert resumed["task_card"]["accepted_revisions"][0]["added_deliverables"] == (
        "focused tests",
        "verification evidence",
    )
    assert resumed["task_card"]["deliverables"] == (
        "review notes",
        "focused tests",
        "verification evidence",
    )
    assert resumed["completed_work_units"] == []
    assert resumed["failed_work_units"] == ["wu-1", "wu-2", "wu-3"]
    assert resumed["reused_work_units"] == []
    assert resumed["superseded_work_units"] == []
    assert resumed["work_summary"]["continuation_mode"] == "revised"
    assert resumed["work_summary"]["accepted_revision_count"] == 1
    assert resumed["work_summary"]["reused_work_unit_count"] == 0
    inspected = inspect_local_run(agent_root=agent_root, run_id="resume-run")
    assert inspected["summary"]["task_id"] == resumed["task_card"]["id"]
    assert inspected["summary"]["work_unit_count"] == 3
    assert inspected["summary"]["continuation_mode"] == "revised"
    assert inspected["summary"]["accepted_revision_count"] == 1
    assert inspected["summary"]["reused_work_unit_count"] == 0
    assert inspected["summary"]["superseded_work_unit_count"] == 0
    assert [unit["bound_skill"] for unit in inspected["module_assignments"]["units"]] == [
        "code-review",
        "code-review",
        "code-review",
    ]


def test_local_kernel_rejects_unstructured_agent_module_acceptance(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    discovery = run_local_kernel(
        agent_root=agent_root,
        prompt="Summarize the local note.",
        run_id="invalid-acceptance-discovery",
        execute=False,
    )
    module_id = discovery["plan"]["work_units"][0]["id"]

    with pytest.raises(ValueError, match="acceptance_criteria must contain objects"):
        run_local_kernel(
            agent_root=agent_root,
            prompt="Summarize the local note.",
            run_id="invalid-acceptance",
            execute=False,
            agent_skill_organization={
                "schema_version": "agent_skill_organization_v1",
                "derived_by": "agent",
                "workflow_level": "L",
                "modules": [
                    {
                        "module_id": module_id,
                        "goal": "Summarize the note.",
                        "candidate_skill_ids": [],
                        "execution_mode": "agent_direct",
                        "acceptance_criteria": ["The summary exists."],
                    }
                ],
                "selected_skills": [],
                "uncovered_modules": [],
                "workflow_level_contract": {
                    "L": "Run the direct module serially.",
                    "XL": "Use bounded waves if scope expands.",
                },
            },
        )


def test_local_kernel_plan_preserves_agent_module_acceptance(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    discovery = run_local_kernel(
        agent_root=agent_root,
        prompt="Summarize the local note.",
        run_id="preserve-acceptance-discovery",
        execute=False,
    )
    module_id = discovery["plan"]["work_units"][0]["id"]
    acceptance = [
        {
            "criterion_id": "summary-result",
            "description": "The summary answers the requested facts.",
            "verification_mode": "automated",
        }
    ]

    result = run_local_kernel(
        agent_root=agent_root,
        prompt="Summarize the local note.",
        run_id="preserve-acceptance",
        execute=False,
        agent_skill_organization={
            "schema_version": "agent_skill_organization_v1",
            "derived_by": "agent",
            "workflow_level": "L",
            "modules": [
                {
                    "module_id": module_id,
                    "goal": "Summarize the note.",
                    "candidate_skill_ids": [],
                    "execution_mode": "agent_direct",
                    "acceptance_criteria": acceptance,
                }
            ],
            "selected_skills": [],
            "uncovered_modules": [],
            "workflow_level_contract": {
                "L": "Run the direct module serially.",
                "XL": "Use bounded waves if scope expands.",
            },
        },
    )

    assert list(result["plan"]["work_units"][0]["acceptance_criteria"]) == acceptance


def test_inspect_local_run_reports_skills_catalog_and_selected_skill_source_kind(tmp_path: Path) -> None:
    agent_root = tmp_path / "skills"
    workspace_root = tmp_path / "workspace"
    host_skill_dir = agent_root / "write-report"
    host_skill_dir.mkdir(parents=True, exist_ok=True)
    (host_skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
enabled: true
---""",
        encoding="utf-8",
    )

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="inspect-host-aware-run",
        host_id="codex",
        workspace_root=workspace_root,
    )

    inspected = inspect_local_run(agent_root=agent_root, run_id="inspect-host-aware-run")

    assert inspected["artifacts"]["skills_catalog"].endswith("skills-catalog.json")
    assert Path(inspected["artifacts"]["skills_catalog"]).is_file()
    unit = inspected["module_assignments"]["units"][0]
    assert unit["bound_skill"] == "write-report"
    assert unit["provenance"]["source_kind"] == "host_installed"
    assert unit["skill_source_kind"] == "host_installed"
    assert [row["binding_profile"] for row in inspected["module_assignments"]["units"]] == ["agent_selected"]
    assert inspected["work_dossier"]["artifact_paths"]["skills_catalog"].endswith("skills-catalog.json")
    assert inspected["skills_catalog"]["host_roots"] == [
        str(agent_root.resolve()),
    ]


def test_inspect_local_run_validates_requested_host_context(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    workspace_root = tmp_path / "workspace"
    extra_skills_root = workspace_root / "extra-skills"
    (workspace_root / ".vibeskills").mkdir(parents=True, exist_ok=True)
    (workspace_root / ".vibeskills" / "skill-roots.json").write_text(
        json.dumps({"schema_version": 1, "extra_skill_roots": ["extra-skills"]}),
        encoding="utf-8",
    )
    host_skill_dir = extra_skills_root / "write-report"
    host_skill_dir.mkdir(parents=True, exist_ok=True)
    (host_skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
enabled: true
---""",
        encoding="utf-8",
    )

    run_local_kernel(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="inspect-opencode-run",
        host_id="opencode",
        workspace_root=workspace_root,
    )

    inspected = inspect_local_run(
        agent_root=agent_root,
        run_id="inspect-opencode-run",
        host_id="opencode",
        workspace_root=workspace_root,
    )

    assert inspected["host_context"] == {
        "host_id": "opencode",
        "workspace_root": str(workspace_root.resolve()),
        "resolved_host_roots": [
            str(extra_skills_root.resolve()),
            str(agent_root.resolve()),
        ],
        "matches_run_catalog": True,
    }

    with pytest.raises(ValueError, match="run skills catalog host roots do not match requested host context"):
        inspect_local_run(
            agent_root=agent_root,
            run_id="inspect-opencode-run",
            host_id="opencode",
            workspace_root=None,
        )


def test_inspect_main_passes_host_context_to_inspect_local_run(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    recorded: dict[str, object] = {}

    def fake_inspect_local_run(
        *,
        agent_root: Path,
        run_id: str,
        host_id: str | None = None,
        workspace_root: Path | None = None,
    ) -> dict[str, object]:
        recorded["agent_root"] = agent_root
        recorded["run_id"] = run_id
        recorded["host_id"] = host_id
        recorded["workspace_root"] = workspace_root
        return {"run_id": run_id, "summary": {"proof_ready": True}}

    monkeypatch.setattr("vgo_runtime.kernel.loop.inspect_local_run", fake_inspect_local_run)

    assert inspect_main(
        [
            "--agent-root", str(tmp_path / "agent"),
            "--run-id", "run-1",
            "--host-id", "opencode",
            "--workspace-root", str(tmp_path / "workspace"),
        ]
    ) == 0

    assert recorded == {
        "agent_root": tmp_path / "agent",
        "run_id": "run-1",
        "host_id": "opencode",
        "workspace_root": (tmp_path / "workspace"),
    }
    assert json.loads(capsys.readouterr().out) == {"run_id": "run-1", "summary": {"proof_ready": True}}


def test_run_local_kernel_does_not_reuse_work_when_selected_skill_source_changes(tmp_path: Path) -> None:
    agent_root = tmp_path / "skills"
    workspace_root = tmp_path / "workspace"
    vibe_local_skill_dir = agent_root / "vibe" / "skills" / "local" / "write-report"
    vibe_local_skill_dir.mkdir(parents=True, exist_ok=True)
    (vibe_local_skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
enabled: true
---""",
        encoding="utf-8",
    )

    first = run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="source-shift-run",
    )

    assert first["module_assignments"]["units"][0]["provenance"]["source_kind"] == "vibe_local"
    assert first["reused_work_units"] == []

    host_skill_dir = agent_root / "write-report"
    host_skill_dir.mkdir(parents=True, exist_ok=True)
    (host_skill_dir / "SKILL.md").write_text(
        """---
id: write-report
name: Write Report
description: Turn results into a concise report or summary.
when_to_use:
  - The user needs a report, summary, or briefing.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
enabled: true
---""",
        encoding="utf-8",
    )

    resumed = run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Summarize the benchmark results and produce a report.",
        run_id="source-shift-run",
        host_id="codex",
        workspace_root=workspace_root,
    )

    assert resumed["reused_work_units"] == []
    assert resumed["module_assignments"]["units"][0]["provenance"]["source_kind"] == "host_installed"
    assert resumed["work_results"]["work_results"][0]["reused_from_work_unit_id"] is None


def test_run_local_kernel_can_replace_deliverables_and_mark_superseded_work(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-root"
    vibe_root = agent_root / "vibe"
    skill_manifests = {
        "code-review": """---
id: code-review
name: Code Review
description: Review implementation risk and test gaps.
when_to_use:
  - The user asks for a review.
not_for:
  - Building a feature from scratch.
inputs:
  - changed files
outputs:
  - findings
enabled: true
---""",
        "write-report": """---
id: write-report
name: Write Report
description: Turn results into a concise report.
when_to_use:
  - The user needs a report.
not_for:
  - Implementing code changes.
inputs:
  - results
outputs:
  - report
tags:
  - report
enabled: true
---""",
    }
    for skill_id, manifest in skill_manifests.items():
        skill_dir = vibe_root / "skills" / "local" / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(manifest, encoding="utf-8")

    run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Review the runtime redesign. Produce review notes.",
        run_id="replace-run",
    )
    replaced = run_local_kernel_with_agent_choice(
        agent_root=agent_root,
        prompt="Instead produce a report.",
        context={
            "revision_mode": "replace",
            "deliverables": ["report"],
            "completion_criteria": ["report exists"],
        },
        run_id="replace-run",
    )

    assert replaced["work_summary"]["continuation_mode"] == "revised"
    assert replaced["task_card"]["deliverables"] == ("report",)
    assert replaced["task_card"]["accepted_revisions"][0]["removed_deliverables"] == ("review notes",)
    assert replaced["task_card"]["accepted_revisions"][0]["added_deliverables"] == ("report",)
    assert replaced["reused_work_units"] == []
    assert replaced["superseded_work_units"] == ["wu-1"]
    inspected = inspect_local_run(agent_root=agent_root, run_id="replace-run")
    assert inspected["summary"]["superseded_work_unit_count"] == 1
    assert inspected["work_plan"]["superseded_work_units"][0]["expected_artifacts"] == ["review notes"]
    assert inspected["work_plan"]["superseded_work_units"][0]["lifecycle_state"] == "superseded"
    assert inspected["work_dossier"]["revision_lineage"]["superseded_work_units"][0]["artifacts"] == ["review notes"]
    assert inspected["work_dossier"]["closure"]["outputs"]["artifacts"] == ["report"]
