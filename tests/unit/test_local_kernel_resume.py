from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from tests.unit.test_local_kernel_execution import run_local_kernel_with_agent_choice
from vgo_runtime.kernel.executor import WorkUnitResult, capture_completed_artifact_sha256
from vgo_runtime.kernel.loop import inspect_local_run, run_local_kernel
from vgo_runtime.kernel.planner import build_work_plan
from vgo_runtime.kernel.task_card import TaskCard, build_task_card
from vgo_runtime.kernel.verifier import verify_run
from vgo_runtime.kernel.work_plan import WorkUnit


@pytest.fixture
def agent_root(tmp_path: Path) -> Path:
    agent = tmp_path / "agent-root"
    skill_file = agent / "vibe/skills/local/write-report/SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        """---
name: Write Report
description: Turn results into a concise report, summary, or briefing.
inputs:
  - results
outputs:
  - report
  - summary
  - briefing
---

# Report workflow

Use verified results to write the report, summary, or briefing.
""",
        encoding="utf-8",
    )
    return agent


def _completed_result(unit: WorkUnit, work_root: Path, content: str) -> WorkUnitResult:
    work_root.mkdir(parents=True, exist_ok=True)
    artifact = work_root / "result.md"
    artifact.write_text(content, encoding="utf-8")
    receipt = work_root / "execution-receipt.json"
    receipt.write_text("{}\n", encoding="utf-8")
    return WorkUnitResult(
        work_unit_id=unit.id,
        status="completed",
        lifecycle_state="executed",
        used_skill=unit.preferred_skill,
        artifacts=unit.expected_artifacts,
        artifact_paths=(str(artifact.resolve()),),
        proof_artifact_paths=(),
        checked_targets=unit.verification,
        notes=("deterministic test execution",),
        proof=(
            f"{unit.id}: used skill {unit.preferred_skill}",
            *(f"{unit.id}: artifact {item}" for item in unit.expected_artifacts),
            *(f"{unit.id}: checked {target}" for target in unit.verification),
        ),
        execution_receipt_path=str(receipt.resolve()),
        artifact_kind="final",
        proof_ready=True,
    )


@pytest.mark.parametrize("field", ["constraints", "known_context", "unknowns"])
@pytest.mark.parametrize("revision_mode", ["replace", "extend"])
def test_resume_rebuilds_report_when_task_inputs_change(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, field: str, revision_mode: str,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, json.dumps(list(getattr(task, field))))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root,
        run_id="changed-requirement",
        prompt="Produce a report about the benchmark results.",
    )
    first = run_local_kernel_with_agent_choice(
        **arguments, context={"deliverables": ["report"], field: ["Data version A"]}
    )
    assert first["verification"]["result"] == "done"
    resumed = run_local_kernel_with_agent_choice(
        **arguments,
        context={"deliverables": ["report"], field: ["Data version B"], "revision_mode": revision_mode},
    )
    report = Path(resumed["work_results"]["work_results"][0]["artifact_paths"][0])
    expected = ["Data version B"] if revision_mode == "replace" else ["Data version A", "Data version B"]
    assert json.loads(report.read_text(encoding="utf-8")) == expected
    assert calls == ["wu-1", "wu-1"]
    assert resumed["reused_work_units"] == []
    assert resumed["verification"]["result"] == "done"


@pytest.mark.parametrize("missing_field", [None, "task_input_sha256", "dependency_output_sha256"])
def test_resume_reuses_only_complete_current_fingerprints(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, missing_field: str | None,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, f"Report execution {len(calls)}")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="unchanged-inputs", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    result_path = Path(first["artifacts"]["work_results"])
    if missing_field is not None:
        stored = json.loads(result_path.read_text(encoding="utf-8"))
        stored["work_results"][0].pop(missing_field, None)
        result_path.write_text(json.dumps(stored), encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    result = resumed["work_results"]["work_results"][0]
    assert len(calls) == (1 if missing_field is None else 2)
    assert resumed["reused_work_units"] == (["wu-1"] if missing_field is None else [])
    assert result["artifact_kind"] == "final"
    assert result["proof_ready"] is True
    assert len(result["task_input_sha256"]) == 64
    assert len(result["dependency_output_sha256"]) == 64
    assert resumed["verification"]["result"] == "done"


@pytest.mark.parametrize("downstream_count", [1, 2])
@pytest.mark.parametrize("mutation", ["none", "upstream_artifact", "dependent_fingerprint"])
def test_resume_validates_dependency_fingerprints(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, downstream_count: int, mutation: str,
) -> None:
    produced: dict[str, Path] = {}
    calls: list[str] = []
    version = "A"

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        content = "summary version " + version
        if unit.depends_on:
            content = "based on: " + produced[unit.depends_on[0]].read_text(encoding="utf-8")
        result = _completed_result(unit, work_root, content)
        produced[unit.id] = Path(result.artifact_paths[0])
        return result

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    deliverables = ["summary", "report", "briefing"][:downstream_count + 1]
    arguments = dict(
        agent_root=agent_root,
        run_id="changed-dependency",
        prompt="Produce a summary, report, and briefing about the benchmark results.",
        context={"deliverables": deliverables},
    )
    first = run_local_kernel_with_agent_choice(**arguments)
    assert first["verification"]["result"] == "done"
    if mutation == "upstream_artifact":
        produced["wu-1"].write_text("external edit triggers upstream refresh", encoding="utf-8")
        version = "B"
    elif mutation == "dependent_fingerprint":
        results_path = Path(first["artifacts"]["work_results"])
        stored = json.loads(results_path.read_text(encoding="utf-8"))
        stored["work_results"][1]["dependency_output_sha256"] = "0" * 64
        results_path.write_text(json.dumps(stored), encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    for path in produced.values():
        assert "summary version " + version in path.read_text(encoding="utf-8")
    unit_ids = [f"wu-{index}" for index in range(1, len(deliverables) + 1)]
    rerun_ids = [] if mutation == "none" else unit_ids if mutation == "upstream_artifact" else unit_ids[1:]
    assert calls == unit_ids + rerun_ids
    expected_reused = [unit_id for unit_id in unit_ids if unit_id not in rerun_ids]
    assert resumed["reused_work_units"] == expected_reused
    assert resumed["verification"]["result"] == "done"
    plan_reused = [unit["id"] for unit in resumed["plan"]["work_units"] if unit["lifecycle_state"] == "reused"]
    assert plan_reused == expected_reused


def test_resume_preserves_independent_work_and_blocks_failed_dependents(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    produced: dict[str, Path] = {}
    calls: list[str] = []
    fail_upstream = False

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        result = _completed_result(unit, work_root, f"{unit.id} execution {len(calls)}")
        produced[unit.id] = Path(result.artifact_paths[0])
        if fail_upstream and unit.id == "wu-1":
            return replace(result, status="failed", failure_reason="upstream data is unavailable")
        return result

    organization = {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "modules": [
            {
                "module_id": module_id,
                "execution_mode": "agent_direct",
                "depends_on": depends_on,
                "acceptance_criteria": [
                    {
                        "criterion_id": module_id + "-result",
                        "description": "Produce the requested artifact.",
                        "verification_mode": "automated",
                    }
                ],
            }
            for module_id, depends_on in [("wu-1", []), ("wu-2", ["wu-1"]), ("wu-3", [])]
        ],
        "selected_skills": [],
        "uncovered_modules": [],
    }
    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root,
        run_id="failed-dependency",
        prompt="Produce a summary, report, and briefing.",
        context={"deliverables": ["summary", "report", "briefing"]},
        agent_skill_organization=organization,
    )
    first = run_local_kernel(**arguments)
    assert first["verification"]["result"] == "done"
    produced["wu-1"].write_text("changed upstream", encoding="utf-8")
    fail_upstream = True
    resumed = run_local_kernel(**arguments)
    assert calls == ["wu-1", "wu-3", "wu-2", "wu-1"]
    assert resumed["reused_work_units"] == ["wu-3"]
    by_id = {result["work_unit_id"]: result for result in resumed["work_results"]["work_results"]}
    assert by_id["wu-2"]["status"] == "blocked"
    assert by_id["wu-2"]["artifact_paths"] == ()
    assert by_id["wu-2"]["proof_ready"] is False
    assert resumed["verification"]["result"] != "done"


@pytest.mark.parametrize(
    ("artifact_kind", "proof_ready"),
    [("scaffold", False), ("scaffold", True), ("final", False)],
)
def test_completed_readiness_controls_verification_and_reuse(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, artifact_kind: str, proof_ready: bool,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return replace(
            _completed_result(unit, work_root, "result awaiting final proof"),
            artifact_kind=artifact_kind, proof_ready=proof_ready,
        )

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, run_id="unready-completion", prompt="Produce a report.",
        context={"deliverables": ["report"]},
    )
    first = run_local_kernel_with_agent_choice(**arguments)
    assert first["verification"]["result"] == "revise_execution"
    assert first["work_summary"]["proof_ready"] is False
    assert first["work_summary"]["completed_work_unit_count"] == 0
    assert first["work_dossier"]["delivery_summary"]["results"] == []
    assert first["work_dossier"]["closure"]["outputs"] == {"artifacts": [], "artifact_paths": []}
    dossier_text = Path(first["artifacts"]["work_dossier_markdown"]).read_text(encoding="utf-8")
    proof_section = dossier_text.split("## Proof", 1)[1].split("## Task Evolution", 1)[0]
    assert "- artifact:" not in proof_section
    assert "- artifact path:" not in proof_section
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["verification"]["result"] == "revise_execution"
    assert resumed["reused_work_units"] == []
    assert calls == ["wu-1", "wu-1"]


@pytest.mark.parametrize(
    ("artifact_kind", "proof_ready"),
    [("scaffold", False), ("scaffold", True), ("final", False)],
)
def test_unready_completed_dependency_blocks_dependent_execution(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, artifact_kind: str, proof_ready: bool,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        result = _completed_result(unit, work_root, "upstream proof pending")
        return replace(result, artifact_kind=artifact_kind, proof_ready=proof_ready) if unit.id == "wu-1" else result

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    result = run_local_kernel_with_agent_choice(
        agent_root=agent_root, run_id="unready-dependency", prompt="Produce a summary and report.",
        context={"deliverables": ["summary", "report"]},
    )
    assert tuple(result["plan"]["work_units"][1]["depends_on"]) == ("wu-1",)
    assert calls == ["wu-1"]
    assert result["work_results"]["work_results"][1]["status"] == "blocked"
    assert result["verification"]["result"] != "done"


@pytest.mark.parametrize("mutation", ["none", "modify", "delete"])
def test_inspect_checks_current_deliveries_and_preserves_verification_snapshot(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, "# Verified report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    first = run_local_kernel_with_agent_choice(
        agent_root=agent_root, run_id="inspect-integrity", prompt="Produce a report.",
        context={"deliverables": ["report"]},
    )
    assert first["verification"]["result"] == "done"
    artifact = Path(first["work_results"]["work_results"][0]["artifact_paths"][0])
    if mutation == "modify":
        artifact.write_text("# Changed after completion\n", encoding="utf-8")
    elif mutation == "delete":
        artifact.unlink()
    run_root = Path(first["artifacts"]["work_results"]).parent
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in run_root.rglob("*") if path.is_file()
    }

    inspected = inspect_local_run(agent_root=agent_root, run_id="inspect-integrity")

    expected = "done" if mutation == "none" else "revise_execution"
    assert inspected["verification"] == json.loads(json.dumps(first["verification"]))
    assert inspected["current_verification"]["result"] == expected
    assert inspected["summary"]["verification_result"] == expected
    assert inspected["summary"]["recorded_verification_result"] == "done"
    assert inspected["summary"]["proof_ready"] is (mutation == "none")
    assert inspected["summary"]["verification_checked_at"] == inspected["verification_checked_at"]
    checked_at = datetime.fromisoformat(inspected["verification_checked_at"].replace("Z", "+00:00"))
    assert checked_at.utcoffset() == timezone.utc.utcoffset(None)
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in run_root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("preview_kind", ["same", "input", "acceptance_criteria", "unbound"])
def test_plan_only_preserves_identity_bound_completed_execution(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, preview_kind: str,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, "# Finished report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="preview-completed", prompt="Produce a report.")
    context: dict[str, object] = {"deliverables": ["report"], "constraints": ["Version A"]}
    first = run_local_kernel_with_agent_choice(**arguments, context=context)
    assert first["verification"]["result"] == "done"
    ledger = Path(first["artifacts"]["work_results"])
    before = json.loads(ledger.read_text(encoding="utf-8"))
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    if preview_kind == "input":
        context = {**context, "constraints": ["Version B"], "revision_mode": "replace"}
    if preview_kind == "acceptance_criteria":
        organization["modules"][0]["acceptance_criteria"][0]["description"] = "Include an audited appendix."
    preview = run_local_kernel(
        **arguments, context=context, execute=False,
        agent_skill_organization=None if preview_kind == "unbound" else organization,
    )
    assert json.loads(ledger.read_text(encoding="utf-8")) == before
    if preview_kind in {"input", "acceptance_criteria", "unbound"}:
        assert preview["verification"]["result"] != "done"
        inspected = inspect_local_run(agent_root=agent_root, run_id="preview-completed")
        assert inspected["current_verification"]["result"] != "done"
    resumed = run_local_kernel(**arguments, context=context, agent_skill_organization=organization)
    assert resumed["verification"]["result"] == "done"
    changed = preview_kind in {"input", "acceptance_criteria"}
    assert calls == (["wu-1", "wu-1"] if changed else ["wu-1"])
    assert resumed["reused_work_units"] == ([] if changed else ["wu-1"])


@pytest.mark.parametrize("failure_boundary", ["executor", "checkpoint_replace"])
def test_completed_checkpoint_survives_a_later_unit_failure(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, failure_boundary: str,
) -> None:
    calls: list[str] = []
    interrupted = False
    ledger: Path | None = None
    original_replace = Path.replace

    def replace_checkpoint(source: Path, target: Path) -> Path:
        nonlocal interrupted
        if failure_boundary == "checkpoint_replace" and Path(target).name == "work-results.json":
            payload = json.loads(source.read_text(encoding="utf-8"))
            if len(payload["work_results"]) == 2 and not interrupted:
                interrupted = True
                raise OSError("simulated checkpoint replacement failure")
        return original_replace(source, target)

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        nonlocal interrupted, ledger
        ledger = work_root.parent.parent / "work-results.json"
        calls.append(unit.id)
        if failure_boundary == "executor" and unit.id == "wu-2" and not interrupted:
            interrupted = True
            raise RuntimeError("simulated second-unit executor interruption")
        return _completed_result(unit, work_root, f"completed {unit.id}")

    monkeypatch.setattr(Path, "replace", replace_checkpoint)
    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, run_id="interrupted-chain", prompt="Produce a summary and report.",
        context={"deliverables": ["summary", "report"]},
    )
    error = RuntimeError if failure_boundary == "executor" else OSError
    with pytest.raises(error, match="simulated"):
        run_local_kernel_with_agent_choice(**arguments)
    assert ledger is not None and ledger.is_file()
    persisted = json.loads(ledger.read_text(encoding="utf-8"))
    assert [row["work_unit_id"] for row in persisted["work_results"]] == ["wu-1"]
    state = json.loads((ledger.parent / "run-state.json").read_text(encoding="utf-8"))
    assert state["completed_work_units"] == ["wu-1"]
    assert not list(ledger.parent.glob(".work-results.json.*.tmp"))
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["verification"]["result"] == "done"
    assert calls == ["wu-1", "wu-2", "wu-2"]
    assert resumed["reused_work_units"] == ["wu-1"]


def test_interrupted_plan_revision_keeps_checkpoint_execution_identity(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    interrupt = False

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        nonlocal interrupt
        calls.append(unit.acceptance_criteria[0].description)
        if interrupt:
            interrupt = False
            raise RuntimeError("simulated revised executor interruption")
        return _completed_result(unit, work_root, "# Finished report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="revised-interruption", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    ledger = Path(first["artifacts"]["work_results"])
    before = json.loads(ledger.read_text(encoding="utf-8"))
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    organization["modules"][0]["acceptance_criteria"][0]["description"] = "Include an audited appendix."
    interrupt = True
    with pytest.raises(RuntimeError, match="simulated revised"):
        run_local_kernel(**arguments, agent_skill_organization=organization)
    assert json.loads(ledger.read_text(encoding="utf-8")) == before
    resumed = run_local_kernel(**arguments, agent_skill_organization=organization)
    assert resumed["verification"]["result"] == "done"
    assert resumed["reused_work_units"] == []
    assert len(calls) == 3
    assert calls[1:] == ["Include an audited appendix.", "Include an audited appendix."]


@pytest.mark.parametrize("identity_case", ["foreign", "duplicate", "missing", "empty", "reordered"])
def test_verifier_binds_results_to_approved_unit_ids(tmp_path: Path, identity_case: str) -> None:
    task = build_task_card(prompt="Produce a summary and report.", context={"deliverables": ["summary", "report"]})
    plan = build_work_plan(task, ())
    results = tuple(
        capture_completed_artifact_sha256(_completed_result(unit, tmp_path / unit.id, f"Output for {unit.id}"))
        for unit in plan.work_units
    )
    assert verify_run(task, plan, results).result == "done"
    if identity_case == "reordered":
        assert verify_run(task, plan, tuple(reversed(results))).result == "done"
        return
    if identity_case == "missing":
        invalid = results[:1]
    else:
        wrong_id = {"foreign": "another-run-unit", "duplicate": "wu-1", "empty": ""}[identity_case]
        invalid = (results[0], replace(results[1], work_unit_id=wrong_id))
    assert verify_run(task, plan, invalid).result != "done"


@pytest.mark.parametrize("bad_unit, wrong_id", [("wu-1", "another-run-unit"), ("wu-2", "wu-1")])
def test_executor_result_identity_is_checked_before_dependency_admission(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, bad_unit: str, wrong_id: str,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        result = _completed_result(unit, work_root, f"Output for {unit.id}")
        return replace(result, work_unit_id=wrong_id) if unit.id == bad_unit else result

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    result = run_local_kernel_with_agent_choice(
        agent_root=agent_root, run_id="wrong-result-binding", prompt="Produce a summary, report and briefing.",
        context={"deliverables": ["summary", "report", "briefing"]},
    )
    assert result["verification"]["result"] != "done"
    assert result["work_summary"]["proof_ready"] is False
    assert calls == (["wu-1"] if bad_unit == "wu-1" else ["wu-1", "wu-2"])
    persisted = json.loads(Path(result["artifacts"]["work_results"]).read_text(encoding="utf-8"))
    rejected = next(row for row in persisted["work_results"] if row["work_unit_id"] == bad_unit)
    assert rejected["status"] == "failed"
    assert rejected["proof_ready"] is False
    assert "executor result ID mismatch" in rejected["failure_reason"]


def test_resume_rejects_checkpoint_result_with_foreign_unit_id(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, "# Report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="foreign-checkpoint-id", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    ledger = Path(first["artifacts"]["work_results"])
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["work_results"][0]["work_unit_id"] = "foreign-unit"
    ledger.write_text(json.dumps(payload), encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["verification"]["result"] == "done"
    assert resumed["reused_work_units"] == []
    assert calls == ["wu-1", "wu-1"]


@pytest.mark.parametrize("field", ["work_plan", "task_input_sha256", "schema_version"])
def test_versioned_checkpoint_requires_complete_execution_identity(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, "# Report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="invalid-checkpoint", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    ledger = Path(first["artifacts"]["work_results"])
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload[field] = None
    ledger.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="execution checkpoint"):
        inspect_local_run(agent_root=agent_root, run_id="invalid-checkpoint")
    with pytest.raises(ValueError, match="execution checkpoint"):
        run_local_kernel(**arguments, agent_skill_organization=first["agent_skill_organization"])


@pytest.mark.parametrize("change_criteria", [False, True])
def test_legacy_results_capture_their_plan_before_preview(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, change_criteria: bool,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, "# Report\n")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="legacy-preview", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    ledger = Path(first["artifacts"]["work_results"])
    rows = json.loads(ledger.read_text(encoding="utf-8"))["work_results"]
    ledger.write_text(json.dumps({"work_results": rows}), encoding="utf-8")
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    if change_criteria:
        organization["modules"][0]["acceptance_criteria"][0]["description"] = "Include an audited appendix."
    run_local_kernel(
        **arguments, execute=False, agent_skill_organization=organization if change_criteria else None,
    )
    checkpoint = json.loads(ledger.read_text(encoding="utf-8"))
    assert checkpoint["work_results"] == rows
    assert checkpoint["work_plan"] == json.loads(json.dumps(first["plan"]))
    resumed = run_local_kernel(**arguments, agent_skill_organization=organization)
    assert resumed["verification"]["result"] == "done"
    assert calls == (["wu-1", "wu-1"] if change_criteria else ["wu-1"])


def test_partial_retry_retains_later_independent_completed_checkpoint(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    interrupt = False

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        nonlocal interrupt
        calls.append(unit.id)
        if interrupt and unit.id == "wu-2":
            interrupt = False
            raise RuntimeError("simulated independent retry interruption")
        return _completed_result(unit, work_root, f"Output for {unit.id}")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, run_id="independent-checkpoints", prompt="Produce a summary, report and briefing.",
        context={"deliverables": ["summary", "report", "briefing"]},
    )
    first = run_local_kernel_with_agent_choice(**arguments)
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    for module in organization["modules"]:
        module["depends_on"] = []
    first = run_local_kernel(**arguments, agent_skill_organization=organization)
    for row in first["work_results"]["work_results"][:2]:
        Path(row["artifact_paths"][0]).write_text("Drifted output", encoding="utf-8")
    calls.clear()
    interrupt = True
    with pytest.raises(RuntimeError, match="simulated independent"):
        run_local_kernel(**arguments, agent_skill_organization=organization)
    checkpoint = json.loads(Path(first["artifacts"]["work_results"]).read_text(encoding="utf-8"))
    assert [row["work_unit_id"] for row in checkpoint["work_results"]] == ["wu-1", "wu-3"]
    resumed = run_local_kernel(**arguments, agent_skill_organization=organization)
    assert resumed["verification"]["result"] == "done"
    assert calls == ["wu-1", "wu-2", "wu-2"]
    assert resumed["reused_work_units"] == ["wu-1", "wu-3"]


def test_resume_rebuilds_report_when_declared_input_content_changes(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "data.csv"
    source.write_text("value\n10\n", encoding="utf-8")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, source.read_text(encoding="utf-8"))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="declared-input-change",
        prompt="Produce a report from the input CSV.",
        context={"deliverables": ["report"], "input_artifacts": [str(source)]},
    )
    first = run_local_kernel_with_agent_choice(**arguments)
    assert first["verification"]["result"] == "done"
    source.write_text("value\n999\n", encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    report = Path(resumed["work_results"]["work_results"][0]["artifact_paths"][0])
    assert report.read_text(encoding="utf-8") == "value\n999\n"
    assert resumed["reused_work_units"] == []
    assert resumed["verification"]["result"] == "done"


def test_resume_recovers_result_with_missing_execution_receipt(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, "A completed report with current execution evidence")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="missing-receipt", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    Path(first["work_results"]["work_results"][0]["execution_receipt_path"]).unlink()
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["verification"]["result"] == "done"
    assert resumed["reused_work_units"] == []
    assert Path(resumed["work_results"]["work_results"][0]["execution_receipt_path"]).is_file()


def test_declared_input_paths_persist_across_resume_and_inspection(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "data.csv"
    source.write_text("stable input", encoding="utf-8")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, source.read_text(encoding="utf-8"))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="persisted-input",
        prompt="Produce a report.",
    )
    first = run_local_kernel_with_agent_choice(
        **arguments, context={"deliverables": ["report"], "input_artifacts": ["data.csv"]},
    )
    assert first["task_card"]["input_artifacts"] == (str(source.resolve()),)
    source.touch()
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["reused_work_units"] == ["wu-1"]
    assert resumed["verification"]["result"] == "done"
    source.write_text("changed input", encoding="utf-8")
    inspected = inspect_local_run(agent_root=agent_root, workspace_root=tmp_path, run_id="persisted-input")
    assert inspected["current_verification"]["result"] == "revise_execution"
    assert inspected["summary"]["proof_ready"] is False


def test_missing_declared_input_blocks_stale_completion_and_can_recover(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "data.csv"
    source.write_text("original data", encoding="utf-8")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, source.read_text(encoding="utf-8"))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="missing-input",
        prompt="Produce a report.",
        context={"deliverables": ["report"], "input_artifacts": [str(source)]},
    )
    assert run_local_kernel_with_agent_choice(**arguments)["verification"]["result"] == "done"
    source.unlink()
    blocked = run_local_kernel_with_agent_choice(**arguments)
    assert blocked["reused_work_units"] == []
    assert blocked["work_results"]["work_results"][0]["status"] == "blocked"
    assert blocked["verification"]["result"] != "done"
    source.write_text("restored data", encoding="utf-8")
    recovered = run_local_kernel_with_agent_choice(**arguments)
    report = Path(recovered["work_results"]["work_results"][0]["artifact_paths"][0])
    assert report.read_text(encoding="utf-8") == "restored data"
    assert recovered["verification"]["result"] == "done"


def test_input_mutation_during_execution_prevents_verified_completion(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "data.csv"
    source.write_text("original data", encoding="utf-8")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        result = _completed_result(unit, work_root, source.read_text(encoding="utf-8"))
        source.write_text("concurrent update", encoding="utf-8")
        return result

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    result = run_local_kernel_with_agent_choice(
        agent_root=agent_root, workspace_root=tmp_path, run_id="changing-input",
        prompt="Produce a report.", context={"input_artifacts": [str(source)]},
    )
    assert result["verification"]["result"] == "revise_execution"
    assert result["work_dossier"]["proof_ready"] is False


@pytest.mark.parametrize("inputs", ["data.csv", {}, 1, [""], [" "], [1], [None]])
def test_task_card_rejects_malformed_input_artifact_declarations(inputs: object) -> None:
    with pytest.raises(ValueError, match="input_artifacts"):
        build_task_card(prompt="Produce a report.", context={"input_artifacts": inputs})


@pytest.mark.parametrize("field", ["used_skill", "checked_targets", "proof"])
def test_resume_recovers_completed_results_that_fail_current_readiness(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, "A report with complete current evidence")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id=f"invalid-evidence-{field}", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    checkpoint = Path(first["artifacts"]["work_results"])
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["work_results"][0][field] = "unbound-skill" if field == "used_skill" else []
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["reused_work_units"] == []
    assert resumed["verification"]["result"] == "done"


def test_input_content_changes_invalidate_dependent_work(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "data.csv"
    source.write_text("data version A", encoding="utf-8")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, source.read_text(encoding="utf-8"))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="input-dependency-chain",
        prompt="Produce a summary and a report.",
        context={"deliverables": ["summary", "report"], "input_artifacts": [str(source)]},
    )
    first = run_local_kernel_with_agent_choice(**arguments)
    assert first["plan"]["work_units"][1]["depends_on"] == ("wu-1",)
    source.write_text("data version B", encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["reused_work_units"] == []
    for result in resumed["work_results"]["work_results"]:
        assert Path(result["artifact_paths"][0]).read_text(encoding="utf-8") == "data version B"
    assert resumed["verification"]["result"] == "done"


def test_input_declaration_revisions_follow_extend_and_replace(
    agent_root: Path, tmp_path: Path,
) -> None:
    for name in ("first.csv", "second.csv"):
        (tmp_path / name).write_text("input data", encoding="utf-8")
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="input-revisions",
        prompt="Produce a report.", execute=False,
    )
    run_local_kernel(**arguments, context={"input_artifacts": ["first.csv"]})
    extended = run_local_kernel(**arguments, context={"input_artifacts": ["second.csv"]})
    assert extended["task_card"]["input_artifacts"] == (
        str((tmp_path / "first.csv").resolve()), str((tmp_path / "second.csv").resolve()),
    )
    assert extended["task_card"]["accepted_revisions"][-1]["added_input_artifacts"] == (
        str((tmp_path / "second.csv").resolve()),
    )
    replaced = run_local_kernel(
        **arguments, context={"input_artifacts": [], "revision_mode": "replace"},
    )
    assert replaced["task_card"]["input_artifacts"] == ()
    assert len(replaced["task_card"]["accepted_revisions"][-1]["removed_input_artifacts"]) == 2



def test_resume_preserves_case_distinct_declared_inputs(
    agent_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    upper = tmp_path / "Data.csv"
    lower = tmp_path / "data.csv"
    upper.write_text("upper version A", encoding="utf-8")
    lower.write_text("lower version A", encoding="utf-8")
    if upper.samefile(lower):
        pytest.skip("Requires case-sensitive path identity")

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        content = " | ".join(Path(path).read_text(encoding="utf-8") for path in task.input_artifacts)
        return _completed_result(unit, work_root, content)

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="case-distinct-inputs",
        prompt="Produce a report.",
    )
    first = run_local_kernel_with_agent_choice(
        **arguments, context={"input_artifacts": [str(upper), str(lower)]},
    )
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["task_card"]["input_artifacts"] == first["task_card"]["input_artifacts"]
    assert resumed["reused_work_units"] == ["wu-1"]
    lower.write_text("lower version B", encoding="utf-8")
    changed = run_local_kernel_with_agent_choice(**arguments)
    assert changed["reused_work_units"] == []
    assert changed["verification"]["result"] == "done"
    report = Path(changed["work_results"]["work_results"][0]["artifact_paths"][0])
    assert report.read_text(encoding="utf-8") == "upper version A | lower version B"


def test_input_replacement_records_case_distinct_path_revision(
    agent_root: Path, tmp_path: Path,
) -> None:
    upper = tmp_path / "Data.csv"
    lower = tmp_path / "data.csv"
    upper.write_text("upper data", encoding="utf-8")
    lower.write_text("lower data", encoding="utf-8")
    if upper.samefile(lower):
        pytest.skip("Requires case-sensitive path identity")
    arguments = dict(
        agent_root=agent_root, workspace_root=tmp_path, run_id="case-distinct-replacement",
        prompt="Produce a report.", execute=False,
    )
    run_local_kernel(**arguments, context={"input_artifacts": [str(upper)]})
    replaced = run_local_kernel(
        **arguments, context={"input_artifacts": [str(lower)], "revision_mode": "replace"},
    )
    revision = replaced["task_card"]["accepted_revisions"][-1]
    assert revision["added_input_artifacts"] == (str(lower.resolve()),)
    assert revision["removed_input_artifacts"] == (str(upper.resolve()),)


@pytest.mark.parametrize("mismatch", ["artifacts", "used_skill"])
def test_dependency_waits_for_result_bound_to_approved_predecessor(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        if unit.id == "wu-1":
            unapproved = (
                replace(unit, expected_artifacts=("unapproved-output",))
                if mismatch == "artifacts" else replace(unit, preferred_skill="unapproved-skill")
            )
            return _completed_result(unapproved, work_root, "Internally consistent evidence with the wrong plan binding")
        return _completed_result(unit, work_root, "Dependent output")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    result = run_local_kernel_with_agent_choice(
        agent_root=agent_root, run_id=f"unapproved-predecessor-{mismatch}",
        prompt="Produce a summary and report.", context={"deliverables": ["summary", "report"]},
    )
    assert calls == ["wu-1"]
    assert result["work_results"]["work_results"][1]["status"] == "blocked"
    assert result["completed_work_units"] == []
    assert result["verification"]["result"] == "revise_execution"


@pytest.mark.parametrize("rejection", ["schema", "candidate", "dependency"])
@pytest.mark.parametrize("execute", [True, False])
def test_rejected_organization_preserves_accepted_run_state(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, rejection: str, execute: bool,
) -> None:
    calls: list[str] = []

    def executor(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, "Approved report")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", executor)
    arguments = dict(agent_root=agent_root, run_id=f"preflight-{rejection}-{execute}", prompt="Produce a report.")
    context = {"deliverables": ["report"], "constraints": ["Approved condition A"]}
    first = run_local_kernel_with_agent_choice(**arguments, context=context, execute=execute)
    root = Path(first["artifacts"]["task_card"]).parent
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    if rejection == "schema":
        organization["schema_version"] = "invalid"
    elif rejection == "candidate":
        organization["selected_skills"][0]["skill_id"] = "unknown-skill"
    else:
        organization["modules"][0]["depends_on"] = ["wu-1"]
    with pytest.raises(ValueError):
        run_local_kernel(
            **arguments, context={**context, "constraints": ["Rejected condition B"], "revision_mode": "replace"},
            agent_skill_organization=organization,
        )
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert after == before
    retried = run_local_kernel(**arguments, context=context, agent_skill_organization=first["agent_skill_organization"])
    assert retried["task_card"]["constraints"] == ("Approved condition A",)
    assert retried["verification"]["result"] == "done"
    assert calls == ["wu-1"]


def test_rejected_first_organization_leaves_a_fresh_task_identity(agent_root: Path) -> None:
    arguments = dict(agent_root=agent_root, run_id="first-rejected", prompt="Produce a report.", execute=False)
    with pytest.raises(ValueError, match="schema_version"):
        run_local_kernel(
            **arguments, context={"constraints": ["Rejected condition"]},
            agent_skill_organization={"schema_version": "invalid"},
        )
    accepted = run_local_kernel_with_agent_choice(**arguments, context={"constraints": ["Approved condition"]})
    assert accepted["work_summary"]["continuation_mode"] == "fresh"
    assert accepted["task_card"]["constraints"] == ("Approved condition",)
    assert accepted["task_card"]["accepted_revisions"] == ()


@pytest.mark.parametrize("field", ["known_context", "unknowns"])
@pytest.mark.parametrize("revision_mode", ["extend", "replace"])
def test_effective_context_revision_is_recorded_and_survives_inspection(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, field: str, revision_mode: str,
) -> None:
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        return _completed_result(unit, work_root, json.dumps(list(getattr(task, field))))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id=f"context-revision-{field}-{revision_mode}", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments, context={field: ["Dataset A"]})
    revised = run_local_kernel_with_agent_choice(
        **arguments, context={field: ["Dataset B"], "revision_mode": revision_mode},
    )
    assert first["verification"]["result"] == revised["verification"]["result"] == "done"
    assert calls == ["wu-1", "wu-1"]
    assert revised["work_summary"]["continuation_mode"] == "revised"
    assert revised["work_summary"]["accepted_revision_count"] == 1
    revision = revised["task_card"]["accepted_revisions"][0]
    assert revision[f"added_{field}"] == ("Dataset B",)
    assert revision[f"removed_{field}"] == (("Dataset A",) if revision_mode == "replace" else ())
    inspected = inspect_local_run(agent_root=agent_root, run_id=arguments["run_id"])
    assert inspected["task_card"]["accepted_revisions"][0][f"added_{field}"] == ["Dataset B"]
    resumed = run_local_kernel_with_agent_choice(
        **arguments, context={field: ["Dataset B"], "revision_mode": revision_mode},
    )
    assert resumed["work_summary"]["continuation_mode"] == "resumed"
    assert resumed["work_summary"]["accepted_revision_count"] == 1
    assert resumed["reused_work_units"] == ["wu-1"]
    assert resumed["task_card"]["accepted_revisions"][0][f"added_{field}"] == ("Dataset B",)


def test_rejected_organization_preserves_a_partially_completed_checkpoint(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    arguments = dict(agent_root=agent_root, run_id="partial-preflight", prompt="Produce a summary and report.")
    context = {"deliverables": ["summary", "report"], "constraints": ["Approved condition"]}
    planned = run_local_kernel_with_agent_choice(**arguments, context=context, execute=False)
    organization = planned["agent_skill_organization"]

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        calls.append(unit.id)
        if calls == ["wu-1", "wu-2"]:
            raise RuntimeError("simulated interruption")
        return _completed_result(unit, work_root, "Approved output")

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_local_kernel(**arguments, context=context, agent_skill_organization=organization)
    root = Path(planned["artifacts"]["task_card"]).parent
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="schema_version"):
        run_local_kernel(
            **arguments, context={"constraints": ["Rejected condition"], "revision_mode": "replace"},
            agent_skill_organization={"schema_version": "invalid"},
        )
    assert before == {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    resumed = run_local_kernel(**arguments, context=context, agent_skill_organization=organization)
    assert resumed["verification"]["result"] == "done"
    assert resumed["reused_work_units"] == ["wu-1"]
    assert calls == ["wu-1", "wu-2", "wu-2"]


def test_legacy_task_revisions_without_context_deltas_remain_readable(agent_root: Path) -> None:
    arguments = dict(agent_root=agent_root, run_id="legacy-context-deltas", prompt="Produce a report.", execute=False)
    run_local_kernel_with_agent_choice(**arguments, context={"constraints": ["Initial condition"]})
    revised = run_local_kernel_with_agent_choice(**arguments, context={"constraints": ["Additional condition"]})
    task_path = Path(revised["artifacts"]["task_card"])
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    for revision in payload["accepted_revisions"]:
        for field in ("added_known_context", "removed_known_context", "added_unknowns", "removed_unknowns"):
            revision.pop(field)
    task_path.write_text(json.dumps(payload), encoding="utf-8")
    resumed = run_local_kernel_with_agent_choice(**arguments, context={"constraints": ["Additional condition"]})
    assert resumed["work_summary"]["accepted_revision_count"] == 1
    assert resumed["task_card"]["accepted_revisions"][0]["added_known_context"] == ()


@pytest.mark.parametrize("change", ["edit", "add", "delete", "cache_noise"])
def test_resume_invalidates_changed_skill_resources(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    skill_root = agent_root / "vibe/skills/local/write-report"
    resource = skill_root / "scripts/template.txt"
    resource.parent.mkdir()
    resource.write_text("version-1", encoding="utf-8")
    calls: list[str] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        content = resource.read_text(encoding="utf-8") if resource.is_file() else "removed"
        calls.append(unit.id)
        return _completed_result(unit, work_root, content)

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="skill-resource-change", prompt="Produce a report.", context={"deliverables": ["report"]})
    first = run_local_kernel_with_agent_choice(**arguments)
    assert first["verification"]["result"] == "done"
    if change == "edit":
        resource.write_text("version-2", encoding="utf-8")
    elif change == "add":
        (resource.parent / "new-rule.txt").write_text("Additional rule", encoding="utf-8")
    elif change == "delete":
        resource.unlink()
    else:
        cache = skill_root / "scripts/__pycache__"
        cache.mkdir()
        (cache / "helper.cpython-310.pyc").write_bytes(b"generated bytecode")
    resumed = run_local_kernel_with_agent_choice(**arguments)
    assert resumed["verification"]["result"] == "done"
    assert len(calls) == (1 if change == "cache_noise" else 2)
    assert resumed["reused_work_units"] == (["wu-1"] if change == "cache_noise" else [])
    artifact = Path(resumed["work_results"]["work_results"][0]["artifact_paths"][0])
    expected = "version-2" if change == "edit" else "removed" if change == "delete" else "version-1"
    assert artifact.read_text(encoding="utf-8") == expected


def test_module_goal_revision_changes_execution_and_remains_reusable(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        return _completed_result(unit, work_root, "# Synthetic execution\n" + unit.goal)

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="module-goal-revision", prompt="Produce a report.")
    first = run_local_kernel_with_agent_choice(**arguments)
    organization = json.loads(json.dumps(first["agent_skill_organization"]))
    revised_goal = "Produce a three-line Windows maintenance report."
    organization["modules"][0]["goal"] = revised_goal
    revised = run_local_kernel(**arguments, agent_skill_organization=organization)

    assert revised["work_plan"]["work_units"][0]["goal"] == revised_goal
    assert revised["reused_work_units"] == []
    artifact = Path(revised["work_results"]["work_results"][0]["artifact_paths"][0])
    assert revised_goal in artifact.read_text(encoding="utf-8")
    inspected = inspect_local_run(agent_root=agent_root, run_id=arguments["run_id"])
    assert inspected["work_plan"]["work_units"][0]["goal"] == revised_goal
    resumed = run_local_kernel(**arguments, agent_skill_organization=organization)
    assert resumed["reused_work_units"] == ["wu-1"]
    assert resumed["verification"]["result"] == "done"


@pytest.mark.parametrize("followup_prompt", [
    "Make the report at most three lines long and include only Windows details.",
    "请将报告压缩为三行，并且仅保留 Windows 相关信息。",
])
def test_free_form_followup_is_retained_invalidates_work_and_can_resume(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, followup_prompt: str,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        instructions = [revision.prompt for revision in task.accepted_revisions]
        return _completed_result(unit, work_root, "# Synthetic execution\n" + json.dumps(instructions, ensure_ascii=False))

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="free-form-followup")
    initial_prompt = "Produce a report."
    first = run_local_kernel_with_agent_choice(**arguments, prompt=initial_prompt)
    organization = first["agent_skill_organization"]
    revised = run_local_kernel(**arguments, prompt=followup_prompt, agent_skill_organization=organization)

    assert revised["work_summary"]["accepted_revision_count"] == 1
    assert revised["task_card"]["accepted_revisions"][0]["prompt"] == followup_prompt
    assert revised["task_card"]["goal"] == initial_prompt
    assert revised["reused_work_units"] == []
    artifact = Path(revised["work_results"]["work_results"][0]["artifact_paths"][0])
    assert followup_prompt in artifact.read_text(encoding="utf-8")
    inspected = inspect_local_run(**arguments)
    assert inspected["task_card"]["accepted_revisions"][0]["prompt"] == followup_prompt
    assert inspected["summary"]["proof_ready"] is True
    for continuation in (followup_prompt, "Continue.", "继续", initial_prompt):
        resumed = run_local_kernel(**arguments, prompt=continuation, agent_skill_organization=organization)
        assert resumed["work_summary"]["accepted_revision_count"] == 1
        assert resumed["reused_work_units"] == ["wu-1"]
        assert resumed["verification"]["result"] == "done"


@pytest.mark.parametrize("completed_before_stop", [0, 1, 2], ids=["initial", "partial", "completed"])
def test_inspection_reads_initial_partial_and_completed_runs_without_writing(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch, completed_before_stop: int,
) -> None:
    run_roots: list[Path] = []

    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        run_roots.append(work_root.parent.parent)
        if int(unit.id.removeprefix("wu-")) > completed_before_stop:
            raise OSError("synthetic execution interruption")
        return _completed_result(unit, work_root, "# Synthetic execution\n" + unit.goal)

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    identity = dict(agent_root=agent_root, workspace_root=agent_root.parent / "workspace", run_id="inspect-progress")
    arguments = dict(**identity, prompt="Produce a summary and report.", context={"deliverables": ["summary", "report"]})
    if completed_before_stop < 2:
        with pytest.raises(OSError, match="synthetic execution interruption"):
            run_local_kernel_with_agent_choice(**arguments)
    else:
        run_local_kernel_with_agent_choice(**arguments)
    run_root = run_roots[-1]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in run_root.rglob("*") if path.is_file()}

    inspected = inspect_local_run(**identity)

    assert inspected["summary"]["completed_work_unit_count"] == completed_before_stop
    assert len(inspected["work_results"]["work_results"]) == completed_before_stop
    assert inspected["summary"]["proof_ready"] is (completed_before_stop == 2)
    if completed_before_stop < 2:
        assert inspected["verification"] is None
        assert inspected["work_dossier"] is None
        assert inspected["summary"]["recorded_verification_result"] is None
        assert inspected["summary"]["primary_artifact"] == "run_state"
    else:
        assert inspected["summary"]["verification_result"] == "done"
        assert inspected["summary"]["primary_artifact"] == "work_dossier"
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in run_root.rglob("*") if path.is_file()}


def test_followup_can_return_to_an_earlier_instruction(
    agent_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def execute(agent: Path, task: TaskCard, unit: WorkUnit, *, work_root: Path) -> WorkUnitResult:
        current = task.accepted_revisions[-1].prompt if task.accepted_revisions else task.goal
        return _completed_result(unit, work_root, "# Synthetic execution\n" + current)

    monkeypatch.setattr("vgo_runtime.kernel.loop.execute_work_unit", execute)
    arguments = dict(agent_root=agent_root, run_id="followup-return")
    first = run_local_kernel_with_agent_choice(**arguments, prompt="Produce a report.")
    for sequence, followup_prompt in enumerate(("Keep it to three lines.", "Keep it to five lines.", "Keep it to three lines."), 1):
        revised = run_local_kernel(
            **arguments, prompt=followup_prompt,
            agent_skill_organization=first["agent_skill_organization"],
        )
        assert revised["work_summary"]["accepted_revision_count"] == sequence
        assert revised["reused_work_units"] == []
        artifact = Path(revised["work_results"]["work_results"][0]["artifact_paths"][0])
        assert artifact.read_text(encoding="utf-8").endswith(followup_prompt)
