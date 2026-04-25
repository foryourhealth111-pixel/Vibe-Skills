from __future__ import annotations

from pathlib import Path
from typing import Any

from .runtime_delivery_acceptance_support import (
    _derive_readiness_state,
    _extract_bullets,
    _manual_spot_checks_from_requirement,
    _missing_frozen_items,
    _normalize_skill_id_list,
    _normalize_truth_state,
    _normalize_string_list,
    _read_text_if_exists,
    _requirement_optional_bullets,
    _resolve_artifact_review_payload,
    _resolve_specialist_execution_payload,
    _resolve_specialist_decision_payload,
    _resolve_tdd_evidence_payload,
    _truth_completion_allowed,
    _truth_success,
    load_json,
    utc_now,
)


def _normalize_entrypoint_path_for_compare(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    normalized = raw.replace("\\", "/").rstrip("/")
    lower_normalized = normalized.lower()
    is_drive_path = len(normalized) >= 3 and normalized[1:3] == ":/"
    is_posix_drive_path = len(normalized) >= 3 and normalized[0] == "/" and normalized[1].isalpha() and normalized[2] == "/"
    is_wsl_drive_path = (
        len(normalized) >= 7
        and lower_normalized.startswith("/mnt/")
        and normalized[5].isalpha()
        and normalized[6] == "/"
    )
    if is_drive_path or is_posix_drive_path or is_wsl_drive_path:
        return normalized.casefold()
    if "\\" in raw:
        return normalized.casefold()
    return normalized


def evaluate_delivery_acceptance(repo_root: Path, session_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / "config" / "project-delivery-acceptance-contract.json")
    execute_receipt_path = session_root / "phase-execute.json"
    cleanup_receipt_path = session_root / "cleanup-receipt.json"

    execute_receipt = load_json(execute_receipt_path)
    cleanup_receipt = load_json(cleanup_receipt_path)

    requirement_doc_path = Path(str(execute_receipt.get("requirement_doc_path") or ""))
    execution_plan_path = Path(str(execute_receipt.get("execution_plan_path") or ""))
    execution_manifest_path = Path(str(execute_receipt.get("execution_manifest_path") or ""))
    runtime_input_packet_path = Path(str(execute_receipt.get("runtime_input_packet_path") or ""))

    requirement_text = _read_text_if_exists(requirement_doc_path)
    execution_plan_text = _read_text_if_exists(execution_plan_path)
    execution_manifest = load_json(execution_manifest_path)
    runtime_input_packet = load_json(runtime_input_packet_path) if runtime_input_packet_path.exists() else {}
    specialist_dispatch = runtime_input_packet.get("specialist_dispatch") or {}
    specialist_accounting = execution_manifest.get("specialist_accounting") or {}

    product_acceptance_criteria = _extract_bullets(requirement_text, "Product Acceptance Criteria")
    manual_spot_checks, manual_section_missing = _manual_spot_checks_from_requirement(requirement_text)
    completion_language_policy = _extract_bullets(requirement_text, "Completion Language Policy")
    delivery_truth_contract = _extract_bullets(requirement_text, "Delivery Truth Contract")
    artifact_review_requirements = _requirement_optional_bullets(requirement_text, "Artifact Review Requirements")
    code_task_tdd_evidence_requirements = _requirement_optional_bullets(
        requirement_text,
        "Code Task TDD Evidence Requirements",
    )
    code_task_tdd_exceptions = _requirement_optional_bullets(requirement_text, "Code Task TDD Exceptions")
    baseline_document_quality_dimensions = _requirement_optional_bullets(
        requirement_text,
        "Baseline Document Quality Dimensions",
    )
    baseline_ui_quality_dimensions = _requirement_optional_bullets(requirement_text, "Baseline UI Quality Dimensions")
    task_specific_acceptance_extensions = _requirement_optional_bullets(
        requirement_text,
        "Task-Specific Acceptance Extensions",
    )
    research_augmentation_sources = _requirement_optional_bullets(
        requirement_text,
        "Research Augmentation Sources",
    )
    artifact_review_payload = _resolve_artifact_review_payload(session_root, execute_receipt)
    specialist_decision_payload = _resolve_specialist_decision_payload(session_root, execute_receipt)
    specialist_execution_payload = _resolve_specialist_execution_payload(session_root, execute_receipt)
    tdd_evidence_payload = _resolve_tdd_evidence_payload(session_root, execute_receipt)
    specialist_user_disclosure = execute_receipt.get("specialist_user_disclosure") or {}
    disclosure_routed_skills = specialist_user_disclosure.get("routed_skills") or []

    governance_truth_state = "passing"
    governance_truth_notes: list[str] = []
    required_artifacts = [
        execute_receipt_path,
        cleanup_receipt_path,
        requirement_doc_path,
        execution_plan_path,
        execution_manifest_path,
    ]
    missing_artifacts = [str(path) for path in required_artifacts if not path.exists()]
    if missing_artifacts:
        governance_truth_state = "failing"
        governance_truth_notes.append("Required runtime artifacts are missing.")
    elif str((runtime_input_packet.get("authority_flags") or {}).get("explicit_runtime_skill") or "vibe") != "vibe":
        governance_truth_state = "degraded"
        governance_truth_notes.append("Runtime authority drifted away from vibe.")
    elif str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        governance_truth_state = "degraded"
        governance_truth_notes.append("Cleanup degraded before closure.")

    execution_status = str(execution_manifest.get("status") or "")
    failed_unit_count = int(execution_manifest.get("failed_unit_count") or 0)
    timed_out_unit_count = int(execution_manifest.get("timed_out_unit_count") or 0)
    executed_unit_count = int(execution_manifest.get("executed_unit_count") or 0)

    engineering_truth_state = "passing"
    engineering_truth_notes: list[str] = []
    if executed_unit_count == 0 or execution_status == "failed":
        engineering_truth_state = "failing"
        engineering_truth_notes.append("No executable verification path completed successfully.")
    elif execution_status == "completed_with_failures" or failed_unit_count > 0 or timed_out_unit_count > 0:
        engineering_truth_state = "partial"
        engineering_truth_notes.append("Execution verification completed with failing or timed-out units.")

    code_task_tdd_evidence_state = "not_applicable"
    code_task_tdd_evidence_notes: list[str] = []
    code_task_tdd_evidence_evidence = _normalize_string_list(tdd_evidence_payload.get("evidence_paths"))
    code_task_tdd_evidence_source_path = str(tdd_evidence_payload.get("source_path") or "").strip()
    if code_task_tdd_evidence_source_path:
        code_task_tdd_evidence_evidence = [code_task_tdd_evidence_source_path, *code_task_tdd_evidence_evidence]
    covered_code_task_tdd_evidence_requirements = _normalize_string_list(
        tdd_evidence_payload.get("covered_code_task_tdd_evidence_requirements")
    )
    covered_code_task_tdd_exceptions = _normalize_string_list(
        tdd_evidence_payload.get("covered_code_task_tdd_exceptions")
    )
    red_phase_evidence_paths = _normalize_string_list(tdd_evidence_payload.get("red_phase_evidence_paths"))
    green_phase_evidence_paths = _normalize_string_list(tdd_evidence_payload.get("green_phase_evidence_paths"))
    refactor_phase_evidence_paths = _normalize_string_list(tdd_evidence_payload.get("refactor_phase_evidence_paths"))
    missing_code_task_tdd_evidence_requirements = _missing_frozen_items(
        code_task_tdd_evidence_requirements,
        covered_code_task_tdd_evidence_requirements,
    )
    missing_code_task_tdd_exceptions = _missing_frozen_items(
        code_task_tdd_exceptions,
        covered_code_task_tdd_exceptions,
    )

    raw_tdd_evidence_state = str(tdd_evidence_payload.get("status") or tdd_evidence_payload.get("state") or "").strip()
    if code_task_tdd_evidence_requirements or code_task_tdd_exceptions:
        if not tdd_evidence_payload:
            code_task_tdd_evidence_state = "manual_review_required"
            code_task_tdd_evidence_notes.append(
                "Requirement doc froze code-task TDD evidence requirements but no TDD evidence payload was recorded."
            )
        else:
            code_task_tdd_evidence_state = _normalize_truth_state(raw_tdd_evidence_state)
            if code_task_tdd_evidence_state in {"", "not_run"}:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD evidence was required, but the recorded TDD status did not close the review."
                )
            elif code_task_tdd_evidence_state == "passing" and not code_task_tdd_evidence_evidence:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD evidence reported passing, but no evidence paths were recorded."
                )

        if code_task_tdd_evidence_state == "passing":
            if code_task_tdd_exceptions and missing_code_task_tdd_exceptions:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD exception coverage did not close all frozen exceptions."
                )
            if code_task_tdd_evidence_requirements and missing_code_task_tdd_evidence_requirements:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD evidence did not record coverage for all frozen TDD requirements."
                )
            if code_task_tdd_evidence_requirements and not red_phase_evidence_paths:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD evidence did not record failing-first evidence paths."
                )
            if code_task_tdd_evidence_requirements and not green_phase_evidence_paths:
                code_task_tdd_evidence_state = "manual_review_required"
                code_task_tdd_evidence_notes.append(
                    "Code-task TDD evidence did not record green-phase verification evidence paths."
                )

    tdd_evidence_payload_notes = str(tdd_evidence_payload.get("notes") or "").strip()
    if tdd_evidence_payload_notes:
        code_task_tdd_evidence_notes.append(tdd_evidence_payload_notes)

    if "approved_dispatch" in specialist_accounting:
        approved_dispatch = specialist_accounting.get("approved_dispatch") or []
    else:
        approved_dispatch = specialist_dispatch.get("approved_dispatch") or []
    approved_dispatch_skill_ids = _normalize_skill_id_list(approved_dispatch)
    runtime_specialist_execution_status = str(specialist_accounting.get("effective_execution_status") or "").strip()
    effective_specialist_execution_status = runtime_specialist_execution_status

    disclosure_entrypoint_by_skill_id: dict[str, str] = {}
    for record in disclosure_routed_skills:
        if not isinstance(record, dict):
            continue
        skill_id = str(record.get("skill_id") or record.get("id") or record.get("name") or "").strip()
        native_skill_entrypoint = str(record.get("native_skill_entrypoint") or "").strip()
        if skill_id and native_skill_entrypoint and skill_id not in disclosure_entrypoint_by_skill_id:
            disclosure_entrypoint_by_skill_id[skill_id] = native_skill_entrypoint

    raw_specialist_execution_units = specialist_execution_payload.get("units") or []
    if not isinstance(raw_specialist_execution_units, list):
        raw_specialist_execution_units = [raw_specialist_execution_units] if raw_specialist_execution_units else []

    direct_routed_units_key_present = "direct_routed_specialist_units" in specialist_accounting
    raw_direct_routed_specialist_units = specialist_accounting.get("direct_routed_specialist_units") or []
    if not direct_routed_units_key_present and raw_specialist_execution_units:
        raw_direct_routed_specialist_units = [
            {
                "unit_id": str(record.get("unit_id") or "").strip(),
                "skill_id": str(record.get("skill_id") or record.get("specialist_skill_id") or "").strip(),
                "result_path": str(record.get("result_path") or "").strip(),
            }
            for record in raw_specialist_execution_units
            if isinstance(record, dict)
        ]
    if not isinstance(raw_direct_routed_specialist_units, list):
        raw_direct_routed_specialist_units = [raw_direct_routed_specialist_units] if raw_direct_routed_specialist_units else []

    direct_routed_specialist_units: list[dict[str, Any]] = []
    direct_routed_unit_index: dict[str, dict[str, Any]] = {}
    for item in raw_direct_routed_specialist_units:
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("unit_id") or "").strip()
        skill_id = str(item.get("skill_id") or item.get("specialist_skill_id") or "").strip()
        result_path_raw = str(item.get("result_path") or "").strip()
        result_path = ""
        if result_path_raw:
            candidate_path = Path(result_path_raw)
            result_path = str((session_root / candidate_path).resolve() if not candidate_path.is_absolute() else candidate_path.resolve())
        normalized_unit = {
            "unit_id": unit_id,
            "skill_id": skill_id,
            "native_skill_entrypoint": disclosure_entrypoint_by_skill_id.get(skill_id, ""),
            "result_path": result_path,
        }
        direct_routed_specialist_units.append(normalized_unit)
        if unit_id and unit_id not in direct_routed_unit_index:
            direct_routed_unit_index[unit_id] = normalized_unit

    direct_routed_unit_ids = list(direct_routed_unit_index.keys())
    direct_routed_skill_ids = _normalize_skill_id_list(direct_routed_specialist_units)

    specialist_execution_source_path = str(specialist_execution_payload.get("source_path") or "").strip()
    specialist_execution_resolution_mode = str(specialist_execution_payload.get("resolution_mode") or "").strip().lower()
    specialist_execution_evidence = _normalize_string_list(specialist_execution_payload.get("evidence_paths"))
    if specialist_execution_source_path:
        specialist_execution_evidence = [specialist_execution_source_path, *specialist_execution_evidence]

    if (
        not runtime_specialist_execution_status
        and approved_dispatch_skill_ids
        and (
            direct_routed_unit_ids
            or raw_specialist_execution_units
            or specialist_execution_resolution_mode == "current_session_host_execution"
        )
    ):
        runtime_specialist_execution_status = "direct_current_session_routed"
        effective_specialist_execution_status = runtime_specialist_execution_status

    specialist_execution_notes: list[str] = []
    specialist_execution_payload_invalid = str(
        specialist_execution_payload.get("__vgo_payload_state") or ""
    ).strip().lower() == "invalid"
    specialist_execution_payload_valid = not specialist_execution_payload_invalid
    if specialist_execution_payload_invalid:
        invalid_reason = str(specialist_execution_payload.get("invalid_reason") or "").strip()
        specialist_execution_notes.append(
            "Specialist execution sidecar was present but invalid"
            + (f": {invalid_reason}" if invalid_reason else ".")
        )
    specialist_host_resolution_state = "not_applicable"
    specialist_host_executed_unit_count = 0
    specialist_host_degraded_unit_count = 0
    specialist_host_blocked_unit_count = 0
    specialist_host_failed_unit_count = 0
    specialist_host_resolved_units: list[dict[str, Any]] = []
    seen_specialist_execution_unit_ids: set[str] = set()
    specialist_execution_state_aliases = {
        "executed": "executed",
        "completed": "executed",
        "passing": "executed",
        "pass": "executed",
        "degraded": "degraded",
        "blocked": "blocked",
        "failed": "failed",
        "failing": "failed",
    }

    expected_source_run_id = str(execute_receipt.get("run_id") or execution_manifest.get("run_id") or "").strip()
    recorded_source_run_id = str(specialist_execution_payload.get("source_run_id") or "").strip()
    if recorded_source_run_id and expected_source_run_id and recorded_source_run_id != expected_source_run_id:
        specialist_execution_payload_valid = False
        specialist_execution_notes.append(
            "Specialist execution sidecar source_run_id did not match the governed run being evaluated."
        )

    direct_routed_unit_id_set = set(direct_routed_unit_ids)
    for record in raw_specialist_execution_units:
        if not isinstance(record, dict):
            specialist_execution_payload_valid = False
            specialist_execution_notes.append("Specialist execution sidecar contained a non-object unit record.")
            continue

        unit_id = str(record.get("unit_id") or "").strip()
        if not unit_id:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append("Specialist execution sidecar contained a unit record without unit_id.")
            continue
        if unit_id in seen_specialist_execution_unit_ids:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar duplicated unit_id `{unit_id}`."
            )
            continue
        seen_specialist_execution_unit_ids.add(unit_id)

        if unit_id not in direct_routed_unit_id_set:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar referenced unknown direct-routed unit_id `{unit_id}`."
            )
            continue

        expected_unit = direct_routed_unit_index.get(unit_id) or {}
        expected_skill_id = str(expected_unit.get("skill_id") or "").strip()
        skill_id = str(record.get("skill_id") or expected_skill_id).strip()
        if expected_skill_id and skill_id and skill_id != expected_skill_id:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar unit `{unit_id}` reported skill_id `{skill_id}` but expected `{expected_skill_id}`."
            )
            continue

        resolution_state_raw = str(
            record.get("resolution_state") or record.get("state") or record.get("status") or ""
        ).strip().lower()
        resolution_state = specialist_execution_state_aliases.get(resolution_state_raw, "")
        if not resolution_state:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar unit `{unit_id}` used unsupported resolution state `{resolution_state_raw or 'missing'}`."
            )
            continue

        evidence_paths = _normalize_string_list(record.get("evidence_paths"))
        if not evidence_paths:
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar unit `{unit_id}` did not record evidence_paths."
            )
            continue

        native_skill_entrypoint = str(record.get("native_skill_entrypoint") or "").strip()
        expected_entrypoint = str(expected_unit.get("native_skill_entrypoint") or "").strip()
        if (
            native_skill_entrypoint
            and expected_entrypoint
            and _normalize_entrypoint_path_for_compare(native_skill_entrypoint)
            != _normalize_entrypoint_path_for_compare(expected_entrypoint)
        ):
            specialist_execution_payload_valid = False
            specialist_execution_notes.append(
                f"Specialist execution sidecar unit `{unit_id}` changed native_skill_entrypoint away from the disclosed value."
            )
            continue

        normalized_record = {
            "unit_id": unit_id,
            "skill_id": skill_id,
            "resolution_state": resolution_state,
            "native_skill_entrypoint": native_skill_entrypoint or expected_entrypoint,
            "evidence_paths": evidence_paths,
            "notes": str(record.get("notes") or "").strip(),
        }
        specialist_host_resolved_units.append(normalized_record)
        if resolution_state == "executed":
            specialist_host_executed_unit_count += 1
        elif resolution_state == "degraded":
            specialist_host_degraded_unit_count += 1
        elif resolution_state == "blocked":
            specialist_host_blocked_unit_count += 1
        elif resolution_state == "failed":
            specialist_host_failed_unit_count += 1

    missing_direct_routed_unit_ids = [
        unit_id for unit_id in direct_routed_unit_ids if unit_id not in seen_specialist_execution_unit_ids
    ]

    specialist_host_continuation_pending = False
    if approved_dispatch_skill_ids and runtime_specialist_execution_status == "direct_current_session_routed":
        if not direct_routed_unit_ids:
            specialist_host_continuation_pending = True
            specialist_host_resolution_state = "pending"
            specialist_execution_notes.append(
                "Approved execution stayed current-session routed but no direct-routed specialist units were recorded."
            )
        elif specialist_execution_payload_invalid:
            specialist_host_resolution_state = "invalid"
        elif not specialist_execution_payload:
            specialist_host_continuation_pending = True
            specialist_host_resolution_state = "pending"
        elif not specialist_execution_payload_valid:
            specialist_host_resolution_state = "invalid"
        elif missing_direct_routed_unit_ids:
            specialist_host_continuation_pending = True
            specialist_host_resolution_state = "pending"
            specialist_execution_notes.append(
                "Specialist execution sidecar did not resolve all direct-routed specialist units."
            )
        elif specialist_host_failed_unit_count > 0 and (
            specialist_host_executed_unit_count > 0
            or specialist_host_degraded_unit_count > 0
            or specialist_host_blocked_unit_count > 0
        ):
            specialist_host_resolution_state = "partial_failed"
            effective_specialist_execution_status = "host_current_session_failed"
        elif specialist_host_failed_unit_count > 0:
            specialist_host_resolution_state = "failed"
            effective_specialist_execution_status = "host_current_session_failed"
        elif specialist_host_blocked_unit_count > 0 and (
            specialist_host_executed_unit_count > 0 or specialist_host_degraded_unit_count > 0
        ):
            specialist_host_resolution_state = "partial_non_green"
            effective_specialist_execution_status = "host_current_session_partial"
        elif specialist_host_blocked_unit_count > 0:
            specialist_host_resolution_state = "blocked"
            effective_specialist_execution_status = "host_current_session_blocked"
        elif specialist_host_degraded_unit_count > 0:
            specialist_host_resolution_state = "degraded"
            effective_specialist_execution_status = "host_current_session_degraded"
        else:
            specialist_host_resolution_state = "executed"
            effective_specialist_execution_status = "host_current_session_executed"

    workflow_truth_state = "passing"
    workflow_truth_notes: list[str] = []
    workflow_truth_evidence = [str(execute_receipt_path), str(cleanup_receipt_path)]
    if specialist_execution_evidence:
        workflow_truth_evidence.extend(specialist_execution_evidence)
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        workflow_truth_state = "degraded"
        workflow_truth_notes.append("Cleanup degraded, so workflow closure is not fully authoritative.")
    elif execution_status == "completed_local_scope" or not bool(execute_receipt.get("completion_claim_allowed")):
        workflow_truth_state = "partial"
        workflow_truth_notes.append("This run closed only a bounded local scope, not the full root task.")
    elif execution_status == "completed_with_failures":
        workflow_truth_state = "partial"
        workflow_truth_notes.append("Workflow closed with failed units still present.")
    elif specialist_host_continuation_pending:
        workflow_truth_state = "manual_review_required"
        workflow_truth_notes.append(
            "Approved execution remained routed to the current host session; host continuation is still required before the run can be reported as complete."
        )
    elif specialist_host_resolution_state == "invalid":
        workflow_truth_state = "manual_review_required"
        workflow_truth_notes.append(
            "Current-session specialist execution was reported, but the specialist execution sidecar did not validate cleanly."
        )
    elif specialist_host_resolution_state == "partial_non_green":
        workflow_truth_state = "partial"
        workflow_truth_notes.append(
            "Current-session specialist execution resolved the handoff, but one or more approved specialists ended in a blocked non-green state."
        )
    elif specialist_host_resolution_state == "partial_failed":
        workflow_truth_state = "partial"
        workflow_truth_notes.append(
            "Current-session specialist execution resolved the handoff, but one or more approved specialists failed."
        )
    elif specialist_host_resolution_state == "failed":
        workflow_truth_state = "partial"
        workflow_truth_notes.append(
            "Current-session specialist execution resolved the handoff, but approved specialist execution failed."
        )
    elif specialist_host_resolution_state == "blocked":
        workflow_truth_state = "partial"
        workflow_truth_notes.append(
            "Current-session specialist execution resolved the handoff, but approved specialist execution stayed blocked."
        )
    elif specialist_host_resolution_state == "degraded":
        workflow_truth_state = "degraded"
        workflow_truth_notes.append(
            "Current-session specialist execution resolved the handoff, but approved specialist execution stayed degraded."
        )
    elif specialist_host_resolution_state == "executed" and execution_status == "completed":
        workflow_truth_notes.append(
            "Approved execution was completed through direct current-session host continuation and recorded in specialist-execution.json."
        )
    elif execution_status != "completed":
        workflow_truth_state = "failing"
        workflow_truth_notes.append("Workflow did not reach a clean completed state.")
    if specialist_execution_notes:
        workflow_truth_notes.extend(specialist_execution_notes)

    specialist_disclosure_state = "not_applicable"
    specialist_disclosure_notes: list[str] = []
    disclosure_skill_ids = _normalize_skill_id_list(disclosure_routed_skills)
    disclosure_missing_entrypoint_skill_ids = _normalize_skill_id_list(
        [
            record
            for record in disclosure_routed_skills
            if not bool(record.get("entrypoint_requirement_satisfied", bool(record.get("native_skill_entrypoint"))))
        ]
    )
    approved_dispatch_skill_id_set = set(approved_dispatch_skill_ids)
    disclosure_skill_id_set = set(disclosure_skill_ids)
    specialist_degraded_skill_ids = _normalize_skill_id_list(
        specialist_accounting.get("degraded_skill_ids") or specialist_dispatch.get("degraded_skill_ids")
    )
    specialist_blocked_skill_ids = _normalize_skill_id_list(
        specialist_accounting.get("blocked_skill_ids") or specialist_dispatch.get("blocked_skill_ids")
    )
    specialist_activity_skill_ids = _normalize_skill_id_list(
        [
            *approved_dispatch_skill_ids,
            *disclosure_skill_ids,
            *specialist_degraded_skill_ids,
            *specialist_blocked_skill_ids,
        ]
    )
    specialist_disclosure_scope = str(specialist_user_disclosure.get("scope") or "").strip()
    specialist_disclosure_timing = str(specialist_user_disclosure.get("timing") or "").strip()
    specialist_disclosure_path_source = str(specialist_user_disclosure.get("path_source") or "").strip()

    if specialist_activity_skill_ids:
        if approved_dispatch_skill_ids and not specialist_user_disclosure:
            specialist_disclosure_state = "failing"
            specialist_disclosure_notes.append(
                "Approved specialist dispatch was present but no specialist user disclosure was recorded."
            )
        elif not approved_dispatch_skill_ids and disclosure_skill_ids:
            specialist_disclosure_state = "failing"
            specialist_disclosure_notes.append(
                "Specialist user disclosure was recorded without any effective approved dispatch."
            )
        elif approved_dispatch_skill_ids:
            if specialist_disclosure_scope != "approved_dispatch_only":
                specialist_disclosure_state = "failing"
                specialist_disclosure_notes.append(
                    "Specialist user disclosure scope did not stay aligned with approved_dispatch_only."
                )
            if specialist_disclosure_timing != "before_execution":
                specialist_disclosure_state = "failing"
                specialist_disclosure_notes.append(
                    "Specialist user disclosure timing did not stay aligned with before_execution."
                )
            if specialist_disclosure_path_source != "native_skill_entrypoint":
                specialist_disclosure_state = "failing"
                specialist_disclosure_notes.append(
                    "Specialist user disclosure path source did not stay aligned with native_skill_entrypoint."
                )
            if disclosure_skill_id_set != approved_dispatch_skill_id_set:
                specialist_disclosure_state = "failing"
                specialist_disclosure_notes.append(
                    "Specialist user disclosure did not match effective approved dispatch."
                )
            if disclosure_missing_entrypoint_skill_ids:
                specialist_disclosure_state = "failing"
                specialist_disclosure_notes.append(
                    "Specialist user disclosure omitted required native entrypoint truth for one or more skills."
                )
            if specialist_disclosure_state != "failing":
                if effective_specialist_execution_status in {"explicitly_degraded", "blocked_before_execution"} or specialist_degraded_skill_ids:
                    specialist_disclosure_state = "degraded"
                    specialist_disclosure_notes.append(
                        "Specialist disclosure stayed aligned, but specialist execution remained explicitly degraded."
                    )
                else:
                    specialist_disclosure_state = "passing"
                    specialist_disclosure_notes.append(
                        "Specialist disclosure stayed aligned with effective approved dispatch."
                    )

    specialist_decision_state = "not_applicable"
    specialist_decision_notes: list[str] = []
    specialist_decision_evidence = _normalize_string_list(specialist_decision_payload.get("evidence_paths"))
    specialist_decision_source_path = str(specialist_decision_payload.get("source_path") or "").strip()
    if specialist_decision_source_path:
        specialist_decision_evidence = [specialist_decision_source_path, *specialist_decision_evidence]
    decision_state = str(specialist_decision_payload.get("decision_state") or "").strip()
    resolution_mode = str(specialist_decision_payload.get("resolution_mode") or "").strip()
    decision_approved_dispatch_skill_ids = _normalize_skill_id_list(
        specialist_decision_payload.get("approved_dispatch_skill_ids")
    )
    decision_approved_dispatch_skill_id_set = set(decision_approved_dispatch_skill_ids)
    repo_asset_fallback = specialist_decision_payload.get("repo_asset_fallback") or {}
    repo_asset_used = bool(repo_asset_fallback.get("used"))
    repo_asset_paths = _normalize_string_list(repo_asset_fallback.get("asset_paths"))
    repo_asset_reason = str(repo_asset_fallback.get("reason") or "").strip()
    repo_asset_legal_basis = str(repo_asset_fallback.get("legal_basis") or "").strip()
    repo_asset_traceability = _normalize_string_list(repo_asset_fallback.get("traceability_basis"))

    if approved_dispatch_skill_ids:
        if not specialist_decision_payload:
            specialist_decision_state = "failing"
            specialist_decision_notes.append(
                "Approved specialist dispatch was present but no specialist decision artifact was recorded."
            )
        elif decision_state != "approved_dispatch" or resolution_mode != "approved_dispatch":
            specialist_decision_state = "failing"
            specialist_decision_notes.append(
                "Specialist decision did not stay aligned with approved_dispatch."
            )
        elif (
            decision_approved_dispatch_skill_ids
            and decision_approved_dispatch_skill_id_set != approved_dispatch_skill_id_set
        ):
            specialist_decision_state = "failing"
            specialist_decision_notes.append(
                "Specialist decision approved dispatch skill ids did not match effective approved dispatch."
            )
        else:
            specialist_decision_state = "passing"
            specialist_decision_notes.append(
                "Specialist decision stayed aligned with approved dispatch."
            )
    else:
        if not specialist_decision_payload:
            specialist_decision_state = "manual_review_required"
            specialist_decision_notes.append(
                "No bounded specialist recommendation path was frozen but no explicit specialist resolution was recorded."
            )
        elif decision_state == "no_specialist_recommendations":
            if resolution_mode in {"", "pending_resolution"}:
                specialist_decision_state = "manual_review_required"
                specialist_decision_notes.append(
                    "No specialist recommendation was frozen and the no-match resolution remained pending."
                )
            elif resolution_mode == "no_matching_specialist":
                specialist_decision_state = "passing"
                specialist_decision_notes.append(
                    "No bounded specialist matched the task; host-led execution remained responsible for decomposition and delivery."
                )
            elif resolution_mode == "no_specialist_needed":
                if repo_asset_used or repo_asset_paths or repo_asset_reason or repo_asset_legal_basis or repo_asset_traceability:
                    specialist_decision_state = "failing"
                    specialist_decision_notes.append(
                        "Specialist decision claimed no_specialist_needed but also recorded repo-asset fallback details."
                    )
                else:
                    specialist_decision_state = "passing"
                    specialist_decision_notes.append(
                        "Specialist decision explicitly recorded that no bounded specialist help was needed."
                    )
            elif resolution_mode == "repo_asset_fallback":
                missing_fallback_fields: list[str] = []
                if not repo_asset_used:
                    missing_fallback_fields.append("used=true")
                if not repo_asset_paths:
                    missing_fallback_fields.append("asset_paths")
                if not repo_asset_reason:
                    missing_fallback_fields.append("reason")
                if not repo_asset_legal_basis:
                    missing_fallback_fields.append("legal_basis")
                if not repo_asset_traceability:
                    missing_fallback_fields.append("traceability_basis")
                if missing_fallback_fields:
                    specialist_decision_state = "failing"
                    specialist_decision_notes.append(
                        "Repo-asset fallback was declared but did not record all required fields: "
                        + ", ".join(missing_fallback_fields)
                        + "."
                    )
                else:
                    specialist_decision_state = "degraded"
                    specialist_decision_notes.append(
                        "Repo-asset fallback stayed explicit and traceable when no dedicated specialist was available."
                    )
            else:
                specialist_decision_state = "failing"
                specialist_decision_notes.append(
                    "Specialist decision recorded an unsupported no-match resolution mode."
                )
        elif decision_state == "local_suggestion_only":
            specialist_decision_state = "manual_review_required"
            specialist_decision_notes.append(
                "Specialist decision remained advisory-only and still requires explicit escalation before closure."
            )
        elif decision_state in {"blocked", "degraded"}:
            specialist_decision_state = "degraded"
            specialist_decision_notes.append(
                "Specialist decision stayed explicit, but the bounded specialist path remained non-green."
            )
        else:
            specialist_decision_state = "failing"
            specialist_decision_notes.append(
                "Specialist decision artifact did not record a supported decision state."
            )

    artifact_review_state = "passing"
    artifact_review_notes: list[str] = []
    artifact_review_evidence = _normalize_string_list(artifact_review_payload.get("evidence_paths"))
    artifact_review_source_path = str(artifact_review_payload.get("source_path") or "").strip()
    if artifact_review_source_path:
        artifact_review_evidence = [artifact_review_source_path, *artifact_review_evidence]
    covered_baseline_document_quality_dimensions = _normalize_string_list(
        artifact_review_payload.get("covered_baseline_document_quality_dimensions")
    )
    covered_baseline_ui_quality_dimensions = _normalize_string_list(
        artifact_review_payload.get("covered_baseline_ui_quality_dimensions")
    )
    covered_task_specific_acceptance_extensions = _normalize_string_list(
        artifact_review_payload.get("covered_task_specific_acceptance_extensions")
    )
    considered_research_augmentation_sources = _normalize_string_list(
        artifact_review_payload.get("considered_research_augmentation_sources")
    )
    missing_task_specific_acceptance_extensions = _missing_frozen_items(
        task_specific_acceptance_extensions,
        covered_task_specific_acceptance_extensions,
    )
    missing_baseline_document_quality_dimensions = _missing_frozen_items(
        baseline_document_quality_dimensions,
        covered_baseline_document_quality_dimensions,
    )
    missing_baseline_ui_quality_dimensions = _missing_frozen_items(
        baseline_ui_quality_dimensions,
        covered_baseline_ui_quality_dimensions,
    )
    missing_research_augmentation_sources = _missing_frozen_items(
        research_augmentation_sources,
        considered_research_augmentation_sources,
    )

    raw_artifact_review_state = str(
        artifact_review_payload.get("status") or artifact_review_payload.get("state") or ""
    ).strip()
    if artifact_review_requirements:
        if not artifact_review_payload:
            artifact_review_state = "manual_review_required"
            artifact_review_notes.append(
                "Requirement doc froze artifact review requirements but no artifact-review evidence was recorded."
            )
        else:
            artifact_review_state = _normalize_truth_state(raw_artifact_review_state)
            if artifact_review_state in {"", "not_run"}:
                artifact_review_state = "manual_review_required"
                artifact_review_notes.append(
                    "Artifact review was required, but the recorded artifact-review status did not close the review."
                )
            elif artifact_review_state == "passing" and not artifact_review_evidence:
                artifact_review_state = "manual_review_required"
                artifact_review_notes.append(
                    "Artifact review reported passing, but no artifact-review evidence paths were recorded."
                )
    elif artifact_review_payload:
        artifact_review_state = _normalize_truth_state(raw_artifact_review_state)
        if artifact_review_state in {"", "not_run"} and not artifact_review_evidence:
            artifact_review_state = "passing"
        elif artifact_review_state == "passing" and not artifact_review_evidence:
            artifact_review_state = "manual_review_required"
            artifact_review_notes.append(
                "Artifact review reported passing, but no artifact-review evidence paths were recorded."
            )
        elif not artifact_review_state:
            artifact_review_state = "manual_review_required"
            artifact_review_notes.append("Artifact review payload did not record a normalized status.")

    if artifact_review_state == "passing" and missing_task_specific_acceptance_extensions:
        artifact_review_state = "manual_review_required"
        artifact_review_notes.append(
            "Artifact review did not record coverage for all frozen task-specific acceptance extensions."
        )
    if artifact_review_state == "passing" and missing_baseline_document_quality_dimensions:
        artifact_review_state = "manual_review_required"
        artifact_review_notes.append(
            "Artifact review did not record coverage for all frozen baseline document quality dimensions."
        )
    if artifact_review_state == "passing" and missing_baseline_ui_quality_dimensions:
        artifact_review_state = "manual_review_required"
        artifact_review_notes.append(
            "Artifact review did not record coverage for all frozen baseline UI quality dimensions."
        )
    if artifact_review_state == "passing" and missing_research_augmentation_sources:
        artifact_review_state = "manual_review_required"
        artifact_review_notes.append(
            "Artifact review did not record consideration of all frozen research augmentation sources."
        )

    artifact_review_payload_notes = str(artifact_review_payload.get("notes") or "").strip()
    if artifact_review_payload_notes:
        artifact_review_notes.append(artifact_review_payload_notes)

    product_truth_state = "passing"
    product_truth_notes: list[str] = []
    if engineering_truth_state in {"failing", "degraded"}:
        product_truth_state = "failing"
        product_truth_notes.append("Engineering verification truth is not strong enough to support product acceptance.")
    elif engineering_truth_state == "partial":
        product_truth_state = "partial"
        product_truth_notes.append("Product acceptance cannot pass while engineering verification remains partial.")
    elif code_task_tdd_evidence_state in {"failing", "degraded", "not_run"}:
        product_truth_state = "failing"
        product_truth_notes.append("Code-task TDD evidence truth is not strong enough to support product acceptance.")
    elif code_task_tdd_evidence_state == "partial":
        product_truth_state = "partial"
        product_truth_notes.append("Product acceptance cannot pass while code-task TDD evidence remains partial.")
    elif code_task_tdd_evidence_state == "manual_review_required":
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Frozen code-task TDD evidence requirements remain pending.")
    elif artifact_review_state in {"failing", "degraded", "not_run"}:
        product_truth_state = "failing"
        product_truth_notes.append("Required artifact-review truth is not strong enough to support product acceptance.")
    elif artifact_review_state == "partial":
        product_truth_state = "partial"
        product_truth_notes.append("Product acceptance cannot pass while artifact review remains partial.")
    elif artifact_review_state == "manual_review_required":
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Frozen artifact review requirements remain pending.")
    elif not product_acceptance_criteria:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Requirement doc is missing frozen product acceptance criteria.")
    elif manual_section_missing:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Requirement doc did not declare whether manual spot checks are needed.")
    elif manual_spot_checks:
        product_truth_state = "manual_review_required"
        product_truth_notes.append("Frozen manual spot checks remain pending.")

    truth_layers = {
        "governance_truth": {
            "state": _normalize_truth_state(governance_truth_state),
            "evidence": [str(path) for path in required_artifacts if path.exists()],
            "notes": " ".join(governance_truth_notes).strip(),
        },
        "engineering_verification_truth": {
            "state": _normalize_truth_state(engineering_truth_state),
            "evidence": [str(execution_manifest_path)],
            "notes": " ".join(engineering_truth_notes).strip(),
        },
        "specialist_disclosure_truth": {
            "state": _normalize_truth_state(specialist_disclosure_state),
            "evidence": [
                str(path)
                for path in (runtime_input_packet_path, execute_receipt_path, execution_manifest_path)
                if path.exists()
            ],
            "notes": " ".join(specialist_disclosure_notes).strip(),
        },
        "specialist_decision_truth": {
            "state": _normalize_truth_state(specialist_decision_state),
            "evidence": specialist_decision_evidence,
            "notes": " ".join(specialist_decision_notes).strip(),
        },
        "code_task_tdd_evidence_truth": {
            "state": _normalize_truth_state(code_task_tdd_evidence_state),
            "evidence": code_task_tdd_evidence_evidence,
            "notes": " ".join(code_task_tdd_evidence_notes).strip(),
        },
        "workflow_completion_truth": {
            "state": _normalize_truth_state(workflow_truth_state),
            "evidence": workflow_truth_evidence,
            "notes": " ".join(workflow_truth_notes).strip(),
        },
        "artifact_review_truth": {
            "state": _normalize_truth_state(artifact_review_state),
            "evidence": artifact_review_evidence,
            "notes": " ".join(artifact_review_notes).strip(),
        },
        "product_acceptance_truth": {
            "state": _normalize_truth_state(product_truth_state),
            "evidence": [str(requirement_doc_path), *artifact_review_evidence],
            "notes": " ".join(product_truth_notes).strip(),
        },
    }

    failing_layers = [layer for layer, info in truth_layers.items() if info["state"] in {"failing", "partial", "not_run"}]
    degraded_layers = [layer for layer, info in truth_layers.items() if info["state"] == "degraded"]
    manual_layers = [layer for layer, info in truth_layers.items() if info["state"] == "manual_review_required"]
    incomplete_layers = [layer for layer, info in truth_layers.items() if not _truth_success(contract, info["state"])]

    gate_result = "PASS"
    if failing_layers:
        gate_result = "FAIL"
    elif manual_layers:
        gate_result = "MANUAL_REVIEW_REQUIRED"
    elif degraded_layers:
        gate_result = "PASS_DEGRADED"

    readiness_state = _derive_readiness_state(gate_result, manual_spot_checks)
    forbidden_hits: list[dict[str, str]] = []
    for rule in list(contract.get("forbidden_completion_collapses") or []):
        source = str(rule.get("source") or "")
        value = str(rule.get("value") or "")
        if source == "runtime_status" and execution_status == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})
        if source == "readiness_state" and readiness_state == value:
            forbidden_hits.append({"source": source, "value": value, "reason": str(rule.get("reason") or "")})

    completion_language_allowed = gate_result == "PASS" and not forbidden_hits and all(
        _truth_completion_allowed(contract, info["state"]) for info in truth_layers.values()
    )

    residual_risks: list[str] = []
    if failed_unit_count > 0:
        residual_risks.append(f"{failed_unit_count} execution unit(s) failed.")
    if timed_out_unit_count > 0:
        residual_risks.append(f"{timed_out_unit_count} execution unit(s) timed out.")
    if manual_spot_checks:
        residual_risks.append("Manual spot checks remain pending.")
    if manual_section_missing:
        residual_risks.append("Manual spot check policy was not frozen in the requirement doc.")
    if (code_task_tdd_evidence_requirements or code_task_tdd_exceptions) and code_task_tdd_evidence_state != "passing":
        residual_risks.append("Required code-task TDD evidence remains unresolved.")
    if artifact_review_requirements and artifact_review_state != "passing":
        residual_risks.append("Required artifact review remains unresolved.")
    if baseline_document_quality_dimensions and artifact_review_state != "passing":
        residual_risks.append("Frozen baseline document quality dimensions remain unresolved.")
    if baseline_ui_quality_dimensions and artifact_review_state != "passing":
        residual_risks.append("Frozen baseline UI quality dimensions remain unresolved.")
    if task_specific_acceptance_extensions and artifact_review_state != "passing":
        residual_risks.append("Frozen task-specific acceptance extensions remain unresolved.")
    if research_augmentation_sources and artifact_review_state != "passing":
        residual_risks.append("Frozen research augmentation sources remain unresolved.")
    if not product_acceptance_criteria:
        residual_risks.append("Product acceptance criteria were not frozen in the requirement doc.")
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        residual_risks.append("Cleanup degraded, so closure is not fully authoritative.")
    if execution_status == "completed_local_scope":
        residual_risks.append("This run is child-scoped and cannot justify root-level completion wording.")
    if specialist_disclosure_state == "failing":
        residual_risks.append("Specialist disclosure truth is internally inconsistent or missing.")
    if specialist_disclosure_state == "degraded":
        residual_risks.append("Specialist disclosure is traceable, but the specialist execution path remained degraded.")
    if specialist_decision_state == "manual_review_required":
        residual_risks.append("Specialist no-match resolution still requires explicit governance review.")
    if specialist_decision_state == "failing":
        residual_risks.append("Specialist decision truth is missing required fallback or dispatch detail.")
    if specialist_decision_state == "degraded":
        residual_risks.append("Specialist decision recorded a traceable but non-green specialist fallback path.")
    if specialist_host_continuation_pending:
        residual_risks.append("Approved execution is still waiting on direct current-session host continuation.")
    elif specialist_host_resolution_state == "invalid":
        residual_risks.append("Current-session specialist execution evidence was recorded, but the specialist-execution sidecar did not validate cleanly.")
    elif specialist_host_resolution_state == "degraded":
        residual_risks.append("Approved execution finished current-session continuation with degraded specialist outcomes.")
    elif specialist_host_resolution_state in {"failed", "partial_failed"}:
        residual_risks.append("Approved execution finished current-session continuation with failed specialist outcomes.")
    elif specialist_host_resolution_state in {"blocked", "partial_non_green"}:
        residual_risks.append("Approved execution finished current-session continuation with blocked specialist outcomes.")

    summary = {
        "gate_result": gate_result,
        "completion_language_allowed": completion_language_allowed,
        "runtime_status": execution_status,
        "readiness_state": readiness_state,
        "manual_review_layer_count": len(manual_layers),
        "failing_layer_count": len(failing_layers),
        "degraded_layer_count": len(degraded_layers),
        "forbidden_completion_hit_count": len(forbidden_hits),
        "incomplete_layers": incomplete_layers,
        "manual_spot_check_count": len(manual_spot_checks),
        "code_task_tdd_evidence_requirement_count": len(code_task_tdd_evidence_requirements),
        "artifact_review_requirement_count": len(artifact_review_requirements),
        "baseline_document_quality_dimension_count": len(baseline_document_quality_dimensions),
        "baseline_ui_quality_dimension_count": len(baseline_ui_quality_dimensions),
    }

    return {
        "evaluated_at": utc_now(),
        "contract_id": str(contract.get("contract_id") or ""),
        "contract_version": int(contract.get("version") or 0),
        "session_root": str(session_root),
        "artifacts": {
            "execute_receipt_path": str(execute_receipt_path),
            "cleanup_receipt_path": str(cleanup_receipt_path),
            "requirement_doc_path": str(requirement_doc_path),
            "execution_plan_path": str(execution_plan_path),
            "execution_manifest_path": str(execution_manifest_path),
            "runtime_input_packet_path": str(runtime_input_packet_path),
        },
        "summary": summary,
        "truth_results": {
            layer: {
                "state": info["state"],
                "success": _truth_success(contract, info["state"]),
                "completion_language_allowed": _truth_completion_allowed(contract, info["state"]),
                "evidence": info["evidence"],
                "notes": info["notes"],
            }
            for layer, info in truth_layers.items()
        },
        "artifact_review_coverage": {
            "covered_baseline_document_quality_dimensions": covered_baseline_document_quality_dimensions,
            "missing_baseline_document_quality_dimensions": missing_baseline_document_quality_dimensions,
            "covered_baseline_ui_quality_dimensions": covered_baseline_ui_quality_dimensions,
            "missing_baseline_ui_quality_dimensions": missing_baseline_ui_quality_dimensions,
            "covered_task_specific_acceptance_extensions": covered_task_specific_acceptance_extensions,
            "missing_task_specific_acceptance_extensions": missing_task_specific_acceptance_extensions,
            "considered_research_augmentation_sources": considered_research_augmentation_sources,
            "missing_research_augmentation_sources": missing_research_augmentation_sources,
        },
        "tdd_evidence_coverage": {
            "covered_code_task_tdd_evidence_requirements": covered_code_task_tdd_evidence_requirements,
            "missing_code_task_tdd_evidence_requirements": missing_code_task_tdd_evidence_requirements,
            "covered_code_task_tdd_exceptions": covered_code_task_tdd_exceptions,
            "missing_code_task_tdd_exceptions": missing_code_task_tdd_exceptions,
            "red_phase_evidence_paths": red_phase_evidence_paths,
            "green_phase_evidence_paths": green_phase_evidence_paths,
            "refactor_phase_evidence_paths": refactor_phase_evidence_paths,
        },
        "frozen_requirement_sections": {
            "product_acceptance_criteria": product_acceptance_criteria,
            "manual_spot_checks": manual_spot_checks,
            "completion_language_policy": completion_language_policy,
            "delivery_truth_contract": delivery_truth_contract,
            "artifact_review_requirements": artifact_review_requirements,
            "code_task_tdd_evidence_requirements": code_task_tdd_evidence_requirements,
            "code_task_tdd_exceptions": code_task_tdd_exceptions,
            "baseline_document_quality_dimensions": baseline_document_quality_dimensions,
            "baseline_ui_quality_dimensions": baseline_ui_quality_dimensions,
            "task_specific_acceptance_extensions": task_specific_acceptance_extensions,
            "research_augmentation_sources": research_augmentation_sources,
        },
        "execution_context": {
            "run_id": str(execute_receipt.get("run_id") or execution_manifest.get("run_id") or ""),
            "session_root": str(session_root),
            "governance_scope": str(execution_manifest.get("governance_scope") or ""),
            "completion_claim_allowed": bool(execute_receipt.get("completion_claim_allowed")),
            "cleanup_mode": str(cleanup_receipt.get("cleanup_mode") or ""),
            "execution_status": execution_status,
            "executed_unit_count": executed_unit_count,
            "failed_unit_count": failed_unit_count,
            "timed_out_unit_count": timed_out_unit_count,
            "execution_plan_contains_delivery_acceptance_plan": "## Delivery Acceptance Plan" in execution_plan_text,
            "tdd_evidence_source_path": code_task_tdd_evidence_source_path,
            "code_task_tdd_evidence_state": _normalize_truth_state(code_task_tdd_evidence_state),
            "artifact_review_source_path": artifact_review_source_path,
            "artifact_review_state": _normalize_truth_state(artifact_review_state),
            "specialist_decision_source_path": specialist_decision_source_path,
            "specialist_execution_source_path": specialist_execution_source_path,
            "specialist_execution_sidecar_path": str(session_root / "specialist-execution.json"),
            "approved_dispatch_skill_ids": approved_dispatch_skill_ids,
            "disclosed_specialist_skill_ids": disclosure_skill_ids,
            "direct_routed_specialist_unit_ids": direct_routed_unit_ids,
            "direct_routed_specialist_skill_ids": direct_routed_skill_ids,
            "direct_routed_specialist_units": direct_routed_specialist_units,
            "specialist_host_resolution_state": specialist_host_resolution_state,
            "specialist_host_executed_unit_count": specialist_host_executed_unit_count,
            "specialist_host_degraded_unit_count": specialist_host_degraded_unit_count,
            "specialist_host_blocked_unit_count": specialist_host_blocked_unit_count,
            "specialist_host_failed_unit_count": specialist_host_failed_unit_count,
            "specialist_host_resolved_units": specialist_host_resolved_units,
            "specialist_host_missing_unit_ids": missing_direct_routed_unit_ids,
            "runtime_specialist_execution_status": runtime_specialist_execution_status,
            "specialist_effective_execution_status": effective_specialist_execution_status,
            "specialist_host_continuation_pending": specialist_host_continuation_pending,
            "specialist_disclosure_state": _normalize_truth_state(specialist_disclosure_state),
            "specialist_execution_notes": specialist_execution_notes,
        },
        "forbidden_completion_hits": forbidden_hits,
        "manual_spot_checks": manual_spot_checks,
        "residual_risks": residual_risks,
    }
