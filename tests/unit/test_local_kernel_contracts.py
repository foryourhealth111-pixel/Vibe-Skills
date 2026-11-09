from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_local_kernel_resume import _completed_result
from vgo_runtime import artifact_contract, canonical_entry
from vgo_runtime.kernel import loop
from vgo_runtime.kernel._io import exclusive_run_update
from vgo_runtime.kernel.finder import find_skill_candidates, resolve_skill_candidates
from vgo_runtime.kernel.skill_index import build_skill_index
from vgo_runtime.kernel.task_card import build_task_card


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep contract tests independent of skills installed on the host."""
    monkeypatch.setattr(loop, "_resolve_host_root_paths", lambda **kwargs: ())


def _organization(*, skill: str | None = None) -> dict:
    """Build an approved module contract for direct execution or a selected skill."""
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
    """Persist direct-module declarations and rerun completed work when a declaration changes."""
    calls = []

    def execute(agent, task, unit, *, work_root):
        """Record each execution and write distinguishable final report evidence."""
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


@pytest.mark.parametrize("execute", [False, True])
@pytest.mark.parametrize("skill", [None, "manual-report"])
def test_modules_with_identical_outputs_reuse_their_own_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manual_skill, execute: bool, skill: str | None,
) -> None:
    """Preserve each module's result and proof when approved outputs are identical."""
    calls = []

    def complete(agent, task, unit, *, work_root):
        """Record module execution and write evidence identifying its owner."""
        calls.append(unit.id)
        return _completed_result(unit, work_root, f"Execution of {unit.id}")

    monkeypatch.setattr(loop, "execute_work_unit", complete)
    agent_root, _ = manual_skill
    organization = _organization(skill=skill)
    if skill:
        organization["selected_skills"][0]["module_ids"] = ["wu-1", "wu-2"]
    organization["modules"] = [
        dict(organization["modules"][0], module_id=unit_id, depends_on=[])
        for unit_id in ("wu-1", "wu-2")
    ]
    arguments = dict(
        agent_root=agent_root, run_id="identical-outputs", prompt="Use $manual-report to write a report.",
        context={"deliverables": ["report", "report"], "revision_mode": "replace"},
        agent_skill_organization=organization,
    )
    loop.run_local_kernel(**arguments)
    resumed = loop.run_local_kernel(**arguments, execute=execute)
    assert calls == ["wu-1", "wu-2"]
    assert resumed["reused_work_units"] == ["wu-1", "wu-2"]
    for unit in resumed["plan"]["work_units"]:
        assert unit["reused_from_work_unit_id"] == unit["id"]
    for result in resumed["work_results"]["work_results"]:
        assert Path(result["artifact_paths"][0]).read_text(encoding="utf-8") == f"Execution of {result['work_unit_id']}"


@pytest.mark.parametrize("execute", [False, True])
def test_unique_skill_checkpoint_can_reuse_a_previous_module_id(
    manual_skill, monkeypatch: pytest.MonkeyPatch, execute: bool,
) -> None:
    """Allow unique ordinary outputs to reuse valid evidence under a previous module ID."""
    agent_root, _ = manual_skill
    calls = []

    def complete(agent, task, unit, *, work_root):
        """Count executions while producing a stable approved report."""
        calls.append(unit.id)
        return _completed_result(unit, work_root, "Approved report")

    monkeypatch.setattr(loop, "execute_work_unit", complete)
    arguments = dict(
        agent_root=agent_root, run_id="unique-checkpoint", prompt="Use $manual-report to write a report.",
        context={"deliverables": ["report"]}, agent_skill_organization=_organization(skill="manual-report"),
    )
    original = loop.run_local_kernel(**arguments)
    checkpoint_path = Path(original["artifacts"]["work_results"])
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["work_plan"]["work_units"][0]["id"] = "previous-report"
    checkpoint["work_results"][0]["work_unit_id"] = "previous-report"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    resumed = loop.run_local_kernel(**arguments, execute=execute)
    assert calls == ["wu-1"]
    assert resumed["reused_work_units"] == ["wu-1"]
    assert resumed["plan"]["work_units"][0]["reused_from_work_unit_id"] == "previous-report"


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
    """Reject invalid direct-module contracts before publishing a task card."""
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
    """Build a canonical launch with isolated workspace and agent roots."""
    return dict(
        repo_root=REPO_ROOT, host_id="codex", entry_id="vibe",
        workspace_root=tmp_path / "workspace", artifact_root=tmp_path / "workspace",
        local_agent_root=tmp_path / "agent", run_id="canonical-lock",
        prompt="Write a report.",
    )


def test_rejected_canonical_launch_preserves_all_accepted_artifacts(tmp_path: Path) -> None:
    """Preserve accepted artifact bytes and timestamps when a competing launch is rejected."""
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


@pytest.mark.parametrize("include_workspace", [False, True])
def test_canonical_launch_keeps_run_locked_through_summary_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, include_workspace: bool,
) -> None:
    """Retain ownership during summary publication for direct callers with either root form."""
    arguments = _canonical_arguments(tmp_path)
    build_summary = canonical_entry.build_runtime_summary
    publication_checked = []

    def guarded_summary(**kwargs):
        """Verify that a direct caller cannot update the run during summary publication."""
        with pytest.raises(RuntimeError, match="already being updated"):
            loop.run_local_kernel(
                agent_root=arguments["local_agent_root"],
                workspace_root=arguments["workspace_root"] if include_workspace else None,
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


def test_canonical_launch_locks_shared_session_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Serialize shared session publication across different workspace and agent roots."""
    arguments = _canonical_arguments(tmp_path)
    arguments["artifact_root"] = tmp_path / "shared-artifacts"
    competitor = dict(
        arguments, workspace_root=tmp_path / "other-workspace",
        local_agent_root=tmp_path / "other-agent",
    )
    build_summary = canonical_entry.build_runtime_summary
    attempted = []

    def guarded_summary(**kwargs):
        """Reject a competing publisher before it alters shared session receipts."""
        if not attempted:
            attempted.append(True)
            session_root = arguments["artifact_root"] / "outputs/runtime/vibe-sessions" / arguments["run_id"]
            before = {path: path.read_bytes() for path in session_root.rglob("*") if path.is_file()}
            with pytest.raises(RuntimeError, match="already being updated"):
                canonical_entry.launch_canonical_vibe(**competitor)
            assert before == {path: path.read_bytes() for path in before}
        return build_summary(**kwargs)

    monkeypatch.setattr(canonical_entry, "build_runtime_summary", guarded_summary)
    canonical_entry.launch_canonical_vibe(**arguments)
    assert attempted == [True]
    canonical_entry.launch_canonical_vibe(**competitor)


def test_legacy_projection_cannot_overwrite_canonical_task_card_through_session_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep overlapping legacy projections from replacing the canonical task card."""
    payload = json.loads((REPO_ROOT / "config/live-document-contract.json").read_text(encoding="utf-8"))
    payload["artifact_sink"]["legacy_write_mode"] = "dual_write"
    payload["artifact_sink"]["legacy_projection_root"] = payload["artifact_sink"]["session_receipts"]["root"]
    contract = artifact_contract.load_runtime_artifact_contract(REPO_ROOT).model_validate(payload)
    monkeypatch.setattr(artifact_contract, "_load_contract", lambda root: contract)
    arguments = _canonical_arguments(tmp_path)
    arguments["artifact_root"] = arguments["local_agent_root"]
    original = canonical_entry.launch_canonical_vibe(**arguments)
    loop.run_local_kernel(
        agent_root=arguments["local_agent_root"], run_id=arguments["run_id"],
        prompt="Write an unrelated summary.", execute=False,
    )
    canonical_entry.launch_canonical_vibe(**{**arguments, "prompt": "continue"})
    task_card = json.loads(Path(original.artifacts["task_card"]).read_text(encoding="utf-8"))
    assert task_card["goal"] == arguments["prompt"]
    assert not (original.session_root / "task-card.json").exists()


@pytest.fixture
def manual_skill(tmp_path: Path, request: pytest.FixtureRequest):
    """Install explicit-only test skills and return their indexed catalog."""
    agent_root = tmp_path / "agent"
    skill_ids = getattr(request, "param", "manual-report")
    if isinstance(skill_ids, str):
        skill_ids = (skill_ids,)
    for skill_id in skill_ids:
        descriptor = agent_root / f"vibe/skills/local/{skill_id}/SKILL.md"
        descriptor.parent.mkdir(parents=True)
        descriptor.write_text(
            f"---\nname: {skill_id}\ndescription: Write a report.\n"
            "disable-model-invocation: true\noutputs: [report]\n---\n",
            encoding="utf-8",
        )
    index = build_skill_index(agent_root)
    assert len(index["skills"]) == len(skill_ids)
    assert all(entry["explicit_only"] is True for entry in index["skills"])
    return agent_root, index


@pytest.mark.parametrize("prompt,allowed", [
    ("Write a report.", False),
    ("Use $manual-report-extra to write a report.", False),
    ("Use $manual-report.extra to write a report.", False),
    ("Use $manual-report. Write a report.", True),
    ("Use `$manual-report`. Write a report.", True),
    ("Do not use $manual-report. Write a report.", False),
    ("Don't use manual-report.", False),
    ("Don't use $manual-report.", False),
    ("Do not use $other, $manual-report.", False),
    ("Do not use `$other`, `$manual-report`.", False),
    ("Do not use $other, $third, and $manual-report.", False),
    ("Do not use $other, use $manual-report.", True),
    ("Use $not-report, $manual-report.", True),
    ("Use $manual-report. Do not use $manual-report anymore.", False),
    ("Do not use $manual-report. Use $manual-report for this report.", True),
    ("Use $manual-report to write a report.", True),
    ("Use manual-report to write a report.", True),
    ("Use /manual-report to write a report.", True),
    ("请使用 manual-report 写报告。", True),
])
def test_manual_skill_requires_user_invocation_in_both_candidate_paths(manual_skill, prompt, allowed):
    """Apply invocation authorization consistently to discovery and explicit selection."""
    _, index = manual_skill
    task = build_task_card(prompt=prompt, context={"deliverables": ["report"]})
    assert bool(find_skill_candidates(task, index)) is allowed
    assert bool(resolve_skill_candidates(task, index, skill_ids=("manual-report",))) is allowed


@pytest.mark.parametrize("manual_skill", [(
    "manual-report", "other.v2", "not-report", "manual-report中文", "manual-report.报告",
)], indirect=True)
@pytest.mark.parametrize("prompt,allowed", [
    ("Don't invoke manual-report. Write a report directly.", False),
    ("Don't run $manual-report. Write a report directly.", False),
    ("Don't call /manual-report. Write a report directly.", False),
    ("Don’t run $manual-report. Write a report directly.", False),
    ("Never use $manual-report. Write a report directly.", False),
    ("Never invoke manual-report. Write a report directly.", False),
    ("Never call $manual-report. Write a report directly.", False),
    ("Do not use $other.v2 and $manual-report. Write a report directly.", False),
    ("Do not use $other.v2 or $manual-report. Write a report directly.", False),
    ("Do not use `$other.v2` and `$manual-report`. Write a report directly.", False),
    ("Use $not-report and $manual-report to write a report.", True),
    ("Use the not-report and $manual-report to write a report.", True),
    ("Use /not-report or /manual-report to write a report.", True),
    ("请使用$manual-report 写报告。", True),
    ("Use $manual-report中文 to write a report.", False),
    ("Use $manual-report.报告 to write a report.", False),
    ("Do not use $other.v2. Use $manual-report to write a report.", True),
    ("Do not use $other.v2, use $manual-report to write a report.", True),
])
def test_manual_skill_authorization_preserves_instruction_scope(manual_skill, prompt, allowed):
    """Enforce complete skill names and invocation scope through discovery and Agent binding."""
    agent_root, index = manual_skill
    task = build_task_card(prompt=prompt, context={"deliverables": ["report"]})
    assert any(candidate.skill_id == "manual-report" for candidate in find_skill_candidates(task, index)) is allowed
    assert bool(resolve_skill_candidates(task, index, skill_ids=("manual-report",))) is allowed
    arguments = dict(
        agent_root=agent_root, run_id="invocation-scope", prompt=prompt,
        context={"deliverables": ["report"]}, execute=False,
        agent_skill_organization=_organization(skill="manual-report"),
    )
    if allowed:
        result = loop.run_local_kernel(**arguments)
        assert result["plan"]["work_units"][0]["preferred_skill"] == "manual-report"
    else:
        with pytest.raises(ValueError, match="selected unknown candidate skill"):
            loop.run_local_kernel(**arguments)


def test_agent_selection_does_not_authorize_a_manual_skill(manual_skill) -> None:
    """Reject Agent binding of a manual skill that the user has not invoked."""
    agent_root, _ = manual_skill
    with pytest.raises(ValueError, match="selected unknown candidate skill"):
        loop.run_local_kernel(
            agent_root=agent_root, prompt="Write a report.", run_id="agent-choice",
            context={"deliverables": ["report"]}, execute=False,
            agent_skill_organization=_organization(skill="manual-report"),
        )


def test_explicit_manual_invocation_survives_continuation(manual_skill) -> None:
    """Retain the user's manual-skill authorization across a continuation."""
    agent_root, _ = manual_skill
    arguments = dict(
        agent_root=agent_root, run_id="manual-continuation",
        context={"deliverables": ["report"]}, execute=False,
        agent_skill_organization=_organization(skill="manual-report"),
    )
    loop.run_local_kernel(**arguments, prompt="Use $manual-report to write a report.")
    resumed = loop.run_local_kernel(**arguments, prompt="continue")
    assert resumed["plan"]["work_units"][0]["preferred_skill"] == "manual-report"


@pytest.mark.parametrize("manual_skill", ["not-report", "notice-report", "manual-report.extra"], indirect=True)
def test_manual_skill_revocation_respects_scope_independently_of_its_name(manual_skill) -> None:
    """Revoke discovery and binding even when a skill name contains negation-like text."""
    agent_root, index = manual_skill
    skill_id = index["skills"][0]["id"]
    arguments = dict(
        agent_root=agent_root, run_id="manual-revocation", execute=False,
        context={"deliverables": ["report"]},
        agent_skill_organization=_organization(skill=skill_id),
    )
    loop.run_local_kernel(**arguments, prompt=f"Use ${skill_id} to write a report.")
    negative_prompt = f"Do not use ${skill_id} any more."
    task = build_task_card(prompt=negative_prompt, context={"deliverables": ["report"]})
    assert not find_skill_candidates(task, index)
    assert not resolve_skill_candidates(task, index, skill_ids=(skill_id,))
    with pytest.raises(ValueError, match="selected unknown candidate skill"):
        loop.run_local_kernel(**arguments, prompt=negative_prompt)


@pytest.mark.parametrize("manual_skill", ["Straße", "manual-report中文", "manual-report.报告"], indirect=True)
def test_unicode_skill_invocation_preserves_the_catalog_id(manual_skill) -> None:
    """Match normalized Unicode invocations while retaining the installed skill ID."""
    agent_root, index = manual_skill
    skill_id = index["skills"][0]["id"]
    assert skill_id in ("Straße", "manual-report中文", "manual-report.报告")
    for name in (skill_id, skill_id.casefold()):
        task = build_task_card(prompt=f"Use ${name} to write a report.", context={"deliverables": ["report"]})
        assert [candidate.skill_id for candidate in find_skill_candidates(task, index)] == [skill_id]
        assert [candidate.skill_id for candidate in resolve_skill_candidates(task, index, skill_ids=(skill_id,))] == [skill_id]
    result = loop.run_local_kernel(
        agent_root=agent_root, run_id="unicode-skill", prompt=f"Use ${skill_id} to write a report.",
        context={"deliverables": ["report"]}, execute=False,
        agent_skill_organization=_organization(skill=skill_id),
    )
    assert result["plan"]["work_units"][0]["preferred_skill"] == skill_id


def test_later_revocation_in_one_prompt_prevents_agent_binding(manual_skill) -> None:
    """Let the last invocation in a prompt revoke an earlier authorization."""
    agent_root, _ = manual_skill
    with pytest.raises(ValueError, match="selected unknown candidate skill"):
        loop.run_local_kernel(
            agent_root=agent_root, run_id="same-prompt-revocation",
            prompt="Use $manual-report. Do not use $manual-report anymore.",
            context={"deliverables": ["report"]}, execute=False,
            agent_skill_organization=_organization(skill="manual-report"),
        )
