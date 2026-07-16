from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_COMMON = REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1"
PLAN_EXECUTE = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"
FREEZE_PACKET = REPO_ROOT / "scripts" / "runtime" / "Freeze-RuntimeInputPacket.ps1"
SKILL_ROUTING = REPO_ROOT / "scripts" / "runtime" / "VibeSkillRouting.Common.ps1"
CUSTOM_ADMISSION = REPO_ROOT / "packages" / "runtime-core" / "src" / "vgo_runtime" / "custom_admission.py"
CUSTOM_ADMISSION_PS = REPO_ROOT / "scripts" / "router" / "modules" / "19-custom-admission.ps1"
RUNTIME_PACKET_POLICY = REPO_ROOT / "config" / "runtime-input-packet-policy.json"
RUNTIME_PROTOCOL = REPO_ROOT / "protocols" / "runtime.md"


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def test_runtime_common_describes_agent_led_module_execution_only() -> None:
    text = RUNTIME_COMMON.read_text(encoding="utf-8")

    assert "Read each listed `SKILL.md`" in text
    assert "write the result to `module-execution.json`" in text
    assert "return through canonical `vibe`" in text
    assert "Vibe organizes modules and skills; the Agent executes the module work." in text

    retired_language = (
        "skill_usage.used",
        "skill_usage.evidence",
        "material-use evidence",
        "live native dispatch",
        "execution-time specialist dispatch",
        "live_native_execution",
        "native_usage_required",
        "usage_required",
        "skill_execution_decision",
    )
    for phrase in retired_language:
        assert phrase not in text


def test_runtime_protocol_defines_the_fillable_result_contract_and_same_run_retry() -> None:
    text = RUNTIME_PROTOCOL.read_text(encoding="utf-8")

    assert "copy `result_contract.submission_template`" in text
    assert "`criterion_results` states are `passing`, `failing`, or `blocked`" in text
    assert "same `module-execution.json`" in text
    assert "same return command" in text
    assert "before `phase_cleanup`" in text


def test_runtime_common_does_not_read_retired_specialist_decision_sidecar() -> None:
    text = RUNTIME_COMMON.read_text(encoding="utf-8") + PLAN_EXECUTE.read_text(encoding="utf-8")

    assert "Get-VibeOptionalSpecialistDecisionOverride" not in text
    assert "Get-VibeSpecialistDecisionSidecarPath" not in text
    assert "specialist-decision.json" not in text


def test_active_agent_handoff_surfaces_remove_native_execution_fields() -> None:
    active_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            FREEZE_PACKET,
            SKILL_ROUTING,
            PLAN_EXECUTE,
            CUSTOM_ADMISSION,
            CUSTOM_ADMISSION_PS,
            RUNTIME_PACKET_POLICY,
        )
    )

    retired_terms = (
        "native_usage_required",
        "usage_required",
        "live_native_execution",
        "live_native_executed",
        "live_native_partial_failures",
        "live_native_failed",
        "native_contract_complete_for_approved_dispatch",
        "Get-VibeDispatchUsageRequirementState",
        "native_skill_entrypoint",
        "native_contract",
    )
    for term in retired_terms:
        assert term not in active_text


def test_plan_execute_does_not_keep_retired_specialist_execution_model() -> None:
    plan_execute_text = PLAN_EXECUTE.read_text(encoding="utf-8")

    retired_terms = (
        "New-VibeBlockedSpecialistDispatchResult",
        "'skill_execution'",
        "specialist_accounting",
        "executedSpecialistUnits",
        "executed_skill_execution_units",
        "failed_skill_execution_units",
        "blocked_skill_execution_units",
        "degraded_skill_execution_units",
        "skill_execution_unit_count",
        "specialist_decision",
        "specialist_user_disclosure",
    )
    for term in retired_terms:
        assert term not in plan_execute_text
