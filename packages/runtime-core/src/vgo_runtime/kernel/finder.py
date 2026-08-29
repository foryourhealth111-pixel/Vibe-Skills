from __future__ import annotations

from dataclasses import asdict, dataclass

from .task_card import TaskCard
from .text_tokens import SKILL_MATCH_STOPWORDS, tokens_from_text, tokens_from_values


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    skill_id: str
    score: float
    matched_tokens: tuple[str, ...]
    search_tokens: tuple[str, ...]
    owner_tokens: tuple[str, ...]
    support_tokens: tuple[str, ...]
    blocked_tokens: tuple[str, ...]
    reasons: tuple[str, ...]
    source_kind: str
    source_root: str
    resolved_source_root: str
    source_priority: int
    source_order: int
    resolved_root_dir: str
    resolved_skill_file: str
    path_contract: str
    path_base: str
    content_sha256: str = ""
    warnings: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    plan_hints: tuple[str, ...] = ()
    verify_hints: tuple[str, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return asdict(self)

def _required_str(raw_entry: dict[str, object], field_name: str) -> str:
    value = raw_entry.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"skill index entry must include string field '{field_name}'")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"skill index entry must include non-empty field '{field_name}'")
    return normalized


def _required_int(raw_entry: dict[str, object], field_name: str) -> int:
    value = raw_entry.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"skill index entry must include integer field '{field_name}'")
    return value


def _optional_strings(raw_entry: dict[str, object], field_name: str) -> tuple[str, ...]:
    values = raw_entry.get(field_name)
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(value for item in values if (value := str(item).strip()))


def _validated_source_metadata(raw_entry: dict[str, object]) -> dict[str, object]:
    return {
        "source_kind": _required_str(raw_entry, "source_kind"),
        "source_root": _required_str(raw_entry, "source_root"),
        "resolved_source_root": _required_str(raw_entry, "resolved_source_root"),
        "source_priority": _required_int(raw_entry, "source_priority"),
        "source_order": _required_int(raw_entry, "source_order"),
        "resolved_root_dir": _required_str(raw_entry, "resolved_root_dir"),
        "resolved_skill_file": _required_str(raw_entry, "resolved_skill_file"),
        "path_contract": _required_str(raw_entry, "path_contract"),
        "path_base": _required_str(raw_entry, "path_base"),
    }


def find_skill_candidates(task_card: TaskCard, index_payload: dict[str, object], *, limit: int = 8) -> tuple[SkillCandidate, ...]:
    query_tokens = tokens_from_text(
        " ".join(
            (
                task_card.goal,
                " ".join(task_card.deliverables),
                " ".join(task_card.constraints),
                " ".join(task_card.completion_criteria),
            )
        ),
        stem=True,
        stopwords=SKILL_MATCH_STOPWORDS,
    )
    candidates: list[SkillCandidate] = []
    for raw_entry in index_payload.get("skills", []):
        if not isinstance(raw_entry, dict):
            continue
        if not bool(raw_entry.get("enabled", False)):
            continue
        source_metadata = _validated_source_metadata(raw_entry)
        skill_id = str(raw_entry.get("id") or "").strip()
        if not skill_id:
            continue
        search_tokens = set()
        search_tokens.update(tokens_from_text(str(raw_entry.get("id") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
        search_tokens.update(tokens_from_text(str(raw_entry.get("name") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
        search_tokens.update(tokens_from_text(str(raw_entry.get("description") or ""), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
        search_tokens.update(tokens_from_values(raw_entry.get("when_to_use"), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
        search_tokens.update(tokens_from_values(raw_entry.get("tags"), stem=True, stopwords=SKILL_MATCH_STOPWORDS))
        owner_tokens = tokens_from_values(raw_entry.get("outputs"), stem=True, stopwords=SKILL_MATCH_STOPWORDS)
        inputs = _optional_strings(raw_entry, "inputs")
        outputs = _optional_strings(raw_entry, "outputs")
        plan_hints = _optional_strings(raw_entry, "plan_hints")
        verify_hints = _optional_strings(raw_entry, "verify_hints")
        support_tokens = set(search_tokens)
        support_tokens.update(owner_tokens)
        blocked_tokens = tokens_from_values(raw_entry.get("not_for"), stem=True, stopwords=SKILL_MATCH_STOPWORDS)
        matched = sorted(query_tokens & search_tokens)
        if not matched:
            continue
        not_for_overlap = sorted(query_tokens & blocked_tokens)
        priority = int(raw_entry.get("priority", 50))
        score = float(len(matched)) + (priority / 1000.0) - (0.25 * len(not_for_overlap))
        reasons = (f"matched tokens: {', '.join(matched)}",)
        warnings = (f"not_for overlap: {', '.join(not_for_overlap)}",) if not_for_overlap else ()
        candidates.append(
            SkillCandidate(
                skill_id=skill_id,
                score=score,
                matched_tokens=tuple(matched),
                search_tokens=tuple(sorted(search_tokens)),
                inputs=inputs,
                outputs=outputs,
                plan_hints=plan_hints,
                verify_hints=verify_hints,
                owner_tokens=tuple(sorted(owner_tokens)),
                support_tokens=tuple(sorted(support_tokens)),
                blocked_tokens=tuple(sorted(blocked_tokens)),
                reasons=reasons,
                warnings=warnings,
                source_kind=str(source_metadata["source_kind"]),
                source_root=str(source_metadata["source_root"]),
                resolved_source_root=str(source_metadata["resolved_source_root"]),
                source_priority=int(source_metadata["source_priority"]),
                source_order=int(source_metadata["source_order"]),
                resolved_root_dir=str(source_metadata["resolved_root_dir"]),
                resolved_skill_file=str(source_metadata["resolved_skill_file"]),
                path_contract=str(source_metadata["path_contract"]),
                path_base=str(source_metadata["path_base"]),
                content_sha256=str(raw_entry.get("content_sha256") or "").strip().lower(),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            candidate.source_priority,
            -candidate.score,
            candidate.source_order,
            candidate.skill_id,
        ),
    )
    return tuple(ranked[: max(limit, 0)])
