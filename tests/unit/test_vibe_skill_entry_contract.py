from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = ROOT / "SKILL.md"
INSTRUCTION_MD = ROOT / "core" / "skills" / "vibe" / "instruction.md"


def _skill_text() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _instruction_text() -> str:
    return INSTRUCTION_MD.read_text(encoding="utf-8")


def test_vibe_skill_entry_preserves_canonical_runtime_anchors() -> None:
    text = _skill_text()

    required = [
        "$vibe",
        "/vibe",
        "scripts/router/resolve-pack-route.ps1",
        "py -3 -m vgo_cli.main canonical-entry",
        "--host-decision-json-file",
        "--continue-from-run-id",
        "--bounded-reentry-token",
        "revision_delta",
        "update --skills-dir <skills-dir>",
        "protocols/runtime.md",
        "core/skill-contracts/v1/vibe.json",
    ]
    for needle in required:
        assert needle in text

    for artifact in (
        "host-launch-receipt.json",
        "runtime-input-packet.json",
        "governance-capsule.json",
        "stage-lineage.json",
    ):
        assert artifact in text

    for stage in (
        "skeleton_check",
        "deep_interview",
        "requirement_doc",
        "xl_plan",
        "plan_execute",
        "phase_cleanup",
    ):
        assert stage in text


def test_vibe_skill_entry_stays_sop_sized_and_avoids_overtriggering_language() -> None:
    text = _skill_text()

    assert len(text.splitlines()) <= 245
    assert "1% chance" not in text
    assert "YOU DO NOT HAVE A CHOICE" not in text
    assert "This is not negotiable" not in text


def test_vibe_skill_entry_requires_requirement_stop_reply_to_explain_agent_skill_search() -> None:
    text = _skill_text()

    assert "host_user_briefing" in text
    assert "skill search guide" in text
    assert "split the task into modules" in text
    assert "search local skills per module" in text
    assert "read candidate `SKILL.md`" in text
    assert "disclose uncovered modules honestly" in text
    assert "backbone of the user reply" in text
    assert "Keep the same field order" in text
    assert "Do not surface shortlist size" in text
    assert "Do not ask the user to choose L or XL until" in text
    assert "task-specific workflow" in text
    assert "task-specific candidate skill names" in text
    assert "not yet selected or used" in text


def test_vibe_core_instruction_locks_requirement_stop_reply_to_host_briefing() -> None:
    text = _instruction_text()

    assert "host must reuse the runtime skill-search guide" in text
    assert "same field order" in text
    assert "split the task into modules" in text
    assert "not surface shortlist or selected-skill rankings" in text
    assert "must not ask the user to choose L or XL until" in text
    assert "task-specific candidate skill names" in text


def test_vibe_entry_requires_agent_skill_organization_before_plan_and_execute() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "HostDecisionJson.agent_skill_organization" in text
        assert "search every declared local skill root" in text
        assert "read each retained candidate's `SKILL.md`" in text
        assert "before entering `xl_plan`" in text
        assert "reuse the frozen `agent_skill_organization`" in text
        assert "do not rerun procedural skill selection" in text


def test_vibe_entry_reentry_example_includes_structured_module_acceptance() -> None:
    text = _skill_text()

    assert '"acceptance_criteria": [{' in text
    assert '"criterion_id": "module-a-result"' in text
    assert '"description": "The module result satisfies the frozen requirement."' in text
    assert '"verification_mode": "automated"' in text


def test_vibe_entry_keeps_module_acceptance_pre_return() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "Module acceptance criteria must be satisfiable before canonical module-result re-entry" in text
        assert "cleanup receipts, delivery acceptance, or completion-language permission" in text


def test_vibe_entry_keeps_module_acceptance_focused_on_real_work_outputs() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "Verify ordinary modules from their actual deliverables and normal command or test output" in text
        assert "Do not invent task-specific hashes, receipts, ledgers, matrices, scans, or proof files" in text
        assert "Only require an extra evidence artifact when the user or domain contract needs that artifact" in text


def test_vibe_entry_requires_module_specific_multi_module_skill_assignments() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "one `module_assignments` entry per module" in text
        assert "`owner`, `support`, or `verifier`" in text
        assert "one concrete write scope" in text
        assert "at most two dependency-ready units" in text
        assert "nested or overlapping write scopes" in text


def test_vibe_entry_explains_role_order_before_plan_freeze() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "`support` runs before and feeds the `owner`" in text
        assert "`verifier` runs only after the `owner`" in text
        assert "post-owner review or minimality check must use `verifier`, not `support`" in text


def test_vibe_entry_requires_explicit_agent_direct_work_contract() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "An `agent_direct` module must declare its own concrete `write_scope`, `expected_outputs`, and `verification`" in text
        assert "must not replace them with a generic module label or restated goal" in text


def test_vibe_entry_requires_full_organization_for_structural_plan_revision() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "A plan revision that changes modules, Skills, roles, dependencies, write scopes, outputs, verification, or workflow level" in text
        assert "must resubmit the complete updated `agent_skill_organization`" in text
        assert "`revision_delta` alone records text and does not mutate the frozen organization" in text


def test_vibe_entry_keeps_task_work_scopes_out_of_runtime_metadata() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "must not claim canonical runtime artifacts such as `module-execution.json`" in text
        assert "use a stable task-owned output scope or `no task-file writes`" in text


def test_vibe_entry_explains_l_stage_order_and_execution_waves() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "`stage_order` records dependency depth, not permission to run in parallel" in text
        assert "L still emits one-unit sequential waves" in text


def test_vibe_entry_makes_agent_module_result_return_directly_fillable_and_retryable() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "copy `result_contract.submission_template`" in text
        assert "`criterion_results` states must be exactly `passing`, `failing`, or `blocked`" in text
        assert "correct the same `module-execution.json` and reuse the same return command" in text


def test_vibe_entry_keeps_code_task_tdd_evidence_in_module_execution() -> None:
    for text in (_skill_text(), _instruction_text()):
        assert "Code-task TDD evidence belongs inside the same `module-execution.json`" in text
        assert "do not create a separate `tdd-evidence.json` sidecar" in text

