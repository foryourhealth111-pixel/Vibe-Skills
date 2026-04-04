from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True, slots=True)
class RuntimeMemoryPolicy:
    backend: str
    enabled: bool
    stage_count: int

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def build_memory_policy(stage_count: int) -> RuntimeMemoryPolicy:
    return RuntimeMemoryPolicy(backend='runtime-neutral', enabled=False, stage_count=stage_count)
