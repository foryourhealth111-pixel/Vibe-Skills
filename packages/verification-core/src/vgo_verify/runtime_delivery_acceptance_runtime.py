from __future__ import annotations

from pathlib import Path
from typing import Any

from .runtime_delivery_acceptance_support import (
    _derive_readiness_state,
    _extract_bullets,
    _manual_spot_checks_from_requirement,
    _missing_frozen_items,
    _normalize_truth_state,
    _normalize_string_list,
    _read_text_if_exists,
    _requirement_optional_bullets,
    _resolve_artifact_review_payload,
    _resolve_tdd_evidence_payload,
    _truth_completion_allowed,
    _truth_success,
    load_json,
    utc_now,
)


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
    tdd_evidence_payload = _resolve_tdd_evidence_payload(session_root, execute_receipt)

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
            if code_task_tdd_exceptions:
                if missing_code_task_tdd_exceptions:
                    code_task_tdd_evidence_state = "manual_review_required"
                    code_task_tdd_evidence_notes.append(
                        "Code-task TDD exception coverage did not close all frozen exceptions."
                    )
            else:
                if missing_code_task_tdd_evidence_requirements:
                    code_task_tdd_evidence_state = "manual_review_required"
                    code_task_tdd_evidence_notes.append(
                        "Code-task TDD evidence did not record coverage for all frozen TDD requirements."
                    )
                if not red_phase_evidence_paths:
                    code_task_tdd_evidence_state = "manual_review_required"
                    code_task_tdd_evidence_notes.append(
                        "Code-task TDD evidence did not record failing-first evidence paths."
                    )
                if not green_phase_evidence_paths:
                    code_task_tdd_evidence_state = "manual_review_required"
                    code_task_tdd_evidence_notes.append(
                        "Code-task TDD evidence did not record green-phase verification evidence paths."
                    )

    tdd_evidence_payload_notes = str(tdd_evidence_payload.get("notes") or "").strip()
    if tdd_evidence_payload_notes:
        code_task_tdd_evidence_notes.append(tdd_evidence_payload_notes)

    workflow_truth_state = "passing"
    workflow_truth_notes: list[str] = []
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        workflow_truth_state = "degraded"
        workflow_truth_notes.append("Cleanup degraded, so workflow closure is not fully authoritative.")
    elif execution_status == "completed_local_scope" or not bool(execute_receipt.get("completion_claim_allowed")):
        workflow_truth_state = "partial"
        workflow_truth_notes.append("This run closed only a bounded local scope, not the full root task.")
    elif execution_status == "completed_with_failures":
        workflow_truth_state = "partial"
        workflow_truth_notes.append("Workflow closed with failed units still present.")
    elif execution_status != "completed":
        workflow_truth_state = "failing"
        workflow_truth_notes.append("Workflow did not reach a clean completed state.")

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
        "code_task_tdd_evidence_truth": {
            "state": _normalize_truth_state(code_task_tdd_evidence_state),
            "evidence": code_task_tdd_evidence_evidence,
            "notes": " ".join(code_task_tdd_evidence_notes).strip(),
        },
        "workflow_completion_truth": {
            "state": _normalize_truth_state(workflow_truth_state),
            "evidence": [str(execute_receipt_path), str(cleanup_receipt_path)],
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

    failing_layers = [
        layer
        for layer, info in truth_layers.items()
        if info["state"] in {"failing", "degraded", "partial", "not_run"}
    ]
    manual_layers = [layer for layer, info in truth_layers.items() if info["state"] == "manual_review_required"]
    incomplete_layers = [layer for layer, info in truth_layers.items() if not _truth_success(contract, info["state"])]

    gate_result = "PASS"
    if failing_layers:
        gate_result = "FAIL"
    elif manual_layers:
        gate_result = "MANUAL_REVIEW_REQUIRED"

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
    if not product_acceptance_criteria:
        residual_risks.append("Product acceptance criteria were not frozen in the requirement doc.")
    if str(cleanup_receipt.get("cleanup_mode") or "") == "cleanup_degraded":
        residual_risks.append("Cleanup degraded, so closure is not fully authoritative.")
    if execution_status == "completed_local_scope":
        residual_risks.append("This run is child-scoped and cannot justify root-level completion wording.")

    summary = {
        "gate_result": gate_result,
        "completion_language_allowed": completion_language_allowed,
        "runtime_status": execution_status,
        "readiness_state": readiness_state,
        "manual_review_layer_count": len(manual_layers),
        "failing_layer_count": len(failing_layers),
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
        },
        "forbidden_completion_hits": forbidden_hits,
        "manual_spot_checks": manual_spot_checks,
        "residual_risks": residual_risks,
    }
