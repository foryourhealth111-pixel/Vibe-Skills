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
    artifact_root = tmp_path / "artifact-root"
    handoff_stop = _launch_handoff_stop(
        tmp_path,
        monkeypatch,
        code_task_tdd_required=True,
    )
    module_execution_path, module_execution = _write_agent_module_execution(
        handoff_stop,
        state="completed",
        result_summary="Produced the approved handoff result with TDD.",
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
                "-Task 'Continue after incomplete code-task TDD evidence.' "
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
    assert "TDD evidence state" in (completed.stdout + completed.stderr)
    lineage = json.loads(
        (handoff_stop.session_root / "stage-lineage.json").read_text(encoding="utf-8")
    )
    assert lineage["last_stage_name"] == "plan_execute"
    assert not (handoff_stop.session_root / "cleanup-receipt.json").exists()

    handoff = json.loads(
        Path(handoff_stop.summary["artifacts"]["agent_execution_handoff"]).read_text(
            encoding="utf-8"
        )
    )
    red_path = handoff_stop.session_root / "direct-red.txt"
    green_path = handoff_stop.session_root / "direct-green.txt"
    red_path.write_text("1 failed\n", encoding="utf-8")
    green_path.write_text("1 passed\n", encoding="utf-8")
    tdd_contract = handoff["result_contract"]["tdd_evidence"]
    module_execution["tdd_evidence"] = {
        "state": "passing",
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
                "-Task 'Continue after corrected code-task TDD evidence.' "
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
    cleanup = json.loads(
        (handoff_stop.session_root / "cleanup-receipt.json").read_text(encoding="utf-8")
    )
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
