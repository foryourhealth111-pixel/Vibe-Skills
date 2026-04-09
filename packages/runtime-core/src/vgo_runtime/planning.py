from __future__ import annotations

from dataclasses import dataclass, asdict

from .governance import choose_internal_grade
from .stage_machine import RuntimeStageMachine


@dataclass(frozen=True, slots=True)
class RuntimeExecutionPlan:
    internal_grade: str
    stages: tuple[str, ...]
    completion_language_rule: str
    delivery_acceptance_required: bool
    requested_grade_floor: str | None = None
    requested_stage_stop: str | None = None

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


GRADE_ORDER = {'M': 0, 'L': 1, 'XL': 2}


def build_execution_plan(
    task_type: str,
    *,
    stage_machine: RuntimeStageMachine | None = None,
    stages: tuple[str, ...] | None = None,
    requested_grade_floor: str | None = None,
    requested_stage_stop: str | None = None,
) -> RuntimeExecutionPlan:
    machine = stage_machine or RuntimeStageMachine()
    selected_grade = choose_internal_grade(task_type)
    normalized_floor = str(requested_grade_floor).strip().upper() if requested_grade_floor else None
    if normalized_floor:
        if normalized_floor not in GRADE_ORDER:
            raise ValueError(f'unsupported requested grade floor: {requested_grade_floor}')
        if GRADE_ORDER[selected_grade] < GRADE_ORDER[normalized_floor]:
            selected_grade = normalized_floor
    return RuntimeExecutionPlan(
        internal_grade=selected_grade,
        stages=stages or machine.stages,
        completion_language_rule='verification_before_completion',
        delivery_acceptance_required=True,
        requested_grade_floor=normalized_floor,
        requested_stage_stop=requested_stage_stop,
    )
