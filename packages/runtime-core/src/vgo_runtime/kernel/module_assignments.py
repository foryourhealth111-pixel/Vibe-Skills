from __future__ import annotations

from dataclasses import asdict, dataclass

from .work_plan import SkillProvenance, WorkPlan


@dataclass(frozen=True, slots=True)
class ModuleAssignmentsUnit:
    work_unit_id: str
    bound_skill: str | None
    binding_profile: str
    binding_reason: str | None
    alternative_skills: tuple[str, ...]
    expected_artifacts: tuple[str, ...]
    verification: tuple[str, ...]
    provenance: SkillProvenance | None = None

    def model_dump(self) -> dict[str, object]:
        payload = asdict(self)
        provenance = payload.get("provenance")
        if isinstance(provenance, dict):
            payload["skill_source_kind"] = provenance["source_kind"]
            payload["skill_source_root"] = provenance["source_root"]
            payload["resolved_skill_file"] = provenance["resolved_skill_file"]
            payload["skill_source_priority"] = provenance["source_priority"]
            payload["skill_source_order"] = provenance["source_order"]
            payload["skill_path_contract"] = provenance["path_contract"]
            payload["skill_path_base"] = provenance["path_base"]
        return payload


@dataclass(frozen=True, slots=True)
class ModuleAssignments:
    task_id: str
    units: tuple[ModuleAssignmentsUnit, ...]

    def model_dump(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "units": [unit.model_dump() for unit in self.units],
        }


def build_module_assignments(plan: WorkPlan) -> ModuleAssignments:
    return ModuleAssignments(
        task_id=plan.task_id,
        units=tuple(
            ModuleAssignmentsUnit(
                work_unit_id=work_unit.id,
                bound_skill=work_unit.preferred_skill,
                binding_profile=work_unit.binding_profile,
                binding_reason=work_unit.binding_reason,
                alternative_skills=work_unit.fallback_skills,
                expected_artifacts=work_unit.expected_artifacts,
                verification=work_unit.verification,
                provenance=work_unit.selected_skill_provenance,
            )
            for work_unit in plan.work_units
        ),
    )
