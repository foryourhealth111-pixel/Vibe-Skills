from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_local_kernel_resume import _completed_result
from vgo_runtime import canonical_entry
from vgo_runtime.kernel import loop
from vgo_runtime.kernel._io import exclusive_run_update
from vgo_runtime.kernel.finder import find_skill_candidates, resolve_skill_candidates
from vgo_runtime.kernel.skill_index import build_skill_index
from vgo_runtime.kernel.task_card import build_task_card


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loop, "_resolve_host_root_paths", lambda **kwargs: ())


def _organization(*, skill: str | None = None) -> dict:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [{
            "module_id": "wu-1",
            "goal": "Produce the approved report.",
            "candidate_skill_ids": [skill] if skill else [],
            "execution_mode": "skill_assigned" if skill else "agent_direct",
            "write_scope": "reports/**",
            "expected_outputs": ["reports/approved.md"],
            "verification": ["Check the approved report against the source."],
            "acceptance_criteria": [{
                "criterion_id": "report-result",
                "description": "The report satisfies the approved request.",
                "verification_mode": "automated",
            }],
        }],
        "selected_skills": [{
            "skill_id": skill, "module_ids": ["wu-1"],
            "responsibility": "Write the report.", "reason": "The Agent selected this owner.",
        }] if skill else [],
        "uncovered_modules": [],
    }


@pytest.mark.parametrize("field,value", [
    ("write_scope", "reports/approved.md"),
    ("expected_outputs", ["reports/revised.md"]),
    ("verification", ["Check the revised report against the new source."]),
])
def test_direct_contract_survives_resume_and_invalidates_revised_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object,
) -> None:
    calls = []

    def execute(agent, task, unit, *, work_root):
        calls.append(unit)
        return _completed_result(unit, work_root, f"Report execution {len(calls)}")

    monkeypatch.setattr(loop, "execute_work_unit", execute)
    organization = _organization()
    arguments = dict(
        agent_root=tmp_path / "agent", run_id="direct-contract",
        context={"deliverables": ["report"]}, agent_skill_organization=organization,
    )
    first = loop.run_local_kernel(**arguments, prompt="Write a report.")
    unit = first["plan"]["work_units"][0]
    declared = organization["modules"][0]
    assert unit["write_scope"] == declared["write_scope"]
    assert list(unit["expected_artifacts"]) == declared["expected_outputs"]
    assert list(unit["verification"]) == declared["verification"]
    assert first["verification"]["result"] == "done"

    resumed = loop.run_local_kernel(**arguments, prompt="continue")
    assert len(calls) == 1
    assert resumed["reused_work_units"] == ["wu-1"]
    declared[field] = value
    revised = loop.run_local_kernel(**arguments, prompt="continue")
    assert len(calls) == 2
    assert revised["reused_work_units"] == []
    inspected = loop.inspect_local_run(agent_root=arguments["agent_root"], run_id="direct-contract")
    persisted = inspected["plan"]["work_units"][0]
    assert persisted["write_scope"] == declared["write_scope"]
    assert list(persisted["expected_artifacts"]) == declared["expected_outputs"]
    assert list(persisted["verification"]) == declared["verification"]


@pytest.mark.parametrize("field,value", [
    ("write_scope", None), ("write_scope", ""), ("write_scope", ["reports/**"]),
    ("expected_outputs", None), ("expected_outputs", []),
    ("expected_outputs", "report.md"), ("expected_outputs", [""]),
    ("verification", None), ("verification", []),
    ("verification", "Check the report."), ("verification", [42]),
])
def test_direct_contract_rejects_missing_or_malformed_declarations(
    tmp_path: Path, field: str, value: object,
) -> None:
    organization = _organization()
    if value is None:
        del organization["modules"][0][field]
    else:
        organization["modules"][0][field] = value
    with pytest.raises(ValueError, match=field):
        loop.run_local_kernel(
            agent_root=tmp_path / "agent", prompt="Write a report.",
            context={"deliverables": ["report"]}, run_id="invalid-direct", execute=False,
            agent_skill_organization=organization,
        )
    assert not (tmp_path / "agent/.vibeskills/runs/invalid-direct/task-card.json").exists()


def _canonical_arguments(tmp_path: Path) -> dict:
    return dict(
        repo_root=REPO_ROOT, host_id="codex", entry_id="vibe",
        workspace_root=tmp_path / "workspace", artifact_root=tmp_path / "workspace",
        local_agent_root=tmp_path / "agent", run_id="canonical-lock",
        prompt="Write a report.",
    )


def test_rejected_canonical_launch_preserves_all_accepted_artifacts(tmp_path: Path) -> None:
    arguments = _canonical_arguments(tmp_path)
    result = canonical_entry.launch_canonical_vibe(**arguments)
    run_root = Path(result.artifacts["run_state"]).parent
    snapshot = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for root in (result.session_root, run_root)
        for path in root.rglob("*") if path.is_file()
    }
    with exclusive_run_update(run_root):
        with pytest.raises(RuntimeError, match="already being updated"):
            canonical_entry.launch_canonical_vibe(**arguments)
    assert snapshot == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in snapshot}
    assert canonical_entry.launch_canonical_vibe(**arguments).summary["run_id"] == result.run_id


def test_canonical_launch_keeps_run_locked_through_summary_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _canonical_arguments(tmp_path)
    build_summary = canonical_entry.build_runtime_summary
    publication_checked = []

    def guarded_summary(**kwargs):
        with pytest.raises(RuntimeError, match="already being updated"):
            loop.run_local_kernel(
                agent_root=arguments["local_agent_root"], workspace_root=arguments["workspace_root"],
                run_id=arguments["run_id"], prompt="continue", execute=False,
            )
        publication_checked.append(True)
        return build_summary(**kwargs)

    monkeypatch.setattr(canonical_entry, "build_runtime_summary", guarded_summary)
    result = canonical_entry.launch_canonical_vibe(**arguments)
    assert publication_checked == [True]
    assert json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))["launch_status"] == "verified"
    loop.run_local_kernel(
        agent_root=arguments["local_agent_root"], workspace_root=arguments["workspace_root"],
        run_id=result.run_id, prompt="continue", execute=False,
    )


@pytest.fixture
def manual_skill(tmp_path: Path):
    agent_root = tmp_path / "agent"
    descriptor = agent_root / "vibe/skills/local/manual-report/SKILL.md"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text(
        "---\nname: manual-report\ndescription: Write a report.\n"
        "disable-model-invocation: true\noutputs: [report]\n---\n",
        encoding="utf-8",
    )
    index = build_skill_index(agent_root)
    assert index["skills"][0]["explicit_only"] is True
    return agent_root, index


@pytest.mark.parametrize("prompt,allowed", [
    ("Write a report.", False),
    ("Use $manual-report-extra to write a report.", False),
    ("Do not use $manual-report. Write a report.", False),
    ("Use $manual-report to write a report.", True),
    ("Use manual-report to write a report.", True),
    ("Use /manual-report to write a report.", True),
    ("请使用 manual-report 写报告。", True),
])
def test_manual_skill_requires_user_invocation_in_both_candidate_paths(manual_skill, prompt, allowed):
    _, index = manual_skill
    task = build_task_card(prompt=prompt, context={"deliverables": ["report"]})
    assert bool(find_skill_candidates(task, index)) is allowed
    assert bool(resolve_skill_candidates(task, index, skill_ids=("manual-report",))) is allowed


def test_agent_selection_does_not_authorize_a_manual_skill(manual_skill) -> None:
    agent_root, _ = manual_skill
    with pytest.raises(ValueError, match="selected unknown candidate skill"):
        loop.run_local_kernel(
            agent_root=agent_root, prompt="Write a report.", run_id="agent-choice",
            context={"deliverables": ["report"]}, execute=False,
            agent_skill_organization=_organization(skill="manual-report"),
        )


def test_explicit_manual_invocation_survives_continuation(manual_skill) -> None:
    agent_root, _ = manual_skill
    arguments = dict(
        agent_root=agent_root, run_id="manual-continuation",
        context={"deliverables": ["report"]}, execute=False,
        agent_skill_organization=_organization(skill="manual-report"),
    )
    loop.run_local_kernel(**arguments, prompt="Use $manual-report to write a report.")
    resumed = loop.run_local_kernel(**arguments, prompt="continue")
    assert resumed["plan"]["work_units"][0]["preferred_skill"] == "manual-report"
