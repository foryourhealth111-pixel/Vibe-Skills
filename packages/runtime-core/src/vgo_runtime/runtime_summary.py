from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

STAGE_ORDER = [
    "skeleton_check",
    "deep_interview",
    "requirement_doc",
    "xl_plan",
    "plan_execute",
    "phase_cleanup",
]


def build_runtime_summary(
    *,
    run_id: str,
    task: str,
    artifacts: dict[str, Any],
    module_assignments: dict[str, Any],
    base_fields: dict[str, Any] | None = None,
    mode: str | None = None,
    artifact_root: str | None = None,
    session_root: str | None = None,
    hierarchy_state: dict[str, Any] | None = None,
    stage_lineage: dict[str, Any] | None = None,
    storage_projection: Any = None,
    memory_activation_report: dict[str, Any] | None = None,
    delivery_acceptance_report: dict[str, Any] | None = None,
    host_stage_disclosure: dict[str, Any] | None = None,
    host_user_briefing: dict[str, Any] | None = None,
    bounded_return_control: dict[str, Any] | None = None,
    agent_execution_handoff: dict[str, Any] | None = None,
    module_execution: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be an object")
    for key, value in artifacts.items():
        if value is not None and not isinstance(value, str):
            raise ValueError(f"artifacts.{key} must be a string or null")
    if not isinstance(module_assignments, dict):
        raise ValueError("module_assignments must be an object")

    if base_fields is None and mode is None and artifact_root is None and session_root is None and hierarchy_state is None:
        summary = {}
    elif base_fields is None:
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("mode must be a non-empty string when base_fields is absent")
        if not isinstance(artifact_root, str) or not artifact_root.strip():
            raise ValueError("artifact_root must be a non-empty string when base_fields is absent")
        if not isinstance(session_root, str) or not session_root.strip():
            raise ValueError("session_root must be a non-empty string when base_fields is absent")
        if not isinstance(hierarchy_state, dict):
            raise ValueError("hierarchy_state must be an object when base_fields is absent")

        summary = {
            "governance_scope": str(hierarchy_state.get("governance_scope") or ""),
            "mode": mode,
            "generated_at": generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "artifact_root": artifact_root,
            "session_root": session_root,
            "session_root_relative": _relative_path(artifact_root, session_root),
            "hierarchy": _build_hierarchy_projection(hierarchy_state),
            "stage_order": list(STAGE_ORDER),
            "executed_stage_order": _executed_stage_order(stage_lineage),
            "terminal_stage": _terminal_stage(stage_lineage),
            "storage": storage_projection,
            "memory_activation": _memory_activation_projection(memory_activation_report),
            "delivery_acceptance": _delivery_acceptance_projection(delivery_acceptance_report),
            "host_stage_disclosure": host_stage_disclosure,
            "host_user_briefing": host_user_briefing,
            "bounded_return_control": bounded_return_control,
            "agent_execution_handoff": agent_execution_handoff,
            "artifacts_relative": _relative_artifacts(artifact_root, artifacts),
        }
    else:
        summary = dict(base_fields)

    summary["run_id"] = run_id
    summary["task"] = task
    summary["truth_owner"] = "python"
    summary["artifacts"] = artifacts
    summary["bound_skill_ids"] = _bound_skill_ids_from_module_assignments(module_assignments)
    if isinstance(module_execution, dict):
        summary["completed_module_work"] = _completed_module_work(module_execution)
    else:
        summary.pop("completed_module_work", None)
    return summary


def build_runtime_summary_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("summary build payload must be an object")

    run_id = payload.get("run_id")
    task = payload.get("task")
    artifacts = payload.get("artifacts")
    module_assignments = payload.get("module_assignments")
    base_fields = payload.get("base_fields")

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("summary build payload missing run_id")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("summary build payload missing task")
    if base_fields is not None and not isinstance(base_fields, dict):
        raise ValueError("base_fields must be an object when present")

    return build_runtime_summary(
        run_id=run_id,
        task=task,
        artifacts=artifacts,
        module_assignments=module_assignments,
        base_fields=base_fields,
        mode=payload.get("mode") if isinstance(payload.get("mode"), str) else None,
        artifact_root=payload.get("artifact_root") if isinstance(payload.get("artifact_root"), str) else None,
        session_root=payload.get("session_root") if isinstance(payload.get("session_root"), str) else None,
        hierarchy_state=payload.get("hierarchy_state") if isinstance(payload.get("hierarchy_state"), dict) else None,
        stage_lineage=payload.get("stage_lineage") if isinstance(payload.get("stage_lineage"), dict) else None,
        storage_projection=payload.get("storage_projection"),
        memory_activation_report=_optional_object_field(payload, "memory_activation_report"),
        delivery_acceptance_report=_optional_object_field(payload, "delivery_acceptance_report"),
        host_stage_disclosure=_optional_object_field(payload, "host_stage_disclosure"),
        host_user_briefing=_optional_object_field(payload, "host_user_briefing"),
        bounded_return_control=_optional_object_field(payload, "bounded_return_control"),
        agent_execution_handoff=_optional_object_field(payload, "agent_execution_handoff"),
        module_execution=_optional_object_field(payload, "module_execution"),
        generated_at=payload.get("generated_at") if isinstance(payload.get("generated_at"), str) else None,
    )


def refresh_runtime_summary_acceptance(
    summary: dict[str, Any],
    delivery_acceptance_report: dict[str, Any],
    *,
    cleanup_receipt_path: str,
    delivery_acceptance_report_path: str,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        raise ValueError("runtime summary must be an object")
    if not isinstance(delivery_acceptance_report, dict):
        raise ValueError("delivery_acceptance_report must be an object")

    refreshed = dict(summary)
    acceptance = _delivery_acceptance_projection(delivery_acceptance_report)
    report_summary = delivery_acceptance_report.get("summary")
    if acceptance is None or not isinstance(report_summary, dict):
        raise ValueError("delivery_acceptance_report.summary must be an object")

    runtime_status = report_summary.get("runtime_status")
    if not isinstance(runtime_status, str) or not runtime_status.strip():
        raise ValueError("delivery_acceptance_report.summary.runtime_status must be a non-empty string")
    completion_language_allowed = report_summary.get("completion_language_allowed")
    if not isinstance(completion_language_allowed, bool):
        raise ValueError(
            "delivery_acceptance_report.summary.completion_language_allowed must be a boolean"
        )
    if completion_language_allowed:
        cleanup_path = Path(cleanup_receipt_path)
        if not cleanup_path.exists():
            raise ValueError("cleanup receipt is required before completion can be reported")
        cleanup_receipt = json.loads(cleanup_path.read_text(encoding="utf-8-sig"))
        if not isinstance(cleanup_receipt, dict) or cleanup_receipt.get("cleanup_admitted") is not True:
            raise ValueError("cleanup receipt has not admitted cleanup")

    refreshed["delivery_acceptance"] = acceptance
    refreshed["status"] = runtime_status
    refreshed["completion_language_allowed"] = completion_language_allowed
    artifacts = dict(refreshed.get("artifacts") or {})
    artifacts["cleanup_receipt"] = cleanup_receipt_path
    artifacts["delivery_acceptance_report"] = delivery_acceptance_report_path
    refreshed["artifacts"] = artifacts

    artifact_root = refreshed.get("artifact_root")
    if isinstance(artifact_root, str) and artifact_root.strip():
        refreshed["artifacts_relative"] = _relative_artifacts(artifact_root, artifacts)
    return refreshed


def _bound_skill_ids_from_module_assignments(module_assignments: dict[str, Any]) -> list[str]:
    units = module_assignments.get("units")
    if not isinstance(units, list):
        return []

    bound_skill_ids: list[str] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        skill_id = str(unit.get("bound_skill") or "").strip()
        if skill_id:
            bound_skill_ids.append(skill_id)
    return bound_skill_ids


def _completed_module_work(module_execution: dict[str, Any]) -> list[dict[str, str]]:
    completed_work: list[dict[str, str]] = []
    for unit in module_execution.get("units") or []:
        if not isinstance(unit, dict) or str(unit.get("state") or "") != "completed":
            continue
        skill_id = str(unit.get("skill_id") or "").strip()
        if not skill_id:
            continue
        completed_work.append(
            {
                "skill_id": skill_id,
                "unit_id": str(unit.get("unit_id") or ""),
                "module_id": str(unit.get("module_id") or ""),
            }
        )
    return completed_work


def _build_hierarchy_projection(hierarchy_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "root_run_id": _optional_string(hierarchy_state.get("root_run_id")),
        "parent_run_id": _optional_string(hierarchy_state.get("parent_run_id")),
        "parent_unit_id": _optional_string(hierarchy_state.get("parent_unit_id")),
        "inherited_requirement_doc_path": _optional_string(hierarchy_state.get("inherited_requirement_doc_path")),
        "inherited_execution_plan_path": _optional_string(hierarchy_state.get("inherited_execution_plan_path")),
        "delegation_envelope_path": _optional_string(hierarchy_state.get("delegation_envelope_path")),
    }


def _executed_stage_order(stage_lineage: dict[str, Any] | None) -> list[str]:
    lineage_source = stage_lineage.get("lineage") if isinstance(stage_lineage, dict) and isinstance(stage_lineage.get("lineage"), dict) else stage_lineage
    if not isinstance(lineage_source, dict):
        return []
    stage_entries = lineage_source.get("stages")
    if not isinstance(stage_entries, list):
        stage_entries = lineage_source.get("entries")
    if not isinstance(stage_entries, list):
        stage_entries = []
    stage_names: list[str] = []
    for entry in stage_entries:
        if not isinstance(entry, dict):
            continue
        for key in ("stage_name", "stage"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                stage_names.append(value)
                break
    if stage_names:
        return stage_names
    for key in ("stage_name", "stage"):
        value = lineage_source.get(key)
        if isinstance(value, str) and value.strip():
            return [value]
    return []


def _terminal_stage(stage_lineage: dict[str, Any] | None) -> str | None:
    lineage_source = stage_lineage.get("lineage") if isinstance(stage_lineage, dict) and isinstance(stage_lineage.get("lineage"), dict) else stage_lineage
    if not isinstance(lineage_source, dict):
        return None
    for key in ("last_stage_name", "last_stage"):
        value = lineage_source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    executed = _executed_stage_order(lineage_source)
    return executed[-1] if executed else None


def _memory_activation_projection(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    policy = report.get("policy") if isinstance(report.get("policy"), dict) else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "policy_mode": str(policy.get("mode") or ""),
        "routing_contract": str(policy.get("routing_contract") or ""),
        "fallback_event_count": int(summary.get("fallback_event_count") or 0),
        "artifact_count": int(summary.get("artifact_count") or 0),
        "budget_guard_respected": bool(summary.get("budget_guard_respected") or False),
    }


def _delivery_acceptance_projection(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    projection = {
        "gate_result": str(summary.get("gate_result") or ""),
        "completion_language_allowed": bool(summary.get("completion_language_allowed") or False),
        "readiness_state": str(summary.get("readiness_state") or ""),
        "manual_review_layer_count": int(summary.get("manual_review_layer_count") or 0),
        "failing_layer_count": int(summary.get("failing_layer_count") or 0),
    }
    runtime_status = summary.get("runtime_status")
    if isinstance(runtime_status, str):
        projection["runtime_status"] = runtime_status
    return projection


def _relative_artifacts(artifact_root: str, artifacts: dict[str, Any]) -> dict[str, Any]:
    relative: dict[str, Any] = {}
    for key, value in artifacts.items():
        if value is None:
            relative[key] = None
            continue
        text = str(value).strip()
        if not text:
            relative[key] = None
            continue
        relative[key] = _relative_path(artifact_root, text)
    return relative


def _relative_path(base_path: str, target_path: str) -> str:
    return os.path.relpath(target_path, start=base_path)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_object_field(payload: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be an object when present")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Python-owned runtime summary projection.")
    parser.add_argument("--input-json-path", required=True)
    parser.add_argument("--output-json-path")
    args = parser.parse_args(argv)

    input_path = Path(args.input_json_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    summary = build_runtime_summary_from_payload(payload)
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"

    if args.output_json_path:
        Path(args.output_json_path).write_text(text, encoding="utf-8")

    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
