from __future__ import annotations

from dataclasses import dataclass, field

GOVERNED_STAGES = (
    'skeleton_check',
    'deep_interview',
    'requirement_doc',
    'xl_plan',
    'plan_execute',
    'phase_cleanup',
)


@dataclass(frozen=True, slots=True)
class RuntimeStageMachine:
    stages: tuple[str, ...] = field(default_factory=lambda: GOVERNED_STAGES)

    def index_of(self, stage: str) -> int:
        normalized = str(stage).strip()
        if normalized not in self.stages:
            raise ValueError(f'unknown governed runtime stage: {stage}')
        return self.stages.index(normalized)

    def iter_from(self, stage: str) -> tuple[str, ...]:
        start = self.index_of(stage)
        return self.stages[start:]

    def next_stage(self, stage: str) -> str | None:
        index = self.index_of(stage)
        if index + 1 >= len(self.stages):
            return None
        return self.stages[index + 1]
