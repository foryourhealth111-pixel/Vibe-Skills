from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class SkillProvenance:
    source_kind: str
    source_root: str
    resolved_skill_file: str
    source_priority: int
    source_order: int
    path_contract: str
    path_base: str

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    criterion_id: str
    description: str
    verification_mode: str

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WorkUnit:
    id: str
    goal: str
    depends_on: tuple[str, ...]
    preferred_skill: str | None
    binding_profile: str
    binding_reason: str | None
    fallback_skills: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    verification: tuple[str, ...]
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    selected_skill_provenance: SkillProvenance | None = None
    status: str = "pending"
    lifecycle_state: str = "active"
    reused_from_work_unit_id: str | None = None

    def model_dump(self) -> dict[str, object]:
        payload = asdict(self)
        # Export neutral binding names so outer contracts can talk about work
        # binding without depending on routing-era wording.
        payload["bound_skill"] = payload["preferred_skill"]
        payload["alternative_skills"] = payload["fallback_skills"]
        return payload


@dataclass(frozen=True, slots=True)
class WorkPlan:
    task_id: str
    work_units: tuple[WorkUnit, ...]
    superseded_work_units: tuple[WorkUnit, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "work_units": [work_unit.model_dump() for work_unit in self.work_units],
            "superseded_work_units": [work_unit.model_dump() for work_unit in self.superseded_work_units],
        }
