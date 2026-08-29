from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .executor import artifact_sha256_for_paths
from .task_card import TaskCard
from .work_plan import WorkPlan


@dataclass(frozen=True, slots=True)
class VerificationResult:
    result: str
    notes: tuple[str, ...]
    failed_criteria: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _result_attr(work_result: Any, name: str, default: Any) -> Any:
    return getattr(work_result, name, default)


def verify_run(task_card: TaskCard, plan: WorkPlan, work_results: tuple[Any, ...]) -> VerificationResult:
    if len(work_results) != len(plan.work_units):
        failed = task_card.completion_criteria or ("work plan is incomplete",)
        return VerificationResult(
            result="revise_plan",
            notes=("work result count does not match the plan",),
            failed_criteria=failed,
            evidence=(),
        )

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
        used_skill = _result_attr(work_result, "used_skill", None)
        artifact_paths = tuple(str(value) for value in _result_attr(work_result, "artifact_paths", ()))
        artifact_sha256 = tuple(str(value) for value in _result_attr(work_result, "artifact_sha256", ()))
        checked_targets = tuple(str(value) for value in _result_attr(work_result, "checked_targets", ()))
        execution_receipt_path = _result_attr(work_result, "execution_receipt_path", None)
        proof_text = " | ".join(proof)
        if work_unit.preferred_skill and str(work_unit.preferred_skill) not in proof_text:
            weak_proof.append(f"{work_unit.id}: missing skill reference")
        for artifact in work_unit.expected_artifacts:
            if artifact not in proof_text:
                weak_proof.append(f"{work_unit.id}: missing artifact reference {artifact}")
        if len(artifact_paths) != len(work_unit.expected_artifacts):
            weak_proof.append(f"{work_unit.id}: artifact_paths count does not match expected artifacts")
        if len(artifact_sha256) != len(artifact_paths) or any(not digest for digest in artifact_sha256):
            weak_proof.append(f"{work_unit.id}: artifact SHA-256 evidence is incomplete")
        elif artifact_sha256 != artifact_sha256_for_paths(artifact_paths):
            weak_proof.append(f"{work_unit.id}: artifact content changed after completion")
        for artifact_path in artifact_paths:
            if not Path(artifact_path).is_file():
                weak_proof.append(f"{work_unit.id}: artifact file missing {artifact_path}")
        expected_targets = work_unit.verification
        if checked_targets != expected_targets:
            weak_proof.append(f"{work_unit.id}: checked targets do not match verification targets")
        for target in expected_targets:
            if target not in proof_text:
                weak_proof.append(f"{work_unit.id}: missing verification target {target}")
        if work_unit.preferred_skill and used_skill != work_unit.preferred_skill:
            weak_proof.append(f"{work_unit.id}: used_skill does not match preferred_skill")
        if execution_receipt_path is None:
            weak_proof.append(f"{work_unit.id}: execution receipt path is missing")
        elif not Path(str(execution_receipt_path)).is_file():
            weak_proof.append(f"{work_unit.id}: execution receipt file missing {execution_receipt_path}")
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
