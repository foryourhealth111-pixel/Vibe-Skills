from __future__ import annotations

from dataclasses import dataclass, asdict

from .planning import KernelPlanningResult, build_kernel_plan
from .route_index import load_runtime_route_index as load_shared_runtime_route_index
from .task_intent import infer_task_type

CANONICAL_RUNTIME_ENTRY_ID = "vibe"


@dataclass(frozen=True, slots=True)
class RuntimeRoute:
    requested_skill: str | None
    router_selected_skill: str
    runtime_selected_skill: str
    task_type: str
    confirm_required: bool = False

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeRouteDecision:
    route: RuntimeRoute
    kernel_plan: KernelPlanningResult


def _normalize_requested_entry(requested_skill: str | None) -> str | None:
    normalized = str(requested_skill or "").strip()
    if not normalized:
        return None
    return CANONICAL_RUNTIME_ENTRY_ID


def load_runtime_route_index() -> dict[str, object]:
    return load_shared_runtime_route_index()


def resolve_runtime_route_decision(task: str, requested_skill: str | None = None) -> RuntimeRouteDecision:
    requested_entry = _normalize_requested_entry(requested_skill)
    canonical_skill = CANONICAL_RUNTIME_ENTRY_ID
    if requested_entry:
        kernel_plan = build_kernel_plan(task=task, requested_entry_id=requested_entry)
        route = RuntimeRoute(
            requested_skill=requested_entry,
            router_selected_skill=canonical_skill,
            runtime_selected_skill=canonical_skill,
            task_type=kernel_plan.resolved_task_type,
        )
        return RuntimeRouteDecision(route=route, kernel_plan=kernel_plan)

    kernel_plan = build_kernel_plan(task=task)
    route = RuntimeRoute(
        requested_skill=None,
        router_selected_skill=kernel_plan.preferred_skill or canonical_skill,
        runtime_selected_skill=canonical_skill,
        task_type=kernel_plan.resolved_task_type,
    )
    return RuntimeRouteDecision(route=route, kernel_plan=kernel_plan)


def route_runtime_task(task: str, requested_skill: str | None = None) -> RuntimeRoute:
    return resolve_runtime_route_decision(task, requested_skill=requested_skill).route
