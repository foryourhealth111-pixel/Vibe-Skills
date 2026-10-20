from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages/contracts/src"))

from vgo_contracts.module_execution_contract import validate_agent_module_execution


@pytest.fixture
def tdd_submission(tmp_path: Path):
    plan = {
        "modules": [{
            "module_id": "implementation", "required": True,
            "execution_mode": "agent", "gap_reason": None,
            "acceptance_criteria": [{"criterion_id": "tested"}],
        }],
        "work_units": [{
            "unit_id": "implement", "module_id": "implementation",
            "skill_id": None, "role": "owner",
        }],
    }
    plan_path = tmp_path / "module-work-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    evidence = {
        "state": "passing", "evidence_paths": ["red.log", "green.log"],
        "red_phase_evidence_paths": ["red.log"], "green_phase_evidence_paths": ["green.log"],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": ["Record red and green runs."],
        "covered_code_task_tdd_exceptions": [], "notes": "Verified the implementation.",
    }
    submitted = {
        "schema_version": "module_execution_v1", "source_run_id": "run",
        "module_work_plan_digest": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "tdd_evidence": evidence,
        "units": [{**plan["work_units"][0], "state": "completed", "result_summary": "Implemented.",
                   "evidence_paths": [], "verification_results": []}],
        "modules": [{**plan["modules"][0], "state": "completed",
                     "criterion_results": [{"criterion_id": "tested", "state": "passing"}]}],
    }
    handoff = {
        "source_run_id": "run",
        "result_contract": {
            "required_top_level_fields": list(submitted),
            "tdd_evidence": {
                "required_result_fields": list(evidence),
                "terminal_states": ["passing", "failing", "blocked"],
                "required_code_task_tdd_evidence_requirements": evidence["covered_code_task_tdd_evidence_requirements"],
                "required_code_task_tdd_exceptions": [],
            },
        },
    }
    return {"session_root": tmp_path, "source_run_id": "run", "handoff": handoff, "submitted": submitted}


@pytest.mark.parametrize("state,status", [
    ("passed", None), (" pass ", None), ("PASSING", None),
    (None, "passed"), ("passing", "PASSED"), (None, "failed"), (None, "blocked"),
])
def test_tdd_admission_accepts_resolved_terminal_state(tdd_submission, state, status) -> None:
    evidence = tdd_submission["submitted"]["tdd_evidence"]
    evidence.pop("state")
    if state is not None:
        evidence["state"] = state
    if status is not None:
        evidence["status"] = status
    validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("field", ["evidence_paths", "red_phase_evidence_paths", "green_phase_evidence_paths"])
def test_legacy_passing_state_still_requires_tdd_evidence(tdd_submission, field) -> None:
    evidence = tdd_submission["submitted"]["tdd_evidence"]
    evidence["state"] = "passed"
    evidence[field] = []
    with pytest.raises(RuntimeError, match="requires .*evidence paths"):
        validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("field", ["notes", "evidence_paths", "covered_code_task_tdd_exceptions"])
def test_status_alias_preserves_other_required_fields(tdd_submission, field) -> None:
    evidence = tdd_submission["submitted"]["tdd_evidence"]
    evidence["status"] = evidence.pop("state")
    del evidence[field]
    with pytest.raises(RuntimeError, match=f"missing required field: {field}"):
        validate_agent_module_execution(**tdd_submission)


def test_tdd_admission_rejects_conflicting_aliases(tdd_submission) -> None:
    tdd_submission["submitted"]["tdd_evidence"]["status"] = "failed"
    with pytest.raises(RuntimeError, match="state and status fields conflict"):
        validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("field,value", [
    ("result_summary", 42),
    ("result_summary", {"error": "No result was produced"}),
    ("result_summary", None),
    ("evidence_paths", "result.md"),
    ("evidence_paths", [None]),
    ("evidence_paths", [""]),
    ("verification_results", "checks failed"),
    ("verification_results", {}),
    ("verification_results", [None]),
])
def test_module_result_admission_rejects_invalid_field_types(tdd_submission, field, value) -> None:
    tdd_submission["submitted"]["units"][0][field] = value
    with pytest.raises(RuntimeError, match=field):
        validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("state", ["failing", "blocked"])
def test_module_result_admission_rejects_checks_conflicting_with_passing_criterion(tdd_submission, state) -> None:
    tdd_submission["submitted"]["units"][0]["verification_results"] = [
        {"criterion_id": "tested", "state": state},
    ]
    with pytest.raises(RuntimeError, match="conflicts with passing module criterion"):
        validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("checks", [
    [{"criterion_id": "tested"}],
    [{"criterion_id": "tested", "state": "passed"}],
    [{"criterion_id": "unknown", "state": "passing"}],
    [{"criterion_id": "tested", "state": "passing"}] * 2,
])
def test_module_result_admission_rejects_invalid_verification_records(tdd_submission, checks) -> None:
    tdd_submission["submitted"]["units"][0]["verification_results"] = checks
    with pytest.raises(RuntimeError, match="verification"):
        validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("state,criterion_state", [
    ("completed", "passing"), ("failed", "failing"), ("blocked", "blocked"),
])
def test_module_result_admission_preserves_consistent_terminal_results(tdd_submission, state, criterion_state) -> None:
    submitted = tdd_submission["submitted"]
    submitted["units"][0].update({
        "state": state,
        "verification_results": [{"criterion_id": "tested", "state": criterion_state}],
    })
    submitted["modules"][0]["state"] = state
    submitted["modules"][0]["criterion_results"][0]["state"] = criterion_state
    validate_agent_module_execution(**tdd_submission)


def test_module_result_admission_allows_module_failure_after_an_earlier_passing_check(tdd_submission) -> None:
    submitted = tdd_submission["submitted"]
    submitted["units"][0]["verification_results"] = [{"criterion_id": "tested", "state": "passing"}]
    submitted["modules"][0]["state"] = "failed"
    submitted["modules"][0]["criterion_results"][0]["state"] = "failing"
    validate_agent_module_execution(**tdd_submission)


@pytest.mark.parametrize("requested", ["omitted", "same"])
def test_result_workspace_uses_frozen_identity(tmp_path: Path, requested: str) -> None:
    from vgo_contracts import module_execution_contract as contract

    frozen = tmp_path / "workspace"
    packet = {"storage": {"workspace_root": str(frozen)}}
    actual = contract.resolve_execution_workspace(
        packet, requested_workspace_root=frozen if requested == "same" else None,
        fallback_workspace_root=tmp_path / "artifact-root",
    )
    assert actual == frozen.resolve()


def test_result_workspace_rejects_conflicting_identity(tmp_path: Path) -> None:
    from vgo_contracts import module_execution_contract as contract

    with pytest.raises(RuntimeError, match="workspace.*frozen"):
        contract.resolve_execution_workspace(
            {"storage": {"workspace_root": str(tmp_path / "source")}},
            requested_workspace_root=tmp_path / "different",
            fallback_workspace_root=tmp_path,
        )


def test_result_workspace_keeps_legacy_fallback(tmp_path: Path) -> None:
    from vgo_contracts import module_execution_contract as contract

    assert contract.resolve_execution_workspace(
        {}, requested_workspace_root=None, fallback_workspace_root=tmp_path,
    ) == tmp_path.resolve()


@pytest.mark.parametrize("storage", [[], "invalid", {"workspace_root": "relative"}, {"workspace_root": 1}])
def test_result_workspace_rejects_malformed_frozen_storage(tmp_path: Path, storage: object) -> None:
    from vgo_contracts import module_execution_contract as contract

    with pytest.raises((RuntimeError, ValueError), match="storage|workspace"):
        contract.resolve_execution_workspace(
            {"storage": storage}, requested_workspace_root=None,
            fallback_workspace_root=tmp_path,
        )
