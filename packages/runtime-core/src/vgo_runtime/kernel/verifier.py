from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .executor import artifact_sha256_for_paths, is_final_completed_result
from .task_card import TaskCard
from .work_plan import WorkPlan, WorkUnit


@dataclass(frozen=True, slots=True)
class VerificationResult:
    result: str
    notes: tuple[str, ...]
    failed_criteria: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _result_attr(work_result: Any, name: str, default: Any) -> Any:
    return work_result.get(name, default) if isinstance(work_result, dict) else getattr(work_result, name, default)


def completed_result_readiness_notes(
    work_result: Any, *, work_unit: WorkUnit | None = None,
) -> tuple[str, ...]:
    unit_id = work_unit.id if work_unit is not None else str(_result_attr(work_result, "work_unit_id", ""))
    notes: list[str] = []
    if not is_final_completed_result(work_result):
        notes.append(f"{unit_id}: completed result requires final, proof-ready artifacts")
    actual_artifacts = tuple(str(value) for value in _result_attr(work_result, "artifacts", ()))
    expected_artifacts = work_unit.expected_artifacts if work_unit is not None else actual_artifacts
    if actual_artifacts != expected_artifacts:
        notes.append(f"{unit_id}: artifacts do not match expected artifacts")
    proof = tuple(str(value) for value in _result_attr(work_result, "proof", ()))
    if not proof:
        notes.append(f"{unit_id}: proof is missing")
    used_skill = _result_attr(work_result, "used_skill", None)
    preferred_skill = work_unit.preferred_skill if work_unit is not None else used_skill
    proof_text = " | ".join(proof)
    if preferred_skill and str(preferred_skill) not in proof_text:
        notes.append(f"{unit_id}: missing skill reference")
    for artifact in expected_artifacts:
        if artifact not in proof_text:
            notes.append(f"{unit_id}: missing artifact reference {artifact}")
    artifact_paths = tuple(str(value) for value in _result_attr(work_result, "artifact_paths", ()))
    artifact_sha256 = tuple(str(value) for value in _result_attr(work_result, "artifact_sha256", ()))
    if len(artifact_paths) != len(expected_artifacts):
        notes.append(f"{unit_id}: artifact_paths count does not match expected artifacts")
    if len(artifact_sha256) != len(artifact_paths) or any(not digest for digest in artifact_sha256):
        notes.append(f"{unit_id}: artifact SHA-256 evidence is incomplete")
    elif artifact_sha256 != artifact_sha256_for_paths(artifact_paths):
        notes.append(f"{unit_id}: artifact content changed after completion")
    for artifact_path in artifact_paths:
        if not Path(artifact_path).is_file():
            notes.append(f"{unit_id}: artifact file missing {artifact_path}")
    checked_targets = tuple(str(value) for value in _result_attr(work_result, "checked_targets", ()))
    expected_targets = work_unit.verification if work_unit is not None else checked_targets
    if checked_targets != expected_targets:
        notes.append(f"{unit_id}: checked targets do not match verification targets")
    for target in expected_targets:
        if target not in proof_text:
            notes.append(f"{unit_id}: missing verification target {target}")
    if preferred_skill and used_skill != preferred_skill:
        notes.append(f"{unit_id}: used_skill does not match preferred_skill")
    receipt = _result_attr(work_result, "execution_receipt_path", None)
    if receipt is None:
        notes.append(f"{unit_id}: execution receipt path is missing")
    elif not Path(str(receipt)).is_file():
        notes.append(f"{unit_id}: execution receipt file missing {receipt}")
    return tuple(notes)


def verify_run(task_card: TaskCard, plan: WorkPlan, work_results: tuple[Any, ...]) -> VerificationResult:
    if task_card.input_artifacts and (
        len(task_card.input_artifact_sha256) != len(task_card.input_artifacts)
        or any(not digest for digest in task_card.input_artifact_sha256)
        or task_card.input_artifact_sha256 != artifact_sha256_for_paths(task_card.input_artifacts)
    ):
        return VerificationResult(
            result="revise_execution",
            notes=("Declared input artifacts changed or are missing since execution started",),
            failed_criteria=task_card.completion_criteria or ("execution inputs must remain current",),
            evidence=(),
        )
    if len(work_results) != len(plan.work_units):
        failed = task_card.completion_criteria or ("work plan is incomplete",)
        return VerificationResult(
            result="revise_plan",
            notes=("work result count does not match the plan",),
            failed_criteria=failed,
            evidence=(),
        )

    plan_ids = tuple(unit.id for unit in plan.work_units)
    result_ids = tuple(_result_attr(result, "work_unit_id", None) for result in work_results)
    if (
        any(not isinstance(unit_id, str) or not unit_id.strip() for unit_id in result_ids)
        or len(set(result_ids)) != len(result_ids)
        or len(set(plan_ids)) != len(plan_ids)
        or set(result_ids) != set(plan_ids)
    ):
        return VerificationResult(
            result="revise_execution",
            notes=("work result IDs must uniquely match the approved work unit IDs",),
            failed_criteria=task_card.completion_criteria or ("work result identity is invalid",),
            evidence=(),
        )
    results_by_id = dict(zip(result_ids, work_results))
    work_results = tuple(results_by_id[unit_id] for unit_id in plan_ids)

    needs_execution_results = [
        result for result in work_results if _result_attr(result, "status", "") == "needs_execution"
    ]
    if needs_execution_results:
        failed = task_card.completion_criteria or ("real execution evidence is required",)
        return VerificationResult(
            result="needs_execution",
            notes=tuple(
                str(note)
                for result in needs_execution_results
                for note in _result_attr(result, "notes", ())
            ),
            failed_criteria=failed,
            evidence=(),
        )

    failed_results = [result for result in work_results if _result_attr(result, "status", "") != "completed"]
    if failed_results:
        failed = task_card.completion_criteria or ("execution completed successfully",)
        return VerificationResult(
            result="revise_execution",
            notes=tuple(str(note) for result in failed_results for note in _result_attr(result, "notes", ())),
            failed_criteria=failed,
            evidence=(),
        )

    missing_artifacts = []
    for work_unit, work_result in zip(plan.work_units, work_results):
        actual_artifacts = tuple(str(value) for value in _result_attr(work_result, "artifacts", ()))
        if actual_artifacts != work_unit.expected_artifacts:
            missing_artifacts.append(work_unit.id)
    if missing_artifacts:
        failed = task_card.completion_criteria or ("expected artifacts are missing",)
        return VerificationResult(
            result="revise_execution",
            notes=(f"artifact mismatch: {', '.join(missing_artifacts)}",),
            failed_criteria=failed,
            evidence=(),
        )

    missing_proof = []
    weak_proof = []
    collected_evidence: list[str] = []
    for work_unit, work_result in zip(plan.work_units, work_results):
        proof = tuple(str(value) for value in _result_attr(work_result, "proof", ()))
        if not proof:
            missing_proof.append(work_unit.id)
            continue
        weak_proof.extend(completed_result_readiness_notes(work_result, work_unit=work_unit))
        collected_evidence.extend(proof)
    if missing_proof:
        failed = task_card.completion_criteria or ("direct proof is missing",)
        return VerificationResult(
            result="revise_execution",
            notes=(f"proof missing: {', '.join(missing_proof)}",),
            failed_criteria=failed,
            evidence=(),
        )
    if weak_proof:
        failed = task_card.completion_criteria or ("direct proof is incomplete",)
        return VerificationResult(
            result="revise_execution",
            notes=tuple(weak_proof),
            failed_criteria=failed,
            evidence=(),
        )

    return VerificationResult(
        result="done",
        notes=("all work units completed and matched expected artifacts",),
        failed_criteria=(),
        evidence=tuple(collected_evidence),
    )
