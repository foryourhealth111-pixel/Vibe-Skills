from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..entry_policy import resolve_runtime_task_type, suggest_stage_stop
from ..grade_intent import suggest_internal_grade
from ..route_index import load_runtime_route_index
from ..stage_stop import StageStopDecision, resolve_stage_stop
from .finder import SkillCandidate
from .finder import find_skill_candidates
from .task_card import TaskCard, build_task_card, infer_task_type
from .text_tokens import SKILL_MATCH_STOPWORDS, expand_tokens, tokens_from_text
from .module_assignments import ModuleAssignments, build_module_assignments
from .work_plan import SkillProvenance, WorkPlan, WorkUnit

GOVERNED_STAGES = (
    "skeleton_check",
    "deep_interview",
    "requirement_doc",
    "xl_plan",
    "plan_execute",
    "phase_cleanup",
)


@dataclass(frozen=True, slots=True)
class RuntimeStageMachine:
    stages: tuple[str, ...] = field(default_factory=lambda: GOVERNED_STAGES)

    def index_of(self, stage: str) -> int:
        normalized = str(stage).strip()
        if normalized not in self.stages:
            raise ValueError(f"unknown governed runtime stage: {stage}")
        return self.stages.index(normalized)

    def iter_from(self, stage: str) -> tuple[str, ...]:
        start = self.index_of(stage)
        return self.stages[start:]

    def iter_between(self, start: str, stop: str | None = None) -> tuple[str, ...]:
        start_index = self.index_of(start)
        if stop is None:
            stop_index = len(self.stages) - 1
        else:
            normalized_stop = str(stop).strip()
            if not normalized_stop:
                raise ValueError("requested stop stage cannot be empty")
            stop_index = self.index_of(normalized_stop)
        if stop_index < start_index:
            raise ValueError(f"requested stop stage {stop!r} cannot precede start stage {start!r}")
        return self.stages[start_index : stop_index + 1]

    def next_stage(self, stage: str) -> str | None:
        index = self.index_of(stage)
        if index + 1 >= len(self.stages):
            return None
        return self.stages[index + 1]


@dataclass(frozen=True, slots=True)
class RuntimeGovernanceProfile:
    mode: str
    governance_scope: str = "root_governed"
    freeze_before_requirement_doc: bool = True


def normalize_runtime_mode(mode: str | None) -> str:
    normalized = str(mode or "interactive_governed").strip() or "interactive_governed"
    if normalized != "interactive_governed":
        raise ValueError(f"unsupported runtime mode: {mode}")
    return "interactive_governed"


def choose_internal_grade(
    task_type: str,
    task: str | None = None,
    *,
    selected_skill: str | None = None,
) -> str:
    normalized = resolve_runtime_task_type(task_type, selected_skill=selected_skill)
    return suggest_internal_grade(normalized, task=task)


def build_governance_profile(mode: str | None, *, governance_scope: str = "root_governed") -> RuntimeGovernanceProfile:
    return RuntimeGovernanceProfile(
        mode=normalize_runtime_mode(mode),
        governance_scope=governance_scope or "root_governed",
    )


@dataclass(frozen=True, slots=True)
class KernelPlanningResult:
    task_card: TaskCard
    candidates: tuple[SkillCandidate, ...]
    work_plan: WorkPlan
    module_assignments: ModuleAssignments
    inferred_task_type: str
    preferred_skill: str | None
    resolved_task_type: str
    suggested_internal_grade: str
    suggested_stage_stop: str

    def model_dump(self) -> dict[str, object]:
        return {
            "task_card": self.task_card.model_dump(),
            "candidates": [candidate.model_dump() for candidate in self.candidates],
            "work_plan": self.work_plan.model_dump(),
            "module_assignments": self.module_assignments.model_dump(),
            "inferred_task_type": self.inferred_task_type,
            "preferred_skill": self.preferred_skill,
            "resolved_task_type": self.resolved_task_type,
            "suggested_internal_grade": self.suggested_internal_grade,
            "suggested_stage_stop": self.suggested_stage_stop,
        }


@dataclass(frozen=True, slots=True)
class RuntimeExecutionPlan:
    internal_grade: str
    stages: tuple[str, ...]
    completion_language_rule: str
    delivery_acceptance_required: bool
    requested_grade_floor: str | None = None
    requested_stage_stop: str | None = None
    effective_requested_stage_stop: str | None = None
    stage_stop_source: str | None = None
    kernel: dict[str, object] | None = None

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


GRADE_ORDER = {"M": 0, "L": 1, "XL": 2}


def _deliverable_support_tokens(deliverable: str) -> set[str]:
    tokens = tokens_from_text(deliverable, stem=True, stopwords=SKILL_MATCH_STOPWORDS)
    if "code" in tokens and "change" in tokens:
        tokens.update({"fix", "debug", "bug", "implement", "implementation"})
    return tokens


def _expanded_candidate_tokens(tokens: tuple[str, ...]) -> set[str]:
    return expand_tokens(tokens)


def _owner_overlap_tokens(candidate: SkillCandidate, deliverable_tokens: set[str]) -> tuple[str, ...]:
    overlap = deliverable_tokens & _expanded_candidate_tokens(candidate.owner_tokens)
    return tuple(sorted(overlap))


def _candidate_supports_deliverable(candidate: SkillCandidate, deliverable_tokens: set[str]) -> bool:
    if not deliverable_tokens:
        return True
    blocked_tokens = _expanded_candidate_tokens(candidate.blocked_tokens)
    if deliverable_tokens & blocked_tokens:
        return False
    candidate_tokens = _expanded_candidate_tokens(candidate.support_tokens)
    candidate_tokens.update(tokens_from_text(candidate.skill_id.replace("-", " "), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
    return bool(deliverable_tokens & candidate_tokens)


def _binding_reason(
    binding_profile: str,
    preferred_skill: str | None,
    fallback_skills: tuple[str, ...],
    *,
    owner_overlap_tokens: tuple[str, ...] = (),
) -> str:
    if binding_profile == "partial_helpers_only":
        return "No available skill claimed full ownership of this deliverable; listed alternatives are partial helpers only."
    if binding_profile == "no_matching_skill":
        return "No available skill matched this deliverable."
    if binding_profile == "declared_output_owner" and owner_overlap_tokens:
        return "Selected this skill because its declared outputs overlap the deliverable."
    if binding_profile == "general_support_owner" and fallback_skills:
        return "Selected one skill as the current owner and kept nearby supporting skills as alternatives."
    return "Selected the only supporting skill."


def _binding_profile(
    preferred_skill: str | None,
    fallback_skills: tuple[str, ...],
    *,
    owner_overlap_tokens: tuple[str, ...] = (),
) -> str:
    if preferred_skill is None:
        return "partial_helpers_only" if fallback_skills else "no_matching_skill"
    return "declared_output_owner" if owner_overlap_tokens else "general_support_owner"


def _ranked_selection_key(candidate: SkillCandidate, deliverable_tokens: set[str]) -> tuple[int, int, int, int, int, float, str]:
    return (
        candidate.source_priority,
        -len(_owner_overlap_tokens(candidate, deliverable_tokens)),
        -len(deliverable_tokens & tokens_from_text(candidate.skill_id.replace("-", " "), stem=True, stopwords=SKILL_MATCH_STOPWORDS)),
        -len(deliverable_tokens & set(candidate.search_tokens)),
        -candidate.score,
        candidate.source_order,
        candidate.skill_id,
    )


def _selected_skill_provenance(candidate: SkillCandidate | None) -> SkillProvenance | None:
    if candidate is None:
        return None
    return SkillProvenance(
        source_kind=candidate.source_kind,
        source_root=candidate.source_root,
        resolved_skill_file=candidate.resolved_skill_file,
        source_priority=candidate.source_priority,
        source_order=candidate.source_order,
        path_contract=candidate.path_contract,
        path_base=candidate.path_base,
    )


def _select_preferred_skill(
    deliverable: str,
    candidates: tuple[SkillCandidate, ...],
) -> tuple[str | None, tuple[str, ...], str, str, SkillProvenance | None]:
    if not candidates:
        profile = "no_matching_skill"
        return None, (), profile, _binding_reason(profile, None, ()), None

    deliverable_tokens = _deliverable_support_tokens(deliverable)
    ranked = sorted(candidates, key=lambda candidate: _ranked_selection_key(candidate, deliverable_tokens))
    supported = [candidate for candidate in ranked if _candidate_supports_deliverable(candidate, deliverable_tokens)]
    if not supported:
        fallback = tuple(candidate.skill_id for candidate in ranked)
        profile = _binding_profile(None, fallback)
        return None, fallback, profile, _binding_reason(profile, None, fallback), None
    selected_candidate = supported[0]
    preferred = selected_candidate.skill_id
    fallback = tuple(candidate.skill_id for candidate in ranked if candidate.skill_id != preferred)
    owner_overlap = _owner_overlap_tokens(selected_candidate, deliverable_tokens)
    profile = _binding_profile(preferred, fallback, owner_overlap_tokens=owner_overlap)
    return (
        preferred,
        fallback,
        profile,
        _binding_reason(
            profile,
            preferred,
            fallback,
            owner_overlap_tokens=owner_overlap,
        ),
        _selected_skill_provenance(selected_candidate),
    )


def _verification_for_deliverable(task_card: TaskCard, deliverable: str) -> tuple[str, ...]:
    deliverable_tokens = tokens_from_text(deliverable, stem=True, stopwords=SKILL_MATCH_STOPWORDS)
    selected = [f"{deliverable} exists"]
    for criterion in task_card.completion_criteria:
        criterion_tokens = tokens_from_text(criterion, stem=True, stopwords=SKILL_MATCH_STOPWORDS)
        if deliverable_tokens & criterion_tokens:
            selected.append(criterion)
    deduped = tuple(dict.fromkeys(selected))
    if len(deduped) == 1:
        for criterion in task_card.completion_criteria:
            lowered = criterion.lower()
            if "code" in deliverable_tokens and "change" in deliverable_tokens and "changed behavior" in lowered:
                selected.append(criterion)
            if "tests" in deliverable_tokens and "tests cover" in lowered:
                selected.append(criterion)
            if "verification" in deliverable_tokens and "evidence" in deliverable_tokens and "verification evidence" in lowered:
                selected.append(criterion)
        deduped = tuple(dict.fromkeys(selected))
    if len(deduped) == 1:
        deduped = tuple(dict.fromkeys([*selected, *task_card.completion_criteria]))
    return deduped


def build_work_plan(task_card: TaskCard, candidates: tuple[SkillCandidate, ...]) -> WorkPlan:
    deliverables = task_card.deliverables or (task_card.goal,)

    work_units: list[WorkUnit] = []
    for index, deliverable in enumerate(deliverables, start=1):
        unit_id = f"wu-{index}"
        preferred_skill, fallback_skills, binding_profile, binding_reason, selected_skill_provenance = _select_preferred_skill(
            deliverable,
            candidates,
        )
        verification = _verification_for_deliverable(task_card, deliverable) or ("confirm work is complete",)
        work_unit = WorkUnit(
            id=unit_id,
            goal=f"Produce {deliverable}",
            depends_on=((f"wu-{index - 1}",) if index > 1 else ()),
            preferred_skill=preferred_skill,
            binding_profile=binding_profile,
            binding_reason=binding_reason,
            fallback_skills=fallback_skills,
            expected_artifacts=(deliverable,),
            verification=verification,
            selected_skill_provenance=selected_skill_provenance,
        )
        work_units.append(work_unit)
    plan = WorkPlan(task_id=task_card.id, work_units=tuple(work_units))
    return plan


def build_kernel_plan(
    task_type: str | None = None,
    *,
    task: str | None = None,
    requested_entry_id: str | None = None,
) -> KernelPlanningResult:
    inferred_task_type = infer_task_type(task or task_type)
    seed_task_type = str(task_type).strip().lower() if task_type else inferred_task_type
    resolved_seed_task_type = resolve_runtime_task_type(
        seed_task_type,
        requested_entry_id=requested_entry_id,
    )
    task_card = build_task_card(
        prompt=str(task or task_type),
        context={"mode": resolved_seed_task_type},
    )
    candidates = find_skill_candidates(task_card, load_runtime_route_index())
    work_plan = build_work_plan(task_card, candidates)
    module_assignments = build_module_assignments(work_plan)
    first_unit = work_plan.work_units[0] if work_plan.work_units else None
    preferred_skill = first_unit.preferred_skill if first_unit else (candidates[0].skill_id if candidates else None)
    resolved_task_type = resolve_runtime_task_type(
        seed_task_type,
        requested_entry_id=requested_entry_id,
        selected_skill=preferred_skill,
    )
    suggested_internal_grade = suggest_internal_grade(resolved_task_type, task=task)
    suggested_stage_stop = suggest_stage_stop(requested_entry_id or preferred_skill)
    return KernelPlanningResult(
        task_card=task_card,
        candidates=candidates,
        work_plan=work_plan,
        module_assignments=module_assignments,
        inferred_task_type=inferred_task_type,
        preferred_skill=preferred_skill,
        resolved_task_type=resolved_task_type,
        suggested_internal_grade=suggested_internal_grade,
        suggested_stage_stop=suggested_stage_stop,
    )


def build_execution_plan(
    task_type: str | None = None,
    *,
    task: str | None = None,
    stage_machine: RuntimeStageMachine | None = None,
    stages: tuple[str, ...] | None = None,
    requested_grade_floor: str | None = None,
    requested_stage_stop: str | None = None,
    kernel_plan: KernelPlanningResult | None = None,
    stage_stop_decision: StageStopDecision | None = None,
) -> RuntimeExecutionPlan:
    if kernel_plan is None and task_type is None:
        raise ValueError("task_type is required when kernel_plan is not provided")
    resolved_kernel_plan = kernel_plan or build_kernel_plan(task_type, task=task)
    selected_grade = resolved_kernel_plan.suggested_internal_grade
    stage_stop = stage_stop_decision or resolve_stage_stop(
        requested_stage_stop,
        resolved_kernel_plan.suggested_stage_stop,
        default_source="kernel_suggested",
    )
    normalized_floor = str(requested_grade_floor).strip().upper() if requested_grade_floor else None
    if normalized_floor:
        if normalized_floor not in GRADE_ORDER:
            raise ValueError(f"unsupported requested grade floor: {requested_grade_floor}")
        if GRADE_ORDER[selected_grade] < GRADE_ORDER[normalized_floor]:
            selected_grade = normalized_floor
    resolved_stages = stages
    if resolved_stages is None:
        machine = stage_machine or RuntimeStageMachine()
        resolved_stages = machine.iter_between(machine.stages[0], stage_stop.effective_requested_stage_stop)
    return RuntimeExecutionPlan(
        internal_grade=selected_grade,
        stages=resolved_stages,
        completion_language_rule="verification_before_completion",
        delivery_acceptance_required=True,
        requested_grade_floor=normalized_floor,
        requested_stage_stop=stage_stop.requested_stage_stop,
        effective_requested_stage_stop=stage_stop.effective_requested_stage_stop,
        stage_stop_source=stage_stop.stage_stop_source,
        kernel=resolved_kernel_plan.model_dump(),
    )
