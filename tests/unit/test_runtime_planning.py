from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SRC = ROOT / 'packages' / 'runtime-core' / 'src'
if str(RUNTIME_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SRC))

import vgo_runtime.planning as planning_module
import vgo_runtime.kernel.planner as kernel_planning_module
from vgo_runtime.kernel.planner import (
    KernelPlanningResult as KernelPlanningResultFromKernel,
    RuntimeExecutionPlan as RuntimeExecutionPlanFromKernel,
    build_execution_plan as build_execution_plan_from_kernel,
    build_kernel_plan as build_kernel_plan_from_kernel,
)
from vgo_runtime.planning import build_execution_plan, build_kernel_plan
from vgo_runtime.stage_stop import StageStopDecision


def test_planning_module_exports_kernel_authority() -> None:
    assert planning_module.KernelPlanningResult is KernelPlanningResultFromKernel
    assert planning_module.RuntimeExecutionPlan is RuntimeExecutionPlanFromKernel
    assert planning_module.build_kernel_plan is build_kernel_plan_from_kernel
    assert planning_module.build_execution_plan is build_execution_plan_from_kernel


def test_build_execution_plan_keeps_legacy_fields_and_exposes_kernel_plan() -> None:
    plan = build_execution_plan(
        'planning',
        task='design the architecture and write an implementation plan',
        requested_grade_floor='m',
        requested_stage_stop='xl_plan',
    )

    assert plan.internal_grade == 'L'
    assert plan.requested_grade_floor == 'M'
    assert plan.requested_stage_stop == 'xl_plan'
    assert plan.effective_requested_stage_stop == 'xl_plan'
    assert plan.stage_stop_source == 'requested'
    assert plan.kernel['task_card']['goal'] == 'design the architecture and write an implementation plan'
    assert plan.kernel['task_card']['mode'] == 'planning'
    assert plan.kernel['candidates'] == []
    assert plan.kernel['work_plan']['task_id'] == plan.kernel['task_card']['id']


def test_build_execution_plan_uses_task_type_to_shape_kernel_work_plan() -> None:
    plan = build_execution_plan(
        'coding',
        task='implement the approved plan',
    )

    assert plan.internal_grade == 'L'
    assert len(plan.kernel['work_plan']['work_units']) == 1
    assert plan.kernel['work_plan']['work_units'][0]['preferred_skill'] is None
    assert plan.kernel['work_plan']['work_units'][0]['bound_skill'] is None


def test_build_kernel_plan_returns_typed_kernel_planning_result() -> None:
    kernel_plan = build_kernel_plan(
        'planning',
        task='design the architecture and write an implementation plan',
    )

    assert kernel_plan.task_card.goal == 'design the architecture and write an implementation plan'
    assert kernel_plan.candidates == ()
    assert kernel_plan.work_plan.task_id == kernel_plan.task_card.id
    assert kernel_plan.module_assignments.task_id == kernel_plan.task_card.id
    assert kernel_plan.module_assignments.units[0].work_unit_id == "wu-1"
    assert kernel_plan.module_assignments.units[0].bound_skill is None
    assert kernel_plan.inferred_task_type == 'planning'
    assert kernel_plan.preferred_skill is None
    assert kernel_plan.model_dump()['module_assignments']['units'][0]['bound_skill'] is None
    assert kernel_plan.resolved_task_type == 'planning'
    assert kernel_plan.suggested_internal_grade == 'L'
    assert kernel_plan.suggested_stage_stop == 'phase_cleanup'


def test_build_execution_plan_prefers_kernel_selected_skill_over_legacy_task_type() -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )
    plan = build_execution_plan(
        'coding',
        task='need a plan',
        kernel_plan=kernel_plan,
    )

    assert kernel_plan.work_plan.work_units[0].preferred_skill is None
    assert kernel_plan.inferred_task_type == 'planning'
    assert kernel_plan.resolved_task_type == 'coding'
    assert kernel_plan.suggested_internal_grade == 'L'
    assert plan.internal_grade == 'L'


def test_build_execution_plan_uses_kernel_suggested_stage_stop_when_none_requested() -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )
    plan = build_execution_plan(
        'coding',
        task='need a plan',
        kernel_plan=kernel_plan,
    )

    assert kernel_plan.suggested_stage_stop == 'phase_cleanup'
    assert plan.stages == ('skeleton_check', 'deep_interview', 'requirement_doc', 'xl_plan', 'plan_execute', 'phase_cleanup')
    assert plan.requested_stage_stop is None
    assert plan.effective_requested_stage_stop == 'phase_cleanup'
    assert plan.stage_stop_source == 'kernel_suggested'


def test_build_execution_plan_reuses_precomputed_stage_stop_decision(monkeypatch) -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )

    def fail_resolve_stage_stop(*_args, **_kwargs):
        raise AssertionError('resolve_stage_stop should not run when a precomputed decision is provided')

    monkeypatch.setattr(kernel_planning_module, 'resolve_stage_stop', fail_resolve_stage_stop)

    plan = build_execution_plan(
        'coding',
        task='need a plan',
        kernel_plan=kernel_plan,
        stage_stop_decision=StageStopDecision(
            requested_stage_stop='xl_plan',
            effective_requested_stage_stop='xl_plan',
            stage_stop_source='requested',
        ),
    )

    assert plan.requested_stage_stop == 'xl_plan'
    assert plan.effective_requested_stage_stop == 'xl_plan'
    assert plan.stage_stop_source == 'requested'


def test_build_kernel_plan_can_infer_task_type_without_router_hint() -> None:
    kernel_plan = build_kernel_plan(task='triage runtime specialist dispatch duplication')

    assert kernel_plan.inferred_task_type == 'debug'
    assert kernel_plan.task_card.mode == 'debug'


def test_build_execution_plan_can_use_kernel_plan_without_legacy_task_type() -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )

    plan = build_execution_plan(
        kernel_plan=kernel_plan,
    )

    assert plan.kernel['task_card']['goal'] == 'need a plan'
    assert plan.kernel['work_plan']['work_units'][0]['preferred_skill'] is None
    assert plan.internal_grade == 'L'


def test_build_execution_plan_can_use_precomputed_stages_without_stage_machine() -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )

    plan = build_execution_plan(
        stages=('requirement_doc', 'xl_plan'),
        kernel_plan=kernel_plan,
        stage_stop_decision=StageStopDecision(
            requested_stage_stop='xl_plan',
            effective_requested_stage_stop='xl_plan',
            stage_stop_source='requested',
        ),
    )

    assert plan.stages == ('requirement_doc', 'xl_plan')
    assert plan.requested_stage_stop == 'xl_plan'
    assert plan.stage_stop_source == 'requested'


def test_build_execution_plan_does_not_construct_default_stage_machine_when_stages_are_provided(monkeypatch) -> None:
    kernel_plan = build_kernel_plan(
        'coding',
        task='need a plan',
    )

    def fail_runtime_stage_machine():
        raise AssertionError('default RuntimeStageMachine should not be constructed when stages are already provided')

    monkeypatch.setattr(kernel_planning_module, 'RuntimeStageMachine', fail_runtime_stage_machine)

    plan = build_execution_plan(
        stages=('requirement_doc', 'xl_plan'),
        kernel_plan=kernel_plan,
        stage_stop_decision=StageStopDecision(
            requested_stage_stop='xl_plan',
            effective_requested_stage_stop='xl_plan',
            stage_stop_source='requested',
        ),
    )

    assert plan.stages == ('requirement_doc', 'xl_plan')


def test_build_execution_plan_requires_task_type_when_kernel_plan_is_missing() -> None:
    try:
        build_execution_plan(task='need a plan')
    except ValueError as exc:
        assert str(exc) == 'task_type is required when kernel_plan is not provided'
    else:
        raise AssertionError('expected build_execution_plan to require task_type without kernel_plan')


def test_planning_module_is_compatibility_surface_only() -> None:
    text = Path("packages/runtime-core/src/vgo_runtime/planning.py").read_text(encoding="utf-8")
    assert "find_skill_candidates" not in text
    assert "infer_task_type(" not in text
