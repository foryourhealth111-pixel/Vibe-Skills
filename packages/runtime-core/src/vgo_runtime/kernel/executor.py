from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import re

from .task_card import TaskCard
from .work_plan import WorkUnit


@dataclass(frozen=True, slots=True)
class WorkUnitResult:
    work_unit_id: str
    status: str
    lifecycle_state: str
    used_skill: str | None
    artifacts: tuple[str, ...]
    artifact_paths: tuple[str, ...]
    proof_artifact_paths: tuple[str, ...]
    checked_targets: tuple[str, ...]
    notes: tuple[str, ...]
    proof: tuple[str, ...]
    execution_receipt_path: str | None
    reused_from_work_unit_id: str | None = None
    failure_reason: str | None = None
    artifact_kind: str = "scaffold"
    proof_ready: bool = False
    artifact_sha256: tuple[str, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return asdict(self)

    def artifact_evidence_paths(self) -> tuple[str, ...]:
        return tuple(path for path in (*self.artifact_paths, *self.proof_artifact_paths) if str(path).strip())


def artifact_sha256_for_paths(artifact_paths: tuple[str, ...]) -> tuple[str, ...]:
    digests: list[str] = []
    for raw_path in artifact_paths:
        path = Path(raw_path)
        try:
            is_file = path.is_file()
        except OSError:
            is_file = False
        if not is_file:
            digests.append("")
            continue
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            digests.append("")
            continue
        digests.append(digest.hexdigest())
    return tuple(digests)


def capture_completed_artifact_sha256(result: WorkUnitResult) -> WorkUnitResult:
    if result.status != "completed":
        return result
    return replace(
        result,
        artifact_sha256=artifact_sha256_for_paths(result.artifact_paths),
    )


SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(value: str, *, fallback: str) -> str:
    slug = SLUG_PATTERN.sub("-", value.casefold()).strip("-")
    return slug or fallback


def _render_artifact_lines(
    *,
    artifact_name: str,
    task_goal: str,
    work_unit: WorkUnit,
    preferred_skill: str,
) -> list[str]:
    lowered_artifact = artifact_name.casefold()
    header = [
        f"# {artifact_name}",
        "",
        f"- task goal: {task_goal}",
        f"- work unit: {work_unit.id}",
        f"- work goal: {work_unit.goal}",
        f"- used skill: {preferred_skill}",
        f"- binding profile: {work_unit.binding_profile}",
        f"- binding reason: {work_unit.binding_reason or 'not recorded'}",
        "",
    ]
    if "review notes" in lowered_artifact:
        return [
            *header,
            "## Findings",
            "- Primary risk surface: review the changed behavior and interfaces.",
            "- Likely regression area: any code path touched by the requested change.",
            "",
            "## Evidence To Check",
            *[f"- {target}" for target in work_unit.verification],
            "",
            "## Recommendation",
            "- Keep the review concrete and tie each finding to a code or test surface.",
        ]
    if "implementation plan" in lowered_artifact or "work plan" in lowered_artifact:
        return [
            *header,
            "## Objective",
            f"- Deliver: {artifact_name}",
            "",
            "## Work Steps",
            "- Understand the task boundary.",
            "- Implement the smallest useful slice.",
            "- Verify the changed behavior before closeout.",
            "",
            "## Exit Criteria",
            *[f"- {target}" for target in work_unit.verification],
        ]
    if "focused tests" in lowered_artifact or "tests" in lowered_artifact:
        return [
            *header,
            "## Test Targets",
            "- Cover the changed behavior directly.",
            "- Keep the test narrow enough to explain the failure clearly.",
            "",
            "## Assertions",
            *[f"- {target}" for target in work_unit.verification],
            "",
            "## Notes",
            "- Prefer a focused regression test over a broad smoke replacement.",
        ]
    if "report" in lowered_artifact or "summary" in lowered_artifact or "brief" in lowered_artifact:
        return [
            *header,
            "## Summary",
            "- State the main outcome first.",
            "- Keep the report tied to the requested evidence.",
            "",
            "## Key Points",
            *[f"- {target}" for target in work_unit.verification],
            "",
            "## Notes",
            "- Prefer a concise report that surfaces the decision-ready facts.",
        ]
    return [
        *header,
        "This artifact was produced by the local work kernel execution receipt path.",
        "",
        f"Expected artifact: {artifact_name}",
        "",
        "## Verification",
        *[f"- {target}" for target in work_unit.verification],
    ]


def _write_artifact_file(
    artifact_dir: Path,
    *,
    artifact_name: str,
    index: int,
    task_goal: str,
    work_unit: WorkUnit,
    preferred_skill: str,
) -> Path:
    artifact_path = artifact_dir / f"{index:02d}-{_slugify(artifact_name, fallback=f'artifact-{index}')}.md"
    lines = _render_artifact_lines(
        artifact_name=artifact_name,
        task_goal=task_goal,
        work_unit=work_unit,
        preferred_skill=preferred_skill,
    )
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifact_path


def _write_delivery_artifact_file(
    delivery_dir: Path,
    *,
    artifact_name: str,
    index: int,
    task_goal: str,
    work_unit: WorkUnit,
    preferred_skill: str,
) -> Path:
    artifact_path = delivery_dir / f"{index:02d}-{_slugify(artifact_name, fallback=f'artifact-{index}')}.md"
    lines = _render_artifact_lines(
        artifact_name=artifact_name,
        task_goal=task_goal,
        work_unit=work_unit,
        preferred_skill=preferred_skill,
    )
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifact_path


def _write_execution_receipt(
    work_root: Path,
    *,
    work_unit: WorkUnit,
    preferred_skill: str,
    artifact_paths: tuple[str, ...],
    checked_targets: tuple[str, ...],
) -> Path:
    receipt_path = work_root / "execution-receipt.json"
    payload = {
        "work_unit_id": work_unit.id,
        "work_goal": work_unit.goal,
        "bound_skill": preferred_skill,
        "used_skill": None,
        "binding_profile": work_unit.binding_profile,
        "binding_reason": work_unit.binding_reason,
        "artifact_paths": list(artifact_paths),
        "checked_targets": list(checked_targets),
        "status": "needs_execution",
        "artifact_kind": "scaffold",
        "proof_ready": False,
    }
    receipt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt_path


def execute_work_unit(
    agent_root: Path,
    task_card: TaskCard,
    work_unit: WorkUnit,
    *,
    work_root: Path | None = None,
) -> WorkUnitResult:
    del agent_root
    preferred_skill = work_unit.preferred_skill or "no-skill"
    artifact_paths: tuple[str, ...] = ()
    proof_artifact_paths: tuple[str, ...] = ()
    execution_receipt_path: str | None = None
    if work_root is not None:
        artifact_dir = work_root / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        proof_paths = [
            str(
                _write_artifact_file(
                    artifact_dir,
                    artifact_name=artifact_name,
                    index=index,
                    task_goal=task_card.goal,
                    work_unit=work_unit,
                    preferred_skill=preferred_skill,
                ).resolve()
            )
            for index, artifact_name in enumerate(work_unit.expected_artifacts, start=1)
        ]
        proof_artifact_paths = tuple(proof_paths)
        run_root = work_root.parent.parent
        delivery_dir = run_root.parent.parent / "work-products" / run_root.name / work_unit.id
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivery_paths = [
            str(
                _write_delivery_artifact_file(
                    delivery_dir,
                    artifact_name=artifact_name,
                    index=index,
                    task_goal=task_card.goal,
                    work_unit=work_unit,
                    preferred_skill=preferred_skill,
                ).resolve()
            )
            for index, artifact_name in enumerate(work_unit.expected_artifacts, start=1)
        ]
        artifact_paths = tuple(delivery_paths)
        execution_receipt_path = str(
            _write_execution_receipt(
                work_root,
                work_unit=work_unit,
                preferred_skill=preferred_skill,
                artifact_paths=artifact_paths,
                checked_targets=work_unit.verification,
            ).resolve()
        )
    proof = (
        f"{work_unit.id}: scaffolded for bound skill {preferred_skill}",
        f"{work_unit.id}: binding profile {work_unit.binding_profile}",
        f"{work_unit.id}: binding reason {work_unit.binding_reason or 'not recorded'}",
        f"{work_unit.id}: scaffold artifacts {', '.join(work_unit.expected_artifacts)}",
        f"{work_unit.id}: artifact paths {', '.join(artifact_paths) if artifact_paths else 'in-memory only'}",
        f"{work_unit.id}: checked targets {', '.join(work_unit.verification)}",
        f"{work_unit.id}: execution receipt {execution_receipt_path or 'not written'}",
    )
    return WorkUnitResult(
        work_unit_id=work_unit.id,
        status="needs_execution",
        lifecycle_state="scaffolded",
        used_skill=None,
        artifacts=work_unit.expected_artifacts,
        artifact_paths=artifact_paths,
        proof_artifact_paths=proof_artifact_paths,
        checked_targets=work_unit.verification,
        notes=(
            f"requires real execution evidence for bound skill {preferred_skill}",
            f"binding profile: {work_unit.binding_profile}",
            f"binding reason: {work_unit.binding_reason or 'not recorded'}",
        ),
        proof=proof,
        execution_receipt_path=execution_receipt_path,
        reused_from_work_unit_id=None,
        artifact_kind="scaffold",
        proof_ready=False,
    )
