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

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def build_execution_plan(task_type: str, *, stage_machine: RuntimeStageMachine | None = None) -> RuntimeExecutionPlan:
    machine = stage_machine or RuntimeStageMachine()
    return RuntimeExecutionPlan(
        internal_grade=choose_internal_grade(task_type),
        stages=machine.stages,
        completion_language_rule='verification_before_completion',
        delivery_acceptance_required=True,
    )
