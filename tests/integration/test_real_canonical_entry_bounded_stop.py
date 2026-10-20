from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
for src in (RUNTIME_CORE_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

import vgo_runtime.canonical_entry as canonical_entry


def _require_powershell() -> None:
    if not (shutil.which("pwsh") or shutil.which("powershell")):
        pytest.skip("PowerShell executable not available in PATH")


def _powershell() -> str:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell executable not available in PATH")
    return shell


def _ps_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _agent_skill_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "XL",
        "modules": [
            {
                "module_id": "bounded_stop_verification",
                "goal": "Verify the requested governed stage stop.",
                "candidate_skill_ids": [],
                "execution_mode": "blocked_gap",
                "acceptance_criteria": [
                    {
                        "criterion_id": "bounded-stop-result",
                        "description": "The requested governed stage stop is verified.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [],
        "uncovered_modules": [
            {
                "module_id": "bounded_stop_verification",
                "reason": "No task specialist is required for the bounded-stop contract test.",
            }
        ],
        "workflow_level_contract": {
            "L": "Use one serial governed lane.",
            "XL": "Use bounded waves when the approved organization needs them.",
        },
    }


def _write_local_skill_root(tmp_path: Path) -> dict[str, str]:
    agents_home = tmp_path / "home" / ".agents"
    skill_dir = agents_home / "skills" / "handoff-owner"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: handoff-owner\ndescription: Complete the approved handoff module.\n---\n",
        encoding="utf-8",
    )
    return {"VCO_HOST_ID": "codex", "VIBE_AGENTS_HOME": str(agents_home)}


def _handoff_organization() -> dict[str, object]:
    return {
        "schema_version": "agent_skill_organization_v1",
        "derived_by": "agent",
        "workflow_level": "L",
        "modules": [
            {
                "module_id": "handoff_module",
                "goal": "Produce the approved handoff result.",
                "candidate_skill_ids": ["handoff-owner"],
                "execution_mode": "skill_assigned",
                "acceptance_criteria": [
                    {
                        "criterion_id": "handoff-result",
                        "description": "The handoff result is complete.",
                        "verification_mode": "automated",
                    }
                ],
            }
        ],
        "selected_skills": [
            {
                "skill_id": "handoff-owner",
                "module_ids": ["handoff_module"],
                "responsibility": "Produce the approved handoff result.",
                "reason": "Its SKILL.md owns this module.",
                "expected_outputs": ["outputs/handoff-result.md"],
                "verification": ["Confirm the result exists."],
            }
        ],
        "uncovered_modules": [],
        "workflow_level_contract": {
            "L": "Run the module in the current Agent.",
            "XL": "Use bounded lanes only for independent modules.",
        },
    }


def _handoff_organization_with_optional_module() -> dict[str, object]:
    organization = _handoff_organization()
    organization["modules"].append(
        {
            "module_id": "optional_followup",
            "goal": "Attempt an optional follow-up result.",
            "candidate_skill_ids": [],
            "execution_mode": "agent_direct",
            "required": False,
            "depends_on": ["handoff_module"],
            "write_scope": "outputs/optional/**",
            "expected_outputs": ["outputs/optional/result.md"],
            "verification": ["Check the optional result when it is produced."],
            "acceptance_criteria": [
                {
                    "criterion_id": "optional-result",
                    "description": "The optional follow-up result is complete when available.",
                    "verification_mode": "automated",
                }
            ],
        }
    )
    return organization



def _write_handoff_output_evidence(session_root: Path, execution: dict[str, object]) -> None:
    handoff = json.loads((session_root / "agent-execution-handoff.json").read_text(encoding="utf-8"))
    units = {unit["unit_id"]: unit for unit in handoff["units"]}
    packet = json.loads((session_root / "runtime-input-packet.json").read_text(encoding="utf-8"))
    workspace = Path(packet["storage"]["workspace_root"])
    for unit in execution["units"]:
        if unit["state"] != "completed":
            continue
        paths = []
        for value in units[unit["unit_id"]]["expected_outputs"]:
            path = Path(value)
            if not ("/" in value or "\\" in value or path.suffix):
                continue
            if not path.is_absolute():
                path = workspace / path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Verified handoff output.\n", encoding="utf-8")
            paths.append(str(path))
        unit["evidence_paths"] = paths


def _write_agent_module_execution(
    handoff_stop: canonical_entry.CanonicalLaunchResult,
    *,
    state: str,
    result_summary: str = "",
) -> tuple[Path, dict[str, object]]:
    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    result_contract = handoff["result_contract"]
    module_execution_path = Path(handoff["module_execution_path"])
    assert not module_execution_path.exists()

    criteria_by_module = {
        str(module["module_id"]): [
            {"criterion_id": str(criterion["criterion_id"]), "state": "passing"}
            for criterion in module.get("acceptance_criteria", [])
        ]
        for module in result_contract["modules"]
    }
    module_execution = json.loads(json.dumps(result_contract["submission_template"]))
    for unit in module_execution["units"]:
        unit["state"] = state
        unit["result_summary"] = result_summary
        unit["verification_results"] = (
            criteria_by_module[str(unit["module_id"])] if state == "completed" else []
        )
    criterion_state = {
        "completed": "passing",
        "failed": "failing",
        "blocked": "blocked",
    }.get(state)
    for module in module_execution["modules"]:
        module["state"] = state
        for criterion in module["criterion_results"]:
            criterion["state"] = criterion_state
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return module_execution_path, module_execution


def _launch_handoff_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    code_task_tdd_required: bool = False,
    workspace_root: Path | None = None,
    organization: dict[str, object] | None = None,
) -> canonical_entry.CanonicalLaunchResult:
    _require_powershell()
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the Agent handoff plan.",
        workspace_root=workspace_root,
        artifact_root=artifact_root,
    )
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the requirement and prepare the plan.",
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "code_task_tdd_decision": {
                "mode": "required" if code_task_tdd_required else "not_applicable",
                "reason": (
                    "This handoff lifecycle test requires code-task TDD evidence."
                    if code_task_tdd_required
                    else "This handoff lifecycle test does not implement or repair product code."
                ),
            },
            "agent_skill_organization": organization or _handoff_organization(),
        },
    )
    return canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the plan and hand work to the Agent.",
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )


def test_separate_workspace_and_artifact_roots_survive_agent_execution_reentry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    workspace_root = tmp_path / "workspace-root"
    artifact_root = tmp_path / "artifact-root"
    handoff_stop = _launch_handoff_stop(
        tmp_path,
        monkeypatch,
        workspace_root=workspace_root,
    )
    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    assert f'--workspace-root "{workspace_root.resolve()}"' in handoff["return_command"]
    assert f'--artifact-root "{artifact_root.resolve()}"' in handoff["return_command"]

    module_execution_path, _ = _write_agent_module_execution(
        handoff_stop,
        state="completed",
        result_summary="Produced the approved handoff result.",
    )
    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Continue after Agent module execution.",
        workspace_root=workspace_root,
        artifact_root=artifact_root,
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    assert Path(result.summary["storage"]["workspace_root"]).resolve() == workspace_root.resolve()
    assert Path(result.summary["storage"]["artifact_root"]).resolve() == artifact_root.resolve()
    assert result.summary["terminal_stage"] == "phase_cleanup"
    runtime_packet = json.loads(
        (result.session_root / "runtime-input-packet.json").read_text(encoding="utf-8")
    )
    assert result.summary["task"] == runtime_packet["task"]
    cleanup = json.loads(
        (result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
    assert cleanup["task"] == runtime_packet["task"]


def test_optional_module_failure_does_not_block_canonical_agent_execution_reentry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(
        tmp_path,
        monkeypatch,
        organization=_handoff_organization_with_optional_module(),
    )
    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    module_execution = json.loads(json.dumps(handoff["result_contract"]["submission_template"]))
    for unit in module_execution["units"]:
        is_required = unit["module_id"] == "handoff_module"
        unit["state"] = "completed" if is_required else "failed"
        unit["result_summary"] = "Required result completed." if is_required else "Optional result failed."
        unit["verification_results"] = (
            [{"criterion_id": "handoff-result", "state": "passing"}]
            if is_required
            else []
        )
    for module in module_execution["modules"]:
        is_required = module["module_id"] == "handoff_module"
        module["state"] = "completed" if is_required else "failed"
        for criterion in module["criterion_results"]:
            criterion["state"] = "passing" if is_required else "failing"
    module_execution_path = Path(handoff["module_execution_path"])
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Continue after Agent module execution.",
        artifact_root=tmp_path / "artifact-root",
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    execution_manifest = json.loads(
        (result.session_root / "execution-manifest.json").read_text(encoding="utf-8")
    )
    delivery = json.loads(
        (result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8")
    )
    cleanup = json.loads(
        (result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
    assert execution_manifest["status"] == "completed"
    assert execution_manifest["failed_unit_count"] == 0
    assert delivery["summary"]["gate_result"] == "PASS"
    assert cleanup["cleanup_admitted"] is True


def test_agent_selected_skill_is_not_marked_rejected_in_runtime_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    runtime_packet = json.loads(
        (handoff_stop.session_root / "runtime-input-packet.json").read_text(encoding="utf-8")
    )

    candidate_ids = {
        str(row["skill_id"]) for row in runtime_packet["skill_routing"]["candidates"]
    }
    rejected_ids = {
        str(row["skill_id"]) for row in runtime_packet["skill_routing"]["rejected"]
    }
    assert "handoff-owner" in candidate_ids
    assert "handoff-owner" not in rejected_ids


def test_code_task_handoff_includes_inline_tdd_evidence_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(
        tmp_path,
        monkeypatch,
        code_task_tdd_required=True,
    )
    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    contract = handoff["result_contract"]

    assert "tdd_evidence" in contract["required_top_level_fields"]
    assert contract["tdd_evidence"]["required_code_task_tdd_evidence_requirements"]
    assert contract["tdd_evidence"]["terminal_states"] == ["passing", "failing", "blocked"]
    assert contract["submission_template"]["tdd_evidence"] == {
        "state": None,
        "evidence_paths": [],
        "red_phase_evidence_paths": [],
        "green_phase_evidence_paths": [],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": [],
        "covered_code_task_tdd_exceptions": [],
        "notes": "",
    }


def test_code_task_tdd_evidence_is_validated_before_cleanup_and_resubmitted_in_same_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(
        tmp_path,
        monkeypatch,
        code_task_tdd_required=True,
    )
    handoff_path = Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"])
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    module_execution_path, module_execution = _write_agent_module_execution(
        handoff_stop,
        state="completed",
        result_summary="Produced the approved handoff result with TDD.",
    )

    with pytest.raises(RuntimeError, match="TDD evidence state"):
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT,
            host_id="codex",
            entry_id="vibe",
            prompt="Continue after incomplete code-task TDD evidence.",
            artifact_root=tmp_path / "artifact-root",
            continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=module_execution_path,
        )

    lineage = json.loads(
        (handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8")
    )
    assert lineage["last_stage_name"] == "plan_execute"
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()

    red_path = handoff_stop.session_root / "focused-red.txt"
    green_path = handoff_stop.session_root / "focused-green.txt"
    red_path.write_text("1 failed\n", encoding="utf-8")
    green_path.write_text("1 passed\n", encoding="utf-8")
    tdd_contract = handoff["result_contract"]["tdd_evidence"]
    module_execution["tdd_evidence"] = {
        "state": "passing",
        "status": "passed",
        "evidence_paths": [str(red_path), str(green_path)],
        "red_phase_evidence_paths": [str(red_path)],
        "green_phase_evidence_paths": [str(green_path)],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": tdd_contract[
            "required_code_task_tdd_evidence_requirements"
        ],
        "covered_code_task_tdd_exceptions": tdd_contract[
            "required_code_task_tdd_exceptions"
        ],
        "notes": "The focused test failed before the change and passed afterward.",
    }
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Continue after corrected code-task TDD evidence.",
        artifact_root=tmp_path / "artifact-root",
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    delivery = json.loads(
        (result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8")
    )
    cleanup = json.loads(
        (result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
    assert delivery["summary"]["gate_result"] == "PASS"
    assert cleanup["cleanup_admitted"] is True
    assert not (result.session_root / "tdd-evidence.json").exists()
    assert list((tmp_path / "artifact-root" / "outputs" / "runtime" / "vibe-sessions").rglob("agent-execution-handoff.json")) == [handoff_path]


@pytest.mark.parametrize("host_id", ["codex", "claude-code", "opencode"])
@pytest.mark.parametrize(
    ("requested_stage_stop", "requested_grade_floor"),
    [
        ("requirement_doc", None),
        ("xl_plan", "XL"),
    ],
)
def test_real_canonical_entry_honors_explicit_bounded_stop_on_vibe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host_id: str,
    requested_stage_stop: str,
    requested_grade_floor: str | None,
) -> None:
    _require_powershell()

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id=host_id,
        entry_id="vibe",
        prompt=f"Verify bounded stop for {host_id} {requested_stage_stop}",
        requested_stage_stop=requested_stage_stop,
        requested_grade_floor=requested_grade_floor,
        artifact_root=tmp_path / host_id / requested_stage_stop,
        host_decision=(
            {"agent_skill_organization": _agent_skill_organization()}
            if requested_stage_stop == "xl_plan"
            else None
        ),
    )

    stage_lineage = json.loads(Path(result.artifacts["stage_lineage"]).read_text(encoding="utf-8"))
    runtime_packet = json.loads(Path(result.artifacts["runtime_input_packet"]).read_text(encoding="utf-8"))
    host_launch_receipt = json.loads(result.host_launch_receipt_path.read_text(encoding="utf-8"))

    assert stage_lineage["last_stage_name"] == requested_stage_stop
    assert host_launch_receipt["entry_id"] == "vibe"
    assert runtime_packet["entry_intent_id"] == "vibe"
    assert runtime_packet["requested_stage_stop"] == requested_stage_stop
    if requested_grade_floor is None:
        assert runtime_packet["requested_grade_floor"] is None
    else:
        assert runtime_packet["requested_grade_floor"] == requested_grade_floor

    cleanup_receipt = result.session_root / "cleanup-receipt.json"
    execute_receipt = result.session_root / "phase-execute.json"
    plan_receipt = result.session_root / "execution-plan-receipt.json"
    requirement_receipt = result.session_root / "requirement-doc-receipt.json"

    assert requirement_receipt.exists()
    if requested_stage_stop == "requirement_doc":
        assert not plan_receipt.exists()
        assert not execute_receipt.exists()
        assert not cleanup_receipt.exists()
    elif requested_stage_stop == "xl_plan":
        assert plan_receipt.exists()
        assert not execute_receipt.exists()
        assert not cleanup_receipt.exists()


def test_plan_approval_returns_agent_execution_handoff_before_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the Agent handoff plan.",
        artifact_root=artifact_root,
    )
    requirement_control = requirement_stop.summary["bounded_return_control"]
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the requirement and prepare the plan.",
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_control["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "code_task_tdd_decision": {
                "mode": "not_applicable",
                "reason": "This handoff lifecycle test does not implement or repair product code.",
            },
            "agent_skill_organization": _handoff_organization(),
        },
    )
    plan_control = plan_stop.summary["bounded_return_control"]
    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the plan and execute it.",
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_control["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    handoff_path = result.session_root / "agent-execution-handoff.json"

    assert summary["terminal_stage"] == "plan_execute"
    assert summary["agent_execution_handoff"]["status"] == "agent_action_required"
    assert summary["agent_execution_handoff"]["control_owner"] == "agent"
    assert handoff_path.exists()
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    module_execution_path = Path(handoff["module_execution_path"])
    assert handoff["status"] == "agent_action_required"
    assert summary["artifacts"]["module_execution"] is None
    assert module_execution_path == result.session_root / "module-execution.json"
    assert not module_execution_path.exists()
    assert all("state" not in unit for unit in handoff["units"])
    assert handoff["units"] == [
        {
                "unit_id": "handoff_module--handoff-owner--owner",
                "module_id": "handoff_module",
                "skill_id": "handoff-owner",
                "role": "owner",
                "skill_entrypoint": str(
                tmp_path / "home" / ".agents" / "skills" / "handoff-owner" / "SKILL.md"
            ),
            "responsibility": "Produce the approved handoff result.",
            "expected_outputs": ["outputs/handoff-result.md"],
            "verification": ["Confirm the result exists."],
            "depends_on_unit_ids": [],
            "write_scope": "module:handoff_module",
        }
    ]
    briefing = (result.session_root / "host-user-briefing.md").read_text(encoding="utf-8")
    assert "Use `handoff-owner`" in briefing
    assert "handoff-owner\\SKILL.md" in briefing or "handoff-owner/SKILL.md" in briefing
    assert "Produce the approved handoff result." in briefing
    assert "outputs/handoff-result.md" in briefing

    assert not (result.session_root / "cleanup-receipt.json").exists()
    assert not (result.session_root / "delivery-acceptance-report.json").exists()
    execution_results = result.session_root / "execution-results"
    assert not execution_results.exists() or not list(execution_results.rglob("*.json"))


def test_completed_agent_module_execution_reenters_cleanup_without_replanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the Agent handoff plan.",
        artifact_root=artifact_root,
    )
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the requirement and prepare the plan.",
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "code_task_tdd_decision": {
                "mode": "not_applicable",
                "reason": "This handoff lifecycle test does not implement or repair product code.",
            },
            "agent_skill_organization": _handoff_organization(),
        },
    )
    handoff_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the plan and execute it.",
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )

    module_execution_path, module_execution = _write_agent_module_execution(
        handoff_stop,
        state="completed",
        result_summary="Produced the approved handoff result.",
    )

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Continue after Agent module execution.",
        artifact_root=artifact_root,
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    assert result.run_id == handoff_stop.run_id
    assert result.summary["terminal_stage"] == "phase_cleanup"
    assert (result.session_root / "cleanup-receipt.json").exists()
    assert (result.session_root / "delivery-acceptance-report.json").exists()
    assert not result.summary.get("bounded_return_control")
    assert result.summary["artifacts"]["module_work_plan"] == handoff_stop.summary["artifacts"]["module_work_plan"]
    execution_manifest = json.loads(
        (result.session_root / "execution-manifest.json").read_text(encoding="utf-8")
    )
    assert execution_manifest["status"] == "completed"
    assert execution_manifest["module_handoff"]["status"] == "agent_results_received"
    assert execution_manifest["module_handoff"]["control_owner"] == "vibe"
    assert execution_manifest["module_execution_path"] == str(module_execution_path)
    completed_units = [
        unit for unit in module_execution["units"] if unit["state"] == "completed"
    ]
    assert [unit["skill_id"] for unit in completed_units] == ["handoff-owner"]
    delivery = json.loads(
        (result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8")
    )
    assert delivery["summary"]["gate_result"] == "PASS"
    assert delivery["summary"]["completion_language_allowed"] is True
    assert delivery["execution_context"]["completion_claim_allowed"] is True
    assert delivery["truth_results"]["module_acceptance_truth"]["state"] == "passing"
    briefing = result.summary["host_user_briefing"]
    briefing_text = briefing["rendered_text"]
    briefing_path = Path(result.summary["artifacts"]["host_user_briefing"])
    assert briefing["segments"][0]["stage"] == "phase_cleanup"
    assert "Task is complete." in briefing_text
    assert "The approved plan is ready for the current Agent to execute." not in briefing_text
    assert "agent_action_required" not in json.dumps(briefing)
    assert briefing_path.read_text(encoding="utf-8").strip() == briefing_text.strip()
    assert result.summary["agent_execution_handoff"] is None


def test_malformed_criterion_result_is_rejected_before_cleanup_and_same_run_can_be_resubmitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    handoff_path = Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"])
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    module_execution_path = Path(handoff["module_execution_path"])
    module_execution = json.loads(
        json.dumps(handoff["result_contract"]["submission_template"])
    )
    for unit in module_execution["units"]:
        unit["state"] = "completed"
        unit["result_summary"] = "Produced the approved handoff result."
    for module in module_execution["modules"]:
        module["state"] = "completed"
        for criterion in module["criterion_results"]:
            criterion["state"] = "passed"
            criterion["details"] = "The result satisfies the frozen criterion."
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="criterion .* unsupported state"):
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT,
            host_id="codex",
            entry_id="vibe",
            prompt="Continue after Agent module execution.",
            artifact_root=tmp_path / "artifact-root",
            continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=module_execution_path,
        )

    lineage = json.loads(
        (handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8")
    )
    assert lineage["last_stage_name"] == "plan_execute"
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()
    assert not (handoff_stop.session_root / "delivery-acceptance-report.json").exists()

    for module in module_execution["modules"]:
        for criterion in module["criterion_results"]:
            criterion["state"] = "passing"
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Continue after corrected Agent module execution.",
        artifact_root=tmp_path / "artifact-root",
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    delivery = json.loads(
        (result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8")
    )
    cleanup = json.loads(
        (result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
    assert result.run_id == handoff_stop.run_id
    assert result.summary["terminal_stage"] == "phase_cleanup"
    assert delivery["summary"]["gate_result"] == "PASS"
    assert cleanup["cleanup_admitted"] is True
    assert list((tmp_path / "artifact-root" / "outputs" / "runtime" / "vibe-sessions").rglob("agent-execution-handoff.json")) == [handoff_path]


def test_blocked_agent_module_withholds_cleanup_until_delivery_acceptance_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    module_execution_path, _ = _write_agent_module_execution(
        handoff_stop,
        state="blocked",
        result_summary="Required input is missing.",
    )

    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Return the blocked Agent module result.",
        artifact_root=tmp_path / "artifact-root",
        continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=module_execution_path,
    )

    delivery = json.loads(
        (result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8")
    )
    cleanup = json.loads(
        (result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )

    assert delivery["summary"]["gate_result"] == "FAIL"
    assert delivery["summary"]["completion_language_allowed"] is False
    assert delivery["execution_context"]["completion_claim_allowed"] is False
    assert cleanup["cleanup_mode"] == "receipt_only"
    assert cleanup["cleanup_admitted"] is False
    assert cleanup["default_bounded_cleanup_applied"] is False
    assert cleanup["managed_node_cleanup_applied"] is False
    assert cleanup["cleanup_result"] == {
        "performed": False,
        "reason": "delivery_acceptance_not_passed",
    }
    briefing = result.summary["host_user_briefing"]
    briefing_text = briefing["rendered_text"]
    briefing_path = Path(result.summary["artifacts"]["host_user_briefing"])
    assert briefing["segments"][0]["stage"] == "phase_cleanup"
    assert "Task is not complete." in briefing_text
    assert "The approved plan is ready for the current Agent to execute." not in briefing_text
    assert "agent_action_required" not in json.dumps(briefing)
    assert briefing_path.read_text(encoding="utf-8").strip() == briefing_text.strip()
    assert result.summary["agent_execution_handoff"] is None
    assert not (result.session_root / "process-health-audits").exists()
    assert not (result.session_root / "process-health-cleanups").exists()


def test_pending_agent_module_execution_cannot_enter_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_powershell()
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the Agent handoff plan.",
        artifact_root=artifact_root,
    )
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the requirement and prepare the plan.",
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "agent_skill_organization": _handoff_organization(),
        },
    )
    handoff_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the plan and execute it.",
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )
    module_execution_path, _ = _write_agent_module_execution(
        handoff_stop,
        state="pending",
    )

    with pytest.raises(RuntimeError, match="not terminal"):
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT,
            host_id="codex",
            entry_id="vibe",
            prompt="Continue after Agent module execution.",
            artifact_root=artifact_root,
            continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=module_execution_path,
        )

    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()


def test_direct_powershell_canonical_reentry_rejects_pending_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the direct PowerShell Agent handoff plan.",
        artifact_root=artifact_root,
    )
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the direct PowerShell requirement.",
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "agent_skill_organization": _handoff_organization(),
        },
    )
    handoff_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the direct PowerShell plan.",
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )
    module_execution_path, _ = _write_agent_module_execution(
        handoff_stop,
        state="pending",
    )
    bridge = REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1"
    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                f"& {_ps_quote(bridge)} "
                "-Task 'Continue after Agent module execution.' "
                "-HostId codex -EntryId vibe -RequestedStageStop phase_cleanup "
                f"-RunId {_ps_quote(handoff_stop.run_id)} "
                f"-ArtifactRoot {_ps_quote(artifact_root)} "
                f"-ModuleExecutionJsonFile {_ps_quote(module_execution_path)}"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ},
    )

    assert completed.returncode != 0
    assert "not terminal" in (completed.stdout + completed.stderr)
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()


def test_direct_powershell_reentry_rejects_malformed_criterion_results_before_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = tmp_path / "artifact-root"
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    module_execution_path = Path(handoff["module_execution_path"])
    module_execution = json.loads(
        json.dumps(handoff["result_contract"]["submission_template"])
    )
    for unit in module_execution["units"]:
        unit["state"] = "completed"
        unit["result_summary"] = "Produced the approved handoff result."
    for module in module_execution["modules"]:
        module["state"] = "completed"
        for criterion in module["criterion_results"]:
            criterion["state"] = "passed"
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    bridge = REPO_ROOT / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1"
    completed = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                f"& {_ps_quote(bridge)} "
                "-Task 'Continue after Agent module execution.' "
                "-HostId codex -EntryId vibe -RequestedStageStop phase_cleanup "
                f"-RunId {_ps_quote(handoff_stop.run_id)} "
                f"-ArtifactRoot {_ps_quote(artifact_root)} "
                f"-ModuleExecutionJsonFile {_ps_quote(module_execution_path)}"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ},
    )

    assert completed.returncode != 0
    assert "criterion" in (completed.stdout + completed.stderr)
    assert "unsupported state" in (completed.stdout + completed.stderr)
    lineage = json.loads(
        (handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8")
    )
    assert lineage["last_stage_name"] == "plan_execute"
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()

    for module in module_execution["modules"]:
        for criterion in module["criterion_results"]:
            criterion["state"] = "passing"
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    corrected = subprocess.run(
        [
            _powershell(),
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                f"& {_ps_quote(bridge)} "
                "-Task 'Continue after corrected Agent module execution.' "
                "-HostId codex -EntryId vibe -RequestedStageStop phase_cleanup "
                f"-RunId {_ps_quote(handoff_stop.run_id)} "
                f"-ArtifactRoot {_ps_quote(artifact_root)} "
                f"-ModuleExecutionJsonFile {_ps_quote(module_execution_path)}"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ},
    )

    assert corrected.returncode == 0, corrected.stderr or corrected.stdout
    corrected_lineage = json.loads(
        (handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8")
    )
    cleanup = json.loads(
        (handoff_stop.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
    assert corrected_lineage["last_stage_name"] == "phase_cleanup"
    assert cleanup["cleanup_admitted"] is True
    assert list((artifact_root / "outputs" / "runtime" / "vibe-sessions").rglob("agent-execution-handoff.json")) == [
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"])
    ]


def test_direct_powershell_reentry_rejects_incomplete_code_task_tdd_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch, code_task_tdd_required=True)
    module_execution_path, module_execution = _write_agent_module_execution(
        handoff_stop, state="completed", result_summary="Produced the approved handoff result with TDD.",
    )
    original = module_execution_path.read_bytes()
    completed = _submit_direct_external_result(tmp_path, handoff_stop, module_execution_path)

    assert completed.returncode != 0
    assert "TDD evidence state" in (completed.stdout + completed.stderr)
    assert module_execution_path.read_bytes() == original
    lineage = json.loads((handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8"))
    assert lineage["last_stage_name"] == "plan_execute"
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()

    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(encoding="utf-8")
    )
    red_path = handoff_stop.session_root / "direct-red.txt"
    green_path = handoff_stop.session_root / "direct-green.txt"
    red_path.write_text("1 failed\n", encoding="utf-8")
    green_path.write_text("1 passed\n", encoding="utf-8")
    tdd_contract = handoff["result_contract"]["tdd_evidence"]
    module_execution["tdd_evidence"] = {
        "state": "passing", "status": "passed",
        "evidence_paths": [str(red_path), str(green_path)],
        "red_phase_evidence_paths": [str(red_path)], "green_phase_evidence_paths": [str(green_path)],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": tdd_contract["required_code_task_tdd_evidence_requirements"],
        "covered_code_task_tdd_exceptions": tdd_contract["required_code_task_tdd_exceptions"],
        "notes": "The focused test failed before the change and passed afterward.",
    }
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    corrected = _submit_direct_external_result(tmp_path, handoff_stop, module_execution_path)

    assert corrected.returncode == 0, corrected.stderr or corrected.stdout
    cleanup = json.loads((handoff_stop.session_root / "cleanup-receipt.json").read_text(encoding="utf-8"))
    assert cleanup["cleanup_admitted"] is True
    assert not (handoff_stop.session_root / "tdd-evidence.json").exists()


@pytest.mark.parametrize(
    ("tamper", "expected_error"),
    [
        ("plan_digest", "approved module work plan digest"),
        ("role", "changed its role binding"),
        ("required", "changed its required binding"),
        ("execution_mode", "changed its execution_mode binding"),
        ("gap_reason", "changed its gap_reason binding"),
    ],
)
def test_agent_module_execution_must_match_the_approved_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
    expected_error: str,
) -> None:
    _require_powershell()
    for key, value in _write_local_skill_root(tmp_path).items():
        monkeypatch.setenv(key, value)

    artifact_root = tmp_path / "artifact-root"
    requirement_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Prepare the Agent handoff plan.",
        artifact_root=artifact_root,
    )
    plan_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the requirement and prepare the plan.",
        artifact_root=artifact_root,
        continue_from_run_id=requirement_stop.run_id,
        bounded_reentry_token=requirement_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_requirement",
            "approval_decision": "approve",
            "agent_skill_organization": _handoff_organization(),
        },
    )
    handoff_stop = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT,
        host_id="codex",
        entry_id="vibe",
        prompt="Approve the plan and execute it.",
        artifact_root=artifact_root,
        continue_from_run_id=plan_stop.run_id,
        bounded_reentry_token=plan_stop.summary["bounded_return_control"]["reentry_token"],
        host_decision={
            "decision_kind": "approval_response",
            "decision_action": "approve_plan",
            "approval_decision": "approve",
        },
    )
    module_execution_path, module_execution = _write_agent_module_execution(
        handoff_stop,
        state="completed",
        result_summary="Completed the wrong plan.",
    )
    if tamper == "plan_digest":
        module_execution["module_work_plan_digest"] = "0" * 64
    elif tamper == "role":
        module_execution["units"][0]["role"] = "reviewer"
    elif tamper == "required":
        module_execution["modules"][0]["required"] = False
    elif tamper == "execution_mode":
        module_execution["modules"][0]["execution_mode"] = "agent_direct"
    else:
        module_execution["modules"][0]["gap_reason"] = "fabricated gap"
    _write_handoff_output_evidence(module_execution_path.parent, module_execution)
    module_execution_path.write_text(
        json.dumps(module_execution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=expected_error):
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT,
            host_id="codex",
            entry_id="vibe",
            prompt="Continue after Agent module execution.",
            artifact_root=artifact_root,
            continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=module_execution_path,
        )

    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()


@pytest.mark.parametrize("source_stage", ["plan_execute", "phase_cleanup"])
def test_rejected_external_result_preserves_published_run_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_stage: str,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    result_path, accepted = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the result.")
    lineage_path = handoff_stop.session_root / "stage-lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    if source_stage == "phase_cleanup":
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return the completed module result.",
            artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=result_path,
        )
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        assert lineage["last_stage_name"] == "phase_cleanup"
    preserved = {
        name: (handoff_stop.session_root / name).read_bytes()
        for name in ("module-execution.json", "stage-lineage.json", "execution-manifest.json", "agent-execution-handoff.json")
    }
    rejected = dict(accepted, source_run_id="different-source-run")
    submitted = tmp_path / "rejected-external.json"
    submitted.write_text(json.dumps(rejected), encoding="utf-8")
    completed = subprocess.run(
        [_powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(REPO_ROOT / "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"),
         "-Task", "Return module results.", "-HostId", "codex", "-EntryId", "vibe", "-RequestedStageStop", "phase_cleanup",
         "-RunId", handoff_stop.run_id, "-ArtifactRoot", str(tmp_path / "artifact-root"), "-ModuleExecutionJsonFile", str(submitted)],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert completed.returncode != 0
    diagnostic = completed.stdout + completed.stderr
    assert "source_run_id" in diagnostic or ("stopped" in diagnostic and "plan_execute" in diagnostic)
    assert preserved == {name: (handoff_stop.session_root / name).read_bytes() for name in preserved}


@pytest.mark.parametrize("evidence_kind", ["missing", "directory"])
def test_canonical_cleanup_requires_the_declared_file_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence_kind: str,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    result_path, payload = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the result.")
    evidence = Path(payload["units"][0]["evidence_paths"][0])
    evidence.unlink()
    if evidence_kind == "directory":
        evidence.mkdir()
    result = canonical_entry.launch_canonical_vibe(
        repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return the module result.",
        artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
        module_execution_json_file=result_path,
    )
    delivery = json.loads((result.session_root / "delivery-acceptance-report.json").read_text(encoding="utf-8"))
    cleanup = json.loads((result.session_root / "cleanup-receipt.json").read_text(encoding="utf-8"))
    assert delivery["summary"]["gate_result"] == "FAIL"
    assert delivery["summary"]["completion_language_allowed"] is False
    assert cleanup["cleanup_admitted"] is False
    assert not (result.session_root / "process-health-audits").exists()


@pytest.mark.parametrize("prior_result", [False, True])
@pytest.mark.parametrize("source_name", ["external", "case_variant"])
def test_valid_external_result_is_published_without_replanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior_result: bool, source_name: str,
) -> None:
    if source_name == "case_variant" and sys.platform == "win32":
        pytest.skip("Distinct paths differing only by case require a case-sensitive filesystem")
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    session = handoff_stop.session_root
    result_path, payload = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the result.")
    before_plan = (session / "module-work-plan.json").read_bytes()
    if not prior_result:
        result_path.unlink()
    payload["units"][0]["result_summary"] = "Published the validated external result."
    external = result_path.with_name("MODULE-EXECUTION.json") if source_name == "case_variant" else tmp_path / "valid-external-result.json"
    external.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [_powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(REPO_ROOT / "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"),
         "-Task", "Return module results.", "-HostId", "codex", "-EntryId", "vibe", "-RequestedStageStop", "phase_cleanup",
         "-RunId", handoff_stop.run_id, "-ArtifactRoot", str(tmp_path / "artifact-root"), "-ModuleExecutionJsonFile", str(external)],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(result_path.read_text(encoding="utf-8")) == payload
    assert (session / "module-work-plan.json").read_bytes() == before_plan
    assert not list(session.glob(".module-execution.*.tmp"))
    report = json.loads((session / "delivery-acceptance-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["completion_language_allowed"] is True


@pytest.mark.parametrize("entry", ["python", "powershell"])
def test_conflicting_tdd_state_is_rejected_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch, code_task_tdd_required=True)
    session = handoff_stop.session_root
    result_path, payload = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the result.")
    handoff = json.loads((session / "agent-execution-handoff.json").read_text(encoding="utf-8"))
    contract = handoff["result_contract"]["tdd_evidence"]
    payload["tdd_evidence"] = {
        "state": "passing", "status": "not_applicable",
        "evidence_paths": [str(session / "missing-red.log"), str(session / "missing-green.log")],
        "red_phase_evidence_paths": [str(session / "missing-red.log")],
        "green_phase_evidence_paths": [str(session / "missing-green.log")],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": contract["required_code_task_tdd_evidence_requirements"],
        "covered_code_task_tdd_exceptions": contract["required_code_task_tdd_exceptions"],
        "notes": "Conflicting fields must not cancel required TDD evidence.",
    }
    external = tmp_path / "conflicting-tdd.json"
    external.write_text(json.dumps(payload), encoding="utf-8")
    before = {name: (session / name).read_bytes() for name in ("module-execution.json", "execution-manifest.json", "stage-lineage.json")}
    if entry == "python":
        with pytest.raises(RuntimeError, match="TDD.*conflict"):
            canonical_entry.launch_canonical_vibe(
                repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return results.",
                artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
                module_execution_json_file=external,
            )
    else:
        completed = _submit_direct_external_result(tmp_path, handoff_stop, external)
        assert completed.returncode != 0
        assert "conflict" in completed.stdout + completed.stderr
    assert before == {name: (session / name).read_bytes() for name in before}
    assert not (session / "cleanup-receipt.json").exists()


def _submit_direct_external_result(
    tmp_path: Path, handoff_stop: canonical_entry.CanonicalLaunchResult, submitted: Path,
) -> subprocess.CompletedProcess[str]:
    bridge = REPO_ROOT / "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"
    # Capture the exception message before terminal wrapping and ANSI formatting.
    command = (
        "try { "
        f"& {_ps_quote(bridge)} -Task 'Return module results.' "
        "-HostId codex -EntryId vibe -RequestedStageStop phase_cleanup "
        f"-RunId {_ps_quote(handoff_stop.run_id)} -ArtifactRoot {_ps_quote(tmp_path / 'artifact-root')} "
        f"-ModuleExecutionJsonFile {_ps_quote(submitted)}"
        " } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"
    )
    return subprocess.run(
        [_powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )


def test_malformed_external_result_shape_preserves_run_and_allows_corrected_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    session = handoff_stop.session_root
    result_path, accepted = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the result.")
    before = {name: (session / name).read_bytes() for name in ("module-execution.json", "execution-manifest.json", "stage-lineage.json", "agent-execution-handoff.json")}
    external = tmp_path / "malformed-external-result.json"
    malformed_results = [
        [accepted],
        dict(accepted, units=accepted["units"][0]),
        dict(accepted, modules=accepted["modules"][0]),
        json.loads(json.dumps(accepted)),
    ]
    malformed_results[-1]["modules"][0]["criterion_results"] = accepted["modules"][0]["criterion_results"][0]
    for malformed in malformed_results:
        external.write_text(json.dumps(malformed), encoding="utf-8")
        rejected = _submit_direct_external_result(tmp_path, handoff_stop, external)
        assert rejected.returncode != 0
        diagnostic = rejected.stdout + rejected.stderr
        assert "JSON object" in diagnostic or "array" in diagnostic
        assert before == {name: (session / name).read_bytes() for name in before}
    external.write_text(json.dumps(accepted), encoding="utf-8")
    corrected = _submit_direct_external_result(tmp_path, handoff_stop, external)
    assert corrected.returncode == 0, corrected.stdout + corrected.stderr
    report = json.loads((session / "delivery-acceptance-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["completion_language_allowed"] is True
    assert json.loads(result_path.read_text(encoding="utf-8")) == accepted


@pytest.mark.parametrize("required", ["false", 1, None])
def test_direct_powershell_required_boolean_matches_python_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, required: object,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    session = handoff_stop.session_root
    result_path, result = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the declared output.")
    original = result_path.read_bytes()
    result["modules"][0]["required"] = required
    external = tmp_path / "malformed-boolean.json"
    external.write_text(json.dumps(result), encoding="utf-8")
    handoff = json.loads((session / "agent-execution-handoff.json").read_text(encoding="utf-8"))
    with pytest.raises(RuntimeError, match="required binding"):
        canonical_entry._validate_agent_module_execution(session_root=session, source_run_id=handoff_stop.run_id, handoff=handoff, submitted=result)
    completed = _submit_direct_external_result(tmp_path, handoff_stop, external)
    assert completed.returncode != 0
    assert result_path.read_bytes() == original
    assert not (session / "cleanup-receipt.json").exists()


@pytest.mark.parametrize("entry", ["python", "powershell", "standalone"])
def test_valid_external_result_with_legacy_tdd_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch, code_task_tdd_required=True)
    session = handoff_stop.session_root
    result_path, result = _write_agent_module_execution(handoff_stop, state="completed", result_summary="Produced the tested result.")
    handoff = json.loads((session / "agent-execution-handoff.json").read_text(encoding="utf-8"))
    contract = handoff["result_contract"]["tdd_evidence"]
    red, green = session / "red.log", session / "green.log"
    red.write_text("1 failed\n", encoding="utf-8")
    green.write_text("1 passed\n", encoding="utf-8")
    result["tdd_evidence"] = {
        "evidence_paths": [str(red), str(green)],
        "red_phase_evidence_paths": [str(red)], "green_phase_evidence_paths": [str(green)],
        "refactor_phase_evidence_paths": [],
        "covered_code_task_tdd_evidence_requirements": contract["required_code_task_tdd_evidence_requirements"],
        "covered_code_task_tdd_exceptions": contract["required_code_task_tdd_exceptions"],
        "notes": "Verified red and green runs.",
    }
    if entry == "standalone":
        result["tdd_evidence"]["state"] = "passing"
    else:
        result["tdd_evidence"]["status" if entry == "powershell" else "state"] = "passed"
    external = tmp_path / "valid-tdd.json"
    external.write_text(json.dumps(result), encoding="utf-8")
    if entry == "python":
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return tested results.",
            artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=external,
        )
    elif entry == "powershell":
        completed = _submit_direct_external_result(tmp_path, handoff_stop, external)
        assert completed.returncode == 0, completed.stdout + completed.stderr
    else:
        script = REPO_ROOT / "scripts/runtime/invoke-vibe-runtime.ps1"
        completed = subprocess.run(
            [_powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
             "try { "
             f"& {_ps_quote(script)} -Task 'Return tested results.' -RequestedStageStop phase_cleanup "
             f"-RunId {_ps_quote(handoff_stop.run_id)} -ArtifactRoot {_ps_quote(tmp_path / 'artifact-root')} "
             f"-ModuleExecutionJsonFile {_ps_quote(external)}"
             " } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=120,
            env={**os.environ, "VCO_HOST_ID": "codex"},
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result_path.read_bytes() == external.read_bytes()
    report = json.loads((session / "delivery-acceptance-report.json").read_text(encoding="utf-8"))
    cleanup = json.loads((session / "cleanup-receipt.json").read_text(encoding="utf-8"))
    assert report["summary"]["completion_language_allowed"] is True
    assert cleanup["cleanup_admitted"] is True


@pytest.mark.parametrize("entry", ["python", "powershell"])
@pytest.mark.parametrize("defect", ["summary", "verification_shape", "verification_conflict"])
def test_invalid_unit_result_is_rejected_before_publication_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, defect: str,
) -> None:
    handoff_stop = _launch_handoff_stop(tmp_path, monkeypatch)
    session = handoff_stop.session_root
    result_path, accepted = _write_agent_module_execution(
        handoff_stop, state="completed", result_summary="Produced the approved output.",
    )
    malformed = json.loads(json.dumps(accepted))
    unit = malformed["units"][0]
    if defect == "summary":
        unit["result_summary"] = {"error": "Unstructured result"}
        expected_error = "result_summary"
    elif defect == "verification_shape":
        unit["verification_results"] = "checks failed"
        expected_error = "verification_results"
    else:
        unit["verification_results"][0]["state"] = "failing"
        expected_error = "conflicts with passing module criterion"
    external = tmp_path / "invalid-unit-result.json"
    external.write_text(json.dumps(malformed), encoding="utf-8")
    preserved = {
        name: (session / name).read_bytes()
        for name in ("module-execution.json", "module-work-plan.json", "execution-manifest.json",
                     "stage-lineage.json", "agent-execution-handoff.json")
    }
    if entry == "python":
        with pytest.raises(RuntimeError, match=expected_error):
            canonical_entry.launch_canonical_vibe(
                repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return module results.",
                artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
                module_execution_json_file=external,
            )
    else:
        rejected = _submit_direct_external_result(tmp_path, handoff_stop, external)
        assert rejected.returncode != 0
        assert expected_error in rejected.stdout + rejected.stderr
    assert preserved == {name: (session / name).read_bytes() for name in preserved}
    assert not (session / "cleanup-receipt.json").exists()
    assert not list(session.glob(".module-execution.*.tmp"))

    external.write_text(json.dumps(accepted), encoding="utf-8")
    if entry == "python":
        canonical_entry.launch_canonical_vibe(
            repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return corrected module results.",
            artifact_root=tmp_path / "artifact-root", continue_from_run_id=handoff_stop.run_id,
            module_execution_json_file=external,
        )
    else:
        corrected = _submit_direct_external_result(tmp_path, handoff_stop, external)
        assert corrected.returncode == 0, corrected.stdout + corrected.stderr
    assert json.loads(result_path.read_text(encoding="utf-8")) == accepted
    assert (session / "module-work-plan.json").read_bytes() == preserved["module-work-plan.json"]
    report = json.loads((session / "delivery-acceptance-report.json").read_text(encoding="utf-8"))
    assert report["summary"]["completion_language_allowed"] is True


@pytest.mark.parametrize("entry", ["python", "powershell", "raw-powershell"])
@pytest.mark.parametrize("requested_root", ["omitted", "conflicting"])
def test_result_reentry_preserves_frozen_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, requested_root: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    different = tmp_path / "different-workspace"
    different.mkdir()
    stopped = _launch_handoff_stop(tmp_path, monkeypatch, workspace_root=workspace)
    submitted, _ = _write_agent_module_execution(stopped, state="completed", result_summary="Produced the result in the approved workspace.")
    session = stopped.session_root
    before = {path.relative_to(session): path.read_bytes() for path in session.rglob("*") if path.is_file()}
    if entry == "python":
        arguments = dict(repo_root=REPO_ROOT, host_id="codex", entry_id="vibe", prompt="Return module results.", artifact_root=tmp_path / "artifact-root", continue_from_run_id=stopped.run_id, module_execution_json_file=submitted)
        if requested_root == "conflicting":
            with pytest.raises(RuntimeError, match="workspace.*frozen"):
                canonical_entry.launch_canonical_vibe(**arguments, workspace_root=different)
        else:
            result = canonical_entry.launch_canonical_vibe(**arguments)
            assert Path(result.summary["storage"]["workspace_root"]).resolve() == workspace.resolve()
    else:
        script = REPO_ROOT / (
            "scripts/runtime/invoke-vibe-runtime.ps1" if entry == "raw-powershell"
            else "scripts/runtime/Invoke-VibeCanonicalEntry.ps1"
        )
        command = [
            _powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
            "-Task", "Return module results.",
            "-RequestedStageStop", "phase_cleanup", "-RunId", stopped.run_id,
            "-ArtifactRoot", str(tmp_path / "artifact-root"), "-ModuleExecutionJsonFile", str(submitted),
        ]
        if entry == "powershell":
            command.extend(["-HostId", "codex", "-EntryId", "vibe"])
        if requested_root == "conflicting":
            command.extend(["-WorkspaceRoot", str(different)])
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if requested_root == "conflicting":
            assert result.returncode != 0
            assert "workspace" in result.stdout + result.stderr
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            summary = json.loads((session / "runtime-summary.json").read_text(encoding="utf-8"))
            assert Path(summary["storage"]["workspace_root"]).resolve() == workspace.resolve()
    if requested_root == "conflicting":
        assert before == {path.relative_to(session): path.read_bytes() for path in session.rglob("*") if path.is_file()}
        assert not any(different.iterdir())
    else:
        packet = json.loads((session / "runtime-input-packet.json").read_text(encoding="utf-8"))
        assert Path(packet["storage"]["workspace_root"]).resolve() == workspace.resolve()
        assert (workspace / "outputs/handoff-result.md").is_file()
        assert not any(different.iterdir())
