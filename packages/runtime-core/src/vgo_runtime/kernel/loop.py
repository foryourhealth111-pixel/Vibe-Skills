from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .executor import WorkUnitResult, execute_work_unit
from .finder import find_skill_candidates
from .host_skill_roots import resolve_host_skill_roots
from .planner import build_work_plan
from .run_state import load_run_state, write_run_state
from .skill_index import build_skill_catalog, build_skill_index_from_catalog, write_skill_catalog, write_skill_index
from .task_card import TaskCard, TaskRevision, build_task_card
from .verifier import verify_run
from .module_assignments import ModuleAssignments, build_module_assignments
from .work_plan import AcceptanceCriterion, SkillProvenance, WorkPlan, WorkUnit


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _load_required_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"missing run artifact: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"run artifact must be a JSON object: {path}")
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _resolve_host_root_paths(
    *,
    agent_root: Path,
    host_id: str | None,
    workspace_root: Path | None,
) -> tuple[Path, ...]:
    normalized_host_id = str(host_id or "").strip()
    if not normalized_host_id:
        return ()
    return tuple(
        root.path
        for root in resolve_host_skill_roots(
            repo_root=_repo_root(),
            host_id=normalized_host_id,
            agent_root=agent_root,
            workspace_root=workspace_root,
        )
    )


def _skill_provenance(candidate: object) -> SkillProvenance:
    return SkillProvenance(
        source_kind=str(getattr(candidate, "source_kind")),
        source_root=str(getattr(candidate, "source_root")),
        resolved_skill_file=str(getattr(candidate, "resolved_skill_file")),
        source_priority=int(getattr(candidate, "source_priority")),
        source_order=int(getattr(candidate, "source_order")),
        path_contract=str(getattr(candidate, "path_contract")),
        path_base=str(getattr(candidate, "path_base")),
    )


def _unbound_plan_for_agent(plan: WorkPlan) -> WorkPlan:
    return WorkPlan(
        task_id=plan.task_id,
        work_units=tuple(
            replace(
                unit,
                preferred_skill=None,
                binding_profile="agent_selection_required",
                binding_reason="Agent skill organization is required before this work unit can be bound.",
                fallback_skills=tuple(
                    dict.fromkeys(
                        [
                            *([unit.preferred_skill] if unit.preferred_skill else []),
                            *unit.fallback_skills,
                        ]
                    )
                ),
                selected_skill_provenance=None,
            )
            for unit in plan.work_units
        ),
        superseded_work_units=plan.superseded_work_units,
    )


def _apply_agent_skill_organization(
    plan: WorkPlan,
    candidates: tuple[object, ...],
    organization: dict[str, object],
) -> WorkPlan:
    if organization.get("schema_version") != "agent_skill_organization_v1":
        raise ValueError("agent_skill_organization.schema_version must be agent_skill_organization_v1")
    if organization.get("derived_by") != "agent":
        raise ValueError("agent_skill_organization.derived_by must be agent")

    raw_modules = organization.get("modules")
    raw_selected = organization.get("selected_skills")
    raw_uncovered = organization.get("uncovered_modules")
    if not isinstance(raw_modules, list) or not isinstance(raw_selected, list) or not isinstance(raw_uncovered, list):
        raise ValueError("agent_skill_organization modules, selected_skills, and uncovered_modules must be lists")

    modules: dict[str, dict[str, object]] = {}
    for row in raw_modules:
        if not isinstance(row, dict):
            raise ValueError("agent_skill_organization modules must contain objects")
        module_id = str(row.get("module_id") or "").strip()
        if not module_id or module_id in modules:
            raise ValueError("agent_skill_organization modules must use unique non-empty module_id values")
        raw_criteria = row.get("acceptance_criteria")
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise ValueError(f"agent_skill_organization module {module_id} must include acceptance_criteria")
        criterion_ids: set[str] = set()
        for criterion in raw_criteria:
            if not isinstance(criterion, dict):
                raise ValueError(
                    f"agent_skill_organization module {module_id} acceptance_criteria must contain objects"
                )
            criterion_id = str(criterion.get("criterion_id") or "").strip()
            description = str(criterion.get("description") or "").strip()
            verification_mode = str(criterion.get("verification_mode") or "").strip()
            if not criterion_id or not description:
                raise ValueError(
                    f"agent_skill_organization module {module_id} acceptance criteria require criterion_id and description"
                )
            if criterion_id in criterion_ids:
                raise ValueError(
                    f"agent_skill_organization module {module_id} has duplicate acceptance criterion {criterion_id}"
                )
            if verification_mode not in {"automated", "manual"}:
                raise ValueError(
                    f"agent_skill_organization module {module_id} acceptance criterion verification_mode must be automated or manual"
                )
            criterion_ids.add(criterion_id)
        modules[module_id] = row

    work_unit_ids = {unit.id for unit in plan.work_units}
    if set(modules) != work_unit_ids:
        raise ValueError("agent_skill_organization module ids must match the local kernel work units")

    candidate_by_id = {str(getattr(candidate, "skill_id")): candidate for candidate in candidates}
    selected_by_module: dict[str, dict[str, object]] = {}
    for row in raw_selected:
        if not isinstance(row, dict):
            raise ValueError("agent_skill_organization selected_skills must contain objects")
        skill_id = str(row.get("skill_id") or "").strip()
        module_ids = row.get("module_ids")
        if not skill_id or skill_id not in candidate_by_id:
            raise ValueError(f"agent_skill_organization selected unknown candidate skill: {skill_id}")
        if not isinstance(module_ids, list) or not module_ids:
            raise ValueError(f"agent_skill_organization selected skill {skill_id} must include module_ids")
        for raw_module_id in module_ids:
            module_id = str(raw_module_id).strip()
            module = modules.get(module_id)
            if module is None:
                raise ValueError(f"agent_skill_organization selected skill {skill_id} references unknown module {module_id}")
            declared_candidates = [str(value).strip() for value in module.get("candidate_skill_ids", [])]
            if skill_id not in declared_candidates:
                raise ValueError(f"agent_skill_organization selected skill {skill_id} is not a candidate for {module_id}")
            if module_id in selected_by_module:
                raise ValueError(f"agent_skill_organization module {module_id} has more than one selected skill")
            selected_by_module[module_id] = row

    uncovered_by_module: dict[str, dict[str, object]] = {}
    for row in raw_uncovered:
        if not isinstance(row, dict):
            raise ValueError("agent_skill_organization uncovered_modules must contain objects")
        module_id = str(row.get("module_id") or "").strip()
        if module_id not in modules or module_id in uncovered_by_module:
            raise ValueError(f"agent_skill_organization has invalid uncovered module {module_id}")
        uncovered_by_module[module_id] = row

    organized_units: list[WorkUnit] = []
    for unit in plan.work_units:
        selected = selected_by_module.get(unit.id)
        uncovered = uncovered_by_module.get(unit.id)
        execution_mode = str(modules[unit.id].get("execution_mode") or "").strip()
        acceptance_criteria = tuple(
            AcceptanceCriterion(
                criterion_id=str(criterion["criterion_id"]).strip(),
                description=str(criterion["description"]).strip(),
                verification_mode=str(criterion["verification_mode"]).strip(),
            )
            for criterion in modules[unit.id]["acceptance_criteria"]
        )
        if selected is not None and uncovered is not None:
            raise ValueError(f"agent_skill_organization module {unit.id} cannot be selected and uncovered")
        if execution_mode == "skill_assigned" and selected is None:
            raise ValueError(f"agent_skill_organization module {unit.id} declares skill_assigned without a selected skill")
        if execution_mode == "blocked_gap" and uncovered is None:
            raise ValueError(f"agent_skill_organization module {unit.id} declares blocked_gap without an uncovered module")
        if execution_mode == "agent_direct" and (selected is not None or uncovered is not None):
            raise ValueError(f"agent_skill_organization agent_direct module {unit.id} cannot be selected or uncovered")
        if execution_mode not in {"skill_assigned", "agent_direct", "blocked_gap"}:
            raise ValueError(f"agent_skill_organization module {unit.id} has invalid execution_mode")
        if execution_mode == "agent_direct":
            organized_units.append(
                replace(
                    unit,
                    preferred_skill=None,
                    binding_profile="agent_direct",
                    binding_reason="The current Agent directly owns this approved module.",
                    acceptance_criteria=acceptance_criteria,
                    selected_skill_provenance=None,
                )
            )
            continue
        if selected is None:
            organized_units.append(
                replace(
                    unit,
                    preferred_skill=None,
                    binding_profile="uncovered_by_agent",
                    binding_reason=str(uncovered.get("reason") or "The Agent left this module uncovered."),
                    acceptance_criteria=acceptance_criteria,
                    selected_skill_provenance=None,
                )
            )
            continue

        skill_id = str(selected["skill_id"])
        module_candidates = tuple(
            value
            for value in (str(item).strip() for item in modules[unit.id].get("candidate_skill_ids", []))
            if value and value != skill_id
        )
        organized_units.append(
            replace(
                unit,
                preferred_skill=skill_id,
                binding_profile="agent_selected",
                binding_reason=str(selected.get("reason") or "The Agent selected this skill."),
                fallback_skills=module_candidates,
                acceptance_criteria=acceptance_criteria,
                selected_skill_provenance=_skill_provenance(candidate_by_id[skill_id]),
            )
        )

    return WorkPlan(
        task_id=plan.task_id,
        work_units=tuple(organized_units),
        superseded_work_units=plan.superseded_work_units,
    )


def _bound_module_assignments(plan: WorkPlan) -> ModuleAssignments:
    binding = build_module_assignments(plan)
    return ModuleAssignments(
        task_id=binding.task_id,
        units=tuple(unit for unit in binding.units if unit.bound_skill),
    )


def _coerce_task_card(payload: dict[str, object]) -> TaskCard:
    return TaskCard(
        id=str(payload["id"]),
        goal=str(payload["goal"]),
        deliverables=tuple(str(value) for value in payload.get("deliverables", [])),
        constraints=tuple(str(value) for value in payload.get("constraints", [])),
        known_context=tuple(str(value) for value in payload.get("known_context", [])),
        unknowns=tuple(str(value) for value in payload.get("unknowns", [])),
        completion_criteria=tuple(str(value) for value in payload.get("completion_criteria", [])),
        mode=str(payload.get("mode") or "general"),
        initial_goal=str(payload.get("initial_goal") or payload["goal"]),
        accepted_revisions=tuple(
            TaskRevision(
                sequence=int(item.get("sequence", index)),
                prompt=str(item.get("prompt") or ""),
                revision_mode=str(item.get("revision_mode") or "extend"),
                added_deliverables=tuple(str(value) for value in item.get("added_deliverables", [])),
                removed_deliverables=tuple(str(value) for value in item.get("removed_deliverables", [])),
                added_constraints=tuple(str(value) for value in item.get("added_constraints", [])),
                removed_constraints=tuple(str(value) for value in item.get("removed_constraints", [])),
                added_completion_criteria=tuple(str(value) for value in item.get("added_completion_criteria", [])),
                removed_completion_criteria=tuple(str(value) for value in item.get("removed_completion_criteria", [])),
            )
            for index, item in enumerate(payload.get("accepted_revisions", []), start=1)
            if isinstance(item, dict)
        ),
    )


def _coerce_work_result(payload: dict[str, object]) -> WorkUnitResult:
    return WorkUnitResult(
        work_unit_id=str(payload["work_unit_id"]),
        status=str(payload["status"]),
        lifecycle_state=str(payload.get("lifecycle_state") or "executed"),
        used_skill=(str(payload["used_skill"]) if payload.get("used_skill") is not None else None),
        artifacts=tuple(str(value) for value in payload.get("artifacts", [])),
        artifact_paths=tuple(str(value) for value in payload.get("artifact_paths", [])),
        proof_artifact_paths=tuple(str(value) for value in payload.get("proof_artifact_paths", [])),
        checked_targets=tuple(str(value) for value in payload.get("checked_targets", [])),
        notes=tuple(str(value) for value in payload.get("notes", [])),
        proof=tuple(str(value) for value in payload.get("proof", [])),
        execution_receipt_path=(
            str(payload["execution_receipt_path"])
            if payload.get("execution_receipt_path") is not None
            else None
        ),
        reused_from_work_unit_id=(
            str(payload["reused_from_work_unit_id"])
            if payload.get("reused_from_work_unit_id") is not None
            else None
        ),
        failure_reason=(str(payload["failure_reason"]) if payload.get("failure_reason") is not None else None),
    )


def _coerce_skill_provenance(payload: object) -> SkillProvenance | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError("selected_skill_provenance must be an object when present")
    return SkillProvenance(
        source_kind=str(payload["source_kind"]),
        source_root=str(payload["source_root"]),
        resolved_skill_file=str(payload["resolved_skill_file"]),
        source_priority=int(payload["source_priority"]),
        source_order=int(payload["source_order"]),
        path_contract=str(payload["path_contract"]),
        path_base=str(payload["path_base"]),
    )


def _coerce_work_unit(payload: dict[str, object]) -> WorkUnit:
    return WorkUnit(
        id=str(payload["id"]),
        goal=str(payload["goal"]),
        depends_on=tuple(str(value) for value in payload.get("depends_on", [])),
        preferred_skill=(str(payload["preferred_skill"]) if payload.get("preferred_skill") is not None else None),
        binding_profile=str(payload.get("binding_profile") or ""),
        binding_reason=(str(payload["binding_reason"]) if payload.get("binding_reason") is not None else None),
        fallback_skills=tuple(str(value) for value in payload.get("fallback_skills", [])),
        expected_artifacts=tuple(str(value) for value in payload.get("expected_artifacts", [])),
        verification=tuple(str(value) for value in payload.get("verification", [])),
        acceptance_criteria=tuple(
            AcceptanceCriterion(
                criterion_id=str(item["criterion_id"]),
                description=str(item["description"]),
                verification_mode=str(item["verification_mode"]),
            )
            for item in payload.get("acceptance_criteria", [])
            if isinstance(item, dict)
        ),
        selected_skill_provenance=_coerce_skill_provenance(payload.get("selected_skill_provenance")),
        status=str(payload.get("status") or "pending"),
        lifecycle_state=str(payload.get("lifecycle_state") or "active"),
        reused_from_work_unit_id=(
            str(payload["reused_from_work_unit_id"])
            if payload.get("reused_from_work_unit_id") is not None
            else None
        ),
    )


def _coerce_work_plan(payload: dict[str, object]) -> WorkPlan:
    return WorkPlan(
        task_id=str(payload["task_id"]),
        work_units=tuple(
            _coerce_work_unit(item)
            for item in payload.get("work_units", [])
            if isinstance(item, dict)
        ),
        superseded_work_units=tuple(
            _coerce_work_unit(item)
            for item in payload.get("superseded_work_units", [])
            if isinstance(item, dict)
        ),
    )


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _can_reuse_previous_work(*, previous_work_unit: WorkUnit | None, current_work_unit: WorkUnit) -> bool:
    if previous_work_unit is None:
        return False
    return (
        previous_work_unit.preferred_skill == current_work_unit.preferred_skill
        and previous_work_unit.selected_skill_provenance == current_work_unit.selected_skill_provenance
        and previous_work_unit.acceptance_criteria == current_work_unit.acceptance_criteria
    )


def _inspect_host_context(
    *,
    agent_root: Path,
    skills_catalog: dict[str, object],
    skills_catalog_path: Path,
    host_id: str | None,
    workspace_root: Path | None,
) -> dict[str, object] | None:
    normalized_host_id = str(host_id or "").strip()
    recorded_host_roots = skills_catalog.get("host_roots", [])
    if not isinstance(recorded_host_roots, list) or any(
        not isinstance(value, str) or not value.strip() for value in recorded_host_roots
    ):
        raise ValueError(f"skills catalog host_roots must be a list of non-empty strings: {skills_catalog_path}")
    if not normalized_host_id:
        return None

    resolved_workspace_root = workspace_root.resolve() if workspace_root is not None else None
    resolved_host_roots = [
        str(path.resolve())
        for path in _resolve_host_root_paths(
            agent_root=agent_root,
            host_id=normalized_host_id,
            workspace_root=resolved_workspace_root,
        )
    ]
    if recorded_host_roots != resolved_host_roots:
        raise ValueError(
            "run skills catalog host roots do not match requested host context: "
            f"recorded={recorded_host_roots!r} requested={resolved_host_roots!r}"
        )
    return {
        "host_id": normalized_host_id,
        "workspace_root": str(resolved_workspace_root) if resolved_workspace_root is not None else None,
        "resolved_host_roots": resolved_host_roots,
        "matches_run_catalog": True,
    }


def _dedupe(values: tuple[str, ...], additions: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in (*values, *additions):
        normalized = str(value).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return tuple(ordered)


def _ordered_difference(values: tuple[str, ...], baseline: tuple[str, ...]) -> tuple[str, ...]:
    baseline_keys = {value.casefold() for value in baseline}
    return tuple(value for value in values if value.casefold() not in baseline_keys)


def _merge_or_replace(
    existing: tuple[str, ...],
    followup: tuple[str, ...],
    *,
    replace: bool,
) -> tuple[str, ...]:
    return followup if replace else _dedupe(existing, followup)


def _build_task_revision(
    *,
    previous: TaskCard,
    current: TaskCard,
    prompt: str,
    revision_mode: str,
) -> TaskRevision | None:
    added_deliverables = _ordered_difference(current.deliverables, previous.deliverables)
    removed_deliverables = _ordered_difference(previous.deliverables, current.deliverables)
    added_constraints = _ordered_difference(current.constraints, previous.constraints)
    removed_constraints = _ordered_difference(previous.constraints, current.constraints)
    added_completion_criteria = _ordered_difference(current.completion_criteria, previous.completion_criteria)
    removed_completion_criteria = _ordered_difference(previous.completion_criteria, current.completion_criteria)
    if not any(
        (
            added_deliverables,
            removed_deliverables,
            added_constraints,
            removed_constraints,
            added_completion_criteria,
            removed_completion_criteria,
        )
    ):
        return None
    return TaskRevision(
        sequence=len(previous.accepted_revisions) + 1,
        prompt=prompt,
        revision_mode=revision_mode,
        added_deliverables=added_deliverables,
        removed_deliverables=removed_deliverables,
        added_constraints=added_constraints,
        removed_constraints=removed_constraints,
        added_completion_criteria=added_completion_criteria,
        removed_completion_criteria=removed_completion_criteria,
    )


def _merge_task_cards(existing: TaskCard, followup: TaskCard, *, revision_prompt: str, revision_context: dict[str, object] | None) -> TaskCard:
    context_payload = revision_context or {}
    revision_mode = "replace" if str(context_payload.get("revision_mode") or "").strip().casefold() == "replace" else "extend"
    merged = TaskCard(
        id=existing.id,
        goal=existing.goal,
        deliverables=_merge_or_replace(
            existing.deliverables,
            followup.deliverables,
            replace=revision_mode == "replace" and "deliverables" in context_payload,
        ),
        constraints=_merge_or_replace(
            existing.constraints,
            followup.constraints,
            replace=revision_mode == "replace" and "constraints" in context_payload,
        ),
        known_context=_merge_or_replace(
            existing.known_context,
            followup.known_context,
            replace=revision_mode == "replace" and "known_context" in context_payload,
        ),
        unknowns=_merge_or_replace(
            existing.unknowns,
            followup.unknowns,
            replace=revision_mode == "replace" and "unknowns" in context_payload,
        ),
        completion_criteria=_merge_or_replace(
            existing.completion_criteria,
            followup.completion_criteria,
            replace=revision_mode == "replace" and "completion_criteria" in context_payload,
        ),
        mode=existing.mode,
        initial_goal=existing.initial_goal,
        accepted_revisions=existing.accepted_revisions,
    )
    accepted_revision = _build_task_revision(
        previous=existing,
        current=merged,
        prompt=revision_prompt,
        revision_mode=revision_mode,
    )
    if accepted_revision is None:
        return merged
    return TaskCard(
        id=merged.id,
        goal=merged.goal,
        deliverables=merged.deliverables,
        constraints=merged.constraints,
        known_context=merged.known_context,
        unknowns=merged.unknowns,
        completion_criteria=merged.completion_criteria,
        mode=merged.mode,
        initial_goal=merged.initial_goal,
        accepted_revisions=(*existing.accepted_revisions, accepted_revision),
    )


def _build_work_dossier(
    *,
    run_id: str,
    task_card: dict[str, object],
    work_plan: dict[str, object],
    module_assignments: dict[str, object],
    work_results: dict[str, object],
    verification: dict[str, object],
    run_state: dict[str, object],
    artifact_paths: dict[str, str],
) -> dict[str, object]:
    work_units = work_plan.get("work_units", [])
    work_unit_rows = work_units if isinstance(work_units, list) else []
    superseded_work_units = work_plan.get("superseded_work_units", [])
    superseded_rows = superseded_work_units if isinstance(superseded_work_units, list) else []
    work_results_rows = work_results.get("work_results", [])
    result_rows = work_results_rows if isinstance(work_results_rows, list) else []
    bound_skill_ids = _unique_non_empty(
        [
            str(unit.get("bound_skill") or "")
            for unit in module_assignments.get("units", [])
            if isinstance(unit, dict)
        ]
    )
    delivered_artifacts = _unique_non_empty(
        [
            str(artifact)
            for row in result_rows
            if isinstance(row, dict)
            for artifact in row.get("artifacts", [])
        ]
    )
    delivered_artifact_paths = _unique_non_empty(
        [
            str(path)
            for row in result_rows
            if isinstance(row, dict)
            for path in row.get("artifact_paths", [])
        ]
    )
    verification_evidence = verification.get("evidence", [])
    evidence_rows = (
        [str(item) for item in verification_evidence]
        if isinstance(verification_evidence, (list, tuple))
        else []
    )
    completed_work_unit_count = sum(
        1
        for row in result_rows
        if isinstance(row, dict) and str(row.get("status") or "") == "completed"
    )
    reused_rows = [
        row
        for row in result_rows
        if isinstance(row, dict) and str(row.get("lifecycle_state") or "") == "reused"
    ]
    failed_work_unit_count = sum(
        1
        for row in result_rows
        if isinstance(row, dict) and str(row.get("status") or "") != "completed"
    )
    accepted_revisions = task_card.get("accepted_revisions", [])
    revision_rows = (
        [item for item in accepted_revisions if isinstance(item, dict)]
        if isinstance(accepted_revisions, (list, tuple))
        else []
    )
    revision_lineage = {
        "initial_goal": str(task_card.get("initial_goal") or task_card.get("goal") or ""),
        "continuation_mode": str(run_state.get("continuation_mode") or "fresh"),
        "accepted_revision_count": len(revision_rows),
        "accepted_revisions": revision_rows,
        "reused_work_units": [
            {
                "work_unit_id": str(row.get("work_unit_id") or ""),
                "reused_from_work_unit_id": str(row.get("reused_from_work_unit_id") or ""),
                "artifacts": [str(value) for value in row.get("artifacts", [])],
            }
            for row in reused_rows
        ],
        "superseded_work_units": [
            {
                "work_unit_id": str(row.get("id") or ""),
                "goal": str(row.get("goal") or ""),
                "artifacts": [str(value) for value in row.get("expected_artifacts", [])],
            }
            for row in superseded_rows
            if isinstance(row, dict)
        ],
    }
    return {
        "schema_version": "work_dossier_v1",
        "run_id": run_id,
        "task_id": str(task_card.get("id") or ""),
        "state": str(run_state.get("state") or ""),
        "proof_ready": str(verification.get("result") or "") == "done",
        "reading_order": [
            "task_card",
            "work_plan",
            "module_assignments",
            "work_results",
            "verification",
            "proof",
        ],
        "artifact_paths": artifact_paths,
        "task_card": task_card,
        "work_plan": work_plan,
        "module_assignments": module_assignments,
        "work_results": work_results,
        "verification": verification,
        "closure": {
            "task": str(task_card.get("goal") or ""),
            "continuity": {
                "continuation_mode": str(run_state.get("continuation_mode") or "fresh"),
                "accepted_revision_count": len(revision_rows),
                "reused_work_unit_count": len(reused_rows),
                "superseded_work_unit_count": len(superseded_rows),
            },
            "work": {
                "work_unit_count": len(work_unit_rows),
                "completed_work_unit_count": completed_work_unit_count,
                "failed_work_unit_count": failed_work_unit_count,
                "work_unit_goals": [
                    str(work_unit.get("goal") or "")
                    for work_unit in work_unit_rows
                    if isinstance(work_unit, dict)
                ],
            },
            "skills": {
                "bound_skill_ids": bound_skill_ids,
            },
            "outputs": {
                "artifacts": delivered_artifacts,
                "artifact_paths": delivered_artifact_paths,
            },
            "proof": {
                "result": str(verification.get("result") or ""),
                "completion_criteria": list(task_card.get("completion_criteria", [])),
                "evidence_count": len(evidence_rows),
                "evidence": evidence_rows,
            },
        },
        "revision_lineage": revision_lineage,
    }


def _render_work_dossier_markdown(work_dossier: dict[str, object]) -> str:
    closure = work_dossier.get("closure")
    closure_payload = closure if isinstance(closure, dict) else {}
    task_card_payload = work_dossier.get("task_card")
    task_card = task_card_payload if isinstance(task_card_payload, dict) else {}
    work_plan_payload = work_dossier.get("work_plan")
    work_plan = work_plan_payload if isinstance(work_plan_payload, dict) else {}
    module_assignments_payload = work_dossier.get("module_assignments")
    module_assignments = module_assignments_payload if isinstance(module_assignments_payload, dict) else {}
    work_results_payload = work_dossier.get("work_results")
    work_results = work_results_payload if isinstance(work_results_payload, dict) else {}
    work_payload = closure_payload.get("work")
    work_section = work_payload if isinstance(work_payload, dict) else {}
    skills_payload = closure_payload.get("skills")
    skills_section = skills_payload if isinstance(skills_payload, dict) else {}
    outputs_payload = closure_payload.get("outputs")
    outputs_section = outputs_payload if isinstance(outputs_payload, dict) else {}
    proof_payload = closure_payload.get("proof")
    proof_section = proof_payload if isinstance(proof_payload, dict) else {}
    continuity_payload = closure_payload.get("continuity")
    continuity_section = continuity_payload if isinstance(continuity_payload, dict) else {}
    revision_payload = work_dossier.get("revision_lineage")
    revision_section = revision_payload if isinstance(revision_payload, dict) else {}
    artifact_payload = work_dossier.get("artifact_paths")
    artifact_paths = artifact_payload if isinstance(artifact_payload, dict) else {}
    reading_order_payload = work_dossier.get("reading_order")
    reading_order = (
        [str(item) for item in reading_order_payload]
        if isinstance(reading_order_payload, (list, tuple))
        else []
    )
    accepted_revisions = revision_section.get("accepted_revisions", [])
    if not isinstance(accepted_revisions, (list, tuple)):
        accepted_revisions = []
    reused_work_units = revision_section.get("reused_work_units", [])
    if not isinstance(reused_work_units, (list, tuple)):
        reused_work_units = []
    superseded_work_units = revision_section.get("superseded_work_units", [])
    if not isinstance(superseded_work_units, (list, tuple)):
        superseded_work_units = []

    lines = [
        "# Work Dossier",
        "",
        "## Conclusion",
        "",
        f"- state: {work_dossier.get('state', '')}",
        f"- proof ready: {work_dossier.get('proof_ready', False)}",
        f"- verification result: {proof_section.get('result', '')}",
        f"- continuation mode: {continuity_section.get('continuation_mode', 'fresh')}",
        "",
        "## Reading Path",
        "",
    ]
    for step in reading_order:
        label = step.replace("_", " ")
        artifact_path = str(artifact_paths.get(step) or "")
        if artifact_path:
            lines.append(f"- {label}: {artifact_path}")
        else:
            lines.append(f"- {label}")
    lines.extend(
        [
            "",
            "## Task Card",
            "",
            f"- task: {closure_payload.get('task', '')}",
            f"- mode: {task_card.get('mode', '')}",
            f"- completion criteria: {len(task_card.get('completion_criteria', []))}",
            "",
            "## Work Plan",
            "",
            f"- work units: {work_section.get('work_unit_count', 0)}",
        ]
    )
    for goal in work_section.get("work_unit_goals", []):
        lines.append(f"- {goal}")
    lines.extend(
        [
            "",
            "## Work Binding",
            "",
        ]
    )
    binding_units = module_assignments.get("units", [])
    if isinstance(binding_units, list) and binding_units:
        for unit in binding_units:
            if not isinstance(unit, dict):
                continue
            verification_targets = unit.get("verification", [])
            verification_text = (
                ", ".join(str(value) for value in verification_targets)
                if isinstance(verification_targets, (list, tuple))
                else ""
            )
            lines.append(
                f"- {unit.get('work_unit_id', '')}: {unit.get('bound_skill', '')} ({unit.get('binding_profile', '')})"
            )
            if verification_text:
                lines.append(f"  - verification targets: {verification_text}")
    else:
        lines.append("- no bound work units")
    lines.extend(
        [
            "",
            "## Work Results",
            "",
            f"- completed work units: {work_section.get('completed_work_unit_count', 0)}",
            f"- failed work units: {work_section.get('failed_work_unit_count', 0)}",
        ]
    )
    work_result_rows = work_results.get("work_results", [])
    if isinstance(work_result_rows, list):
        for row in work_result_rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('work_unit_id', '')}: {row.get('status', '')} via {row.get('used_skill', '')}"
            )
            artifacts = row.get("artifacts", [])
            if isinstance(artifacts, (list, tuple)) and artifacts:
                lines.append(f"  - artifacts: {', '.join(str(value) for value in artifacts)}")
    lines.extend(
        [
            "",
            "## Verification",
            "",
            f"- result: {proof_section.get('result', '')}",
            f"- completion criteria: {len(proof_section.get('completion_criteria', []))}",
            f"- evidence count: {proof_section.get('evidence_count', 0)}",
        ]
    )
    for evidence in proof_section.get("evidence", []):
        lines.append(f"- {evidence}")
    lines.extend(
        [
            "",
            "## Proof",
            "",
        ]
    )
    for artifact in outputs_section.get("artifacts", []):
        lines.append(f"- artifact: {artifact}")
    for artifact_path in outputs_section.get("artifact_paths", []):
        lines.append(f"- artifact path: {artifact_path}")
    lines.extend(
        [
            "",
            "## Task Evolution",
            "",
            f"- initial goal: {revision_section.get('initial_goal', closure_payload.get('task', ''))}",
            f"- accepted revisions: {continuity_section.get('accepted_revision_count', 0)}",
            f"- reused work units: {continuity_section.get('reused_work_unit_count', 0)}",
            f"- superseded work units: {continuity_section.get('superseded_work_unit_count', 0)}",
        ]
    )
    for revision in accepted_revisions:
        if not isinstance(revision, dict):
            continue
        lines.append(
            f"- revision {revision.get('sequence', '')} ({revision.get('revision_mode', 'extend')}): {revision.get('prompt', '')}"
        )
        added_deliverables = revision.get("added_deliverables", [])
        removed_deliverables = revision.get("removed_deliverables", [])
        if added_deliverables:
            lines.append(f"  - add deliverables: {', '.join(str(value) for value in added_deliverables)}")
        if removed_deliverables:
            lines.append(f"  - remove deliverables: {', '.join(str(value) for value in removed_deliverables)}")
    if reused_work_units:
        for row in reused_work_units:
            if isinstance(row, dict):
                lines.append(
                    f"- reused {row.get('work_unit_id', '')}: {', '.join(str(value) for value in row.get('artifacts', []))}"
                )
    if superseded_work_units:
        for row in superseded_work_units:
            if isinstance(row, dict):
                lines.append(
                    f"- superseded {row.get('work_unit_id', '')}: {', '.join(str(value) for value in row.get('artifacts', []))}"
                )
    return "\n".join(lines) + "\n"


def run_local_kernel(
    *,
    agent_root: Path,
    prompt: str,
    context: dict[str, object] | None = None,
    run_id: str | None = None,
    host_id: str | None = None,
    workspace_root: Path | None = None,
    agent_skill_organization: dict[str, object] | None = None,
    execute: bool = True,
) -> dict[str, object]:
    resolved_agent_root = agent_root.resolve()
    resolved_workspace_root = workspace_root.resolve() if workspace_root is not None else None
    resolved_run_id = str(run_id or "run-default").strip() or "run-default"
    vibe_root = resolved_agent_root / "vibe"
    run_root = vibe_root / "runs" / resolved_run_id
    task_card_path = run_root / "task-card.json"
    plan_path = run_root / "plan.json"
    work_results_path = run_root / "work-results.json"
    resume_mode = task_card_path.is_file()

    host_roots = _resolve_host_root_paths(
        agent_root=resolved_agent_root,
        host_id=host_id,
        workspace_root=resolved_workspace_root,
    )
    skills_catalog_payload = build_skill_catalog(
        agent_root=resolved_agent_root,
        host_roots=host_roots,
    )
    write_skill_catalog(resolved_agent_root, skills_catalog_payload)
    skills_catalog_path = _write_json(run_root / "skills-catalog.json", skills_catalog_payload)
    index_payload = build_skill_index_from_catalog(skills_catalog_payload)
    write_skill_index(resolved_agent_root, index_payload)

    previous_revision_count = 0
    previous_plan = WorkPlan(task_id="", work_units=(), superseded_work_units=())
    if resume_mode:
        existing_task_card = _coerce_task_card(_load_required_json(task_card_path))
        previous_revision_count = len(existing_task_card.accepted_revisions)
        followup_task_card = build_task_card(prompt=prompt, context=context)
        task_card = _merge_task_cards(
            existing_task_card,
            followup_task_card,
            revision_prompt=prompt,
            revision_context=context,
        )
        if plan_path.is_file():
            previous_plan = _coerce_work_plan(_load_required_json(plan_path))
    else:
        task_card = build_task_card(prompt=prompt, context=context)
    continuation_mode = "fresh"
    if resume_mode:
        continuation_mode = "revised" if len(task_card.accepted_revisions) > previous_revision_count else "resumed"
    task_card_payload = task_card.model_dump()
    task_card_path = _write_json(task_card_path, task_card_payload)
    write_run_state(
        run_root / "run-state.json",
        run_id=resolved_run_id,
        task_id=task_card.id,
        state="find_skills",
        continuation_mode=continuation_mode,
        accepted_revision_count=len(task_card.accepted_revisions),
    )

    candidates = find_skill_candidates(task_card, index_payload)
    plan = build_work_plan(task_card, candidates)
    if agent_skill_organization is not None:
        plan = _apply_agent_skill_organization(plan, candidates, agent_skill_organization)
    else:
        plan = _unbound_plan_for_agent(plan)

    previous_results_by_artifacts: dict[tuple[str, ...], WorkUnitResult] = {}
    previous_work_units_by_artifacts: dict[tuple[str, ...], WorkUnit] = {
        work_unit.expected_artifacts: work_unit for work_unit in previous_plan.work_units
    }
    if resume_mode and work_results_path.is_file():
        previous_payload = _load_required_json(work_results_path)
        for item in previous_payload.get("work_results", []):
            if not isinstance(item, dict):
                continue
            result = _coerce_work_result(item)
            if result.status == "completed":
                previous_results_by_artifacts[result.artifacts] = result

    reused_work_unit_ids: list[str] = []
    planned_work_units: list[WorkUnit] = []
    for work_unit in plan.work_units:
        reused_result = previous_results_by_artifacts.get(work_unit.expected_artifacts)
        previous_work_unit = previous_work_units_by_artifacts.get(work_unit.expected_artifacts)
        if reused_result is None or not _can_reuse_previous_work(
            previous_work_unit=previous_work_unit,
            current_work_unit=work_unit,
        ):
            planned_work_units.append(work_unit)
            continue
        planned_work_units.append(
            WorkUnit(
                id=work_unit.id,
                goal=work_unit.goal,
                depends_on=work_unit.depends_on,
                preferred_skill=work_unit.preferred_skill,
                binding_profile=work_unit.binding_profile,
                binding_reason=work_unit.binding_reason,
                fallback_skills=work_unit.fallback_skills,
                expected_artifacts=work_unit.expected_artifacts,
                verification=work_unit.verification,
                acceptance_criteria=work_unit.acceptance_criteria,
                selected_skill_provenance=work_unit.selected_skill_provenance,
                status=work_unit.status,
                lifecycle_state="reused",
                reused_from_work_unit_id=reused_result.work_unit_id,
            )
        )
        reused_work_unit_ids.append(work_unit.id)
    current_artifacts = {work_unit.expected_artifacts for work_unit in plan.work_units}
    superseded_work_units = tuple(
        WorkUnit(
            id=work_unit.id,
            goal=work_unit.goal,
            depends_on=work_unit.depends_on,
            preferred_skill=work_unit.preferred_skill,
            binding_profile=work_unit.binding_profile,
            binding_reason=work_unit.binding_reason,
            fallback_skills=work_unit.fallback_skills,
            expected_artifacts=work_unit.expected_artifacts,
            verification=work_unit.verification,
            acceptance_criteria=work_unit.acceptance_criteria,
            selected_skill_provenance=work_unit.selected_skill_provenance,
            status=work_unit.status,
            lifecycle_state="superseded",
            reused_from_work_unit_id=work_unit.reused_from_work_unit_id,
        )
        for work_unit in previous_plan.work_units
        if work_unit.expected_artifacts not in current_artifacts
    )
    plan = WorkPlan(
        task_id=plan.task_id,
        work_units=tuple(planned_work_units),
        superseded_work_units=superseded_work_units,
    )
    module_assignments = _bound_module_assignments(plan)
    work_plan_payload = plan.model_dump()
    plan_path = _write_json(run_root / "plan.json", work_plan_payload)
    module_assignments_payload = module_assignments.model_dump()
    module_assignments_payload = {
        "schema_version": "runtime_module_assignments_v1",
        "source": "agent_skill_organization" if agent_skill_organization is not None else None,
        "task_id": module_assignments_payload["task_id"],
        "unit_count": len(module_assignments_payload["units"]),
        "status": (
            "projected_from_agent_skill_organization"
            if agent_skill_organization is not None
            else "no_bound_skills"
        ),
        "units": module_assignments_payload["units"],
    }
    module_assignments_path = _write_json(run_root / "module-assignments.json", module_assignments_payload)

    work_results: list[WorkUnitResult] = []
    completed_work_units: list[str] = []
    failed_work_units: list[str] = []
    should_execute = bool(execute and agent_skill_organization is not None)
    for work_unit in (plan.work_units if should_execute else ()):
        reused_result = previous_results_by_artifacts.get(work_unit.expected_artifacts)
        previous_work_unit = previous_work_units_by_artifacts.get(work_unit.expected_artifacts)
        if reused_result is not None and _can_reuse_previous_work(
            previous_work_unit=previous_work_unit,
            current_work_unit=work_unit,
        ):
            work_results.append(
                WorkUnitResult(
                    work_unit_id=work_unit.id,
                    status=reused_result.status,
                    lifecycle_state="reused",
                    used_skill=reused_result.used_skill,
                    artifacts=reused_result.artifacts,
                    artifact_paths=reused_result.artifact_paths,
                    proof_artifact_paths=reused_result.proof_artifact_paths,
                    checked_targets=reused_result.checked_targets,
                    notes=(*reused_result.notes, "reused from previous completed work"),
                    proof=(*reused_result.proof, f"{work_unit.id}: reused from {reused_result.work_unit_id}"),
                    execution_receipt_path=reused_result.execution_receipt_path,
                    reused_from_work_unit_id=reused_result.work_unit_id,
                    failure_reason=reused_result.failure_reason,
                )
            )
            completed_work_units.append(work_unit.id)
            continue
        write_run_state(
            run_root / "run-state.json",
            run_id=resolved_run_id,
            task_id=task_card.id,
            state="execute",
            continuation_mode=continuation_mode,
            accepted_revision_count=len(task_card.accepted_revisions),
            active_work_unit=work_unit.id,
            completed_work_units=tuple(completed_work_units),
            failed_work_units=tuple(failed_work_units),
            reused_work_units=tuple(reused_work_unit_ids),
            superseded_work_units=tuple(work_unit.id for work_unit in superseded_work_units),
        )
        result = execute_work_unit(
            resolved_agent_root,
            task_card,
            work_unit,
            work_root=run_root / "work-units" / work_unit.id,
        )
        work_results.append(result)
        if result.status == "completed":
            completed_work_units.append(work_unit.id)
        else:
            failed_work_units.append(work_unit.id)
    work_results_payload = {"work_results": [result.model_dump() for result in work_results]}
    _write_json(work_results_path, work_results_payload)

    verification = verify_run(task_card, plan, tuple(work_results))
    verification_payload = verification.model_dump()
    verification_path = _write_json(run_root / "verification.json", verification_payload)
    final_state = (
        "awaiting_agent_skill_organization"
        if agent_skill_organization is None
        else "ready_for_execution"
        if not should_execute
        else "close"
        if verification.result == "done"
        else "verify"
    )
    run_state = write_run_state(
        run_root / "run-state.json",
        run_id=resolved_run_id,
        task_id=task_card.id,
        state=final_state,
        continuation_mode=continuation_mode,
        accepted_revision_count=len(task_card.accepted_revisions),
        completed_work_units=tuple(completed_work_units),
        failed_work_units=tuple(failed_work_units),
        reused_work_units=tuple(reused_work_unit_ids),
        superseded_work_units=tuple(work_unit.id for work_unit in superseded_work_units),
    )
    work_dossier_path = run_root / "work-dossier.json"
    work_dossier_markdown_path = run_root / "work-dossier.md"
    artifacts = {
        "work_dossier": str(work_dossier_path),
        "work_dossier_markdown": str(work_dossier_markdown_path),
        "skills_catalog": str(skills_catalog_path),
        "task_card": str(task_card_path),
        "work_plan": str(plan_path),
        "plan": str(plan_path),
        "module_assignments": str(module_assignments_path),
        "work_results": str(work_results_path),
        "run_state": str(run_root / "run-state.json"),
        "verification": str(verification_path),
    }
    work_dossier_payload = _build_work_dossier(
        run_id=resolved_run_id,
        task_card=task_card_payload,
        work_plan=work_plan_payload,
        module_assignments=module_assignments_payload,
        work_results=work_results_payload,
        verification=verification_payload,
        run_state=run_state.model_dump(),
        artifact_paths={
            "skills_catalog": artifacts["skills_catalog"],
            "task_card": artifacts["task_card"],
            "work_plan": artifacts["work_plan"],
            "module_assignments": artifacts["module_assignments"],
            "work_results": artifacts["work_results"],
            "verification": artifacts["verification"],
            "proof": artifacts["work_dossier"],
            "proof_markdown": artifacts["work_dossier_markdown"],
        },
    )
    work_dossier_path = _write_json(work_dossier_path, work_dossier_payload)
    work_dossier_markdown_path.write_text(
        _render_work_dossier_markdown(work_dossier_payload),
        encoding="utf-8",
    )
    work_summary = {
        "run_id": resolved_run_id,
        "task_id": task_card.id,
        "goal": task_card.goal,
        "state": run_state.state,
        "verification_result": verification_payload["result"],
        "work_unit_count": len(plan.work_units),
        "completed_work_unit_count": len(completed_work_units),
        "failed_work_unit_count": len(failed_work_units),
        "continuation_mode": run_state.continuation_mode,
        "accepted_revision_count": run_state.accepted_revision_count,
        "reused_work_unit_count": len(reused_work_unit_ids),
        "superseded_work_unit_count": len(superseded_work_units),
        "proof_ready": verification_payload["result"] == "done",
        "primary_artifact": "work_dossier",
        "primary_artifact_path": str(work_dossier_path),
    }
    return {
        "run_id": resolved_run_id,
        "work_dossier": work_dossier_payload,
        "artifacts": artifacts,
        "work_summary": work_summary,
        "skills_catalog": skills_catalog_payload,
        "candidates": [candidate.model_dump() for candidate in candidates],
        "agent_skill_organization": agent_skill_organization,
        "task_card": task_card_payload,
        "work_plan": work_plan_payload,
        "plan": work_plan_payload,
        "module_assignments": module_assignments_payload,
        "work_results": work_results_payload,
        "work_dossier_path": str(work_dossier_path),
        "work_dossier_markdown_path": str(work_dossier_markdown_path),
        "skills_catalog_path": str(skills_catalog_path),
        "task_card_path": str(task_card_path),
        "plan_path": str(plan_path),
        "work_plan_path": str(plan_path),
        "module_assignments_path": str(module_assignments_path),
        "work_results_path": str(work_results_path),
        "run_state_path": str(run_root / "run-state.json"),
        "verification": verification_payload,
        "verification_path": str(verification_path),
        "candidate_count": len(candidates),
        "completed_work_units": list(completed_work_units),
        "failed_work_units": list(failed_work_units),
        "reused_work_units": list(reused_work_unit_ids),
        "superseded_work_units": [work_unit.id for work_unit in superseded_work_units],
        "state": run_state.state,
    }


def inspect_local_run(
    *,
    agent_root: Path,
    run_id: str,
    host_id: str | None = None,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    resolved_agent_root = agent_root.resolve()
    resolved_run_id = str(run_id).strip()
    if not resolved_run_id:
        raise ValueError("run_id must be a non-empty string")

    run_root = resolved_agent_root / "vibe" / "runs" / resolved_run_id
    skills_catalog_path = run_root / "skills-catalog.json"
    task_card_path = run_root / "task-card.json"
    plan_path = run_root / "plan.json"
    module_assignments_path = run_root / "module-assignments.json"
    run_state_path = run_root / "run-state.json"
    work_results_path = run_root / "work-results.json"
    verification_path = run_root / "verification.json"
    work_dossier_path = run_root / "work-dossier.json"
    work_dossier_markdown_path = run_root / "work-dossier.md"

    skills_catalog = _load_required_json(skills_catalog_path)
    work_dossier = _load_required_json(work_dossier_path)
    task_card = _load_required_json(task_card_path)
    plan = _load_required_json(plan_path)
    module_assignments = _load_required_json(module_assignments_path)
    work_results = _load_required_json(work_results_path)
    verification = _load_required_json(verification_path)
    run_state = load_run_state(run_state_path)

    work_units = plan.get("work_units", [])
    if not isinstance(work_units, list):
        raise ValueError(f"plan work_units must be a list: {plan_path}")

    goal = str(task_card.get("goal") or "")
    verification_result = str(verification.get("result") or "")
    host_context = _inspect_host_context(
        agent_root=resolved_agent_root,
        skills_catalog=skills_catalog,
        skills_catalog_path=skills_catalog_path,
        host_id=host_id,
        workspace_root=workspace_root,
    )
    summary = {
        "run_id": resolved_run_id,
        "task_id": run_state.task_id,
        "goal": goal,
        "state": run_state.state,
        "verification_result": verification_result,
        "work_unit_count": len(work_units),
        "completed_work_unit_count": len(run_state.completed_work_units),
        "failed_work_unit_count": len(run_state.failed_work_units),
        "continuation_mode": run_state.continuation_mode,
        "accepted_revision_count": run_state.accepted_revision_count,
        "reused_work_unit_count": len(run_state.reused_work_units),
        "superseded_work_unit_count": len(run_state.superseded_work_units),
        "proof_ready": verification_result == "done",
        "primary_artifact": "work_dossier",
        "primary_artifact_path": str(work_dossier_path),
    }
    return {
        "run_id": resolved_run_id,
        "work_dossier": work_dossier,
        "summary": summary,
        "artifacts": {
            "work_dossier": str(work_dossier_path),
            "work_dossier_markdown": str(work_dossier_markdown_path),
            "skills_catalog": str(skills_catalog_path),
            "task_card": str(task_card_path),
            "work_plan": str(plan_path),
            "plan": str(plan_path),
            "module_assignments": str(module_assignments_path),
            "work_results": str(work_results_path),
            "run_state": str(run_state_path),
            "verification": str(verification_path),
        },
        "skills_catalog": skills_catalog,
        "task_card": task_card,
        "work_plan": plan,
        "plan": plan,
        "module_assignments": module_assignments,
        "work_results": work_results,
        "run_state": run_state.model_dump(),
        "verification": verification,
        "host_context": host_context,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-root", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--host-id")
    parser.add_argument("--workspace-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_local_kernel(
        agent_root=Path(args.agent_root),
        prompt=args.prompt,
        run_id=args.run_id,
        host_id=args.host_id,
        workspace_root=Path(args.workspace_root) if args.workspace_root else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def inspect_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--host-id")
    parser.add_argument("--workspace-root")
    args = parser.parse_args(argv)

    result = inspect_local_run(
        agent_root=Path(args.agent_root),
        run_id=args.run_id,
        host_id=args.host_id,
        workspace_root=Path(args.workspace_root) if args.workspace_root else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
