from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from vgo_contracts.tdd_evidence_contract import resolve_tdd_evidence_state


def _load_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return payload


def module_required_binding_notes(planned: list[Any], submitted: list[Any]) -> tuple[str, ...]:
    notes: list[str] = []
    planned_by_id = {str(row.get("module_id") or ""): row for row in planned if isinstance(row, dict)}
    for row in submitted:
        if not isinstance(row, dict):
            notes.append("module execution modules must be a JSON array of objects")
            continue
        module_id = str(row.get("module_id") or "")
        approved = planned_by_id.get(module_id)
        if (
            approved is None
            or not isinstance(approved.get("required"), bool)
            or not isinstance(row.get("required"), bool)
            or row["required"] != approved["required"]
        ):
            notes.append(f"module execution module {module_id} changed its required binding")
    return tuple(notes)


def validate_agent_module_execution(
    *,
    session_root: Path,
    source_run_id: str,
    handoff: dict[str, Any],
    submitted: dict[str, Any],
) -> None:
    result_contract = handoff.get("result_contract")
    if not isinstance(result_contract, dict):
        raise RuntimeError("Agent execution handoff is missing result_contract")
    required_top_level_fields = result_contract.get("required_top_level_fields")
    if not isinstance(required_top_level_fields, list) or any(
        not isinstance(field, str) or not field.strip() for field in required_top_level_fields
    ):
        raise RuntimeError("Agent execution handoff result_contract required_top_level_fields is invalid")
    for field in required_top_level_fields:
        if field not in submitted:
            raise RuntimeError(f"module execution is missing required field: {field}")
    if submitted.get("schema_version") != "module_execution_v1":
        raise RuntimeError("Agent module execution must use module_execution_v1")
    if str(handoff.get("source_run_id") or "") != source_run_id:
        raise RuntimeError("Agent execution handoff source_run_id does not match the source run")
    if str(submitted.get("source_run_id") or "") != source_run_id:
        raise RuntimeError("module execution source_run_id does not match the handoff run")

    tdd_contract = result_contract.get("tdd_evidence")
    if tdd_contract is not None:
        if not isinstance(tdd_contract, dict):
            raise RuntimeError("Agent execution handoff TDD evidence contract is invalid")
        tdd_evidence = submitted.get("tdd_evidence")
        if not isinstance(tdd_evidence, dict):
            raise RuntimeError("module execution TDD evidence must be a JSON object")
        required_tdd_fields = tdd_contract.get("required_result_fields")
        if not isinstance(required_tdd_fields, list) or any(
            not isinstance(field, str) or not field.strip() for field in required_tdd_fields
        ):
            raise RuntimeError("Agent execution handoff TDD evidence required fields are invalid")
        for field in required_tdd_fields:
            if field not in tdd_evidence:
                raise RuntimeError(f"module execution TDD evidence is missing required field: {field}")

        try:
            resolve_tdd_evidence_state(tdd_evidence)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        tdd_state = str(tdd_evidence.get("state") or "")
        allowed_tdd_states = tdd_contract.get("terminal_states")
        if not isinstance(allowed_tdd_states, list) or tdd_state not in allowed_tdd_states:
            raise RuntimeError("module execution TDD evidence state must be passing, failing, or blocked")

        list_fields = (
            "evidence_paths",
            "red_phase_evidence_paths",
            "green_phase_evidence_paths",
            "refactor_phase_evidence_paths",
            "covered_code_task_tdd_evidence_requirements",
            "covered_code_task_tdd_exceptions",
        )
        for field in list_fields:
            value = tdd_evidence.get(field)
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise RuntimeError(f"module execution TDD evidence {field} must be a JSON array of strings")
        if not isinstance(tdd_evidence.get("notes"), str):
            raise RuntimeError("module execution TDD evidence notes must be a string")

        if tdd_state == "passing":
            required_tdd_requirements = tdd_contract.get(
                "required_code_task_tdd_evidence_requirements"
            )
            required_tdd_exceptions = tdd_contract.get("required_code_task_tdd_exceptions")
            if tdd_evidence["covered_code_task_tdd_evidence_requirements"] != required_tdd_requirements:
                raise RuntimeError(
                    "passing module execution TDD evidence must cover the frozen TDD requirements"
                )
            if tdd_evidence["covered_code_task_tdd_exceptions"] != required_tdd_exceptions:
                raise RuntimeError(
                    "passing module execution TDD evidence must cover the frozen TDD exceptions"
                )
            if not tdd_evidence["evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires evidence paths")
            if required_tdd_requirements and not tdd_evidence["red_phase_evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires red-phase evidence paths")
            if required_tdd_requirements and not tdd_evidence["green_phase_evidence_paths"]:
                raise RuntimeError("passing module execution TDD evidence requires green-phase evidence paths")

    plan_path = session_root / "module-work-plan.json"
    plan = _load_json_dict(plan_path, label="module-work-plan")
    if str(submitted.get("module_work_plan_digest") or "") != hashlib.sha256(plan_path.read_bytes()).hexdigest():
        raise RuntimeError("module execution does not match the approved module work plan digest")

    raw_submitted_units = submitted.get("units")
    if not isinstance(raw_submitted_units, list) or any(
        not isinstance(unit, dict) for unit in raw_submitted_units
    ):
        raise RuntimeError("module execution units must be a JSON array of objects")
    planned_units = {
        str(unit.get("unit_id") or ""): unit
        for unit in plan.get("work_units") or []
        if isinstance(unit, dict) and str(unit.get("unit_id") or "")
    }
    submitted_units = {
        str(unit.get("unit_id") or ""): unit
        for unit in raw_submitted_units
        if isinstance(unit, dict) and str(unit.get("unit_id") or "")
    }
    if set(submitted_units) != set(planned_units) or len(raw_submitted_units) != len(planned_units):
        raise RuntimeError("module execution work units must exactly match the approved plan")
    for unit_id, planned_unit in planned_units.items():
        unit = submitted_units[unit_id]
        for field in (
            "unit_id",
            "module_id",
            "skill_id",
            "role",
            "state",
            "result_summary",
            "evidence_paths",
            "verification_results",
        ):
            if field not in unit:
                raise RuntimeError(f"module execution unit {unit_id} is missing required field: {field}")
        if str(unit.get("module_id") or "") != str(planned_unit.get("module_id") or ""):
            raise RuntimeError(f"module execution unit {unit_id} changed its module binding")
        if (str(unit.get("skill_id") or "") or None) != (str(planned_unit.get("skill_id") or "") or None):
            raise RuntimeError(f"module execution unit {unit_id} changed its Skill binding")
        if str(unit.get("role") or "") != str(planned_unit.get("role") or ""):
            raise RuntimeError(f"module execution unit {unit_id} changed its role binding")
        state = str(unit.get("state") or "")
        if state not in {"completed", "failed", "blocked"}:
            raise RuntimeError(f"module execution unit {unit_id} is not terminal")
        if state == "completed" and not str(unit.get("result_summary") or "").strip():
            raise RuntimeError(f"completed module execution unit {unit_id} requires a result summary")

    raw_submitted_modules = submitted.get("modules")
    if not isinstance(raw_submitted_modules, list) or any(
        not isinstance(module, dict) for module in raw_submitted_modules
    ):
        raise RuntimeError("module execution modules must be a JSON array of objects")
    planned_modules = {
        str(module.get("module_id") or ""): module
        for module in plan.get("modules") or []
        if isinstance(module, dict) and str(module.get("module_id") or "")
    }
    submitted_modules = {
        str(module.get("module_id") or ""): module
        for module in raw_submitted_modules
        if isinstance(module, dict) and str(module.get("module_id") or "")
    }
    if set(submitted_modules) != set(planned_modules) or len(raw_submitted_modules) != len(planned_modules):
        raise RuntimeError("module execution modules must exactly match the approved plan")
    required_notes = module_required_binding_notes(list(planned_modules.values()), raw_submitted_modules)
    if required_notes:
        raise RuntimeError(required_notes[0])
    for module_id, planned_module in planned_modules.items():
        module = submitted_modules[module_id]
        for field in (
            "module_id",
            "required",
            "execution_mode",
            "gap_reason",
            "state",
            "criterion_results",
        ):
            if field not in module:
                raise RuntimeError(f"module execution module {module_id} is missing required field: {field}")
        if str(module.get("execution_mode") or "") != str(planned_module.get("execution_mode") or ""):
            raise RuntimeError(f"module execution module {module_id} changed its execution_mode binding")
        if module.get("gap_reason") != planned_module.get("gap_reason"):
            raise RuntimeError(f"module execution module {module_id} changed its gap_reason binding")
        if str(module.get("state") or "") not in {
            "completed",
            "failed",
            "blocked",
        }:
            raise RuntimeError(f"module execution module {module_id} is not terminal")

        planned_criteria = [
            criterion
            for criterion in planned_module.get("acceptance_criteria") or []
            if isinstance(criterion, dict) and str(criterion.get("criterion_id") or "")
        ]
        criterion_results = module.get("criterion_results")
        if not isinstance(criterion_results, list) or any(
            not isinstance(result, dict) for result in criterion_results
        ):
            raise RuntimeError(
                f"module execution module {module_id} criterion_results must be a JSON array of objects"
            )
        planned_criterion_ids = [str(criterion["criterion_id"]) for criterion in planned_criteria]
        submitted_criterion_ids = [
            str(result.get("criterion_id") or "") for result in criterion_results
        ]
        if (
            set(submitted_criterion_ids) != set(planned_criterion_ids)
            or len(submitted_criterion_ids) != len(planned_criterion_ids)
        ):
            raise RuntimeError(
                f"module execution module {module_id} criterion results must exactly match the approved plan"
            )
        for result in criterion_results:
            criterion_id = str(result.get("criterion_id") or "")
            if "state" not in result:
                raise RuntimeError(
                    f"module execution criterion {module_id}:{criterion_id} is missing required field: state"
                )
            criterion_state = str(result.get("state") or "")
            if criterion_state not in {"passing", "failing", "blocked"}:
                raise RuntimeError(
                    f"module execution criterion {module_id}:{criterion_id} has unsupported state: {criterion_state}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a terminal module execution against its frozen handoff.")
    parser.add_argument("--session-root", type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--submitted-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        handoff = _load_json_dict(args.session_root / "agent-execution-handoff.json", label="Agent execution handoff")
        submitted = _load_json_dict(args.submitted_file, label="module execution")
        validate_agent_module_execution(session_root=args.session_root, source_run_id=args.source_run_id, handoff=handoff, submitted=submitted)
    except (RuntimeError, ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
