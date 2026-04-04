from __future__ import annotations

from dataclasses import dataclass

from vgo_contracts.runtime_packet import RuntimePacket

from .governance import build_governance_profile
from .memory import RuntimeMemoryPolicy, build_memory_policy
from .planning import RuntimeExecutionPlan, build_execution_plan
from .router import RuntimeRoute, route_runtime_task
from .stage_machine import RuntimeStageMachine


@dataclass(frozen=True, slots=True)
class RuntimeExecutionResult:
    final_packet: RuntimePacket
    stage_receipts: list[dict[str, object]]
    mode: str
    route: dict[str, object]
    plan: dict[str, object]
    memory: dict[str, object]


def execute_runtime_packet(
    packet: RuntimePacket,
    *,
    mode: str | None = None,
    requested_skill: str | None = None,
    stage_machine: RuntimeStageMachine | None = None,
) -> RuntimeExecutionResult:
    machine = stage_machine or RuntimeStageMachine()
    governance = build_governance_profile(mode)
    route = route_runtime_task(packet.goal, requested_skill=requested_skill)
    plan = build_execution_plan(route.task_type, stage_machine=machine)
    memory = build_memory_policy(len(plan.stages))

    stage_receipts: list[dict[str, object]] = []
    final_packet = packet
    for order, stage in enumerate(machine.iter_from(packet.stage), start=1):
        final_packet = RuntimePacket(goal=packet.goal, stage=stage)
        stage_receipts.append(
            {
                'stage': stage,
                'order': order,
                'mode': governance.mode,
                'governance_scope': governance.governance_scope,
                'task_type': route.task_type,
                'runtime_selected_skill': route.runtime_selected_skill,
                'freeze_before_requirement_doc': governance.freeze_before_requirement_doc,
            }
        )

    return RuntimeExecutionResult(
        final_packet=final_packet,
        stage_receipts=stage_receipts,
        mode=governance.mode,
        route=route.model_dump(),
        plan=plan.model_dump(),
        memory=memory.model_dump(),
    )
