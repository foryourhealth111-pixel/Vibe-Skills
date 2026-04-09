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
    effective_requested_skill = requested_skill or packet.entry_intent_id
    executed_stages = machine.iter_between(packet.stage, packet.requested_stage_stop)
    route = route_runtime_task(packet.goal, requested_skill=effective_requested_skill)
    plan = build_execution_plan(
        route.task_type,
        stage_machine=machine,
        stages=executed_stages,
        requested_grade_floor=packet.requested_grade_floor,
        requested_stage_stop=packet.requested_stage_stop,
    )
    memory = build_memory_policy(len(executed_stages))

    stage_receipts: list[dict[str, object]] = []
    final_packet = packet
    for order, stage in enumerate(executed_stages, start=1):
        final_packet = RuntimePacket(
            goal=packet.goal,
            stage=stage,
            entry_intent_id=packet.entry_intent_id,
            requested_stage_stop=packet.requested_stage_stop,
            requested_grade_floor=packet.requested_grade_floor,
        )
        stage_receipts.append(
            {
                'stage': stage,
                'order': order,
                'mode': governance.mode,
                'governance_scope': governance.governance_scope,
                'task_type': route.task_type,
                'runtime_selected_skill': route.runtime_selected_skill,
                'entry_intent_id': packet.entry_intent_id,
                'requested_stage_stop': packet.requested_stage_stop,
                'requested_grade_floor': packet.requested_grade_floor,
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
